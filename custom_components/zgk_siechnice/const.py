from typing import Final

DOMAIN: Final = "zgk_siechnice"

BASE_URL: Final = "https://zgksiechnice.pl"
FAILURES_URL: Final = f"{BASE_URL}/awarie-i-wylaczenia"

CONF_CITY: Final = "city"
CONF_STREET: Final = "street"
CONF_DAYS_ACTIVE: Final = "days_active"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_DAYS_ACTIVE: Final = 3
DEFAULT_SCAN_INTERVAL: Final = 60  # minutes

TYPE_FAILURE: Final = "Awaria"

MAX_PAGES: Final = 10
