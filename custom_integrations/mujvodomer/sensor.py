from __future__ import annotations
from .const import DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import callback

# Correct m3 
CUBIC_METERS = "m\u00b3"

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    total_sensor = MujVodomerTotalSensor(coordinator)
    delta_sensor = MujVodomerDeltaSensor(coordinator, total_sensor.entity_id)

    async_add_entities([total_sensor, delta_sensor])

class MujVodomerBaseSensor(SensorEntity):
    """Base class for both sensors."""
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_native_unit_of_measurement = CUBIC_METERS

    def __init__(self, coordinator):
        self.coordinator = coordinator

    # type: ignore

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class MujVodomerTotalSensor(MujVodomerBaseSensor):
    """Total water consumption."""

    _attr_name = "Total Water Consumption"
    _attr_icon = "mdi:water"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator):
        super().__init__(coordinator)
        username = coordinator.client.username.lower()
        self._attr_unique_id = f"{username}_total_water"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, username)},
            "name": "Vodomer",
            "manufacturer": "TS Chyne",
            "model": "Smart Metering",
        }

    @property
    def native_value(self):
        return self.coordinator.data.get("current_total") if self.coordinator.data else None

    @property
    def extra_state_attributes(self):
        return (
            {"last_reading_date": self.coordinator.data.get("last_update")}
            if self.coordinator.data
            else {}
        )


class MujVodomerDeltaSensor(MujVodomerBaseSensor):
    """Delta water consumption."""

    _attr_name = "Delta Water Consumption"
    _attr_icon = "mdi:water-pump"
    _attr_state_class = SensorStateClass.MEASUREMENT
    # This forces the entity to appear even if value is 0
    _attr_force_update = False

    def __init__(self, coordinator, parent_entity_id):
        super().__init__(coordinator)
        username = coordinator.client.username.lower()
        self._attr_unique_id = f"{username}_delta_water"
        
        # This ties the delta sensor to the same device as the total sensor
        self._attr_device_info = {
            "identifiers": {(DOMAIN, username)},
            # optional: shows parent entity name on the device card
            "via_device": (DOMAIN, username),
        }


    @property
    def native_value(self):
        """Return todays consumption - with fallback parsing if coordinator missed it."""
        if self.coordinator.data and self.coordinator.data.get("delta_consumption") is not None:
            return round(self.coordinator.data["delta_consumption"], 3)

        # Fallback: parse directly from the last known HTML (very rare, but makes entity appear instantly)
        try:
            from bs4 import BeautifulSoup
            if hasattr(self.coordinator, "last_html"):
                soup = BeautifulSoup(self.coordinator.last_html, "lxml")
                table = soup.find("table")
                if table:
                    first_row = table.find("tbody").find("tr")
                    if first_row:
                        cells = first_row.find_all("td")
                        if len(cells) >= 4:
                            val = cells[3].get_text(strip=True).replace(",", ".")
                            if val and val != "":
                                return round(float(val), 3)
        except:
            pass

        return 0.0  # entity always exists and shows 0.0 until real data arrives