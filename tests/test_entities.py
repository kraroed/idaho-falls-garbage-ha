from homeassistant.helpers import issue_registry as ir

from custom_components.idaho_falls_garbage.const import CONF_COLLECTION_DAY, DOMAIN

from .conftest import make_entry, setup_entry

NEXT = "sensor.idaho_falls_garbage_next_pickup"
TODAY = "binary_sensor.idaho_falls_garbage_pickup_today"
TOMORROW = "binary_sensor.idaho_falls_garbage_pickup_tomorrow"


async def test_next_pickup_normal(hass, freezer, mock_lookups):
    freezer.move_to("2026-10-27 18:00:00+00:00")  # Tuesday, midday local
    await setup_entry(hass, make_entry("tuesday"))
    state = hass.states.get(NEXT)
    assert state.state == "2026-10-27"
    assert state.attributes["delayed"] is False
    assert hass.states.get(TODAY).state == "on"


async def test_thanksgiving_delay(hass, freezer, mock_lookups):
    freezer.move_to("2026-11-24 18:00:00+00:00")
    await setup_entry(hass, make_entry("thursday"))
    state = hass.states.get(NEXT)
    assert state.state == "2026-11-27"
    assert state.attributes["delayed"] is True
    assert state.attributes["delay_reason"] == "Thanksgiving"


async def test_pickup_tomorrow(hass, freezer, mock_lookups):
    freezer.move_to("2026-10-26 18:00:00+00:00")  # Monday
    await setup_entry(hass, make_entry("tuesday"))
    assert hass.states.get(TOMORROW).state == "on"
    assert hass.states.get(TODAY).state == "off"


async def test_cutoff_moves_to_next_pickup(hass, freezer, mock_lookups):
    freezer.move_to("2026-10-27 23:00:00+00:00")  # Tuesday 17:00 local, past 15:00
    await setup_entry(hass, make_entry("tuesday", cutoff_hour=15))
    assert hass.states.get(NEXT).state == "2026-11-03"
    assert hass.states.get(TODAY).state == "off"


async def test_auto_redetect_updates_day(hass, freezer, mock_lookups):
    freezer.move_to("2026-10-27 18:00:00+00:00")
    entry = make_entry("monday", auto_detect=True)  # city lookup mock says tuesday
    await setup_entry(hass, entry)
    assert entry.data[CONF_COLLECTION_DAY] == "tuesday"
    assert hass.states.get(NEXT).state == "2026-10-27"


async def test_refresh_button(hass, freezer, mock_lookups):
    freezer.move_to("2026-10-27 18:00:00+00:00")
    await setup_entry(hass, make_entry("tuesday"))
    day_mock, _ = mock_lookups
    day_mock.reset_mock()
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.idaho_falls_garbage_refresh_from_city"},
        blocking=True,
    )
    day_mock.assert_awaited()


async def test_calendar_shows_delay(hass, freezer, mock_lookups):
    freezer.move_to("2026-11-24 18:00:00+00:00")
    await setup_entry(hass, make_entry("thursday"))
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": "calendar.idaho_falls_garbage",
            "start_date_time": "2026-11-23 00:00:00",
            "end_date_time": "2026-11-30 00:00:00",
        },
        blocking=True,
        return_response=True,
    )
    events = result["calendar.idaho_falls_garbage"]["events"]
    assert len(events) == 1
    assert events[0]["start"] == "2026-11-27"
    assert "Thanksgiving" in events[0]["summary"]


async def test_january_review_issue(hass, freezer, mock_lookups):
    freezer.move_to("2027-01-10 18:00:00+00:00")
    await setup_entry(hass, make_entry("tuesday"))
    assert ir.async_get(hass).async_get_issue(DOMAIN, "holiday_review_2027") is not None
