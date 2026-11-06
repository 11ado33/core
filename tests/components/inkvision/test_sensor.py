"""Tests for the inkVision sensors."""

from unittest.mock import MagicMock, patch

from pyinkvision import InkVisionConnectionError
import pytest
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration
from .conftest import FakeWebSocket

TEMPERATURE = "sensor.atmos_smart_clock_temperature"
SIGNAL_STRENGTH = "sensor.atmos_smart_clock_signal_strength"


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "mock_inkvision_client")
async def test_all_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "mock_inkvision_client")
async def test_websocket_pushes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_websocket: FakeWebSocket,
) -> None:
    """Test that pushed sensor and status updates change the states."""
    await setup_integration(hass, mock_config_entry)

    mock_websocket.push(
        {"type": "sensor_update", "data": {"bme680": {"temperature": 23.5}}}
    )
    mock_websocket.push({"type": "status_update", "data": {"rssi": -60}})
    # Ignored: no data, and a type that the integration doesn't use.
    mock_websocket.push({"type": "sensor_update"})
    mock_websocket.push({"type": "button_event", "data": {"button": 1}})
    await hass.async_block_till_done()

    assert hass.states.get(TEMPERATURE).state == "23.5"
    assert hass.states.get(SIGNAL_STRENGTH).state == "-60"


async def test_websocket_closed(
    hass: HomeAssistant,
    mock_inkvision_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    mock_websocket: FakeWebSocket,
) -> None:
    """Test that the entities become unavailable when the device is gone."""
    with patch("homeassistant.components.inkvision.coordinator.RECONNECT_DELAY", 0):
        await setup_integration(hass, mock_config_entry)

        mock_inkvision_client.get_status.side_effect = InkVisionConnectionError(
            "timeout"
        )
        mock_websocket.close()
        await hass.async_block_till_done()
        assert hass.states.get(TEMPERATURE).state == STATE_UNAVAILABLE

        # The device is back, and the WebSocket reconnected.
        mock_websocket.push(
            {"type": "sensor_update", "data": {"bme680": {"temperature": 22.0}}}
        )
        await hass.async_block_till_done()
        assert hass.states.get(TEMPERATURE).state == "22.0"
