import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import aiohttp_client
from .const import DOMAIN
from .__init__ import MujVodomerClient


# Compatibility fix for old HA
try:
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
except ImportError:  # pragma: no cover
    async_get_clientsession = aiohttp_client.async_get_clientsession

class MujVodomerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = MujVodomerClient(
                session=session,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
            )

            try:
                await client.login()
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Muj Vodomer ({user_input[CONF_USERNAME]})",
                    data=user_input,
                )
            except Exception:
                errors["base"] = "auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )