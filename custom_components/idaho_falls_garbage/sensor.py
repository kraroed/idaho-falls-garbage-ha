"""Sensors: next garbage pickup and leaf collection."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import GarbageConfigEntry, GarbageCoordinator
from .entity import GarbageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarbageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([NextPickupSensor(coordinator), LeafCollectionSensor(coordinator)])


class NextPickupSensor(GarbageEntity, SensorEntity):
    """Date of the next garbage pickup, adjusted for holidays."""

    _attr_name = "Next pickup"
    _attr_icon = "mdi:trash-can"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: GarbageCoordinator) -> None:
        super().__init__(coordinator, "next_pickup")

    @property
    def native_value(self) -> date:
        return self.coordinator.pickup_info().next_date

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        info = self.coordinator.pickup_info()
        return {
            "collection_day": info.collection_day.title(),
            "normal_date": info.scheduled_date.isoformat(),
            "delayed": info.next_date != info.scheduled_date,
            "delay_reason": ", ".join(info.reasons) or None,
            "days_until": info.days_until,
            "upcoming": [d.isoformat() for d in info.upcoming],
        }


class LeafCollectionSensor(GarbageEntity, SensorEntity):
    """Seasonal leaf collection date for the home's leaf zone."""

    _attr_name = "Leaf collection"
    _attr_icon = "mdi:leaf"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: GarbageCoordinator) -> None:
        super().__init__(coordinator, "leaf_collection")

    @property
    def native_value(self) -> date | None:
        leaf = self.coordinator.data
        if leaf and leaf.collect_date and leaf.collect_date >= dt_util.now().date():
            return leaf.collect_date
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        leaf = self.coordinator.data
        if leaf is None:
            return {"status": "not_in_leaf_area"}
        today = dt_util.now().date()
        if leaf.collect_date is None:
            status = "not_scheduled"
        elif leaf.collect_date < today:
            status = "completed"
        elif leaf.collect_date == today:
            status = "today"
        else:
            status = "scheduled"
        return {
            "status": status,
            "zone": leaf.zone,
            "collect_date": leaf.collect_date.isoformat() if leaf.collect_date else None,
            "comments": leaf.comments,
        }
