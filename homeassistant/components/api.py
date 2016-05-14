"""
Rest API for Home Assistant.

For more details about the RESTful API, please refer to the documentation at
https://home-assistant.io/developers/api/
"""
import json
import logging

import homeassistant.core as ha
import homeassistant.remote as rem
from homeassistant.bootstrap import ERROR_LOG_FILENAME
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP, EVENT_TIME_CHANGED,
    HTTP_BAD_REQUEST, HTTP_CREATED, HTTP_NOT_FOUND,
    HTTP_UNPROCESSABLE_ENTITY, MATCH_ALL, URL_API, URL_API_COMPONENTS,
    URL_API_CONFIG, URL_API_DISCOVERY_INFO, URL_API_ERROR_LOG,
    URL_API_EVENT_FORWARD, URL_API_EVENTS, URL_API_LOG_OUT, URL_API_SERVICES,
    URL_API_STATES, URL_API_STATES_ENTITY, URL_API_STREAM, URL_API_TEMPLATE,
    __version__)
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.state import TrackStates
from homeassistant.helpers import template
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.components.http import HomeAssistantView

DOMAIN = 'api'
DEPENDENCIES = ['http']

STREAM_PING_PAYLOAD = "ping"
STREAM_PING_INTERVAL = 50  # seconds

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    """Register the API with the HTTP interface."""
    hass.wsgi.register_view(APIStatusView)
    hass.wsgi.register_view(APIEventStream)
    hass.wsgi.register_view(APIConfigView)
    hass.wsgi.register_view(APIDiscoveryView)
    hass.wsgi.register_view(APIStatesView)
    hass.wsgi.register_view(APIEntityStateView)
    hass.wsgi.register_view(APIEventListenersView)
    hass.wsgi.register_view(APIEventView)
    hass.wsgi.register_view(APIServicesView)
    hass.wsgi.register_view(APIDomainServicesView)
    hass.wsgi.register_view(APIEventForwardingView)
    hass.wsgi.register_view(APIComponentsView)
    hass.wsgi.register_view(APIErrorLogView)
    hass.wsgi.register_view(APILogOutView)
    hass.wsgi.register_view(APITemplateView)

    return True


class APIStatusView(HomeAssistantView):
    """View to handle Status requests."""

    url = URL_API
    name = "api:status"

    def get(self, request):
        """Retrieve if API is running."""
        return self.json_message('API running.')


class APIEventStream(HomeAssistantView):
    """View to handle EventSt requests."""

    url = URL_API_STREAM
    name = "api:stream"

    def get(self, request):
        """Provide a streaming interface for the event bus."""
        import eventlet
        from eventlet import queue as eventlet_queue
        import queue as thread_queue
        from threading import Event
        from time import time

        to_write = thread_queue.Queue()
        # to_write = eventlet.Queue()
        stop_obj = object()
        hass = self.hass
        connection_closed = Event()

        restrict = request.args.get('restrict')
        if restrict:
            restrict = restrict.split(',')

        restrict = False

        def ping(now):
            """Add a ping message to queue."""
            print(id(stop_obj), 'ping')
            to_write.put(STREAM_PING_PAYLOAD)

        def forward_events(event):
            """Forward events to the open request."""
            print(id(stop_obj), 'forwarding', event)
            if event.event_type == EVENT_TIME_CHANGED:
                pass
            elif event.event_type == EVENT_HOMEASSISTANT_STOP:
                to_write.put(stop_obj)
            else:
                to_write.put(json.dumps(event, cls=rem.JSONEncoder))

        def stream():
            """Stream events to response."""
            if restrict:
                for event_type in restrict:
                    hass.bus.listen(event_type, forward_events)
            else:
                hass.bus.listen(MATCH_ALL, forward_events)

            attached_ping = track_utc_time_change(
                hass, ping, second=(0, 30))

            print(id(stop_obj), 'attached goodness')

            while not connection_closed.is_set():
                try:
                    print(id(stop_obj), "Try getting obj")
                    payload = to_write.get(False)

                    if payload is stop_obj:
                        break

                    msg = "data: {}\n\n".format(payload)
                    print(id(stop_obj), msg)
                    yield msg.encode("UTF-8")
                except eventlet_queue.Empty:
                    print(id(stop_obj), "queue empty, sleep 0.5")
                    eventlet.sleep(.5)
                except GeneratorExit:
                    pass

            print(id(stop_obj), "cleaning up")

            hass.bus.remove_listener(EVENT_TIME_CHANGED, attached_ping)

            if restrict:
                for event in restrict:
                    hass.bus.remove_listener(event, forward_events)
            else:
                hass.bus.remove_listener(MATCH_ALL, forward_events)

        resp = self.Response(stream(), mimetype='text/event-stream')

        def closing():
            print()
            print()
            print()
            print()
            print()
            print()
            print()
            print()
            print(id(stop_obj), "CLOSING RESPONSE")
            print()
            print()
            print()
            print()
            print()
            print()
            print()
            connection_closed.set()

        resp.call_on_close(closing)
        return resp


