"""Test shopping list todo platform."""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from homeassistant.core import HomeAssistant

from tests.typing import WebSocketGenerator

TEST_ENTITY = "todo.shopping_list"


@pytest.fixture
def ws_req_id() -> Callable[[], int]:
    """Fixture for incremental websocket requests."""

    id = 0

    def next() -> int:
        nonlocal id
        id += 1
        return id

    return next


@pytest.fixture
async def ws_get_items(
    hass_ws_client: WebSocketGenerator, ws_req_id: Callable[[], int]
) -> Callable[[], Awaitable[dict[str, str]]]:
    """Fixture to fetch items from the todo websocket."""

    async def get() -> list[dict[str, str]]:
        # Fetch items using To-do platform
        client = await hass_ws_client()
        id = ws_req_id()
        await client.send_json(
            {
                "id": id,
                "type": "todo/item/list",
                "entity_id": TEST_ENTITY,
            }
        )
        resp = await client.receive_json()
        assert resp.get("id") == id
        assert resp.get("success")
        return resp.get("result", {}).get("items", [])

    return get


@pytest.fixture
async def ws_move_item(
    hass_ws_client: WebSocketGenerator,
    ws_req_id: Callable[[], int],
) -> Callable[[str, str | None], Awaitable[None]]:
    """Fixture to move an item in the todo list."""

    async def move(uid: str, previous: str | None) -> dict[str, Any]:
        # Fetch items using To-do platform
        client = await hass_ws_client()
        id = ws_req_id()
        data = {
            "id": id,
            "type": "todo/item/move",
            "entity_id": TEST_ENTITY,
            "uid": uid,
        }
        if previous is not None:
            data["previous"] = previous
        await client.send_json(data)
        resp = await client.receive_json()
        assert resp.get("id") == id
        return resp

    return move


