"""Calendar entity showing garbage pickups (with delays) and leaf collection."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import GarbageConfigEntry, GarbageCoordinator
from .entity import GarbageEntity

MAX_RANGE_DAYS = 800


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarbageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([GarbageCalendar(entry.runtime_data)])


def _summary(reasons: list[str]) -> str:
    if reasons:
        return f"Garbage pickup (delayed: {', '.join(reasons)})"
    return "Garbage pickup"


class GarbageCalendar(GarbageEntity, CalendarEntity):
    """All-day events for each pickup."""

    _attr_name = None  # use the device name -> calendar.idaho_falls_garbage
    _attr_icon = "mdi:trash-can"

    def __init__(self, coordinator: GarbageCoordinator) -> None:
        super().__init__(coordinator, "calendar")

    @property
    def event(self) -> CalendarEvent | None:
        info = self.coordinator.pickup_info()
        return CalendarEvent(
            start=info.next_date,
            end=info.next_date + timedelta(days=1),
            summary=_summary(info.reasons),
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        start = dt_util.as_local(start_date)
        end = dt_util.as_local(end_date)
        first = start.date() - timedelta(days=1)
        last = min(end.date(), first + timedelta(days=MAX_RANGE_DAYS))

        def overlaps(d: date) -> bool:
            d_start = dt_util.start_of_local_day(d)
            return d_start < end and d_start + timedelta(days=1) > start

        events: list[CalendarEvent] = []
        for actual, _scheduled, reasons in self.coordinator.pickups_between(first, last):
            if overlaps(actual):
                events.append(
                    CalendarEvent(
                        start=actual,
                        end=actual + timedelta(days=1),
                        summary=_summary(reasons),
                    )
                )

        leaf = self.coordinator.data
        if leaf and leaf.collect_date and overlaps(leaf.collect_date):
            zone = f" (Zone {leaf.zone})" if leaf.zone else ""
            events.append(
                CalendarEvent(
                    start=leaf.collect_date,
                    end=leaf.collect_date + timedelta(days=1),
                    summary=f"Leaf collection{zone}",
                    description=leaf.comments,
                )
            )
        events.sort(key=lambda e: e.start)
        return events
