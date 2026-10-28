"""Button: re-check the collection day and leaf data from the city's GIS now."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GarbageConfigEntry, GarbageCoordinator
from .entity import GarbageEntity
from .lookup import CannotConnect


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarbageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RefreshButton(entry.runtime_data)])


class RefreshButton(GarbageEntity, ButtonEntity):
    """Re-detect collection day from the home location."""

    _attr_name = "Refresh from city"
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GarbageCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_redetect()
        except CannotConnect as err:
            raise HomeAssistantError(
                "Couldn't reach the City of Idaho Falls GIS service"
            ) from err
        await self.coordinator.async_request_refresh()
