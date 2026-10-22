"""Sensors only: no control entities and no write services."""
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# key, name, unit, device class, optional settings sensor
FIELDS = [
    ("load_power", "House power", "W", SensorDeviceClass.POWER, False),
    ("grid_power", "Grid power", "W", SensorDeviceClass.POWER, False),
    ("battery_power", "Battery power", "W", SensorDeviceClass.POWER, False),
    ("battery_soc", "Battery", "%", SensorDeviceClass.BATTERY, False),
    ("solar_power", "Solar power", "W", SensorDeviceClass.POWER, False),
    ("pv1_power", "PV1 power", "W", SensorDeviceClass.POWER, False),
    ("pv2_power", "PV2 power", "W", SensorDeviceClass.POWER, False),
    ("inverter_power", "Inverter power", "W", SensorDeviceClass.POWER, False),
    ("battery_voltage", "Battery voltage", "V", SensorDeviceClass.VOLTAGE, False),
    ("battery_current", "Battery current", "A", SensorDeviceClass.CURRENT, False),
    ("grid_frequency", "Grid frequency", "Hz", SensorDeviceClass.FREQUENCY, False),
    ("max_charge_current", "Maximum charge current", "A", SensorDeviceClass.CURRENT, True),
    ("max_discharge_current", "Maximum discharge current", "A", SensorDeviceClass.CURRENT, True),
    ("shutdown_soc", "Battery shutdown", "%", None, True),
    ("low_soc", "Battery low threshold", "%", None, True),
    ("restart_soc", "Battery restart", "%", None, True),
    ("schedule_target_min", "Lowest scheduled target", "%", None, True),
    ("schedule_target_max", "Highest scheduled target", "%", None, True),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities([DeyeSnapshot(coordinator)] + [DeyeSensor(coordinator, *f) for f in FIELDS])


class DeyeEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial)}, name=f"Deye Live {coordinator.serial[-4:]}",
            manufacturer="Deye", model="SUN SG0xLP1 (local Modbus)",
            serial_number=coordinator.serial,
        )


class DeyeSnapshot(DeyeEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:home-lightning-bolt-outline"
    # Snapshot payload is for the card. Individual measurement sensors retain history.
    _unrecorded_attributes = frozenset({"readings", "limits", "sampled_at", "request_started_at", "limits_read_at"})

    def __init__(self, coordinator):
        super().__init__(coordinator, "live_snapshot", "Live snapshot")

    @property
    def native_value(self):
        return datetime.fromisoformat(self.coordinator.data["sampled_at"])

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {"deye_live": True, "read_only": True, "poll_interval": self.coordinator.interval,
                "sampled_at": data["sampled_at"], "request_started_at": data["request_started_at"],
                "readings": data["readings"], "limits": data["limits"],
                "limits_read_at": data["limits_read_at"],
                "power_convention": "grid positive = import; battery positive = discharge"}


class DeyeSensor(DeyeEntity):
    def __init__(self, coordinator, key, name, unit, device_class, is_limit):
        super().__init__(coordinator, key, name)
        self.key, self.is_limit = key, is_limit
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if is_limit:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:shield-check-outline"
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data["limits" if self.is_limit else "readings"].get(self.key)

    @property
    def available(self):
        return super().available and self.native_value is not None
