"""Manual restart button. Device uptime sensor confirms the result afterward."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from . import DOMAIN
from .reboot import RebootError, send_reboot


async def async_setup_entry(hass, entry, async_add_entities):
    # Read-only installs have no restart button until credentials are configured.
    if entry.data.get(CONF_USERNAME) and entry.data.get(CONF_PASSWORD):
        async_add_entities([ClaroRestartButton(hass, entry)])


class ClaroRestartButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass, entry):
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_restart"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            configuration_url=f"http://{entry.data[CONF_HOST]}/",
        )

    async def async_press(self) -> None:
        try:
            await self._hass.async_add_executor_job(
                send_reboot,
                self._entry.data[CONF_HOST],
                self._entry.data[CONF_USERNAME],
                self._entry.data[CONF_PASSWORD],
            )
        except RebootError as exc:
            raise HomeAssistantError(str(exc)) from None