class APIConfigView(HomeAssistantView):
    """View to handle Config requests."""

    url = URL_API_CONFIG
    name = "api:config"

    def get(self, request):
        """Get current configuration."""
        return self.json(self.hass.config.as_dict())


class APIDiscoveryView(HomeAssistantView):
    """View to provide discovery info."""

    requires_auth = False
    url = URL_API_DISCOVERY_INFO
    name = "api:discovery"

    def get(self, request):
        """Get discovery info."""
        needs_auth = self.hass.config.api.api_password is not None
        return self.json({
            'base_url': self.hass.config.api.base_url,
            'location_name': self.hass.config.location_name,
            'requires_api_password': needs_auth,
            'version': __version__
        })


class APIStatesView(HomeAssistantView):
    """View to handle States requests."""

    url = URL_API_STATES
    name = "api:states"

    def get(self, request):
        """Get current states."""
        return self.json(self.hass.states.all())


class APIEntityStateView(HomeAssistantView):
    """View to handle EntityState requests."""

    url = "/api/states/<entity_id>"
    name = "api:entity-state"

    def get(self, request, entity_id):
        """Retrieve state of entity."""
        state = self.hass.states.get(entity_id)
        if state:
            return self.json(state)
        else:
            return self.json_message('Entity not found', HTTP_NOT_FOUND)

    def post(self, request, entity_id):
        """Update state of entity."""
        try:
            new_state = request.json['state']
        except KeyError:
            return self.json_message('No state specified', HTTP_BAD_REQUEST)

        attributes = request.json.get('attributes')

        is_new_state = self.hass.states.get(entity_id) is None

        # Write state
        self.hass.states.set(entity_id, new_state, attributes)

        # Read the state back for our response
        resp = self.json(self.hass.states.get(entity_id))

        if is_new_state:
            resp.status_code = HTTP_CREATED

        resp.headers.add('Location', URL_API_STATES_ENTITY.format(entity_id))

        return resp

    def delete(self, request, entity_id):
        """Remove entity."""
        if self.hass.states.remove(entity_id):
            return self.json_message('Entity removed')
        else:
            return self.json_message('Entity not found', HTTP_NOT_FOUND)


class APIEventListenersView(HomeAssistantView):
    """View to handle EventListeners requests."""

    url = URL_API_EVENTS
    name = "api:event-listeners"

    def get(self, request):
        """Get event listeners."""
        return self.json(events_json(self.hass))


class APIEventView(HomeAssistantView):
    """View to handle Event requests."""

    url = '/api/events/<event_type>'
    name = "api:event"

    def post(self, request, event_type):
        """Fire events."""
        event_data = request.json

        if event_data is not None and not isinstance(event_data, dict):
            return self.json_message('Event data should be a JSON object',
                                     HTTP_BAD_REQUEST)

        # Special case handling for event STATE_CHANGED
        # We will try to convert state dicts back to State objects
        if event_type == ha.EVENT_STATE_CHANGED and event_data:
            for key in ('old_state', 'new_state'):
                state = ha.State.from_dict(event_data.get(key))

                if state:
                    event_data[key] = state

        self.hass.bus.fire(event_type, event_data, ha.EventOrigin.remote)

        return self.json_message("Event {} fired.".format(event_type))


