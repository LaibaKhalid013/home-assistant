"""
Support for Modbus.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/modbus/
"""
import logging
import threading
import time
import os

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.config import load_yaml_config_file
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP,
    CONF_HOST, CONF_METHOD, CONF_PORT, CONF_TYPE,
    CONF_TIMEOUT, ATTR_STATE)

DOMAIN = 'modbus'

REQUIREMENTS = ['pymodbus==1.3.1']

# Type of network
CONF_BAUDRATE = 'baudrate'
CONF_BYTESIZE = 'bytesize'
CONF_STOPBITS = 'stopbits'
CONF_PARITY = 'parity'

CONF_DELAY_BETWEEN_QUERIES = 'delay_between_queries'
CONF_DELAY_BEFORE_TX = 'delay_before_tx'
CONF_DELAY_BEFORE_RX = 'delay_before_rx'
CONF_RTS_LEVEL_FOR_TX = 'rts_level_for_tx'
CONF_RTS_LEVEL_FOR_RX = 'rts_level_for_rx'

ATTR_RTU = 'rtu'
ATTR_ASCII = 'ascii'
ATTR_SERIAL = 'serial'
ATTR_RS485 = 'rs485'
ATTR_TCP = 'tcp'
ATTR_UDP = 'udp'

SERIAL_SCHEMA = {
    vol.Required(CONF_BAUDRATE): cv.positive_int,
    vol.Required(CONF_BYTESIZE): vol.Any(5, 6, 7, 8),
    vol.Required(CONF_METHOD): vol.Any(ATTR_RTU, ATTR_ASCII),
    vol.Required(CONF_PORT): cv.string,
    vol.Required(CONF_PARITY): vol.Any('E', 'O', 'N'),
    vol.Required(CONF_STOPBITS): vol.Any(1, 2),
    vol.Required(CONF_TYPE): ATTR_SERIAL,
    vol.Optional(CONF_TIMEOUT, default=3): cv.socket_timeout,
    vol.Optional(CONF_DELAY_BETWEEN_QUERIES, default=0):
        cv.socket_timeout,
}

RS485_SCHEMA = {
    vol.Required(CONF_BAUDRATE): cv.positive_int,
    vol.Required(CONF_BYTESIZE): vol.Any(5, 6, 7, 8),
    vol.Required(CONF_METHOD): vol.Any(ATTR_RTU, ATTR_ASCII),
    vol.Required(CONF_PORT): cv.string,
    vol.Required(CONF_PARITY): vol.Any('E', 'O', 'N'),
    vol.Required(CONF_STOPBITS): vol.Any(1, 2),
    vol.Required(CONF_TYPE): ATTR_RS485,
    vol.Optional(CONF_TIMEOUT, default=3): cv.socket_timeout,
    vol.Optional(CONF_DELAY_BEFORE_TX, default=0): cv.socket_timeout,
    vol.Optional(CONF_DELAY_BEFORE_RX, default=0): cv.socket_timeout,
    vol.Optional(CONF_RTS_LEVEL_FOR_TX, default=1): cv.boolean,
    vol.Optional(CONF_RTS_LEVEL_FOR_RX, default=0): cv.boolean,
    vol.Optional(CONF_DELAY_BETWEEN_QUERIES, default=0):
        cv.socket_timeout,
}

ETHERNET_SCHEMA = {
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT): cv.positive_int,
    vol.Required(CONF_TYPE): vol.Any('tcp', 'udp'),
    vol.Optional(CONF_TIMEOUT, default=3): cv.socket_timeout,
    vol.Optional(CONF_DELAY_BETWEEN_QUERIES, default=0):
        cv.socket_timeout,
}


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Any(SERIAL_SCHEMA, RS485_SCHEMA, ETHERNET_SCHEMA)
}, extra=vol.ALLOW_EXTRA)


_LOGGER = logging.getLogger(__name__)

SERVICE_WRITE_REGISTER = 'write_register'
SERVICE_WRITE_COIL = 'write_coil'

ATTR_ADDRESS = 'address'
ATTR_UNIT = 'unit'
ATTR_VALUE = 'value'

SERVICE_WRITE_REGISTER_SCHEMA = vol.Schema({
    vol.Required(ATTR_UNIT): cv.positive_int,
    vol.Required(ATTR_ADDRESS): cv.positive_int,
    vol.Required(ATTR_VALUE): vol.All(cv.ensure_list, [cv.positive_int])
})

SERVICE_WRITE_COIL_SCHEMA = vol.Schema({
    vol.Required(ATTR_UNIT): cv.positive_int,
    vol.Required(ATTR_ADDRESS): cv.positive_int,
    vol.Required(ATTR_STATE): cv.boolean
})

HUB = None


