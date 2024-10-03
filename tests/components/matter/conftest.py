"""Provide common fixtures."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from matter_server.client.models.node import MatterNode
from matter_server.common.const import SCHEMA_VERSION
from matter_server.common.models import ServerInfoMessage
import pytest

from homeassistant.core import HomeAssistant

from .common import setup_integration_with_node_fixture

from tests.common import MockConfigEntry

MOCK_FABRIC_ID = 12341234
MOCK_COMPR_FABRIC_ID = 1234


@pytest.fixture(name="matter_client")
async def matter_client_fixture() -> AsyncGenerator[MagicMock]:
    """Fixture for a Matter client."""
    with patch(
        "homeassistant.components.matter.MatterClient", autospec=True
    ) as client_class:
        client = client_class.return_value

        async def connect() -> None:
            """Mock connect."""
            await asyncio.sleep(0)

        async def listen(init_ready: asyncio.Event | None) -> None:
            """Mock listen."""
            if init_ready is not None:
                init_ready.set()
            listen_block = asyncio.Event()
            await listen_block.wait()
            pytest.fail("Listen was not cancelled!")

        client.connect = AsyncMock(side_effect=connect)
        client.start_listening = AsyncMock(side_effect=listen)
        client.server_info = ServerInfoMessage(
            fabric_id=MOCK_FABRIC_ID,
            compressed_fabric_id=MOCK_COMPR_FABRIC_ID,
            schema_version=1,
            sdk_version="2022.11.1",
            wifi_credentials_set=True,
            thread_credentials_set=True,
            min_supported_schema_version=SCHEMA_VERSION,
            bluetooth_enabled=False,
        )

        yield client


@pytest.fixture(name="integration")
async def integration_fixture(
    hass: HomeAssistant, matter_client: MagicMock
) -> MockConfigEntry:
    """Set up the Matter integration."""
    entry = MockConfigEntry(domain="matter", data={"url": "ws://localhost:5580/ws"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    return entry


@pytest.fixture(
    params=[
        "door_lock",
        "smoke_detector",
        "air_purifier",
        "eve_energy_plug_patched",
        "eve_energy_plug",
    ]
)
async def matter_devices(
    hass: HomeAssistant, matter_client: MagicMock, request: pytest.FixtureRequest
) -> MatterNode:
    """Fixture for a Matter device."""
    return await setup_integration_with_node_fixture(hass, request.param, matter_client)


@pytest.fixture
def attributes() -> dict[str, Any]:
    """Return common attributes for all nodes."""
    return {}


@pytest.fixture
async def matter_node(
    hass: HomeAssistant,
    matter_client: MagicMock,
    node_fixture: str,
    attributes: dict[str, Any],
) -> MatterNode:
    """Fixture for a Matter node."""
    return await setup_integration_with_node_fixture(
        hass, node_fixture, matter_client, attributes
    )
