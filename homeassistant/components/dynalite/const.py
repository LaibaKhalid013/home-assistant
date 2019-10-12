"""Constants for the Dynalite component."""
import logging

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite"


CONF_BRIDGES = "bridges"
CONF_AREACREATE = "areacreate"
CONF_AREA_CREATE_MANUAL = "manual"
CONF_AREA_CREATE_ASSIGN = "assign"
CONF_AREA_CREATE_AUTO = "auto"

DATA_CONFIGS = "dynalite_configs"
ENTITY_CATEGORIES = ["light", "switch", "cover"]

DEFAULT_NAME = "dynalite"
DEFAULT_PORT = 12345
DEFAULT_LOGGING = "info"
