"""Poll only confirmed read-only modem status endpoints."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ClaroModemClient, ModemResponseError


class ClaroCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="Claro modem status",
            update_interval=timedelta(seconds=90),
        )
        self.host = entry.data[CONF_HOST]
        self._client = ClaroModemClient(
            async_get_clientsession(hass),
            self.host,
            entry.data.get(CONF_USERNAME, ""),
            entry.data.get(CONF_PASSWORD, ""),
        )

    async def _async_update_data(self):
        try:
            return await self._client.status()
        except (aiohttp.ClientError, TimeoutError, ModemResponseError) as exc:
            raise UpdateFailed(
                f"Modem status unavailable ({type(exc).__name__})"
            ) from exc
