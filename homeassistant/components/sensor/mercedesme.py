"""
Support for Mercedes cars with Mercedes ME.
"""
import logging
import datetime

from homeassistant.helpers.entity import Entity

DEPENDENCIES = ['mercedesme']

DOMAIN = 'mercedesme'

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    if discovery_info is None:
        return

    controller = hass.data[DOMAIN]['controller']

    if not controller.cars:
        return False

    for car in controller.cars:
        add_devices([Sensor('fuelLevelPercent', car, controller)])
        add_devices([Sensor('fuelRangeKm', car, controller)])
        add_devices([Sensor('serviceIntervalDays', car, controller)])
        add_devices([Sensor('odometerKm', car, controller)])
        add_devices([Sensor('doorsClosed', car, controller)])
        add_devices([Sensor('windowsClosed', car, controller)])
        add_devices([Sensor('locked', car, controller)])
        add_devices([Sensor('tireWarningLight', car, controller)])
        add_devices([Sensor('latestTrip', car, controller)])

    return True

class Sensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, SensorName, Car, Controller):
        """Initialize the sensor."""
        self._state = None
        self.__name = SensorName
        self.__car = Car
        self.controller = Controller
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.__name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self.__name == "windowsClosed":
            return {
                "windowStatusFrontLeft": self.__car["windowStatusFrontLeft"],
                "windowStatusFrontRight": self.__car["windowStatusFrontRight"],
                "windowStatusRearLeft": self.__car["windowStatusRearLeft"],
                "windowStatusRearRight": self.__car["windowStatusRearRight"],
                "lastUpdate": datetime.datetime.fromtimestamp(
                    self.__car["lastUpdate"]).strftime('%Y-%m-%d %H:%M:%S'),
                "car" : self.__car["license"]
            }
        elif self.__name == "tireWarningLight":
            return {
                "frontRightTirePressureKpa": self.__car["frontRightTirePressureKpa"],
                "frontLeftTirePressureKpa": self.__car["frontLeftTirePressureKpa"],
                "rearRightTirePressureKpa": self.__car["rearRightTirePressureKpa"],
                "rearLeftTirePressureKpa": self.__car["rearLeftTirePressureKpa"],
                "lastUpdate": datetime.datetime.fromtimestamp(
                    self.__car["lastUpdate"]).strftime('%Y-%m-%d %H:%M:%S'),
                "car" : self.__car["license"]
            }
        elif self.__name == "latestTrip":
            return {
                "durationSeconds": self.__car["latestTrip"]["durationSeconds"],
                "distanceTraveledKm": self.__car["latestTrip"]["distanceTraveledKm"],
                "startedAt": datetime.datetime.fromtimestamp(
                    self.__car["latestTrip"]["startedAt"]).strftime('%Y-%m-%d %H:%M:%S'),
                "averageSpeedKmPerHr": self.__car["latestTrip"]["averageSpeedKmPerHr"],
                "finished": self.__car["latestTrip"]["finished"],
                "lastUpdate": datetime.datetime.fromtimestamp(
                    self.__car["lastUpdate"]).strftime('%Y-%m-%d %H:%M:%S'),
                "car" : self.__car["license"]
            }

        return {
            "lastUpdate": datetime.datetime.fromtimestamp(
                self.__car["lastUpdate"]).strftime('%Y-%m-%d %H:%M:%S'),
            "car" : self.__car["license"]
        }

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self.controller.update()

        if self.__name == "latestTrip":
            self._state = self.__car["latestTrip"]["id"]
        elif self.__name == "tireWarningLight":
            if self.__car[self.__name] == "INACTIVE":
                self._state = "Off"
            else:
                self._state = "On"
        else:
            self._state = self.__car[self.__name]
