"""Explicit manual buttons; Vivo reboot outcome remains unverified."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from . import CONF_MODEM_TYPE, DOMAIN, TYPE_CLARO, TYPE_VIVO
from .reboot import RebootError, send_reboot
from .vivo import VivoError, send_vivo_reboot


async def async_setup_entry(hass, entry, async_add_entities):
    if (
        entry.data.get(CONF_MODEM_TYPE, TYPE_CLARO) in (TYPE_CLARO, TYPE_VIVO)
        and entry.data.get(CONF_USERNAME)
        and entry.data.get(CONF_PASSWORD)
    ):
        async_add_entities([ISPModemRestartButton(hass, entry)])


class ISPModemRestartButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        if entry.data.get(CONF_MODEM_TYPE, TYPE_CLARO) == TYPE_VIVO:
            self._attr_name = "Restart (experimental)"
        self._attr_unique_id = f"{entry.unique_id}_restart"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            configuration_url=f"http://{entry.data[CONF_HOST]}/",
        )

    async def async_press(self) -> None:
        try:
            modem_type = self._entry.data.get(CONF_MODEM_TYPE, TYPE_CLARO)
            if modem_type not in (TYPE_CLARO, TYPE_VIVO):
                raise HomeAssistantError("Unsupported modem type")
            await self._hass.async_add_executor_job(
                send_vivo_reboot if modem_type == TYPE_VIVO else send_reboot,
                self._entry.data[CONF_HOST],
                self._entry.data[CONF_USERNAME],
                self._entry.data[CONF_PASSWORD],
            )
        except (RebootError, VivoError) as exc:
            raise HomeAssistantError(str(exc)) from None
