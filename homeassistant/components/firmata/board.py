"""Code to handle a Firmata board."""
import logging

from pymata_express.pymata_express import PymataExpress

from homeassistant.const import CONF_NAME

from .const import (
    CONF_ARDUINO_INSTANCE_ID,
    CONF_ARDUINO_WAIT,
    CONF_BINARY_SENSORS,
    CONF_SAMPLING_INTERVAL,
    CONF_SERIAL_BAUD_RATE,
    CONF_SERIAL_PORT,
    CONF_SLEEP_TUNE,
    CONF_SWITCHES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class FirmataBoard:
    """Manages a single Firmata board."""

    def __init__(self, hass, config_entry):
        """Initialize the board."""
        self.config_entry = config_entry
        self.config = self.config_entry.data
        self.hass = hass
        self.available = True
        self.api = None
        self.firmware_version = None
        self.protocol_version = None
        self.name = self.config[CONF_NAME]
        self.switches = []
        self.binary_sensors = []
        self.used_pins = []
        self.board_info = {
            "connections": {},
            "identifiers": {(DOMAIN, self.name)},
            "manufacturer": "Firmata",
            "name": self.name,
        }

    async def async_setup(self, tries=0):
        """Set up a Firmata instance."""
        try:
            _LOGGER.info("Connecting to Firmata %s", self.name)
            self.api = await get_board(self.config)
            self.firmware_version = await self.api.get_firmware_version()
            self.board_info["sw_version"] = self.firmware_version
        except RuntimeError as err:
            _LOGGER.error("Error connecting to PyMata board %s: %s", self.name, err)
            return False

        if CONF_SAMPLING_INTERVAL in self.config:
            try:
                await self.api.set_sampling_interval(
                    self.config[CONF_SAMPLING_INTERVAL]
                )
            except RuntimeError as err:
                _LOGGER.error(
                    "Error setting sampling interval for PyMata \
board %s: %s",
                    self.name,
                    err,
                )
                return False

        if CONF_SWITCHES in self.config:
            self.switches = self.config[CONF_SWITCHES]
        if CONF_BINARY_SENSORS in self.config:
            self.binary_sensors = self.config[CONF_BINARY_SENSORS]

        _LOGGER.info("Firmata connection successful for %s", self.name)
        return True

    async def async_reset(self):
        """Reset the board to default state."""
        _LOGGER.debug("Shutting down board %s", self.name)
        # If the board was never setup, continue.
        if self.api is None:
            return True

        await self.api.shutdown()
        self.api = None

        return True

    async def async_update_device_registry(self):
        """Update board registry."""
        device_registry = await self.hass.helpers.device_registry.async_get_registry()
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id, **self.board_info
        )

    def mark_pin_used(self, pin):
        """Test if a pin is used already on the board or mark as used."""
        if pin in self.used_pins:
            return False
        self.used_pins.append(pin)
        return True

    def get_pin_type(self, pin):
        """Return the type and Firmata location of a pin on the board."""
        if isinstance(pin, str):
            pin_type = "analog"
            firmata_pin = int(pin[1:])
            firmata_pin += self.api.first_analog_pin
        else:
            pin_type = "digital"
            firmata_pin = pin
        return (pin_type, firmata_pin)


async def get_board(data: dict):
    """Create a Pymata board object."""
    board_data = {}

    if CONF_SERIAL_PORT in data:
        board_data["com_port"] = data[CONF_SERIAL_PORT]
    if CONF_SERIAL_BAUD_RATE in data:
        board_data["baud_rate"] = data[CONF_SERIAL_BAUD_RATE]
    if CONF_ARDUINO_INSTANCE_ID in data:
        board_data["arduino_instance_id"] = data[CONF_ARDUINO_INSTANCE_ID]

    if CONF_ARDUINO_WAIT in data:
        board_data["arduino_wait"] = data[CONF_ARDUINO_WAIT]
    if CONF_SLEEP_TUNE in data:
        board_data["sleep_tune"] = data[CONF_SLEEP_TUNE]

    board_data["autostart"] = False
    board_data["shutdown_on_exception"] = True
    board_data["close_loop_on_shutdown"] = False

    board = PymataExpress(**board_data)

    await board.start_aio()
    return board
