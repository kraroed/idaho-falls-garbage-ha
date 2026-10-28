"""Binary sensors: pickup today / tomorrow."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GarbageConfigEntry, GarbageCoordinator
from .entity import GarbageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarbageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([PickupTodaySensor(coordinator), PickupTomorrowSensor(coordinator)])


class PickupTodaySensor(GarbageEntity, BinarySensorEntity):
    """On when garbage pickup is today and the cutoff hour hasn't passed."""

    _attr_name = "Pickup today"
    _attr_icon = "mdi:truck-delivery"

    def __init__(self, coordinator: GarbageCoordinator) -> None:
        super().__init__(coordinator, "pickup_today")

    @property
    def is_on(self) -> bool:
        return self.coordinator.pickup_info().today_pickup


class PickupTomorrowSensor(GarbageEntity, BinarySensorEntity):
    """On when garbage pickup is tomorrow (use it for 'take the bins out' alerts)."""

    _attr_name = "Pickup tomorrow"
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, coordinator: GarbageCoordinator) -> None:
        super().__init__(coordinator, "pickup_tomorrow")

    @property
    def is_on(self) -> bool:
        return self.coordinator.pickup_info().tomorrow_pickup
