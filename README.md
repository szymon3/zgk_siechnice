# ZGK Siechnice — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io)

Monitors the [ZGK Siechnice](https://zgksiechnice.pl) municipal water utility website for active water network **failures** (Awaria) and **planned maintenance** (Prace na sieci wodociągowej) in your area.

---

## Features

- Two binary sensors per configured location:
  - **Water failure** — `ON` when an unplanned outage is listed for your city/street
  - **Planned maintenance** — `ON` when scheduled works are listed for your city/street
- Configurable recency window (default: last 3 days)
- Configurable polling interval (default: every 60 minutes)
- Optional street-level filtering
- Full Polish and English UI translations
- City can be reconfigured without removing the entry

---

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/szymon3/zgk_siechnice` with category **Integration**
3. Find **ZGK Siechnice** in the list and click **Download**
4. Restart Home Assistant

### Manual

Copy `custom_components/zgk_siechnice/` into your HA `config/custom_components/` directory and restart.

---

## Configuration

1. **Settings → Devices & Services → Add Integration → ZGK Siechnice**
2. Fill in the form:

| Field | Required | Description |
|-------|----------|-------------|
| City | Yes | City/village name, e.g. `Iwiny` |
| Street | No | Street name for narrower matching, e.g. `Wiśniowa` |
| Days active | No | Events within this many days are treated as active (default: 3) |
| Update interval | No | Polling interval in minutes (default: 60) |

The integration creates a virtual device **ZGK Siechnice – {City}** with two binary sensors.

### Changing options

Go to **Settings → Devices & Services → ZGK Siechnice → Configure**. Changing any option automatically reloads the integration.

To change the monitored city, use **Settings → Devices & Services → ZGK Siechnice → ⋮ → Reconfigure**.

---

## Sensor attributes

Both sensors expose the following state attributes when active (`ON`):

| Attribute | Description |
|-----------|-------------|
| `matching_events` | Number of matching events found |
| `last_date` | Date of the most recent matching event (ISO 8601) |
| `last_description` | Address description from the most recent event |
| `last_url` | Direct link to the event page on zgksiechnice.pl |

---

## How it works

The integration scrapes `https://zgksiechnice.pl/awarie-i-wylaczenia` (paginated HTML, up to 10 pages × 10 items). Each item is parsed for city, street, event type, and date. Events are matched against your configured city/street and recency window. No API key or account required.

---

## Limitations

- Data is scraped from public HTML; if ZGK Siechnice changes their page layout the integration may need updating.
- Events are identified by date, city, and street text — there is no stable event ID from the source.
- Only covers the ZGK Siechnice service area (gmina Siechnice, Lower Silesia, Poland).

---

## License

MIT
