"""Experimental ISP modem local status integration (no reboot capability yet)."""
from __future__ import annotations

DOMAIN = "isp_modem"
PLATFORMS = ["sensor"]


async def async_setup_entry(hass, entry):
    from .coordinator import ClaroCoordinator

    coordinator = ClaroCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return result
