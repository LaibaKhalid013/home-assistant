"""
Jabber (XMPP) notification service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.xmpp/
"""
import logging
import mimetypes
import random
import string
import asyncio
from concurrent.futures import TimeoutError as FutTimeoutError

import requests
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.notify import (
    ATTR_TITLE, ATTR_TITLE_DEFAULT, PLATFORM_SCHEMA, BaseNotificationService)
from homeassistant.const import (
    CONF_PASSWORD, CONF_SENDER, CONF_RECIPIENT, CONF_ROOM, CONF_RESOURCE)

REQUIREMENTS = ['slixmpp==1.4.0']

DEFAULT_CONTENT_TYPE = 'application/octet-stream'

_LOGGER = logging.getLogger(__name__)

CONF_TLS = 'tls'
CONF_VERIFY = 'verify'

ATTR_DATA = 'data'
ATTR_PATH = 'path'
ATTR_URL = 'url'
ATTR_VERIFY = 'verify'
ATTR_TIMEOUT = 'timeout'
XEP_0363_TIMEOUT = 10

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SENDER): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_RECIPIENT): cv.string,
    vol.Optional(CONF_TLS, default=True): cv.boolean,
    vol.Optional(CONF_VERIFY, default=True): cv.boolean,
    vol.Optional(CONF_ROOM, default=''): cv.string,
    vol.Optional(CONF_RESOURCE, default="home-assistant"): cv.string,
})


async def async_get_service(hass, config, discovery_info=None):
    """Get the Jabber (XMPP) notification service."""
    return XmppNotificationService(
        config.get(CONF_SENDER), config.get(CONF_RESOURCE),
        config.get(CONF_PASSWORD), config.get(CONF_RECIPIENT),
        config.get(CONF_TLS), config.get(CONF_VERIFY),
        config.get(CONF_ROOM), hass)


class XmppNotificationService(BaseNotificationService):
    """Implement the notification service for Jabber (XMPP)."""

    def __init__(self, sender, resource, password,
                 recipient, tls, verify, room, hass):
        """Initialize the service."""
        self._hass = hass
        self._sender = sender
        self._resource = resource
        self._password = password
        self._recipient = recipient
        self._tls = tls
        self._verify = verify
        self._room = room

    async def async_send_message(self, message="", **kwargs):
        """Send a message to a user."""
        title = kwargs.get(ATTR_TITLE, ATTR_TITLE_DEFAULT)
        text = '{}: {}'.format(title, message) if title else message
        data = None or kwargs.get(ATTR_DATA)
        timeout = data.get(ATTR_TIMEOUT, XEP_0363_TIMEOUT) if data else None

        await async_send_message(
            '{}/{}'.format(self._sender, self._resource),
            self._password, self._recipient, self._tls,
            self._verify, self._room, self._hass, text,
            timeout, data)


