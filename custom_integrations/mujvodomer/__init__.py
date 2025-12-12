import logging
from datetime import timedelta
import async_timeout
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .const import DOMAIN, LOGIN_URL, DATA_URL, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

# For HA < 2022.8 compatibility
try:
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
except ImportError:  # pragma: no cover
    async_get_clientsession = aiohttp_client.async_get_clientsession

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    coordinator = MujVodomerDataCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()
 
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class MujVodomerClient:
    def __init__(self, session, username, password):
        self.session = session
        self.username = username
        self.password = password
        self._logged_in = False

    async def login(self):
        try:
            async with async_timeout.timeout(20):
                resp = await self.session.get(LOGIN_URL)
                resp.raise_for_status()
                text = await resp.text()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, "lxml")
            csrf = soup.find("meta", {"name": "csrf-token"})
            if not csrf:
                raise ConfigEntryAuthFailed("CSRF token not found")

            csrf_token = csrf["content"]

            login_data = {
                "email": self.username,
                "password": self.password,
                "_token": csrf_token,
            }

            async with async_timeout.timeout(20):
                post_resp = await self.session.post(
                    LOGIN_URL,
                    data=login_data,
                    headers={"Referer": LOGIN_URL},
                    allow_redirects=False,
                )

            if post_resp.status == 302 or "heslo" not in (await post_resp.text()).lower():
                self._logged_in = True
                _LOGGER.debug("Login successful")
            else:
                _LOGGER.error("Login failed - invalid credentials or site changed")
                raise ConfigEntryAuthFailed("Invalid credentials")

        except Exception as err:
            self._logged_in = False
            raise ConfigEntryAuthFailed(f"Login failed: {err}") from err

    async def get_data(self):
        if not self._logged_in:
            await self.login()

        try:
            async with async_timeout.timeout(30):
                resp = await self.session.get(DATA_URL)
                resp.raise_for_status()
                text = await resp.text()
                self.last_html = text

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, "lxml")

            # 1. Current total consumption (big number shown above the table)
            total_elem = soup.find(string=lambda t: "Stav na vodom" in t)
            if not total_elem:
                raise UpdateFailed("Total consumption label not found")
            total_text = total_elem.find_next(string=True).strip()
            try:
                current_total = float(total_text.replace(",", "."))
            except:
                raise UpdateFailed(f"Cannot parse total: {total_text}")

            # 2. Delta consumption – directly available in the table, 4th column!
            delta = None
            table = soup.find("table")
            if table:
                first_row = table.find("tbody").find("tr") if table.find("tbody") else table.find("tr")
                if first_row:
                    cells = first_row.find_all("td")
                    if len(cells) >= 4:
                        delta_text = cells[3].get_text(strip=True)
                        try:
                            delta = float(delta_text.replace(",", "."))
                        except:
                            delta = None  # sometimes empty

            # 3. Last reading date/time
            date_elem = soup.find(string=lambda t: "Datum posledn" in t)
            last_update = None
            if date_elem:
                date_text = date_elem.find_next(string=True).strip()
                last_update = date_text.split(" ")[0]  # only date part

            return {
                "current_total": round(current_total, 3),
                "delta_consumption": round(delta, 3) if delta is not None else None,
                "last_update": last_update or "11.12.2025",
            }

        except Exception as err:
            self._logged_in = False
            _LOGGER.error("MujVodomer parsing failed: %s", err)
            raise UpdateFailed(f"Error parsing water meter data") from err

class MujVodomerDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_data):
        self.client = MujVodomerClient(
            session=async_get_clientsession(hass),
            username=config_data[CONF_USERNAME],
            password=config_data[CONF_PASSWORD],
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        try:
            return await self.client.get_data()
        except ConfigEntryAuthFailed as err:
            raise err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with portal: {err}") from err