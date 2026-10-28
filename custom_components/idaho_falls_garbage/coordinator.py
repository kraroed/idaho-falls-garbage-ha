"""Coordinator: schedule math, leaf lookups, auto re-detection, repair notices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CITY_SANITATION_URL,
    CONF_AUTO_DETECT,
    CONF_COLLECTION_DAY,
    CONF_CUTOFF_HOUR,
    CONF_EXTRA_DELAY_DATES,
    CONF_NO_DELAY_HOLIDAYS,
    DEFAULT_CUTOFF_HOUR,
    DOMAIN,
)
from .lookup import (
    CannotConnect,
    LeafInfo,
    async_lookup_collection_day,
    async_lookup_leaf,
)
from .schedule import build_delay_map, pickups_in_range

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=6)
REDETECT_INTERVAL = timedelta(hours=24)


@dataclass
class PickupInfo:
    """Computed garbage pickup state for 'now'."""

    next_date: date
    scheduled_date: date
    reasons: list[str]
    upcoming: list[date]
    days_until: int
    collection_day: str
    today_pickup: bool
    tomorrow_pickup: bool


class GarbageCoordinator(DataUpdateCoordinator[LeafInfo | None]):
    """Holds config-derived schedule logic and polled leaf data.

    Garbage dates are computed locally, so a GIS outage never makes them
    unavailable; this coordinator never raises UpdateFailed.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=UPDATE_INTERVAL,
        )
        self._last_redetect: datetime | None = None

    # ----- configuration helpers -----
    @property
    def collection_day(self) -> str:
        entry = self.config_entry
        if entry.options.get(CONF_AUTO_DETECT, True):
            return entry.data[CONF_COLLECTION_DAY]
        return entry.options.get(CONF_COLLECTION_DAY, entry.data[CONF_COLLECTION_DAY])

    @property
    def cutoff_hour(self) -> int:
        return int(self.config_entry.options.get(CONF_CUTOFF_HOUR, DEFAULT_CUTOFF_HOUR))

    def _extra_dates(self) -> set[date]:
        text = self.config_entry.options.get(CONF_EXTRA_DELAY_DATES, "") or ""
        out: set[date] = set()
        for part in text.replace("\n", ",").split(","):
            part = part.strip()
            if part:
                try:
                    out.add(date.fromisoformat(part))
                except ValueError:
                    _LOGGER.warning("Ignoring invalid delay date %r", part)
        return out

    def delay_map(self, start: date, end: date) -> dict[date, str]:
        ignored = set(self.config_entry.options.get(CONF_NO_DELAY_HOLIDAYS, []))
        years = list(range(start.year - 1, end.year + 2))
        return build_delay_map(years, ignored, self._extra_dates())

    # ----- schedule -----
    def pickup_info(self, now: datetime | None = None) -> PickupInfo:
        now = dt_util.as_local(now) if now else dt_util.now()
        today = now.date()
        past_cutoff = now.hour >= self.cutoff_hour
        end = today + timedelta(weeks=8)
        pickups = pickups_in_range(
            today, end, self.collection_day, self.delay_map(today, end)
        )
        effective = today + timedelta(days=1) if past_cutoff else today
        upcoming = [p for p in pickups if p[0] >= effective]
        actual, scheduled, reasons = upcoming[0]
        tomorrow = today + timedelta(days=1)
        return PickupInfo(
            next_date=actual,
            scheduled_date=scheduled,
            reasons=reasons,
            upcoming=[p[0] for p in upcoming[:4]],
            days_until=(actual - today).days,
            collection_day=self.collection_day,
            today_pickup=pickups[0][0] == today and not past_cutoff,
            tomorrow_pickup=any(p[0] == tomorrow for p in pickups),
        )

    def pickups_between(
        self, start: date, end: date
    ) -> list[tuple[date, date, list[str]]]:
        return pickups_in_range(
            start, end, self.collection_day, self.delay_map(start, end)
        )

    # ----- polling -----
    async def _async_update_data(self) -> LeafInfo | None:
        self._update_repairs()
        session = async_get_clientsession(self.hass)
        entry = self.config_entry

        if entry.options.get(CONF_AUTO_DETECT, True):
            now = dt_util.utcnow()
            if self._last_redetect is None or now - self._last_redetect > REDETECT_INTERVAL:
                self._last_redetect = now
                try:
                    await self._async_redetect_day()
                except CannotConnect:
                    _LOGGER.debug("Collection-day re-check failed; keeping %s", self.collection_day)

        try:
            return await async_lookup_leaf(
                session, entry.data[CONF_LATITUDE], entry.data[CONF_LONGITUDE]
            )
        except CannotConnect:
            _LOGGER.debug("Leaf lookup failed; keeping previous data")
            return self.data

    async def async_redetect(self) -> bool:
        """Re-check the collection day now. Raises CannotConnect on failure."""
        return await self._async_redetect_day()

    async def _async_redetect_day(self) -> bool:
        entry = self.config_entry
        day = await async_lookup_collection_day(
            async_get_clientsession(self.hass),
            entry.data[CONF_LATITUDE],
            entry.data[CONF_LONGITUDE],
        )
        if day is None or day == entry.data[CONF_COLLECTION_DAY]:
            return False
        old = entry.data[CONF_COLLECTION_DAY]
        _LOGGER.warning("City collection day changed from %s to %s", old, day)
        persistent_notification.async_create(
            self.hass,
            f"The City of Idaho Falls now lists your garbage collection day as "
            f"{day.title()} (was {old.title()}).",
            title="Idaho Falls garbage day changed",
            notification_id=f"{DOMAIN}_day_changed",
        )
        self.hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_COLLECTION_DAY: day}
        )
        return True

    # ----- repairs -----
    def _update_repairs(self) -> None:
        """Remind the user each Jan/Feb to re-check the city's holiday rules."""
        year = dt_util.now().year
        issue_id = f"holiday_review_{year}"
        if dt_util.now().month in (1, 2):
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="holiday_review",
                translation_placeholders={"year": str(year), "url": CITY_SANITATION_URL},
                learn_more_url=CITY_SANITATION_URL,
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        ir.async_delete_issue(self.hass, DOMAIN, f"holiday_review_{year - 1}")


type GarbageConfigEntry = ConfigEntry[GarbageCoordinator]
