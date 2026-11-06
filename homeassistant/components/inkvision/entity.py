"""Base entity for inkVision."""

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import InkVisionCoordinator


class InkVisionEntity(CoordinatorEntity[InkVisionCoordinator]):
    """An entity of an inkVision device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: InkVisionCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        mac = coordinator.config_entry.unique_id
        if TYPE_CHECKING:
            assert mac is not None
        status = coordinator.data.status
        self._attr_unique_id = f"{mac}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            configuration_url=f"http://{coordinator.client.host}",
            manufacturer="inkVision",
            model=status.get("device"),
            model_id=status.get("model"),
            name=coordinator.config_entry.title,
            sw_version=status.get("version"),
        )
