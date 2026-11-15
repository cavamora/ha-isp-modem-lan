"""Experimental ISP modem local status and manual reboot integration."""

from __future__ import annotations

DOMAIN = "isp_modem"
CONF_MODEM_TYPE = "modem_type"
TYPE_CLARO = "claro_tc7337"
TYPE_VIVO = "vivo_gpt2741"
PLATFORMS = ["sensor", "button"]


async def async_setup_entry(hass, entry):
    from .coordinator import ISPModemCoordinator

    coordinator = ISPModemCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return result
