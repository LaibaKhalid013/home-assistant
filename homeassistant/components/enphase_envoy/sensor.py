"""Support for Enphase Envoy solar energy monitor."""
from datetime import timedelta
import json
import logging

from envoy_reader.envoy_reader import EnvoyReader
import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_MONITORED_CONDITIONS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    ENERGY_WATT_HOUR,
    POWER_WATT,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

MIN_SCAN_INTERVAL = timedelta(seconds=30)

SENSORS = {
    "production": ("Envoy Current Energy Production", POWER_WATT),
    "daily_production": ("Envoy Today's Energy Production", ENERGY_WATT_HOUR),
    "seven_days_production": (
        "Envoy Last Seven Days Energy Production",
        ENERGY_WATT_HOUR,
    ),
    "lifetime_production": ("Envoy Lifetime Energy Production", ENERGY_WATT_HOUR),
    "consumption": ("Envoy Current Energy Consumption", POWER_WATT),
    "daily_consumption": ("Envoy Today's Energy Consumption", ENERGY_WATT_HOUR),
    "seven_days_consumption": (
        "Envoy Last Seven Days Energy Consumption",
        ENERGY_WATT_HOUR,
    ),
    "lifetime_consumption": ("Envoy Lifetime Energy Consumption", ENERGY_WATT_HOUR),
    "inverters": ("Envoy Inverter", POWER_WATT),
}


ICON = "mdi:flash"
CONST_DEFAULT_HOST = "envoy"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_IP_ADDRESS, default=CONST_DEFAULT_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default="envoy"): cv.string,
        vol.Optional(CONF_PASSWORD, default=""): cv.string,
        vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSORS)): vol.All(
            cv.ensure_list, [vol.In(list(SENSORS))]
        ),
        vol.Optional(CONF_NAME, default=""): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Enphase Envoy sensor."""
    ip_address = config[CONF_IP_ADDRESS]
    monitored_conditions = config[CONF_MONITORED_CONDITIONS]
    name = config[CONF_NAME]
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]

    envoy_reader = EnvoyReader(ip_address, username, password)

    envoy_data = EnvoyData(envoy_reader)
    await envoy_data.update()

    entities = []
    # Iterate through the list of sensors
    for condition in monitored_conditions:
        if condition == "inverters":
            try:
                inverters = await envoy_reader.inverters_production()
            except requests.exceptions.HTTPError:
                _LOGGER.warning(
                    "Authentication for Inverter data failed during setup: %s",
                    ip_address,
                )
                continue

            if isinstance(inverters, dict):
                for inverter in inverters:
                    entities.append(
                        EnvoySensor(
                            envoy_data,
                            condition,
                            f"{name}{SENSORS[condition][0]} {inverter}",
                            SENSORS[condition][1],
                        )
                    )

        else:
            entities.append(
                EnvoySensor(
                    envoy_data,
                    condition,
                    f"{name}{SENSORS[condition][0]}",
                    SENSORS[condition][1],
                )
            )
    async_add_entities(entities)


class EnvoySensor(Entity):
    """Implementation of the Enphase Envoy sensors."""

    def __init__(self, envoy_data, sensor_type, name, unit):
        """Initialize the sensor."""
        self._envoy_data = envoy_data
        self._type = sensor_type
        self._name = name
        self._unit_of_measurement = unit
        self._state = None
        self._last_reported = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self._type == "inverters":
            return {"last_reported": self._last_reported}

        return None

    async def async_update(self):
        """Get the latest data from the Enphase Envoy device."""
        await self._envoy_data.update()
        self._state = self._envoy_data.get_state(self._type, self._name)


class EnvoyData:
    """Get the latest data from the Enphase Envoy device."""

    def __init__(self, envoy_reader):
        """Initialize the data object."""
        self._envoy_reader = envoy_reader
        self.data = {}

    @Throttle(MIN_SCAN_INTERVAL)
    async def update(self):
        """Get the latest data from the Enphase Envoy device."""
        # try:
        #    self.data = self._eagle_reader.update()
        #    _LOGGER.debug("API data: %s", self.data)
        # except (ConnectError, HTTPError, Timeout, ValueError) as error:
        #    _LOGGER.error("Unable to connect during update: %s", error)
        #    self.data = {}

        try:
            self.data = await self._envoy_reader.update()
            _LOGGER.error(self.data)
            # _LOGGER.warning(f"Data: {self._type} - {data.get(self._type)}")
        except (
            requests.exceptions.ConnectionError,
            json.decoder.JSONDecodeError,
            KeyError,
            IndexError,
            TypeError,
        ) as err:
            _LOGGER.warning("Exception: %s", err)

    def get_state(self, sensor_type, name):
        """Get the sensor value from the dictionary."""
        # state = self.data.get(sensor_type)

        state = ""
        if sensor_type != "inverters":

            # try:
            #    _state = await getattr(self._envoy_reader, self._type)()
            # except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError, KeyError, IndexError, RuntimeError) as e:
            #    _LOGGER.warning(e)
            #    return

            if isinstance(self.data.get(sensor_type), int):
                state = self.data.get(sensor_type)
                _LOGGER.warning("Type: %s State: %s", sensor_type, state)
            else:
                state = None

        elif sensor_type == "inverters":

            # try:
            #    inverters = await (self._envoy_reader.inverters_production())
            #    _LOGGER.warning(f"Got inverter data: {inverters}")
            # except requests.exceptions.HTTPError:
            #    _LOGGER.warning(
            #        "Authentication for Inverter data failed during update: %s",
            #        self._envoy_reader.host,
            #    )
            # except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError, KeyError, IndexError, RuntimeError) as e:
            #    _LOGGER.warning(e)

            if isinstance(self.data.get("inverters_production"), dict):
                serial_number = name.split(" ")[2]
                state = self.data.get("inverters_production").get(serial_number)[0]
                # self._state = inverters[serial_number][0]
                # self._last_reported = self.data.get("inverters_production").get(serial_number)[1]
                # self._last_reported = inverters[serial_number][1]
                # _LOGGER.warning(f"Inverter {data.get(self._type)} - {self._last_reported}: {self._state} W")
                _LOGGER.warning("Inv: %s Data: %s", serial_number, state)
            else:
                state = None

        _LOGGER.debug("Updating: %s - %s", sensor_type, state)
        return state
