"""Config and options flow."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_AUTO_DETECT,
    CONF_COLLECTION_DAY,
    CONF_CUTOFF_HOUR,
    CONF_EXTRA_DELAY_DATES,
    CONF_NO_DELAY_HOLIDAYS,
    DEFAULT_CUTOFF_HOUR,
    DOMAIN,
)
from .lookup import CannotConnect, async_lookup_collection_day
from .schedule import DELAY_HOLIDAYS, WEEKDAYS


def _day_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[{"value": d, "label": d.title()} for d in WEEKDAYS],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _parse_dates(text: str) -> list[date] | None:
    """Parse 'YYYY-MM-DD, YYYY-MM-DD'; return None if any entry is invalid."""
    out: list[date] = []
    for part in text.replace("\n", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(date.fromisoformat(part))
        except ValueError:
            return None
    return out


class IdahoFallsGarbageConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._lat: float | None = None
        self._lon: float | None = None
        self._error: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._lat = user_input[CONF_LATITUDE]
            self._lon = user_input[CONF_LONGITUDE]
            await self.async_set_unique_id(f"{self._lat:.4f}_{self._lon:.4f}")
            self._abort_if_unique_id_configured()
            try:
                day = await async_lookup_collection_day(
                    async_get_clientsession(self.hass), self._lat, self._lon
                )
            except CannotConnect:
                self._error = "cannot_connect"
                return await self.async_step_manual()
            if day is None:
                self._error = "outside_service_area"
                return await self.async_step_manual()
            return self._create(day, manual=False)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LATITUDE, default=self.hass.config.latitude
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_LONGITUDE, default=self.hass.config.longitude
                    ): vol.Coerce(float),
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._create(user_input[CONF_COLLECTION_DAY], manual=True)
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {vol.Required(CONF_COLLECTION_DAY, default="monday"): _day_selector()}
            ),
            errors={"base": self._error} if self._error else {},
        )

    def _create(self, day: str, manual: bool) -> ConfigFlowResult:
        return self.async_create_entry(
            title="Idaho Falls Garbage",
            data={
                CONF_LATITUDE: self._lat,
                CONF_LONGITUDE: self._lon,
                CONF_COLLECTION_DAY: day,
            },
            options={
                CONF_AUTO_DETECT: not manual,
                CONF_CUTOFF_HOUR: DEFAULT_CUTOFF_HOUR,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return IdahoFallsGarbageOptionsFlow()


class IdahoFallsGarbageOptionsFlow(OptionsFlow):
    """Adjust detection, cutoff, and holiday behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.config_entry
        if user_input is not None:
            if _parse_dates(user_input.get(CONF_EXTRA_DELAY_DATES, "")) is None:
                errors[CONF_EXTRA_DELAY_DATES] = "invalid_date"
            else:
                user_input[CONF_CUTOFF_HOUR] = int(
                    user_input.get(CONF_CUTOFF_HOUR, DEFAULT_CUTOFF_HOUR)
                )
                return self.async_create_entry(data=user_input)

        opts = entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_AUTO_DETECT, default=opts.get(CONF_AUTO_DETECT, True)
                ): BooleanSelector(),
                vol.Required(
                    CONF_COLLECTION_DAY,
                    default=opts.get(CONF_COLLECTION_DAY, entry.data[CONF_COLLECTION_DAY]),
                ): _day_selector(),
                vol.Required(
                    CONF_CUTOFF_HOUR,
                    default=int(opts.get(CONF_CUTOFF_HOUR, DEFAULT_CUTOFF_HOUR)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=24, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_NO_DELAY_HOLIDAYS,
                    default=opts.get(CONF_NO_DELAY_HOLIDAYS, []),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v} for k, v in DELAY_HOLIDAYS.items()
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_EXTRA_DELAY_DATES,
                    default=opts.get(CONF_EXTRA_DELAY_DATES, ""),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
