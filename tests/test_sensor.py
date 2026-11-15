"""Type-specific entities: Vivo optical power must not inherit Claro RF/uptime."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch


class SensorSelectionTests(unittest.TestCase):
    def test_modem_types_expose_only_confirmed_measurements(self):
        names = [
            "homeassistant",
            "homeassistant.components",
            "homeassistant.components.sensor",
            "homeassistant.const",
            "homeassistant.helpers",
            "homeassistant.helpers.device_registry",
            "homeassistant.helpers.update_coordinator",
        ]
        mods = {name: types.ModuleType(name) for name in names}
        mods["homeassistant.components.sensor"].SensorEntity = type("SensorEntity", (), {})
        mods["homeassistant.components.sensor"].SensorEntityDescription = (
            lambda **kw: types.SimpleNamespace(**kw)
        )
        mods["homeassistant.components.sensor"].SensorStateClass = types.SimpleNamespace(
            MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing"
        )
        mods["homeassistant.const"].EntityCategory = types.SimpleNamespace(DIAGNOSTIC="diagnostic")
        mods["homeassistant.const"].UnitOfTime = types.SimpleNamespace(SECONDS="s")
        mods["homeassistant.helpers.device_registry"].DeviceInfo = dict
        mods["homeassistant.helpers.update_coordinator"].CoordinatorEntity = type(
            "CoordinatorEntity", (), {}
        )
        with patch.dict(sys.modules, mods):
            module = importlib.import_module("custom_components.isp_modem.sensor")
            claro = {x.key for x in module.descriptions_for_type("claro_tc7337")}
            vivo = {x.key for x in module.descriptions_for_type("vivo_gpt2741")}
            self.assertIn("uptime_seconds", claro)
            self.assertIn("downstream_channels", claro)
            self.assertNotIn("uptime_seconds", vivo)
            self.assertNotIn("downstream_channels", vivo)
            self.assertEqual(
                vivo,
                {"model", "software_version", "hardware_version", "optical_rx_dbm", "optical_tx_dbm"},
            )
        sys.modules.pop("custom_components.isp_modem.sensor", None)


if __name__ == "__main__":
    unittest.main()
