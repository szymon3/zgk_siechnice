"""Live tests against zgksiechnice.pl.

No city or street is hardcoded: each run downloads the current listing,
derives the city and street a resident affected by each event would
configure, and checks the integration's sensors react to that event.
"""

import re
from datetime import date
from types import SimpleNamespace

import pytest
from conftest import live_events, live_item_count, make_entry

from zgk_siechnice.binary_sensor import ZGKFailureSensor, ZGKMaintenanceSensor
from zgk_siechnice.const import (
    DEFAULT_DAYS_ACTIVE,
    TYPE_FAILURE,
    TYPE_MAINTENANCE_PREFIX,
)

# Placeholder that must not match any listed location
NOWHERE = "Nieistniejąca"

# "ul. Polna, Leśna" -> "Polna"; "ulicy Miodowej nr 43" -> "Miodowej"
_STREET_RE = re.compile(r"\bul(?:\.|ic\w*)\s*([^,.;:()\-]+)", re.IGNORECASE)


def _sensor_class(ev: dict):
    if ev["type"] == TYPE_FAILURE:
        return ZGKFailureSensor
    if ev["type"].startswith(TYPE_MAINTENANCE_PREFIX):
        return ZGKMaintenanceSensor
    return None


def _location(ev: dict, localities: set[str]) -> tuple[str, str] | None:
    """City and first street a resident affected by the event would configure."""
    city = ev["city"].split(",")[0].strip()
    if not city:
        # City field left empty; the name is somewhere in the addresses text
        found = [n for n in localities if n.lower() in ev["addresses"].lower()]
        if not found:
            return None
        city = max(found, key=len)
    m = _STREET_RE.search(ev["addresses"])
    street = re.sub(r"\s+(nr\b.*|\d.*)$", "", m.group(1).strip()) if m else ""
    return city, street


def _matched(cls, ev: dict, city: str, street: str, days_active: int) -> bool:
    """Whether a sensor configured with city/street reports this event."""
    sensor = cls(SimpleNamespace(data=live_events()), make_entry(city, street, days_active))
    matched = ev in sensor._events
    assert not matched or sensor.is_on
    return matched


def _age(ev: dict) -> int:
    return max((date.today() - ev["date"]).days, 0)


def pytest_generate_tests(metafunc):
    if "event" not in metafunc.fixturenames:
        return
    events = live_events()
    localities = {
        n.strip() for ev in events for n in ev["city"].split(",") if n.strip()
    }
    params = []
    for ev in events:
        loc = _location(ev, localities)
        city, street = loc or ("?", "?")
        params.append(
            pytest.param(
                ev, loc, id=f"{ev['date']} {ev['type'][:6]} {city}/{street or '*'}"
            )
        )
    metafunc.parametrize("event,location", params)


# --- Parsing ----------------------------------------------------------------


def test_listing_not_empty():
    assert live_events(), "no events parsed from the listing"


def test_parser_keeps_every_item():
    """Each item in the raw HTML yields exactly one parsed event."""
    assert len(live_events()) == live_item_count()


def test_events_have_required_fields():
    for ev in live_events():
        assert ev["city"] or ev["addresses"], ev
        assert ev["type"], ev
        assert ev["url"], ev


def test_listing_has_known_event_types():
    assert any(_sensor_class(ev) for ev in live_events())


def test_placeholder_is_not_listed():
    for ev in live_events():
        assert NOWHERE.lower() not in f"{ev['city']} {ev['addresses']}".lower()


# --- Matching ---------------------------------------------------------------


def test_most_recent_event_with_default_window():
    """A resident of the newest event's location, with default options."""
    events = live_events()
    localities = {n.strip() for ev in events for n in ev["city"].split(",") if n.strip()}
    ev = max((e for e in events if _sensor_class(e)), key=lambda e: e["date"])
    city, street = _location(ev, localities)
    sensor = _sensor_class(ev)(
        SimpleNamespace(data=events), make_entry(city, street)
    )
    expected_on = _age(ev) <= DEFAULT_DAYS_ACTIVE
    assert (ev in sensor._events) == expected_on
    if expected_on:
        assert sensor.is_on
        assert sensor.extra_state_attributes["matching_events"] >= 1


def test_event_matches_its_location(event, location):
    cls = _sensor_class(event)
    if location is None:
        pytest.skip("city not identifiable from listing text")
    city, street = location
    days = _age(event)

    if cls is None:
        # Announcements and other types never switch a sensor on
        for sensor_cls in (ZGKFailureSensor, ZGKMaintenanceSensor):
            assert not _matched(sensor_cls, event, city, "", days)
        return

    other = ZGKMaintenanceSensor if cls is ZGKFailureSensor else ZGKFailureSensor

    assert _matched(cls, event, city, street, days)
    assert _matched(cls, event, city, "", days)
    assert not _matched(other, event, city, street, days)
    assert not _matched(cls, event, NOWHERE, street, days)
    if days > 0:
        assert not _matched(cls, event, city, street, days - 1)
    # Events naming streets only match those streets; others cover the city
    assert _matched(cls, event, city, NOWHERE, days) == (not street)
