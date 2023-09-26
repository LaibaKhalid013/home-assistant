"""application_credentials platform the fitbit integration.

See https://dev.fitbit.com/build/reference/web-api/authorization/ for additional
details on Fitbit authorization.
"""

import base64
import logging
from typing import Any, cast

from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import OAUTH2_AUTHORIZE, OAUTH2_TOKEN

_LOGGER = logging.getLogger(__name__)


class FitbitOAuth2Implementation(AuthImplementation):
    """Local OAuth2 implementation for Fitbit.

    This implementation is needed to send the client id and secret as a Basic
    Authorization header.
    """

    async def async_resolve_external_data(self, external_data: dict[str, Any]) -> dict:
        """Resolve the authorization code to tokens."""
        session = async_get_clientsession(self.hass)
        data = {
            "grant_type": "authorization_code",
            "code": external_data["code"],
            "redirect_uri": external_data["state"]["redirect_uri"],
        }
        resp = await session.post(self.token_url, data=data, headers=self._headers)
        resp.raise_for_status()
        return cast(dict, await resp.json())

    async def _token_request(self, data: dict) -> dict:
        """Make a token request."""
        session = async_get_clientsession(self.hass)

        data["client_id"] = self.client_id
        if self.client_secret is not None:
            data["client_secret"] = self.client_secret

        resp = await session.post(self.token_url, data=data, headers=self._headers)
        resp.raise_for_status()
        return cast(dict, await resp.json())

    @property
    def _headers(self) -> dict[str, str]:
        """Build necessary authorization headers."""
        basic_auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        return {"Authorization": f"Basic {basic_auth}"}


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return a custom auth implementation."""
    return FitbitOAuth2Implementation(
        hass,
        auth_domain,
        credential,
        AuthorizationServer(
            authorize_url=OAUTH2_AUTHORIZE,
            token_url=OAUTH2_TOKEN,
        ),
    )
