"""Shared fixtures (needs pytest-homeassistant-custom-component)."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from custom_components.idaho_falls_garbage.const import (
    CONF_AUTO_DETECT,
    CONF_COLLECTION_DAY,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"

COORD = "custom_components.idaho_falls_garbage.coordinator"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
async def set_tz(hass):
    await hass.config.async_set_time_zone("America/Boise")


@pytest.fixture
def mock_lookups():
    """Patch the city GIS calls: day -> tuesday, no leaf data."""
    with patch(f"{COORD}.async_lookup_collection_day", return_value="tuesday") as day, patch(
        f"{COORD}.async_lookup_leaf", return_value=None
    ) as leaf:
        yield day, leaf


def make_entry(day: str = "tuesday", **options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Idaho Falls Garbage",
        unique_id="43.4666_-112.0341",
        data={
            CONF_LATITUDE: 43.4666,
            CONF_LONGITUDE: -112.0341,
            CONF_COLLECTION_DAY: day,
        },
        options={CONF_AUTO_DETECT: False, **options},
    )


async def setup_entry(hass, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
