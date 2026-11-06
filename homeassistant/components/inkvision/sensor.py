"""Sensors of inkVision devices."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfPressure,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import InkVisionConfigEntry, InkVisionCoordinator, InkVisionData
from .entity import InkVisionEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class InkVisionSensorEntityDescription(SensorEntityDescription):
    """Describes an inkVision sensor."""

    value_fn: Callable[[InkVisionData], StateType]


def _environment(key: str) -> Callable[[InkVisionData], StateType]:
    """Return a reading of the BME680 environment sensor."""
    return lambda data: data.sensors.get("bme680", {}).get(key)


# The keys match the unique IDs of the custom integration this one replaces.
SENSORS: tuple[InkVisionSensorEntityDescription, ...] = (
    InkVisionSensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_environment("temperature"),
    ),
    InkVisionSensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_environment("humidity"),
    ),
    InkVisionSensorEntityDescription(
        key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_environment("pressure"),
    ),
    InkVisionSensorEntityDescription(
        key="bsec_iaq",
        translation_key="indoor_air_quality",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_environment("iaq"),
    ),
    InkVisionSensorEntityDescription(
        key="bsec_co2_equivalent",
        translation_key="co2_equivalent",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_environment("co2_equivalent"),
    ),
    InkVisionSensorEntityDescription(
        key="bsec_breath_voc",
        translation_key="breath_voc",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_environment("breath_voc"),
    ),
    InkVisionSensorEntityDescription(
        key="gas_resistance",
        translation_key="gas_resistance",
        native_unit_of_measurement="kΩ",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_environment("gas_resistance_kohm"),
    ),
    InkVisionSensorEntityDescription(
        key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.status.get("rssi"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InkVisionConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of an inkVision device."""
    coordinator = entry.runtime_data
    async_add_entities(
        InkVisionSensorEntity(coordinator, description) for description in SENSORS
    )


class InkVisionSensorEntity(InkVisionEntity, SensorEntity):
    """A sensor of an inkVision device."""

    entity_description: InkVisionSensorEntityDescription

    def __init__(
        self,
        coordinator: InkVisionCoordinator,
        description: InkVisionSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    @override
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)
