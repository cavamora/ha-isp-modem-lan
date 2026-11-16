"""Config-flow regression checks with minimal HA stubs; no network or secrets."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_vivo_credentials_validate_in_executor_and_store_type(self):
        modules = {name: types.ModuleType(name) for name in (
            "aiohttp", "voluptuous", "homeassistant", "homeassistant.config_entries",
            "homeassistant.const", "homeassistant.helpers", "homeassistant.helpers.selector",
            "homeassistant.helpers.aiohttp_client",
        )}
        modules["aiohttp"].ClientError = type("ClientError", (Exception,), {})
        modules["voluptuous"].Schema = lambda value: value
        modules["voluptuous"].Required = lambda name, **kwargs: name
        modules["voluptuous"].Optional = lambda name, **kwargs: name
        modules["voluptuous"].In = lambda options: options
        constants = modules["homeassistant.const"]
        constants.CONF_HOST = "host"
        constants.CONF_USERNAME = "username"
        constants.CONF_PASSWORD = "password"
        selector = modules["homeassistant.helpers.selector"]
        selector.TextSelector = lambda *args: str
        selector.TextSelectorConfig = lambda **kwargs: kwargs
        selector.TextSelectorType = types.SimpleNamespace(PASSWORD="password")
        modules["homeassistant.helpers"].selector = selector
        modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = (
            lambda hass: "session"
        )

        class ConfigFlow:
            def __init_subclass__(cls, **kwargs):
                pass

            async def async_set_unique_id(self, uid):
                self.unique_id = uid

            def _abort_if_unique_id_configured(self):
                pass

            def async_create_entry(self, title, data):
                return {"type": "entry", "title": title, "data": data}

            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}

        modules["homeassistant.config_entries"].ConfigFlow = ConfigFlow
        modules["homeassistant.config_entries"].OptionsFlowWithReload = ConfigFlow
        modules["homeassistant"].config_entries = modules["homeassistant.config_entries"]

        class HA:
            def __init__(self):
                self.executed = []

            async def async_add_executor_job(self, fn, *args):
                self.executed.append((fn, args))
                return fn(*args)

        with patch.dict(sys.modules, modules):
            flow_module = importlib.import_module("custom_components.isp_modem.config_flow")
            try:
                class FakeVivo:
                    def __init__(self, host, username, password):
                        self.args = host, username, password

                    def status(self):
                        return {"model": "GPT-2741GNAC-N1"}

                with patch.object(flow_module, "VivoModemClient", FakeVivo):
                    flow = flow_module.ISPModemConfigFlow()
                    flow.hass = HA()
                    result = await flow.async_step_user({
                        "host": "192.0.2.2", "username": "u", "password": "p",
                        "modem_type": "vivo_gpt2741",
                    })
                    self.assertEqual(result["type"], "entry")
                    self.assertEqual(result["title"], "Vivo modem (192.0.2.2)")
                    self.assertEqual(result["data"]["modem_type"], "vivo_gpt2741")
                    self.assertIs(result["data"]["poll_status"], True)
                    self.assertEqual(len(flow.hass.executed), 1)
                    self.assertEqual(flow.hass.executed[0][1], ())
                    self.assertIsNotNone(flow.hass.executed[0][0].__self__)

                    flow = flow_module.ISPModemConfigFlow()
                    flow.hass = HA()
                    form = await flow.async_step_user({
                        "host": "192.0.2.2", "modem_type": "vivo_gpt2741"
                    })
                    self.assertEqual(form["type"], "form")
                    self.assertEqual(form["errors"]["base"], "credentials_required")
                    self.assertEqual(flow.hass.executed, [])

                    class NoPollingVivo:
                        def __init__(self, *args):
                            raise AssertionError("No modem client should be built")

                    class NoPollingClaro:
                        def __init__(self, *args):
                            raise AssertionError("No modem client should be built")

                    with patch.object(flow_module, "VivoModemClient", NoPollingVivo), patch.object(
                        flow_module, "ClaroModemClient", NoPollingClaro
                    ):
                        for modem_type in ("vivo_gpt2741", "claro_tc7337"):
                            with self.subTest(modem_type=modem_type):
                                flow = flow_module.ISPModemConfigFlow()
                                flow.hass = HA()
                                result = await flow.async_step_user({
                                    "host": "192.0.2.2", "username": "u", "password": "p",
                                    "modem_type": modem_type, "poll_status": False,
                                })
                                self.assertEqual(result["type"], "entry")
                                self.assertIs(result["data"]["poll_status"], False)
                                self.assertEqual(flow.hass.executed, [])

                        flow = flow_module.ISPModemConfigFlow()
                        flow.hass = HA()
                        form = await flow.async_step_user({
                            "host": "192.0.2.2", "modem_type": "claro_tc7337",
                            "poll_status": False,
                        })
                        self.assertEqual(form["errors"]["base"], "credentials_required")

                    entry = types.SimpleNamespace(
                        data={"host": "192.0.2.2", "username": "u", "password": "p",
                              "modem_type": "claro_tc7337", "poll_status": True},
                        options={},
                    )
                    options_flow = flow_module.ISPModemConfigFlow.async_get_options_flow(entry)
                    options_flow.config_entry = entry  # Home Assistant injects this property.
                    options_form = await options_flow.async_step_init()
                    self.assertEqual(options_form["type"], "form")
                    result = await options_flow.async_step_init({"poll_status": False})
                    self.assertEqual(result["data"], {"poll_status": False})

                    entry.data["password"] = ""
                    options_flow = flow_module.ISPModemConfigFlow.async_get_options_flow(entry)
                    options_flow.config_entry = entry
                    form = await options_flow.async_step_init({"poll_status": False})
                    self.assertEqual(form["errors"]["base"], "credentials_required")
            finally:
                sys.modules.pop("custom_components.isp_modem.config_flow", None)


if __name__ == "__main__":
    unittest.main()
