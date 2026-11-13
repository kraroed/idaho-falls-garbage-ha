"""Look up a location's collection info from the City of Idaho Falls GIS."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import math
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


def _extract_rows(data: Any) -> list[dict[str, Any]]:
    """Validate an ArcGIS query response and return its attribute rows.

    ArcGIS normally returns a dictionary containing a features list. A
    malformed top-level response is treated as a service failure, while
    individual malformed features are ignored so one bad record does not
    discard otherwise usable results.
    """
    if not isinstance(data, dict) or "error" in data:
        raise CannotConnect(f"GIS error: {data}")
    features = data.get("features")
    if not isinstance(features, list):
        raise CannotConnect("GIS response did not contain a features list")

    rows: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        attributes = feature.get("attributes")
        if isinstance(attributes, dict) and attributes:
            rows.append(attributes)

    if features and not rows:
        raise CannotConnect("GIS response contained no usable feature attributes")
    return rows


def _esri_date(value: Any) -> date | None:
    """Convert an ArcGIS epoch-millisecond date to a calendar date safely."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date()
    except (OverflowError, OSError, ValueError):
        return None


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

    return _extract_rows(data)


async def async_lookup_collection_day(
    session: aiohttp.ClientSession, latitude: float, longitude: float
) -> str | None:
    """Return e.g. 'tuesday', or None if the point is outside the collection area."""
    rows = await _async_query(
        session, GARBAGE_QUERY_URL, latitude, longitude, "CollectionDay"
    )
    # GIS can return more than one intersecting feature (notably at polygon
    # boundaries). Ignore malformed values rather than letting the first
    # unusable feature hide a later valid collection-day record.
    for row in rows:
        day = str(row.get("CollectionDay", "")).strip().lower()
        if day in WEEKDAYS:
            return day
    return None


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
    zone_value = row.get("AreaName")
    comments_value = row.get("Comments")
    zone = str(zone_value).strip() if zone_value is not None else ""
    comments = str(comments_value).strip() if comments_value is not None else ""
    return LeafInfo(
        zone=zone or None,
        collect_date=_esri_date(row.get("CollectDate")),
        comments=comments or None,
    )
