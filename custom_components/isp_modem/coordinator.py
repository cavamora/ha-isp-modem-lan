"""Poll only confirmed read-only modem status endpoints."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import CONF_MODEM_TYPE, TYPE_CLARO, TYPE_VIVO
from .client import ClaroModemClient, ModemResponseError
from .vivo import VivoError, VivoModemClient


class ISPModemCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass, entry):
        modem_type = entry.data.get(CONF_MODEM_TYPE, TYPE_CLARO)
        if modem_type not in (TYPE_CLARO, TYPE_VIVO):
            raise ValueError("Unsupported modem type")
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="ISP modem status",
            update_interval=timedelta(seconds=90),
        )
        self._modem_type = modem_type
        self.host = entry.data[CONF_HOST]
        self._username = entry.data.get(CONF_USERNAME, "")
        self._password = entry.data.get(CONF_PASSWORD, "")
        if modem_type == TYPE_CLARO:
            self._client = ClaroModemClient(
                async_get_clientsession(hass),
                self.host,
                self._username,
                self._password,
            )

    def _vivo_status(self) -> dict:
        return VivoModemClient(self.host, self._username, self._password).status()

    async def _async_update_data(self):
        try:
            if self._modem_type == TYPE_VIVO:
                return await self.hass.async_add_executor_job(self._vivo_status)
            return await self._client.status()
        except (aiohttp.ClientError, TimeoutError, ModemResponseError, VivoError) as exc:
            raise UpdateFailed(
                f"Modem status unavailable ({type(exc).__name__})"
            ) from exc
