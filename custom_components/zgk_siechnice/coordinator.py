import logging
import ssl
from datetime import date, timedelta
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FAILURES_URL,
    MAX_PAGES,
)

_LOGGER = logging.getLogger(__name__)

_CA_BUNDLE = Path(__file__).parent / "cyber_folks_ca.pem"


def _build_ssl_context() -> ssl.SSLContext:
    """Return an SSLContext that trusts the cyber_Folks intermediate CA."""
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=str(_CA_BUNDLE))
    return ctx


_SSL_CONTEXT = _build_ssl_context()


class ZGKCoordinator(DataUpdateCoordinator[list[dict]]):
    """Coordinator that scrapes zgksiechnice.pl for failure/maintenance events."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        scan_minutes = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(minutes=scan_minutes),
        )
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> list[dict]:
        """Fetch all pages and parse failure items."""
        all_items: list[dict] = []

        for page_num in range(1, MAX_PAGES + 1):
            try:
                resp = await self._session.get(
                    FAILURES_URL,
                    params={"page": page_num},
                    timeout=aiohttp.ClientTimeout(total=15),
                    ssl=_SSL_CONTEXT,
                )
                resp.raise_for_status()
                html = await resp.text()
            except (aiohttp.ClientError, TimeoutError) as err:
                raise UpdateFailed(f"Error fetching page {page_num}: {err}") from err

            items = _parse_page(html)
            if not items:
                break
            all_items.extend(items)

        return all_items


def _parse_page(html: str) -> list[dict]:
    """Parse a single page of failure items from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []

    for el in soup.select(".failures-items .failure-item"):
        date_span = el.select_one(".failure-item-date span")
        city_span = el.select_one(".failure-item-address .city")
        addr_span = el.select_one(".failure-item-address .addresses")
        type_div = el.select_one(".failure-item-type")
        link_a = el.select_one(".failure-item-link a")

        if not date_span or not city_span:
            continue

        try:
            day, month, year = date_span.get_text(strip=True).split(".")
            event_date = date(int(year), int(month), int(day))
        except (ValueError, AttributeError):
            continue

        items.append(
            {
                "date": event_date,
                "city": city_span.get_text(strip=True),
                "addresses": addr_span.get_text(strip=True) if addr_span else "",
                "type": type_div.get_text(strip=True) if type_div else "",
                "url": link_a["href"] if link_a and link_a.has_attr("href") else "",
            }
        )

    return items
