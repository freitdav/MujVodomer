# Můj Vodoměr Chýně – Home Assistant Integration

Simple custom integration that brings your **Chýně water meter**[](https://chyne.mujvodomer.cz) into Home Assistant.

### Features
- **Total water consumption** (m³) usable for **Energy dashboard**
- **Last reading delta water consumption** – exact delta from last reading (as shown on the portal)
- Config flow with login test

### Requires Python dependencies:
- BeautifulSoup4
- Requests
- Lxml

### Installation
1. Copy the `mujvodomer` folder into your `custom_components/` directory
2. Restart HA
3. Go to **Settings → Devices & Services → + Add Integration → Muj Vodomer**
4. Enter your portal credentials

### Entities created
- `sensor.xxx_total_water_consumption` (Energy dashboard ready)
- `sensor.xxx_delta_water_consumption` (today’s usage)

### Energy Dashboard
Just go to **Energy → Water** and select **Total Water Consumption – Můj Vodoměr Chýně** – it will be accepted without warnings.
