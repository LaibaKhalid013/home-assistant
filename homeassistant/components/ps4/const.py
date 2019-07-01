"""Constants for PlayStation 4."""
ATTR_MEDIA_IMAGE_URL = 'media_image_url'
DEFAULT_NAME = "PlayStation 4"
DEFAULT_REGION = "United States"
DEFAULT_ALIAS = 'Home-Assistant'
DEFAULT_URL = 'http://localhost'
DOMAIN = 'ps4'
GAMES_FILE = '.ps4-games.json'
PS4_DATA = 'ps4_data'

COMMANDS = (
    'up', 'down', 'right', 'left', 'enter', 'back', 'option', 'ps',)

# Deprecated used for logger/backwards compatibility from 0.89
REGIONS = ['R1', 'R2', 'R3', 'R4', 'R5']
