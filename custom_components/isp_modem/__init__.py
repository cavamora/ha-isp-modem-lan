"""Experimental ISP modem local status and manual reboot integration."""

from __future__ import annotations

DOMAIN = "isp_modem"
CONF_MODEM_TYPE = "modem_type"
CONF_POLL_STATUS = "poll_status"
TYPE_CLARO = "claro_tc7337"
TYPE_VIVO = "vivo_gpt2741"
PLATFORMS = ["sensor", "button"]
BUTTON_PLATFORMS = ["button"]


def poll_status_enabled(entry):
    """Keep older entries polling; options may override the initial choice."""
    return entry.options.get(CONF_POLL_STATUS, entry.data.get(CONF_POLL_STATUS, True))


async def async_setup_entry(hass, entry):
    coordinator = None
    platforms = BUTTON_PLATFORMS
    if poll_status_enabled(entry):
        from .coordinator import ISPModemCoordinator

        coordinator = ISPModemCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        platforms = PLATFORMS
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass, entry):
    # Options may already have changed; unload the platforms actually set up.
    platforms = PLATFORMS if hass.data[DOMAIN][entry.entry_id] is not None else BUTTON_PLATFORMS
    result = await hass.config_entries.async_unload_platforms(entry, platforms)
    if result:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return result
