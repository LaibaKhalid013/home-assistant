"""
Support for UK Met Office weather service.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.metoffice/
"""
import logging

import voluptuous as vol
import datapoint as dp

from homeassistant.components.weather import WeatherEntity, PLATFORM_SCHEMA
from homeassistant.const import \
    CONF_NAME, TEMP_CELSIUS, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers import config_validation as cv
# Reuse data and API logic from the sensor implementation
from homeassistant.components.sensor.metoffice import \
    MetOfficeCurrentData, CONF_MO_API_KEY, CONF_ATTRIBUTION

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_MO_API_KEY): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Met Office weather platform."""
    datapoint = dp.connection(api_key=config.get(CONF_MO_API_KEY))

    if None in (hass.config.latitude, hass.config.longitude):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")
        return False

    site = datapoint.get_nearest_site(longitude=hass.config.longitude,
                                      latitude=hass.config.latitude)

    if not site:
        _LOGGER.error("Unable to get nearest Met Office forecast site")
        return False
    else:
        # Get data
        data = MetOfficeCurrentData(hass, datapoint, site)
        try:
            data.update()
        except ValueError as err:
            _LOGGER.error("Received error from Met Office Datapoint: %s", err)
            return False
        add_devices([MetOfficeWeather(site, data, config.get(CONF_NAME))], True)
        return True


class MetOfficeWeather(WeatherEntity):
    """Implementation of a Met Office weather condition."""

    def __init__(self, site, data, config):
        """Initialise the platform with a data instance and site."""
        self.data = data
        self.site = site

    def update(self):
        """Update current conditions."""
        self.data.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Met Office ({})'.format(self.site.name)

    @property
    def condition(self):
        """Return the current condition."""
        return self.data.data.weather.text

    # Now implement the WeatherEntity interface

    @property
    def temperature(self):
        """Return the platform temperature."""
        return self.data.data.temperature.value

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def pressure(self):
        """Return the mean sea-level pressure."""
        return False

    @property
    def humidity(self):
        """Return the relative humidity."""
        return self.data.data.humidity.value

    @property
    def wind_speed(self):
        """Return the wind speed."""
        return self.data.data.wind_speed.value

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return self.data.data.wind_direction.value

    @property
    def attribution(self):
        """Return the attribution."""
        return CONF_ATTRIBUTION
