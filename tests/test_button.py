"""Button wiring tested with HA stubs; no modem request is made."""

import importlib
import sys
import types
import unittest
from unittest.mock import patch


class ButtonTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_button_uses_executor_only_when_configured(self):
        names = [
            "homeassistant",
            "homeassistant.components",
            "homeassistant.components.button",
            "homeassistant.const",
            "homeassistant.helpers",
            "homeassistant.helpers.device_registry",
            "homeassistant.exceptions",
        ]
        mods = {name: types.ModuleType(name) for name in names}
        mods["homeassistant.components.button"].ButtonEntity = type(
            "ButtonEntity", (), {}
        )
        mods[
            "homeassistant.components.button"
        ].ButtonDeviceClass = types.SimpleNamespace(RESTART="restart")
        mods["homeassistant.const"].CONF_HOST = "host"
        mods["homeassistant.const"].CONF_USERNAME = "username"
        mods["homeassistant.const"].CONF_PASSWORD = "password"
        mods["homeassistant.const"].EntityCategory = types.SimpleNamespace(
            CONFIG="config"
        )
        mods["homeassistant.helpers.device_registry"].DeviceInfo = dict
        mods["homeassistant.exceptions"].HomeAssistantError = type(
            "HomeAssistantError", (Exception,), {}
        )
        with patch.dict(sys.modules, mods):
            module = importlib.import_module("custom_components.isp_modem.button")
            called = []

            class HA:
                async def async_add_executor_job(self, fn, *args):
                    called.append(args)

            hass = HA()
            entry = types.SimpleNamespace(
                unique_id="192.0.2.1",
                title="Modem",
                data={"host": "192.0.2.1", "username": "u", "password": "p"},
            )
            added = []
            await module.async_setup_entry(hass, entry, added.extend)
            self.assertEqual(len(added), 1)
            await added[0].async_press()
            self.assertEqual(called, [("192.0.2.1", "u", "p")])
            added.clear()
            entry.data["password"] = ""
            await module.async_setup_entry(hass, entry, added.extend)
            self.assertEqual(added, [])
        sys.modules.pop("custom_components.isp_modem.button", None)


if __name__ == "__main__":
    unittest.main()
