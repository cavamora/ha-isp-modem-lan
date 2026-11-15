"""UI configuration for a known Claro status page family."""

from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import DOMAIN
from .client import ClaroModemClient, ModemResponseError, normalized_host


class ISPModemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                host = normalized_host(user_input[CONF_HOST])
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    await ClaroModemClient(
                        async_get_clientsession(self.hass),
                        host,
                        user_input.get(CONF_USERNAME, ""),
                        user_input.get(CONF_PASSWORD, ""),
                    ).status()
                except (aiohttp.ClientError, TimeoutError, ModemResponseError):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(host)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Claro modem ({host})",
                        data={
                            CONF_HOST: host,
                            CONF_USERNAME: user_input.get(CONF_USERNAME, ""),
                            CONF_PASSWORD: user_input.get(CONF_PASSWORD, ""),
                        },
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_USERNAME, default=""): str,
                    vol.Optional(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )
