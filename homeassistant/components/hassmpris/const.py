"""Constants for the MPRIS media playback remote control integration."""

import logging

from homeassistant.const import CONF_HOST as _CONF_HOST

LOGGER = logging.getLogger(__package__)

DOMAIN = "hassmpris"
ENTRY_CLIENT = "client"
ENTRY_ENTITY_MANAGER = "entity_manager"
ENTRY_PLAYERS = "players"

CONF_HOST = _CONF_HOST
CONF_CAKES_PORT = "cakes_port"
CONF_CLIENT_CERT = "client_cert"
CONF_CLIENT_KEY = "client_key"
CONF_MPRIS_PORT = "mpris_port"
CONF_UNIQUE_ID = "unique_id"
CONF_TRUST_CHAIN = "trust_chain"

DEF_CAKES_PORT = 40052
DEF_HOST = "localhost"
DEF_MPRIS_PORT = 40051

STEP_CONFIRM = "confirm"
STEP_REAUTH_CONFIRM = "reauth_confirm"
STEP_USER = "user"
STEP_ZEROCONF_CONFIRM = "zeroconf_confirm"

ATTR_PLAYBACK_RATE = "playback_rate"
