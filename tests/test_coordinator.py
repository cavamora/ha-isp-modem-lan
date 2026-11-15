"""Coordinator dispatch checks with HA stubs and no modem traffic."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_vivo_poll_runs_in_executor_and_legacy_entry_uses_claro(self):
        names = (
            "aiohttp", "homeassistant", "homeassistant.const", "homeassistant.helpers",
            "homeassistant.helpers.aiohttp_client", "homeassistant.helpers.update_coordinator",
        )
        mods = {name: types.ModuleType(name) for name in names}
        mods["aiohttp"].ClientError = type("ClientError", (Exception,), {})
        constants = mods["homeassistant.const"]
        constants.CONF_HOST = "host"
        constants.CONF_USERNAME = "username"
        constants.CONF_PASSWORD = "password"
        mods["homeassistant.helpers.aiohttp_client"].async_get_clientsession = lambda hass: "session"

        class DataUpdateCoordinator:
            def __class_getitem__(cls, item):
                return cls

            def __init__(self, hass, **kwargs):
                self.hass = hass

        mods["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = DataUpdateCoordinator
        mods["homeassistant.helpers.update_coordinator"].UpdateFailed = type("UpdateFailed", (Exception,), {})

        class HA:
            def __init__(self):
                self.executed = 0

            async def async_add_executor_job(self, fn, *args):
                self.executed += 1
                return fn(*args)

        class FakeVivo:
            def __init__(self, host, user, password):
                self.host = host

            def status(self):
                return {"model": "GPT-2741GNAC-N1"}

        class FakeClaro:
            def __init__(self, session, host, user, password):
                self.host = host

            async def status(self):
                return {"software_version": "claro"}

        with patch.dict(sys.modules, mods):
            module = importlib.import_module("custom_components.isp_modem.coordinator")
            try:
                with patch.object(module, "VivoModemClient", FakeVivo), patch.object(
                    module, "ClaroModemClient", FakeClaro
                ):
                    ha = HA()
                    vivo = module.ISPModemCoordinator(
                        ha, types.SimpleNamespace(data={
                            "host": "192.0.2.2", "username": "u", "password": "p",
                            "modem_type": "vivo_gpt2741",
                        })
                    )
                    self.assertEqual((await vivo._async_update_data())["model"], "GPT-2741GNAC-N1")
                    self.assertEqual(ha.executed, 1)

                    ha = HA()
                    claro = module.ISPModemCoordinator(
                        ha, types.SimpleNamespace(data={"host": "192.0.2.1"})
                    )
                    self.assertEqual((await claro._async_update_data())["software_version"], "claro")
                    self.assertEqual(ha.executed, 0)
            finally:
                sys.modules.pop("custom_components.isp_modem.coordinator", None)


if __name__ == "__main__":
    unittest.main()
