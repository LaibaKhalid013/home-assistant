"""
homeassistant.components.binary_sensor.zigbee

Contains functionality to use a ZigBee device as a binary sensor.
"""
from homeassistant.components.zigbee import (
    ZigBeeDigitalIn, ZigBeeDigitalInConfig)


DEPENDENCIES = ["zigbee"]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """
    Create and add an entity based on the configuration.
    """
    add_entities([
        ZigBeeDigitalIn(hass, ZigBeeDigitalInConfig(config))
    ])
