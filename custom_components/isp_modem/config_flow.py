"""UI configuration for explicitly selected Claro and Vivo firmware families."""

from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import (
    CONF_MODEM_TYPE,
    CONF_POLL_STATUS,
    DOMAIN,
    TYPE_CLARO,
    TYPE_VIVO,
    poll_status_enabled,
)
from .client import ClaroModemClient, ModemResponseError, normalized_host
from .vivo import VivoError, VivoModemClient


class ISPModemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return ISPModemOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                host = normalized_host(user_input[CONF_HOST])
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                modem_type = user_input.get(CONF_MODEM_TYPE, TYPE_CLARO)
                poll_status = user_input.get(CONF_POLL_STATUS, True)
                username = user_input.get(CONF_USERNAME, "")
                password = user_input.get(CONF_PASSWORD, "")
                if (modem_type == TYPE_VIVO or not poll_status) and not (username and password):
                    errors["base"] = "credentials_required"
                elif modem_type not in (TYPE_CLARO, TYPE_VIVO):
                    errors[CONF_MODEM_TYPE] = "unsupported_modem"
                else:
                    try:
                        if poll_status:
                            if modem_type == TYPE_VIVO:
                                client = VivoModemClient(host, username, password)
                                await self.hass.async_add_executor_job(client.status)
                            else:
                                await ClaroModemClient(
                                    async_get_clientsession(self.hass),
                                    host,
                                    username,
                                    password,
                                ).status()
                    except (aiohttp.ClientError, TimeoutError, ModemResponseError, VivoError):
                        errors["base"] = "cannot_connect"
                    else:
                        await self.async_set_unique_id(host)
                        self._abort_if_unique_id_configured()
                        brand = "Vivo" if modem_type == TYPE_VIVO else "Claro"
                        return self.async_create_entry(
                            title=f"{brand} modem ({host})",
                            data={
                                CONF_HOST: host,
                                CONF_MODEM_TYPE: modem_type,
                                CONF_POLL_STATUS: poll_status,
                                CONF_USERNAME: username,
                                CONF_PASSWORD: password,
                            },
                        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEM_TYPE, default=TYPE_CLARO): vol.In(
                        {
                            TYPE_CLARO: "Claro / TC7337 firmware family",
                            TYPE_VIVO: "Vivo / GPT-2741GNAC-N1",
                        }
                    ),
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_POLL_STATUS, default=True): bool,
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


class ISPModemOptionsFlow(config_entries.OptionsFlowWithReload):
    """Allow existing entries to stop polling without losing the reset button."""

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            enabled = user_input[CONF_POLL_STATUS]
            data = self.config_entry.data
            if not enabled and not (data.get(CONF_USERNAME) and data.get(CONF_PASSWORD)):
                errors["base"] = "credentials_required"
            else:
                return self.async_create_entry(title="", data={CONF_POLL_STATUS: enabled})
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_POLL_STATUS, default=poll_status_enabled(self.config_entry)): bool,
            }),
            errors=errors,
        )
