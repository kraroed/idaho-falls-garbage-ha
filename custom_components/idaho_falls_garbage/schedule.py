"""Pure-Python pickup schedule and holiday-delay logic (no Home Assistant imports).

City policy (Idaho Falls Sanitation): on certain weekday holidays there is no
collection that day, and collection for the rest of that week runs one day late.
Holidays that fall on a weekend do not affect the schedule.
"""

from __future__ import annotations

from datetime import date, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]

# key -> display name. These are the holidays that push pickups back a day.
DELAY_HOLIDAYS = {
    "new_years_day": "New Year's Day",
    "memorial_day": "Memorial Day",
    "independence_day": "Independence Day",
    "labor_day": "Labor Day",
    "thanksgiving": "Thanksgiving",
    "christmas": "Christmas Day",
}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def holiday_dates(year: int) -> dict[str, date]:
    """Return the delay-causing holidays for a year (key -> date)."""
    return {
        "new_years_day": date(year, 1, 1),
        "memorial_day": _last_weekday(year, 5, 0),
        "independence_day": date(year, 7, 4),
        "labor_day": _nth_weekday(year, 9, 0, 1),
        "thanksgiving": _nth_weekday(year, 11, 3, 4),
        "christmas": date(year, 12, 25),
    }


def build_delay_map(
    years: list[int],
    ignored: set[str] | None = None,
    extra_dates: set[date] | None = None,
) -> dict[date, str]:
    """Map weekday dates that trigger a one-day delay to a reason string."""
    ignored = ignored or set()
    result: dict[date, str] = {}
    for year in years:
        for key, d in holiday_dates(year).items():
            if key not in ignored and d.weekday() < 5:
                result[d] = DELAY_HOLIDAYS[key]
    for d in extra_dates or set():
        if d.weekday() < 5:
            result[d] = "Announced delay"
    return result


def actual_pickup(scheduled: date, delay_map: dict[date, str]) -> tuple[date, list[str]]:
    """Apply holiday delays to a normally scheduled pickup date."""
    week_start = scheduled - timedelta(days=scheduled.weekday())
    reasons: list[str] = []
    for i in range(scheduled.weekday() + 1):
        d = week_start + timedelta(days=i)
        if d in delay_map:
            reasons.append(delay_map[d])
    return scheduled + timedelta(days=len(reasons)), reasons


def pickups_in_range(
    start: date,
    end: date,
    collection_day: str,
    delay_map: dict[date, str],
) -> list[tuple[date, date, list[str]]]:
    """Return (actual, scheduled, reasons) for pickups with start <= actual <= end."""
    wd = WEEKDAYS.index(collection_day.lower())
    week_start = start - timedelta(days=start.weekday())
    weeks = (end - start).days // 7 + 3
    out: list[tuple[date, date, list[str]]] = []
    for w in range(-1, weeks):
        scheduled = week_start + timedelta(weeks=w, days=wd)
        actual, reasons = actual_pickup(scheduled, delay_map)
        if start <= actual <= end:
            out.append((actual, scheduled, reasons))
    out.sort(key=lambda t: t[0])
    return out


def upcoming_pickups(
    today: date,
    collection_day: str,
    delay_map: dict[date, str],
    count: int = 4,
) -> list[tuple[date, date, list[str]]]:
    """Return up to `count` (actual, scheduled, reasons) tuples on/after today."""
    end = today + timedelta(weeks=count + 6)
    return pickups_in_range(today, end, collection_day, delay_map)[:count]
