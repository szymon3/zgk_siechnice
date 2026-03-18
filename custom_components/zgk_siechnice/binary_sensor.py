from datetime import date

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ZGKConfigEntry
from .const import (
    BASE_URL,
    CONF_CITY,
    CONF_DAYS_ACTIVE,
    CONF_STREET,
    DEFAULT_DAYS_ACTIVE,
    DOMAIN,
    TYPE_FAILURE,
)
from .coordinator import ZGKCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZGKConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZGKCoordinator = entry.runtime_data
    async_add_entities(
        [
            ZGKFailureSensor(coordinator, entry),
            ZGKMaintenanceSensor(coordinator, entry),
        ]
    )


def _matching_events(
    events: list[dict],
    city: str,
    street: str,
    days_active: int,
    event_type_is_failure: bool,
) -> list[dict]:
    """Filter events by city/street, recency, and type."""
    today = date.today()
    result = []
    for ev in events:
        # Type filter
        is_failure = ev["type"].strip().lower() == TYPE_FAILURE.lower()
        if event_type_is_failure != is_failure:
            continue
        # City filter (case-insensitive)
        if city.lower() not in ev["city"].lower():
            continue
        # Street filter (optional substring)
        if street and street.lower() not in ev["addresses"].lower():
            continue
        # Recency filter
        if (today - ev["date"]).days > days_active:
            continue
        result.append(ev)
    return result


class ZGKBaseSensor(CoordinatorEntity[ZGKCoordinator], BinarySensorEntity):
    """Base class for ZGK binary sensors."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    _is_failure_type: bool  # set by subclasses

    def __init__(self, coordinator: ZGKCoordinator, entry: ZGKConfigEntry) -> None:
        super().__init__(coordinator)
        self._city = entry.data[CONF_CITY]
        self._entry = entry

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZGK Siechnice – {self._city}",
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="ZGK Siechnice",
            configuration_url=BASE_URL,
        )

    @property
    def _street(self) -> str:
        return self._entry.options.get(CONF_STREET, "")

    @property
    def _days_active(self) -> int:
        return self._entry.options.get(CONF_DAYS_ACTIVE, DEFAULT_DAYS_ACTIVE)

    @property
    def _events(self) -> list[dict]:
        if not self.coordinator.data:
            return []
        return _matching_events(
            self.coordinator.data,
            self._city,
            self._street,
            self._days_active,
            self._is_failure_type,
        )

    @property
    def is_on(self) -> bool:
        return len(self._events) > 0

    @property
    def extra_state_attributes(self) -> dict:
        events = self._events
        if not events:
            return {"matching_events": 0}

        latest = max(events, key=lambda e: e["date"])
        return {
            "matching_events": len(events),
            "last_date": latest["date"].isoformat(),
            "last_description": latest["addresses"],
            "last_url": f"{BASE_URL}/{latest['url']}" if latest["url"] else None,
        }


class ZGKFailureSensor(ZGKBaseSensor):
    """Binary sensor for water network failures (Awaria)."""

    _attr_translation_key = "failure"
    _is_failure_type = True

    def __init__(self, coordinator: ZGKCoordinator, entry: ZGKConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_failure"


class ZGKMaintenanceSensor(ZGKBaseSensor):
    """Binary sensor for planned maintenance (Prace na sieci)."""

    _attr_translation_key = "maintenance"
    _is_failure_type = False

    def __init__(self, coordinator: ZGKCoordinator, entry: ZGKConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_maintenance"
