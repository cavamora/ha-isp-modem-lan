"""Observed, read-only status and RF aggregates (no subscriber identifiers)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

DESCRIPTIONS = (
    SensorEntityDescription(key="hardware_version", name="Hardware version", icon="mdi:chip"),
    SensorEntityDescription(key="software_version", name="Firmware version", icon="mdi:package-variant", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="network_access", name="Network access", icon="mdi:wan"),
    SensorEntityDescription(key="uptime_seconds", name="Uptime", native_unit_of_measurement=UnitOfTime.SECONDS, icon="mdi:clock-outline", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="downstream_channels", name="Downstream channels", icon="mdi:download-network"),
    SensorEntityDescription(key="upstream_channels", name="Upstream channels", icon="mdi:upload-network"),
    SensorEntityDescription(key="downstream_power_dbmv", name="Downstream power mean", native_unit_of_measurement="dBmV", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="downstream_snr_db", name="Downstream SNR mean", native_unit_of_measurement="dB", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="upstream_power_dbmv", name="Upstream power mean", native_unit_of_measurement="dBmV", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="corrected_total", name="Corrected codewords", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="uncorrectable_total", name="Uncorrectable codewords", state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(ClaroSensor(coordinator, entry, desc) for desc in DESCRIPTIONS)


class ClaroSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)}, name=entry.title,
            sw_version=coordinator.data.get("software_version"),
            configuration_url=f"http://{coordinator.host}/",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get(self.entity_description.key)
