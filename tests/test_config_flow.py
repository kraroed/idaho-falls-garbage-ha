from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.idaho_falls_garbage.const import DOMAIN
from custom_components.idaho_falls_garbage.lookup import CannotConnect

LOOKUP = "custom_components.idaho_falls_garbage.config_flow.async_lookup_collection_day"
USER = {"latitude": 43.4666, "longitude": -112.0341}


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_auto_detect(hass):
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    with patch(LOOKUP, return_value="thursday"), patch(
        "custom_components.idaho_falls_garbage.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["collection_day"] == "thursday"
    assert result["options"]["auto_detect"] is True


async def test_outside_area_falls_back_to_manual(hass):
    result = await _start(hass)
    with patch(LOOKUP, return_value=None):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {"base": "outside_service_area"}
    with patch("custom_components.idaho_falls_garbage.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"collection_day": "friday"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["collection_day"] == "friday"
    assert result["options"]["auto_detect"] is False


async def test_cannot_connect_falls_back_to_manual(hass):
    result = await _start(hass)
    with patch(LOOKUP, side_effect=CannotConnect):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER)
    assert result["step_id"] == "manual"
    assert result["errors"] == {"base": "cannot_connect"}