class APIServicesView(HomeAssistantView):
    """View to handle Services requests."""

    url = URL_API_SERVICES
    name = "api:services"

    def get(self, request):
        """Get registered services."""
        return self.json(services_json(self.hass))


class APIDomainServicesView(HomeAssistantView):
    """View to handle DomainServices requests."""

    url = "/api/services/<domain>/<service>"
    name = "api:domain-services"

    def post(self, request, domain, service):
        """Call a service.

        Returns a list of changed states.
        """
        with TrackStates(self.hass) as changed_states:
            self.hass.services.call(domain, service, request.json, True)

        return self.json(changed_states)


class APIEventForwardingView(HomeAssistantView):
    """View to handle EventForwarding requests."""

    url = URL_API_EVENT_FORWARD
    name = "api:event-forward"
    event_forwarder = None

    def post(self, request):
        """Setup an event forwarder."""
        data = request.json
        if data is None:
            return self.json_message("No data received.", HTTP_BAD_REQUEST)
        try:
            host = data['host']
            api_password = data['api_password']
        except KeyError:
            return self.json_message("No host or api_password received.",
                                     HTTP_BAD_REQUEST)

        try:
            port = int(data['port']) if 'port' in data else None
        except ValueError:
            return self.json_message("Invalid value received for port.",
                                     HTTP_UNPROCESSABLE_ENTITY)

        api = rem.API(host, api_password, port)

        if not api.validate_api():
            return self.json_message("Unable to validate API.",
                                     HTTP_UNPROCESSABLE_ENTITY)

        if self.event_forwarder is None:
            self.event_forwarder = rem.EventForwarder(self.hass)

        self.event_forwarder.connect(api)

        return self.json_message("Event forwarding setup.")

    def delete(self, request):
        """Remove event forwarer."""
        data = request.json
        if data is None:
            return self.json_message("No data received.", HTTP_BAD_REQUEST)

        try:
            host = data['host']
        except KeyError:
            return self.json_message("No host received.", HTTP_BAD_REQUEST)

        try:
            port = int(data['port']) if 'port' in data else None
        except ValueError:
            return self.json_message("Invalid value received for port.",
                                     HTTP_UNPROCESSABLE_ENTITY)

        if self.event_forwarder is not None:
            api = rem.API(host, None, port)

            self.event_forwarder.disconnect(api)

        return self.json_message("Event forwarding cancelled.")


class APIComponentsView(HomeAssistantView):
    """View to handle Components requests."""

    url = URL_API_COMPONENTS
    name = "api:components"

    def get(self, request):
        """Get current loaded components."""
        return self.json(self.hass.config.components)


class APIErrorLogView(HomeAssistantView):
    """View to handle ErrorLog requests."""

    url = URL_API_ERROR_LOG
    name = "api:error-log"

    def get(self, request):
        """Serve error log."""
        return self.file(request, self.hass.config.path(ERROR_LOG_FILENAME))


class APILogOutView(HomeAssistantView):
    """View to handle Log Out requests."""

    url = URL_API_LOG_OUT
    name = "api:log-out"

    def post(self, request):
        """Handle log out."""
        # TODO kill session
        return {}


class APITemplateView(HomeAssistantView):
    """View to handle requests."""

    url = URL_API_TEMPLATE
    name = "api:template"

    def post(self, request):
        """Render a template."""
        try:
            return template.render(self.hass, request.json['template'],
                                   request.json.get('variables'))
        except TemplateError as ex:
            return self.json_message('Error rendering template: {}'.format(ex),
                                     HTTP_BAD_REQUEST)


def services_json(hass):
    """Generate services data to JSONify."""
    return [{"domain": key, "services": value}
            for key, value in hass.services.services.items()]


def events_json(hass):
    """Generate event data to JSONify."""
    return [{"event": key, "listener_count": value}
            for key, value in hass.bus.listeners.items()]
