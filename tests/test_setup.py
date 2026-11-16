"""Entry lifecycle checks: disabling status must never contact a modem."""

import sys
import types
import unittest
from unittest.mock import patch

from custom_components import isp_modem


class SetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_polling_sets_up_only_button_without_first_refresh(self):
        calls = []
        coordinator_module = types.ModuleType("custom_components.isp_modem.coordinator")

        class Coordinator:
            def __init__(self, hass, entry):
                calls.append("coordinator created")

            async def async_config_entry_first_refresh(self):
                calls.append("status read")

        coordinator_module.ISPModemCoordinator = Coordinator

        class ConfigEntries:
            async def async_forward_entry_setups(self, entry, platforms):
                calls.append(("setup", tuple(platforms)))

            async def async_unload_platforms(self, entry, platforms):
                calls.append(("unload", tuple(platforms)))
                return True

        for modem_type in (isp_modem.TYPE_CLARO, isp_modem.TYPE_VIVO):
            with self.subTest(modem_type=modem_type), patch.dict(
                sys.modules, {"custom_components.isp_modem.coordinator": coordinator_module}
            ):
                calls.clear()
                hass = types.SimpleNamespace(data={}, config_entries=ConfigEntries())
                entry = types.SimpleNamespace(
                    entry_id=modem_type,
                    data={"modem_type": modem_type, "poll_status": False},
                    options={},
                )
                self.assertTrue(await isp_modem.async_setup_entry(hass, entry))
                self.assertEqual(calls, [("setup", ("button",))])
                self.assertTrue(await isp_modem.async_unload_entry(hass, entry))
                self.assertEqual(calls[-1], ("unload", ("button",)))

    async def test_legacy_entry_polls_by_default_and_unloads_original_platforms(self):
        calls = []
        coordinator_module = types.ModuleType("custom_components.isp_modem.coordinator")

        class Coordinator:
            def __init__(self, hass, entry):
                calls.append("coordinator created")

            async def async_config_entry_first_refresh(self):
                calls.append("status read")

        coordinator_module.ISPModemCoordinator = Coordinator

        class ConfigEntries:
            async def async_forward_entry_setups(self, entry, platforms):
                calls.append(("setup", tuple(platforms)))

            async def async_unload_platforms(self, entry, platforms):
                calls.append(("unload", tuple(platforms)))
                return True

        with patch.dict(sys.modules, {"custom_components.isp_modem.coordinator": coordinator_module}):
            hass = types.SimpleNamespace(data={}, config_entries=ConfigEntries())
            entry = types.SimpleNamespace(entry_id="legacy", data={}, options={})
            self.assertTrue(await isp_modem.async_setup_entry(hass, entry))
            self.assertEqual(calls, ["coordinator created", "status read", ("setup", ("sensor", "button"))])
            entry.options["poll_status"] = False  # Option changed before reload unloads the old platforms.
            self.assertTrue(await isp_modem.async_unload_entry(hass, entry))
            self.assertEqual(calls[-1], ("unload", ("sensor", "button")))
            calls.clear()
            self.assertTrue(await isp_modem.async_setup_entry(hass, entry))
            self.assertEqual(calls, [("setup", ("button",))])
            entry.options["poll_status"] = True
            self.assertTrue(await isp_modem.async_unload_entry(hass, entry))
            self.assertEqual(calls[-1], ("unload", ("button",)))
            calls.clear()
            self.assertTrue(await isp_modem.async_setup_entry(hass, entry))
            self.assertEqual(calls, ["coordinator created", "status read", ("setup", ("sensor", "button"))])
