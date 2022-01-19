"""Constants for the yolink integration."""

DOMAIN = "yolink"
HOME_ID = "homeId"
HOME_SUBSCRIPTION = "home_subscription"

# TODO Update with your own urls
# OAUTH2_AUTHORIZE = "https://api.yosmart.com/oauth/v2/authorization.htm"
# OAUTH2_TOKEN = "https://api.yosmart.com/oauth/v2/getAccessToken.api"


YOLINK_HOST = "http://192.168.1.135:1088"
OAUTH2_AUTHORIZE = f"{YOLINK_HOST}/oauth/v2/authorization.htm"
OAUTH2_TOKEN = f"{YOLINK_HOST}/open/yolink/token"

YOLINK_API_GATE = f"{YOLINK_HOST}/open/yolink/v2/api"
YOLINK_API_MQTT_BROKER = "192.168.1.135"
YOLINK_API_MQTT_BROKER_POER = 8003


class YoLinkError(Exception):
    """Base class for YoLink errors."""


class YoLinkAPIError(YoLinkError):
    """Errors during access YoLink API.

    code: Error Code
    desc: Desc or Error
    """

    def __init__(
        self,
        code: str,
        desc: str,
    ) -> None:
        """Initialize the yolink api error."""

        self.code = code
        self.message = desc