async def async_send_message(sender, password, recipient, use_tls,
                             verify_certificate, room, hass, message,
                             timeout=None, data=None):
    """Send a message over XMPP."""
    import slixmpp
    from slixmpp.exceptions import IqError, IqTimeout, XMPPError
    from slixmpp.plugins.xep_0363.http_upload import FileTooBig, \
        FileUploadError, UploadServiceNotFound

    class SendNotificationBot(slixmpp.ClientXMPP):
        """Service for sending Jabber (XMPP) messages."""

        def __init__(self):
            """Initialize the Jabber Bot."""
            super().__init__(sender, password)

            # need hass.loop!!
            self.loop = hass.loop

            self.force_starttls = use_tls
            self.use_ipv6 = False
            self.add_event_handler(
                'failed_auth', self.disconnect_on_login_fail)
            self.add_event_handler('session_start', self.start)

            if room:
                self.register_plugin('xep_0045')  # MUC
            if not verify_certificate:
                self.add_event_handler('ssl_invalid_cert',
                                       self.discard_ssl_invalid_cert)
            if data:
                # init XEPs for image sending
                self.register_plugin('xep_0030')  # OOB dep
                self.register_plugin('xep_0066')  # Out of Band Data
                self.register_plugin('xep_0071')  # XHTML IM
                self.register_plugin('xep_0128')  # Service Discovery
                self.register_plugin('xep_0363')  # HTTP upload

            self.connect(force_starttls=self.force_starttls, use_ssl=False)

        async def start(self, event):
            """Start the communication and sends the message."""
            # sending image and message independently from each other
            if data:
                await self.send_image(timeout=timeout)
            if message:
                self.send_text_message()

            self.disconnect(wait=True)

        async def send_image(self, timeout=XEP_0363_TIMEOUT):
            """Send image via XMPP.

            Send XMPP image message using OOB (XEP_0066) and
            HTTP Upload (XEP_0363)
            """
            if room:
                # self.plugin['xep_0045'].join_muc(room, sender, wait=True)
                # message = self.Message(sto=room, stype='groupchat')
                _LOGGER.warning("sorry, sending files to rooms is"
                                " currently not supported")
                return

            try:
                # uploading with XEP_0363
                _LOGGER.debug("timeout set to %ss", timeout)
                url = await self.upload_file(timeout=timeout)
                if url is None:
                    raise FileUploadError("could not upload file")
            except (IqError, IqTimeout, XMPPError) as ex:
                _LOGGER.error("upload error, could not send message %s", ex)
            except FileTooBig as ex:
                _LOGGER.error("File too big for server, "
                              "could not upload file %s", ex)
            except UploadServiceNotFound as ex:
                _LOGGER.error("UploadServiceNotFound: "
                              " could not upload file %s", ex)
            except FileUploadError as ex:
                _LOGGER.error("FileUploadError, could not upload file %s", ex)
            except requests.exceptions.SSLError as ex:
                _LOGGER.error("cannot establish SSL connection %s", ex)
            except requests.exceptions.ConnectionError as ex:
                _LOGGER.error("cannot connect to server %s", ex)
            except (FileNotFoundError,
                    PermissionError,
                    IsADirectoryError,
                    TimeoutError) as ex:
                _LOGGER.error("Error reading file %s", ex)
            except FutTimeoutError as ex:
                _LOGGER.error("the server did not respond in time, %s", ex)
            else:
                _LOGGER.info("Upload success")
                _LOGGER.info('Sending file to %s', recipient)
                message = self.Message(sto=recipient, stype='chat')
                message['body'] = url
                # pylint: disable=invalid-sequence-index
                message['oob']['url'] = url
                _LOGGER.debug("sending image message to %s", recipient)
                try:
                    message.send()
                except (IqError, IqTimeout, XMPPError) as ex:
                    _LOGGER.error("could not send image message %s", ex)

        async def upload_file(self, timeout=None):
            """Upload file to Jabber server and return new URL.

            upload a file with Jabber XEP_0363 from a remote URL or a local
            file path and return a URL of that file.
            """
            if data.get(ATTR_URL):
                url = await self.upload_file_from_url(data.get(ATTR_URL),
                                                      timeout=timeout)
            elif data.get(ATTR_PATH):
                url = await self.upload_file_from_path(data.get(ATTR_PATH),
                                                       timeout=timeout)
            else:
                _LOGGER.error("no path or URL found for image")

            _LOGGER.info('Upload success!')
            return url

        async def upload_file_from_url(self, url, timeout=None):
            """Upload a file from a URL. Returns a URL.

            uploaded via XEP_0363 and HTTPand returns the resulting URL
            """
            # send a file from an URL
            _LOGGER.info('getting file from %s', url)

            def get_url(url):
                return requests.get(url,
                                    verify=data.get(ATTR_VERIFY, True),
                                    timeout=timeout,
                                    )
            result = await hass.async_add_executor_job(get_url, url)

            if result.status_code >= 400:
                _LOGGER.error("could not load file from %s", url)
                return

            filesize = len(result.content)
            # we need a file extension, the upload server needs a
            # filename, if none is provided, through the path
            # we guess the extension
            if not data.get(ATTR_PATH):
                extension = mimetypes.guess_extension(
                    result.headers['Content-Type']) or ".unknown"
                # extension = self.get_extension(
                #     result.headers['Content-Type']) or ".unknown"
                _LOGGER.debug("got %s extension", extension)
                filename = self.get_random_filename(extension)
            else:
                filename = self.get_random_filename(data.get(ATTR_PATH))

            _LOGGER.info('Uploading file from URL, %s', filename)

            # would be call if timeout worked with upload_file
            # url = await self['xep_0363'].upload_file(
            #     filename,
            #     size=filesize,
            #     input_file=result.content,
            #     content_type=result.headers['Content-Type'],
            #     timeout=timeout,
            #     )

            # current workaround for non-working timeout in slixmpp:
            try:
                url = await asyncio.wait_for(self['xep_0363'].upload_file(
                    filename,
                    size=filesize,
                    input_file=result.content,
                    content_type=result.headers['Content-Type'],
                    timeout=timeout,
                    ),
                                             timeout,
                                             loop=self.loop)
            except (IqError, IqTimeout, XMPPError) as ex:
                _LOGGER.error("could not upload file to server %s", ex)
                raise

            return url

        async def upload_file_from_path(self, path, timeout=None):
            """Upload a file from a local file path via XEP_0363."""
            # send message from local path
            _LOGGER.info('Uploading file from path, %s ...', path)

            with open(path, 'rb') as upfile:
                _LOGGER.debug("reading file %s", path)
                input_file = upfile.read()
            filesize = len(input_file)
            _LOGGER.debug("filesize is %s bytes", filesize)

            content_type = mimetypes.guess_type(path)[0]
            if content_type is None:
                content_type = DEFAULT_CONTENT_TYPE
            _LOGGER.debug("content_type is %s", content_type)
            # set random filename for privacy
            filename = self.get_random_filename(data.get(ATTR_PATH))
            _LOGGER.debug("uploading file with random filename %s", filename)
            # would be call if timeout worked with upload_file
            # url = await self['xep_0363'].upload_file(filename,
            #                                      timeout=timeout)

            try:
                url = await asyncio.wait_for(self['xep_0363'].upload_file(
                    filename,
                    size=filesize,
                    input_file=input_file,
                    content_type=content_type,
                    timeout=timeout,
                    ),
                                             timeout,
                                             loop=self.loop)
            except (IqError, IqTimeout, XMPPError) as ex:
                _LOGGER.error("could not upload file to server %s", ex)
                raise

            # current workaround for non-working timeout in slixmpp:
            # url = await asyncio.wait_for(self['xep_0363'].upload_file(
            #     filename,
            #     timeout=timeout,
            #     ),
            #                              timeout,
            #                              loop=self.loop)
            return url

        def send_text_message(self):
            """Send a text only message to a room or a recipient."""
            try:
                if room:
                    _LOGGER.debug("Joining room %s", room)
                    self.plugin['xep_0045'].join_muc(room, sender, wait=True)
                    self.send_message(mto=room,
                                      mbody=message,
                                      mtype='groupchat',
                                      )
                else:
                    _LOGGER.debug("sending message to %s", recipient)
                    self.send_message(mto=recipient,
                                      mbody=message,
                                      mtype='chat',
                                      )
            except (IqError, IqTimeout, XMPPError) as ex:
                _LOGGER.error("could not send text message %s", ex)

        # pylint: disable=no-self-use
        def get_random_filename(self, filename):
            """Return a random filename, leaving the extension intact."""
            if '.' in filename:
                extension = filename.split('.')[-1]
            else:
                extension = "txt"
            return ''.join(random.choice(string.ascii_letters)
                           for i in range(10)) + '.' + extension

        def disconnect_on_login_fail(self, event):
            """Disconnect from the server if credentials are invalid."""
            _LOGGER.warning('Login failed')
            self.disconnect()

        @staticmethod
        def discard_ssl_invalid_cert(event):
            """Do nothing if ssl certificate is invalid."""
            _LOGGER.info('Ignoring invalid ssl certificate as requested')

    SendNotificationBot()
