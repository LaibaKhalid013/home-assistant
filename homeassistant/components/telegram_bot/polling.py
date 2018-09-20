"""
Telegram bot polling implementation.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/telegram_bot.polling/
"""
import asyncio
import logging

from homeassistant.components.telegram_bot import (
    initialize_bot,
    CONF_ALLOWED_CHAT_IDS, BaseTelegramBotEntity,
    PLATFORM_SCHEMA as TELEGRAM_PLATFORM_SCHEMA)
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = TELEGRAM_PLATFORM_SCHEMA

@asyncio.coroutine
def async_setup_platform(hass, config):
    """Set up the Telegram polling platform."""
    bot = initialize_bot(config)
    pol = TelegramPoll(bot, hass, config[CONF_ALLOWED_CHAT_IDS])

    @callback
    def _start_bot(_event):
        """Start the bot."""
        pol.start_polling()

    @callback
    def _stop_bot(_event):
        """Stop the bot."""
        pol.stop_polling()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _start_bot)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_bot)

    return True

@callback
def process_error(bot, update, error):
    """Telegram bot error handler."""
    from telegram.error import (TelegramError, TimedOut, NetworkError, RetryAfter)

    try:
        raise error
    except (TimedOut, NetworkError, RetryAfter):
        # Long polling timeout or connection problem. Nothing serious.
        pass
    except TelegramError:
        _LOGGER.error('Update "%s" caused error "%s"', update, error)

def message_handler(cb):
    """Creates messages handler."""
    from telegram import Update
    from telegram.ext import Handler

    class MessageHandler(Handler):
        """Telegram bot message handler"""

        def __init__(self):
            """Initialize the messages handler instance."""
            super(MessageHandler, self).__init__(cb)

        def check_update(self, update):
            """Check is update valid."""
            return isinstance(update, Update)

        def handle_update(self, update, dispatcher):
            """Handle update."""
            optional_args = self.collect_optional_args(dispatcher, update)
            return self.callback(dispatcher.bot, update, **optional_args)

    return MessageHandler()


class TelegramPoll(BaseTelegramBotEntity):
    """Asyncio telegram incoming message handler."""

    def __init__(self, bot, hass, allowed_chat_ids):
        """Initialize the polling instance."""
        from telegram.ext import Updater

        BaseTelegramBotEntity.__init__(self, hass, allowed_chat_ids)

        self.updater = Updater(bot=bot, workers=4)
        self.dispatcher = self.updater.dispatcher

        self.dispatcher.add_handler(message_handler(self.process_update))
        self.dispatcher.add_error_handler(process_error)

    def start_polling(self):
        """Start the polling task."""
        self.updater.start_polling()

    def stop_polling(self):
        """Stop the polling task."""
        self.updater.stop()

    def process_update(self, bot, update):
        """Process incoming message."""
        self.process_message(update.to_dict())