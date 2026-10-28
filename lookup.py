"""Look up a location's collection info from the City of Idaho Falls GIS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import aiohttp

from .const import GARBAGE_QUERY_URL, LEAF_QUERY_URL
from .schedule import WEEKDAYS


class CannotConnect(Exception):
    """The city GIS service could not be reached or returned bad data."""


@dataclass
class LeafInfo:
    """Leaf collection details for a location."""

    zone: str | None
    collect_date: date | None
    comments: str | None


async def _async_query(
    session: aiohttp.ClientSession,
    url: str,
    latitude: float,
    longitude: float,
    out_fields: str,
) -> list[dict[str, Any]]:
    params = {
        "f": "json",
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "false",
    }
    try:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise CannotConnect from err

    if not isinstance(data, dict) or "error" in data:
        raise CannotConnect(f"GIS error: {data}")
    return [f.get("attributes", {}) for f in data.get("features") or []]


async def async_lookup_collection_day(
    session: aiohttp.ClientSession, latitude: float, longitude: float
) -> str | None:
    """Return e.g. 'tuesday', or None if the point is outside the collection area."""
    rows = await _async_query(session, GARBAGE_QUERY_URL, latitude, longitude, "CollectionDay")
    if not rows:
        return None
    day = str(rows[0].get("CollectionDay", "")).strip().lower()
    return day if day in WEEKDAYS else None


async def async_lookup_leaf(
    session: aiohttp.ClientSession, latitude: float, longitude: float
) -> LeafInfo | None:
    """Return leaf collection info, or None if the point isn't in a leaf area."""
    rows = await _async_query(
        session, LEAF_QUERY_URL, latitude, longitude, "AreaName,CollectDate,Comments"
    )
    if not rows:
        return None
    row = rows[0]
    ms = row.get("CollectDate")
    collect_date = (
        datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
        if isinstance(ms, (int, float))
        else None
    )
    comments = (row.get("Comments") or "").strip() or None
    return LeafInfo(
        zone=(row.get("AreaName") or None), collect_date=collect_date, comments=comments
    )
