"""Test setup.

Home Assistant is not installed for these tests. The few HA names the
integration imports are replaced with minimal stand-ins, so the integration's
own coordinator, parser and sensor classes run unmodified.
"""

import asyncio
import sys
import types
from functools import cache
from pathlib import Path
from types import SimpleNamespace

import aiohttp
from bs4 import BeautifulSoup


class _Stub:
    def __init__(self, *args, **kwargs):
        pass

    def __class_getitem__(cls, _):
        return cls


class _CoordinatorEntity(_Stub):
    def __init__(self, coordinator, *args, **kwargs):
        self.coordinator = coordinator


class UpdateFailed(Exception):
    pass


_HA_STUBS = {
    "homeassistant": {},
    "homeassistant.components": {},
    "homeassistant.helpers": {},
    "homeassistant.config_entries": {"ConfigEntry": _Stub},
    "homeassistant.const": {"Platform": SimpleNamespace(BINARY_SENSOR="binary_sensor")},
    "homeassistant.core": {"HomeAssistant": _Stub},
    "homeassistant.components.binary_sensor": {
        "BinarySensorDeviceClass": SimpleNamespace(PROBLEM="problem"),
        "BinarySensorEntity": type("BinarySensorEntity", (), {}),
    },
    # Tests pass SimpleNamespace(session=<aiohttp session>) as "hass"
    "homeassistant.helpers.aiohttp_client": {
        "async_get_clientsession": lambda hass: hass.session
    },
    "homeassistant.helpers.device_registry": {
        "DeviceEntryType": SimpleNamespace(SERVICE="service"),
        "DeviceInfo": dict,
    },
    "homeassistant.helpers.entity_platform": {"AddEntitiesCallback": object},
    "homeassistant.helpers.update_coordinator": {
        "DataUpdateCoordinator": _Stub,
        "CoordinatorEntity": _CoordinatorEntity,
        "UpdateFailed": UpdateFailed,
    },
}

for _name, _attrs in _HA_STUBS.items():
    _module = types.ModuleType(_name)
    _module.__dict__.update(_attrs)
    sys.modules[_name] = _module

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

from zgk_siechnice import coordinator  # noqa: E402
from zgk_siechnice.const import (  # noqa: E402
    CONF_CITY,
    CONF_DAYS_ACTIVE,
    CONF_STREET,
    FAILURES_URL,
    MAX_PAGES,
)


def make_entry(city: str, street: str = "", days_active: int | None = None):
    """Return a config entry stand-in as created by the config flow."""
    options = {CONF_STREET: street}
    if days_active is not None:
        options[CONF_DAYS_ACTIVE] = days_active
    return SimpleNamespace(entry_id="test", data={CONF_CITY: city}, options=options)


@cache
def live_events() -> list[dict]:
    """Fetch the live listing through the integration's coordinator (once)."""

    async def fetch():
        async with aiohttp.ClientSession() as session:
            hass = SimpleNamespace(session=session)
            return await coordinator.ZGKCoordinator(
                hass, make_entry("")
            )._async_update_data()

    return asyncio.run(fetch())


@cache
def live_item_count() -> int:
    """Count listing items in the raw HTML, independently of the parser."""

    async def fetch():
        total = 0
        async with aiohttp.ClientSession() as session:
            for page in range(1, MAX_PAGES + 1):
                async with session.get(
                    FAILURES_URL, params={"page": page}, ssl=coordinator._SSL_CONTEXT
                ) as resp:
                    resp.raise_for_status()
                    soup = BeautifulSoup(await resp.text(), "html.parser")
                count = len(soup.select(".failure-item"))
                if not count:
                    break
                total += count
        return total

    return asyncio.run(fetch())
