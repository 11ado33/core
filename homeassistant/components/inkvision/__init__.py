"""The inkVision integration."""

from pyinkvision import InkVisionClient

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import InkVisionConfigEntry, InkVisionCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: InkVisionConfigEntry) -> None:
    """Set up inkVision from a config entry."""
    client = InkVisionClient(entry.data[CONF_HOST], async_get_clientsession(hass))
    coordinator = InkVisionCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_create_background_task(
        hass, coordinator.async_listen(), f"inkvision websocket {entry.entry_id}"
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: InkVisionConfigEntry) -> None:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