def setup(hass, config):
    """Set up Modbus component."""
    # Modbus connection type
    # pylint: disable=global-statement, import-error
    client_type = config[DOMAIN][CONF_TYPE]
    delay_between_queries = (
        config[DOMAIN][CONF_DELAY_BETWEEN_QUERIES] / 1000)
    rs485_mode = False

    # Connect to Modbus network
    # pylint: disable=global-statement, import-error

    if client_type in [ATTR_SERIAL, ATTR_RS485]:
        from pymodbus.client.sync import ModbusSerialClient as ModbusClient
        client = ModbusClient(method=config[DOMAIN][CONF_METHOD],
                              port=config[DOMAIN][CONF_PORT],
                              baudrate=config[DOMAIN][CONF_BAUDRATE],
                              stopbits=config[DOMAIN][CONF_STOPBITS],
                              bytesize=config[DOMAIN][CONF_BYTESIZE],
                              parity=config[DOMAIN][CONF_PARITY],
                              timeout=config[DOMAIN][CONF_TIMEOUT])
        if client_type == ATTR_RS485:
            rs485_mode = {
                CONF_DELAY_BEFORE_TX: (
                    config[DOMAIN][CONF_DELAY_BEFORE_TX]),
                CONF_DELAY_BEFORE_RX: (
                    config[DOMAIN][CONF_DELAY_BEFORE_RX]),
                CONF_RTS_LEVEL_FOR_TX: (
                    config[DOMAIN][CONF_RTS_LEVEL_FOR_TX]),
                CONF_RTS_LEVEL_FOR_RX: (
                    config[DOMAIN][CONF_RTS_LEVEL_FOR_RX])}

    elif client_type == ATTR_TCP:
        from pymodbus.client.sync import ModbusTcpClient as ModbusClient
        client = ModbusClient(host=config[DOMAIN][CONF_HOST],
                              port=config[DOMAIN][CONF_PORT],
                              timeout=config[DOMAIN][CONF_TIMEOUT])
    elif client_type == ATTR_UDP:
        from pymodbus.client.sync import ModbusUdpClient as ModbusClient
        client = ModbusClient(host=config[DOMAIN][CONF_HOST],
                              port=config[DOMAIN][CONF_PORT],
                              timeout=config[DOMAIN][CONF_TIMEOUT])
    else:
        return False

    global HUB
    HUB = ModbusHub(client, rs485_mode, delay_between_queries)

    def stop_modbus(event):
        """Stop Modbus service."""
        HUB.close()

    def start_modbus(event):
        """Start Modbus service."""
        HUB.connect()
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_modbus)

        descriptions = load_yaml_config_file(os.path.join(
            os.path.dirname(__file__), 'services.yaml')).get(DOMAIN)

        # Register services for modbus
        hass.services.register(
            DOMAIN, SERVICE_WRITE_REGISTER, write_register,
            descriptions.get(SERVICE_WRITE_REGISTER),
            schema=SERVICE_WRITE_REGISTER_SCHEMA)
        hass.services.register(
            DOMAIN, SERVICE_WRITE_COIL, write_coil,
            descriptions.get(SERVICE_WRITE_COIL),
            schema=SERVICE_WRITE_COIL_SCHEMA)

    def write_register(service):
        """Write modbus registers."""
        unit = int(float(service.data.get(ATTR_UNIT)))
        address = int(float(service.data.get(ATTR_ADDRESS)))
        value = service.data.get(ATTR_VALUE)
        if isinstance(value, list):
            HUB.write_registers(
                unit,
                address,
                [int(float(i)) for i in value])
        else:
            HUB.write_register(
                unit,
                address,
                int(float(value)))

    def write_coil(service):
        """Write modbus coil."""
        unit = service.data.get(ATTR_UNIT)
        address = service.data.get(ATTR_ADDRESS)
        state = service.data.get(ATTR_STATE)
        HUB.write_coil(unit, address, state)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_modbus)

    return True


class ModbusHub(object):
    """Thread safe wrapper class for pymodbus."""

    def __init__(self, modbus_client, rs485_mode=False,
                 delay_between_queries=0):
        """Initialize the modbus hub."""
        self._client = modbus_client
        self._lock = threading.Lock()
        self._rs485_mode = rs485_mode
        self._delay_between_queries = delay_between_queries

    def close(self):
        """Disconnect client."""
        with self._lock:
            self._client.close()

    def connect(self):
        """Connect client."""
        with self._lock:
            self._client.connect()
            if isinstance(self._rs485_mode, dict):
                from serial.rs485 import RS485Settings
                rs485_mode = RS485Settings(
                    delay_before_tx=(
                        self._rs485_mode[CONF_DELAY_BEFORE_TX]),
                    delay_before_rx=(
                        self._rs485_mode[CONF_DELAY_BEFORE_RX]),
                    rts_level_for_tx=(
                        self._rs485_mode[CONF_RTS_LEVEL_FOR_TX]),
                    rts_level_for_rx=(
                        self._rs485_mode[CONF_RTS_LEVEL_FOR_RX]),
                    loopback=False)
                self._client.socket.rs485_mode = rs485_mode

    def read_coils(self, unit, address, count):
        """Read coils."""
        with self._lock:
            time.sleep(self._delay_between_queries)
            kwargs = {'unit': unit} if unit else {}
            return self._client.read_coils(
                address,
                count,
                **kwargs)

    def read_input_registers(self, unit, address, count):
        """Read input registers."""
        with self._lock:
            time.sleep(self._delay_between_queries)
            kwargs = {'unit': unit} if unit else {}
            return self._client.read_input_registers(
                address,
                count,
                **kwargs)

    def read_holding_registers(self, unit, address, count):
        """Read holding registers."""
        with self._lock:
            time.sleep(self._delay_between_queries)
            kwargs = {'unit': unit} if unit else {}
            return self._client.read_holding_registers(
                address,
                count,
                **kwargs)

    def write_coil(self, unit, address, value):
        """Write coil."""
        with self._lock:
            time.sleep(self._delay_between_queries)
            kwargs = {'unit': unit} if unit else {}
            self._client.write_coil(
                address,
                value,
                **kwargs)

    def write_register(self, unit, address, value):
        """Write register."""
        with self._lock:
            time.sleep(self._delay_between_queries)
            kwargs = {'unit': unit} if unit else {}
            self._client.write_register(
                address,
                value,
                **kwargs)

    def write_registers(self, unit, address, values):
        """Write registers."""
        with self._lock:
            time.sleep(self._delay_between_queries)
            kwargs = {'unit': unit} if unit else {}
            self._client.write_registers(
                address,
                values,
                **kwargs)
