"""Idaho Falls Garbage Pickup integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .coordinator import GarbageConfigEntry, GarbageCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: GarbageConfigEntry) -> bool:
    """Set up from a config entry."""
    coordinator = GarbageCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    @callback
    def _tick(_now: datetime) -> None:
        # Dates are computed on demand; just ask entities to re-render.
        coordinator.async_update_listeners()

    entry.async_on_unload(
        async_track_time_change(hass, _tick, hour=0, minute=0, second=5)
    )
    if coordinator.cutoff_hour < 24:
        entry.async_on_unload(
            async_track_time_change(
                hass, _tick, hour=coordinator.cutoff_hour, minute=0, second=5
            )
        )

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GarbageConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: GarbageConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