async def test_get_items(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
) -> None:
    """Test creating a shopping list item with the WS API and verifying with To-do API."""
    client = await hass_ws_client(hass)

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "0"

    # Native shopping list websocket
    await client.send_json(
        {"id": ws_req_id(), "type": "shopping_list/items/add", "name": "soda"}
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    data = msg["result"]
    assert data["name"] == "soda"
    assert data["complete"] is False

    # Fetch items using To-do platform
    items = await ws_get_items()
    assert len(items) == 1
    assert items[0]["summary"] == "soda"
    assert items[0]["status"] == "NEEDS-ACTION"

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "1"


async def test_create_item(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
) -> None:
    """Test creating shopping_list item and listing it."""
    client = await hass_ws_client(hass)

    # Native shopping list websocket
    await client.send_json(
        {"id": ws_req_id(), "type": "shopping_list/items/add", "name": "soda"}
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    data = msg["result"]
    assert data["name"] == "soda"
    assert data["complete"] is False

    # Fetch items using To-do platform
    items = await ws_get_items()
    assert len(items) == 1
    assert items[0]["summary"] == "soda"
    assert items[0]["status"] == "NEEDS-ACTION"

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "1"


async def test_delete_item(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
) -> None:
    """Test deleting a todo item."""
    client = await hass_ws_client(hass)

    await client.send_json(
        {
            "id": ws_req_id(),
            "type": "todo/item/create",
            "entity_id": TEST_ENTITY,
            "item": {
                "summary": "soda",
            },
        }
    )
    resp = await client.receive_json()
    assert resp.get("success")

    items = await ws_get_items()
    assert len(items) == 1
    assert items[0]["summary"] == "soda"
    assert items[0]["status"] == "NEEDS-ACTION"
    assert "uid" in items[0]

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "1"

    await client.send_json(
        {
            "id": ws_req_id(),
            "type": "todo/item/delete",
            "entity_id": TEST_ENTITY,
            "uids": [items[0]["uid"]],
        }
    )
    resp = await client.receive_json()
    assert resp.get("success")

    items = await ws_get_items()
    assert len(items) == 0

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "0"


async def test_bulk_delete(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
) -> None:
    """Test deleting a todo item."""
    client = await hass_ws_client(hass)

    for _i in range(0, 5):
        await client.send_json(
            {
                "id": ws_req_id(),
                "type": "todo/item/create",
                "entity_id": TEST_ENTITY,
                "item": {
                    "summary": "soda",
                },
            }
        )
        resp = await client.receive_json()
        assert resp.get("success")

    items = await ws_get_items()
    assert len(items) == 5
    uids = [item["uid"] for item in items]

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "5"

    await client.send_json(
        {
            "id": ws_req_id(),
            "type": "todo/item/delete",
            "entity_id": TEST_ENTITY,
            "uids": uids,
        }
    )
    resp = await client.receive_json()
    assert resp.get("success")

    items = await ws_get_items()
    assert len(items) == 0

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "0"


async def test_update_item(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
) -> None:
    """Test updating a todo item."""
    client = await hass_ws_client(hass)

    # Create new item
    await client.send_json(
        {
            "id": 5,
            "type": "todo/item/create",
            "entity_id": TEST_ENTITY,
            "item": {
                "summary": "soda",
            },
        }
    )
    resp = await client.receive_json()
    assert resp.get("id") == 5
    assert resp.get("success")

    # Fetch item
    items = await ws_get_items()
    assert len(items) == 1
    item = items[0]
    assert item["summary"] == "soda"
    assert item["status"] == "NEEDS-ACTION"

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "1"

    # Mark item completed
    item["status"] = "COMPLETED"
    await client.send_json(
        {
            "id": 7,
            "type": "todo/item/update",
            "entity_id": TEST_ENTITY,
            "item": item,
        }
    )
    resp = await client.receive_json()
    assert resp.get("id") == 7
    assert resp.get("success")

    # Verify item is marked as completed
    items = await ws_get_items()
    assert len(items) == 1
    item = items[0]
    assert item["summary"] == "soda"
    assert item["status"] == "COMPLETED"

    state = hass.states.get(TEST_ENTITY)
    assert state
    assert state.state == "0"


async def test_update_invalid_item(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
) -> None:
    """Test updating a todo item that does not exist."""
    client = await hass_ws_client(hass)

    await client.send_json(
        {
            "id": 7,
            "type": "todo/item/update",
            "entity_id": TEST_ENTITY,
            "item": {
                "uid": "invalid-uid",
                "summary": "Example task",
            },
        }
    )
    resp = await client.receive_json()
    assert resp.get("id") == 7
    assert not resp.get("success")
    assert resp.get("error")
    assert resp.get("error", {}).get("code") == "failed"
    assert "was not found" in resp.get("error", {}).get("message")


@pytest.mark.parametrize(
    ("src_idx", "dst_idx", "expected_items"),
    [
        # Move any item to the front of the list
        (0, None, ["item 1", "item 2", "item 3", "item 4"]),
        (1, None, ["item 2", "item 1", "item 3", "item 4"]),
        (2, None, ["item 3", "item 1", "item 2", "item 4"]),
        (3, None, ["item 4", "item 1", "item 2", "item 3"]),
        # Move items right
        (0, 1, ["item 2", "item 1", "item 3", "item 4"]),
        (0, 2, ["item 2", "item 3", "item 1", "item 4"]),
        (0, 3, ["item 2", "item 3", "item 4", "item 1"]),
        (1, 2, ["item 1", "item 3", "item 2", "item 4"]),
        (1, 3, ["item 1", "item 3", "item 4", "item 2"]),
        # Move items left
        (2, 0, ["item 1", "item 3", "item 2", "item 4"]),
        (3, 0, ["item 1", "item 4", "item 2", "item 3"]),
        (3, 1, ["item 1", "item 2", "item 4", "item 3"]),
        # No-ops
        (0, 0, ["item 1", "item 2", "item 3", "item 4"]),
        (2, 1, ["item 1", "item 2", "item 3", "item 4"]),
        (2, 2, ["item 1", "item 2", "item 3", "item 4"]),
        (3, 2, ["item 1", "item 2", "item 3", "item 4"]),
        (3, 3, ["item 1", "item 2", "item 3", "item 4"]),
    ],
)
async def test_move_item(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
    ws_move_item: Callable[[str, str | None], Awaitable[dict[str, Any]]],
    src_idx: int,
    dst_idx: int | None,
    expected_items: list[str],
) -> None:
    """Test moving a todo item within the list."""
    client = await hass_ws_client(hass)

    for i in range(1, 5):
        await client.send_json(
            {
                "id": ws_req_id(),
                "type": "todo/item/create",
                "entity_id": TEST_ENTITY,
                "item": {
                    "summary": f"item {i}",
                },
            }
        )
        resp = await client.receive_json()
        assert resp.get("success")

    items = await ws_get_items()
    assert len(items) == 4
    uids = [item["uid"] for item in items]
    summaries = [item["summary"] for item in items]
    assert summaries == ["item 1", "item 2", "item 3", "item 4"]

    # Prepare items for moving
    uid = uids[src_idx]
    previous = None
    if dst_idx is not None:
        previous = uids[dst_idx]

    resp = await ws_move_item(uid, previous)
    assert resp.get("success")

    items = await ws_get_items()
    assert len(items) == 4
    summaries = [item["summary"] for item in items]
    assert summaries == expected_items


async def test_move_invalid_item(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    sl_setup: None,
    ws_req_id: Callable[[], int],
    ws_get_items: Callable[[], Awaitable[dict[str, str]]],
    ws_move_item: Callable[[str, str | None], Awaitable[dict[str, Any]]],
) -> None:
    """Test moving a todo item within the list."""
    client = await hass_ws_client(hass)

    await client.send_json(
        {
            "id": ws_req_id(),
            "type": "todo/item/create",
            "entity_id": TEST_ENTITY,
            "item": {"summary": "soda"},
        }
    )
    resp = await client.receive_json()
    assert resp.get("success")

    items = await ws_get_items()
    assert len(items) == 1
    item = items[0]
    assert item["summary"] == "soda"
    uid = item["uid"]

    resp = await ws_move_item(uid, "unknown")
    assert not resp.get("success")
    assert resp.get("error", {}).get("code") == "failed"
    assert "could not be re-ordered" in resp.get("error", {}).get("message")

    resp = await ws_move_item("unknown", uid)
    assert not resp.get("success")
    assert resp.get("error", {}).get("code") == "failed"
    assert "could not be re-ordered" in resp.get("error", {}).get("message")
