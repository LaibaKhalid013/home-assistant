"""Provide common test tools."""
from __future__ import annotations

import asyncio
from functools import cache
import json
import logging
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

from matter_server.client import MatterClient
from matter_server.common.helpers.util import dataclass_from_dict
from matter_server.common.models.api_command import APICommand
from matter_server.common.models.node import MatterNode
from matter_server.common.models.server_information import ServerInfo
import pytest

from tests.common import MockConfigEntry, load_fixture

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

MOCK_FABRIC_ID = 12341234
MOCK_COMPR_FABRIC_ID = 1234


class MockClient(MatterClient):
    """Represent a mock Matter client."""

    mock_client_disconnect: asyncio.Event
    mock_commands: dict[type, Any] = {}
    mock_sent_commands: list[dict[str, Any]] = []

    def __init__(self) -> None:
        """Initialize the mock client."""
        super().__init__("mock-url", None)
        self.mock_commands: dict[type, Any] = {}
        self.mock_sent_commands = []
        self.server_info = ServerInfo(
            fabric_id=MOCK_FABRIC_ID,
            compressed_fabric_id=MOCK_COMPR_FABRIC_ID,
            schema_version=1,
            sdk_version="2022.11.1",
            wifi_credentials_set=True,
            thread_credentials_set=True,
        )

    async def connect(self) -> None:
        """Connect to the Matter server."""
        self.server_info = Mock(compressed_abric_d=MOCK_COMPR_FABRIC_ID)

    async def start_listening(self, init_ready: asyncio.Event) -> None:
        """Listen for events."""
        init_ready.set()
        self.mock_client_disconnect = asyncio.Event()
        await self.mock_client_disconnect.wait()

    def mock_command(self, command_type: str, response: Any) -> None:
        """Mock a command."""
        self.mock_commands[command_type] = response

    async def send_command(
        self, command: str, require_schema: int | None = None, **kwargs
    ) -> dict:
        """Send mock commands."""

        if command == APICommand.DEVICE_COMMAND and (
            (cmd_type := kwargs["payload"]["_type"]) in self.mock_commands
        ):
            self.mock_sent_commands.append(kwargs)
            return self.mock_commands[cmd_type]

        return await super().send_command(command, require_schema, **kwargs)

    async def send_command_no_wait(
        self, command: str, require_schema: int | None = None, **kwargs
    ) -> None:
        """Send a command without waiting for the response."""
        if command == APICommand.DEVICE_COMMAND and (
            (cmd_type := kwargs["payload"]["_type"]) in self.mock_commands
        ):
            self.mock_sent_commands.append(kwargs)
            return self.mock_commands[cmd_type]

        return await super().send_command_no_wait(command, require_schema, **kwargs)


@pytest.fixture
async def mock_matter() -> Mock:
    """Mock matter fixture."""
    return await get_mock_matter()


async def get_mock_matter() -> Mock:
    """Get mock MatterAdapter."""
    return Mock(
        adapter=Mock(logger=logging.getLogger("mock_matter")),
        matter_client=MockClient(),
    )


@cache
def load_node_fixture(fixture: str) -> str:
    """Load a fixture."""
    return load_fixture(f"matter/nodes/{fixture}.json")


def load_and_parse_node_fixture(fixture: str) -> dict[str, Any]:
    """Load and parse a node fixture."""
    return json.loads(load_node_fixture(fixture))


async def setup_integration_with_node_fixture(
    hass: HomeAssistant, node_fixture: str
) -> MatterNode:
    """Set up Matter integration with fixture as node."""
    node_data = load_and_parse_node_fixture(node_fixture)
    node = dataclass_from_dict(
        MatterNode,
        node_data,
    )
    config_entry = MockConfigEntry(
        domain="matter", data={"url": "http://mock-matter-server-url"}
    )
    config_entry.add_to_hass(hass)

    mock_matter = MockClient()

    with patch(
        "matter_server.client.MatterClient.get_nodes", return_value=[node]
    ), patch("matter_server.client.MatterClient", return_value=mock_matter):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    # set the (mocked) matter client object on the nod eobject to easy access it from the tests
    node.matter = mock_matter
    return node
