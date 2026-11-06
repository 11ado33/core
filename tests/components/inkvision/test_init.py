"""Tests for the inkVision integration setup."""

from unittest.mock import MagicMock

from pyinkvision import InkVisionConnectionError
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from . import setup_integration
from .conftest import MAC


@pytest.mark.usefixtures("mock_inkvision_client")
async def test_load_unload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test loading and unloading a config entry."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry(
    hass: HomeAssistant,
    mock_inkvision_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that setup is retried when the device is unreachable."""
    mock_inkvision_client.get_status.side_effect = InkVisionConnectionError("timeout")

    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("mock_inkvision_client")
async def test_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test the device of a config entry."""
    await setup_integration(hass, mock_config_entry)

    device = device_registry.async_get_device_by_identifier(
        ("inkvision", MAC), mock_config_entry.entry_id
    )
    assert device is not None
    assert device.connections == {(dr.CONNECTION_NETWORK_MAC, MAC)}
    assert device.manufacturer == "inkVision"
    assert device.model == "Atmos Smart Clock"
    assert device.model_id == "ATMOS-SMART-CLOCK-001"
    assert device.sw_version == "1.0.11"
