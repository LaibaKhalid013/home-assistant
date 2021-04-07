"""Constants for the BME280 component."""
from datetime import timedelta
from homeassistant.const import PERCENTAGE

# Common
DOMAIN = "bme280"
CONF_OVERSAMPLING_TEMP = "oversampling_temperature"
CONF_OVERSAMPLING_PRES = "oversampling_pressure"
CONF_OVERSAMPLING_HUM = "oversampling_humidity"
CONF_T_STANDBY = "time_standby"
CONF_FILTER_MODE = "filter_mode"
DEFAULT_NAME = "BME280 Sensor"
DEFAULT_OVERSAMPLING_TEMP = 1
DEFAULT_OVERSAMPLING_PRES = 1
DEFAULT_OVERSAMPLING_HUM = 1
DEFAULT_T_STANDBY = 5
DEFAULT_FILTER_MODE = 0
DEFAULT_SCAN_INTERVAL = 300
SENSOR_TEMP = "temperature"
SENSOR_HUMID = "humidity"
SENSOR_PRESS = "pressure"
SENSOR_TYPES = {
    SENSOR_TEMP: ["Temperature", None],
    SENSOR_HUMID: ["Humidity", PERCENTAGE],
    SENSOR_PRESS: ["Pressure", "mb"],
}
DEFAULT_MONITORED = [SENSOR_TEMP, SENSOR_HUMID, SENSOR_PRESS]
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)
# SPI
CONF_SPI_DEV = "spi_dev"
CONF_SPI_BUS = "spi_bus"
# I2C
CONF_I2C_ADDRESS = "i2c_address"
CONF_I2C_BUS = "i2c_bus"
CONF_DELTA_TEMP = "delta_temperature"
CONF_OPERATION_MODE = "operation_mode"
DEFAULT_OPERATION_MODE = 3  # Normal mode (forced mode: 2)
DEFAULT_I2C_ADDRESS = "0x76"
DEFAULT_I2C_BUS = 1
DEFAULT_DELTA_TEMP = 0.0
INTERFACE_SPI = "spi"
INTERFACE_I2C = "i2c"
