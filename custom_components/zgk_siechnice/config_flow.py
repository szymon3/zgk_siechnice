import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CITY,
    CONF_DAYS_ACTIVE,
    CONF_SCAN_INTERVAL,
    CONF_STREET,
    DEFAULT_DAYS_ACTIVE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FAILURES_URL,
)
from .coordinator import _SSL_CONTEXT

_LOGGER = logging.getLogger(__name__)


class ZGKConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for ZGK Siechnice."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "ZGKOptionsFlow":
        """Return the options flow handler."""
        return ZGKOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            city = user_input[CONF_CITY].strip()
            street = user_input.get(CONF_STREET, "").strip()

            # Validate: try fetching the page
            session = async_get_clientsession(self.hass)
            try:
                _LOGGER.debug("Connectivity check: GET %s", FAILURES_URL)
                resp = await session.get(
                    FAILURES_URL, timeout=aiohttp.ClientTimeout(total=15), ssl=_SSL_CONTEXT
                )
                _LOGGER.debug("Connectivity check: HTTP %s", resp.status)
                resp.raise_for_status()
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Connectivity check failed: %s: %s", type(err).__name__, err)
                errors["base"] = "cannot_connect"
            else:
                slug = f"{city.lower()}_{street.lower() or 'any'}"
                await self.async_set_unique_id(slug)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"ZGK – {city}" + (f", {street}" if street else ""),
                    data={CONF_CITY: city},
                    options={
                        CONF_STREET: street,
                        CONF_DAYS_ACTIVE: user_input.get(
                            CONF_DAYS_ACTIVE, DEFAULT_DAYS_ACTIVE
                        ),
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY): str,
                    vol.Optional(CONF_STREET, default=""): str,
                    vol.Optional(
                        CONF_DAYS_ACTIVE, default=DEFAULT_DAYS_ACTIVE
                    ): vol.All(int, vol.Range(min=1, max=30)),
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(int, vol.Range(min=5, max=1440)),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            city = user_input[CONF_CITY].strip()
            street = user_input.get(CONF_STREET, "").strip()

            session = async_get_clientsession(self.hass)
            try:
                _LOGGER.debug("Reconfigure connectivity check: GET %s", FAILURES_URL)
                resp = await session.get(
                    FAILURES_URL, timeout=aiohttp.ClientTimeout(total=15), ssl=_SSL_CONTEXT
                )
                _LOGGER.debug("Reconfigure connectivity check: HTTP %s", resp.status)
                resp.raise_for_status()
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Reconfigure connectivity check failed: %s: %s", type(err).__name__, err)
                errors["base"] = "cannot_connect"
            else:
                slug = f"{city.lower()}_{street.lower() or 'any'}"
                await self.async_set_unique_id(slug)
                self._abort_if_unique_id_configured(updates={})

                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    title=f"ZGK – {city}" + (f", {street}" if street else ""),
                    data={CONF_CITY: city},
                )

        entry = self._get_reconfigure_entry()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY, default=entry.data.get(CONF_CITY, "")): str,
                }
            ),
            errors=errors,
        )


class ZGKOptionsFlow(OptionsFlowWithReload):
    """Options flow — editing triggers integration reload automatically."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(CONF_STREET): str,
                        vol.Optional(CONF_DAYS_ACTIVE): vol.All(
                            int, vol.Range(min=1, max=30)
                        ),
                        vol.Optional(CONF_SCAN_INTERVAL): vol.All(
                            int, vol.Range(min=5, max=1440)
                        ),
                    }
                ),
                self.config_entry.options,
            ),
        )
