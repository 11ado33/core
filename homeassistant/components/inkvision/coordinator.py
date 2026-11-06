"""Coordinator for inkVision devices."""

import asyncio
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import Any, override

from pyinkvision import InkVisionClient, InkVisionConnectionError, InkVisionError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

type InkVisionConfigEntry = ConfigEntry[InkVisionCoordinator]

# The device pushes updates over its WebSocket, and every push restarts this
# timer, so polling only happens while the WebSocket is down.
UPDATE_INTERVAL = timedelta(minutes=5)
RECONNECT_DELAY = 10


@dataclass(frozen=True)
class InkVisionData:
    """Latest data of an inkVision device."""

    status: dict[str, Any]
    sensors: dict[str, Any]


class InkVisionCoordinator(DataUpdateCoordinator[InkVisionData]):
    """Keep the data of an inkVision device up to date."""

    config_entry: InkVisionConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: InkVisionConfigEntry,
        client: InkVisionClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=f"inkVision {client.host}",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    @override
    async def _async_update_data(self) -> InkVisionData:
        try:
            status = await self.client.get_status()
            sensors = await self.client.get_sensors()
        except InkVisionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_error",
                translation_placeholders={"error": str(err)},
            ) from err
        return InkVisionData(status=status, sensors=sensors)

    async def async_listen(self) -> None:
        """Keep the WebSocket to the device open and apply what it pushes."""
        while True:
            connected = False
            try:
                async with self.client.websocket() as websocket:
                    connected = True
                    async for message in websocket:
                        self._async_handle_message(message)
            except InkVisionConnectionError as err:
                LOGGER.debug("WebSocket to %s closed: %s", self.client.host, err)
            if connected:
                # Poll right away, so the entities become unavailable now if
                # the device is gone.
                await self.async_request_refresh()
            await asyncio.sleep(RECONNECT_DELAY)

    @callback
    def _async_handle_message(self, message: dict[str, Any]) -> None:
        """Apply a message pushed by the device."""
        if not isinstance(data := message.get("data"), dict):
            return
        match message.get("type"):
            case "sensor_update":
                self.async_set_updated_data(replace(self.data, sensors=data))
            case "status_update":
                # Pushes carry only part of the status.
                self.async_set_updated_data(
                    replace(self.data, status={**self.data.status, **data})
                )
