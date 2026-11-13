"""Tests for defensive handling of City of Idaho Falls GIS responses."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.idaho_falls_garbage import lookup


def test_extract_rows_returns_valid_attributes():
    assert lookup._extract_rows(
        {
            "features": [
                {"attributes": {"CollectionDay": "Tuesday"}},
                {"attributes": {"CollectionDay": "Friday"}},
            ]
        }
    ) == [{"CollectionDay": "Tuesday"}, {"CollectionDay": "Friday"}]


def test_extract_rows_ignores_malformed_individual_features():
    assert lookup._extract_rows(
        {
            "features": [
                None,
                "not-a-feature",
                {},
                {"attributes": None},
                {"attributes": {"CollectionDay": "Monday"}},
            ]
        }
    ) == [{"CollectionDay": "Monday"}]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "not-json-object",
        {},
        {"features": None},
        {"features": "not-a-list"},
        {"error": {"code": 400, "message": "Bad query"}},
    ],
)
def test_extract_rows_rejects_malformed_arcgis_payloads(payload):
    with pytest.raises(lookup.CannotConnect):
        lookup._extract_rows(payload)


def test_esri_date_converts_epoch_milliseconds():
    assert lookup._esri_date(1794528000000) == date(2026, 11, 13)


@pytest.mark.parametrize(
    "value",
    [None, "1794528000000", True, float("inf"), float("nan"), 10**1000],
)
def test_esri_date_handles_invalid_values(value):
    assert lookup._esri_date(value) is None


async def test_collection_day_skips_invalid_intersecting_feature(monkeypatch):
    async def fake_query(*args, **kwargs):
        return [
            {"CollectionDay": None},
            {"CollectionDay": "weekend"},
            {"CollectionDay": " Thursday "},
        ]

    monkeypatch.setattr(lookup, "_async_query", fake_query)
    assert await lookup.async_lookup_collection_day(MagicMock(), 43.4, -112.0) == "thursday"


async def test_collection_day_returns_none_when_no_valid_feature(monkeypatch):
    async def fake_query(*args, **kwargs):
        return [{"CollectionDay": "Saturday"}, {}]

    monkeypatch.setattr(lookup, "_async_query", fake_query)
    assert await lookup.async_lookup_collection_day(MagicMock(), 43.4, -112.0) is None


async def test_leaf_lookup_handles_invalid_date_and_empty_text(monkeypatch):
    async def fake_query(*args, **kwargs):
        return [{"AreaName": "  ", "CollectDate": 10**1000, "Comments": None}]

    monkeypatch.setattr(lookup, "_async_query", fake_query)
    result = await lookup.async_lookup_leaf(MagicMock(), 43.4, -112.0)
    assert result == lookup.LeafInfo(zone=None, collect_date=None, comments=None)


async def test_leaf_lookup_parses_valid_fields(monkeypatch):
    async def fake_query(*args, **kwargs):
        return [
            {
                "AreaName": "North",
                "CollectDate": 1794528000000,
                "Comments": " Leaves at curb ",
            }
        ]

    monkeypatch.setattr(lookup, "_async_query", fake_query)
    result = await lookup.async_lookup_leaf(MagicMock(), 43.4, -112.0)
    assert result == lookup.LeafInfo(
        zone="North", collect_date=date(2026, 11, 13), comments="Leaves at curb"
    )


async def test_async_query_translates_arcgis_errors_to_cannot_connect():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value={"error": {"message": "bad request"}})
    request = MagicMock()
    request.__aenter__ = AsyncMock(return_value=response)
    request.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.get.return_value = request

    with pytest.raises(lookup.CannotConnect):
        await lookup._async_query(
            session, "https://example.invalid/query", 43.4, -112.0, "CollectionDay"
        )
    session.get.assert_called_once()
