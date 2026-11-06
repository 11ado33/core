"""Fixtures for inkVision tests."""

import asyncio
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pyinkvision import InkVisionConnectionError
import pytest
from pytest_homeassistant.common import MockConfigEntry, load_json_object_fixture

from homeassistant.components.inkvision.const import DOMAIN
from homeassistant.const import CONF_HOST

HOST = "192.168.1.174"
MAC = "58:8c:81:41:c6:10"


class FakeWebSocket:
    """A device WebSocket that yields the messages put into it."""

    def __init__(self) -> None:
        """Initialize the WebSocket."""
        self.messages: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    def push(self, message: dict[str, Any]) -> None:
        """Push a message from the device."""
        self.messages.put_nowait(message)

    def close(self) -> None:
        """Close the connection from the device side."""
        self.messages.put_nowait(None)

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        """Yield the pushed messages until the connection is closed."""
        while (message := await self.messages.get()) is not None:
            yield message
        raise InkVisionConnectionError("WebSocket closed by the device")


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.inkvision.async_setup_entry", return_value=None
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for an Atmos Smart Clock."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Atmos Smart Clock",
        unique_id=MAC,
        data={CONF_HOST: HOST},
        version=3,
    )


@pytest.fixture
def mock_websocket() -> FakeWebSocket:
    """Return the WebSocket of the mocked device."""
    return FakeWebSocket()


@pytest.fixture
def mock_inkvision_client(mock_websocket: FakeWebSocket) -> Generator[MagicMock]:
    """Mock the inkVision client."""
    with (
        patch(
            "homeassistant.components.inkvision.InkVisionClient", autospec=True
        ) as mock_client_class,
        patch(
            "homeassistant.components.inkvision.config_flow.InkVisionClient",
            new=mock_client_class,
        ),
    ):
        client = mock_client_class.return_value
        client.host = HOST
        client.get_status.return_value = load_json_object_fixture("status.json", DOMAIN)
        client.get_sensors.return_value = load_json_object_fixture(
            "sensors.json", DOMAIN
        )

        @asynccontextmanager
        async def websocket() -> AsyncIterator[FakeWebSocket]:
            yield mock_websocket

        client.websocket.side_effect = websocket
        yield client
