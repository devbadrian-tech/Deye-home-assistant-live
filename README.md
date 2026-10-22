# Deye Live

**English** | [繁體中文](README.zh-Hant.md)

### Your home's energy, directly from your inverter.

**Created by Adrian and Codex**

![Home Assistant](https://img.shields.io/badge/Home_Assistant_tested-2026.9.1-18BCF2?logo=homeassistant&logoColor=white)
![HACS Custom](https://img.shields.io/badge/HACS-Custom_repository-41BDF5)
![Read only](https://img.shields.io/badge/Inverter_access-Read_only-34856D)
![Local polling](https://img.shields.io/badge/Connection-Local_Modbus_TCP-34856D)

Deye Live is a Home Assistant custom integration with a bundled dashboard card.
It connects to a compatible Deye logger over your local network and shows house
consumption, grid import/export, battery power, battery percentage and solar
generation. No Deye Cloud account or Solarman V5 connection is required.

<p align="center"><img src="docs/deye-live-card.png" alt="Deye Live energy-flow card showing solar, home, grid, battery power and battery level" width="450"></p>

<p align="center"><em>Actual card screenshot with synthetic sample data.</em></p>

## At a glance

| Feature | What it does |
| --- | --- |
| Local readings | Polls the inverter every five seconds by default |
| Power-flow card | Shows direction of energy flow, power in W/kW and battery level |
| Battery limits | Shows charge/discharge current limits, low/shutdown/restart SOC and scheduled targets |
| Honest connection status | Clears readings when offline; marks old snapshots delayed and stops animations |
| Simple installation | One HACS integration includes both sensors and the card |
| Fits your dashboard | Light/dark themes, responsive layout, English and Traditional Chinese |
| Accessible | Keyboard navigation and reduced-motion support |
| Read-only operation | No inverter controls, write services, clock changes or firmware updates |

## Specifications

| Item | Specification |
| --- | --- |
| Inverter tested | Deye SUN-5K-SG04LP1-AU |
| Logger firmware tested | DYDA_WiBLE_1.7.2 |
| Register profile | Single-phase SG0xLP1 |
| Home Assistant | Minimum in HACS: 2026.9.1; tested on Core 2026.9.1 |
| Connection | Local standard Modbus TCP; default port 502, unit 1 |
| Power refresh | 5 seconds by default; configurable from 5–60 seconds |
| Battery-limit refresh | Once per minute; card hides limits older than 3 minutes |
| Entities | 19 sensors: 1 snapshot, 11 measurements, 7 battery-limit sensors |
| Access | Read only; integration uses Modbus function 03 |
| Languages | Automatic, English, Traditional Chinese; per-card selector in the next release |
| Display | Mobile/tablet layouts, light/dark themes, power-flow animation, reduced-motion support |
| License | [MIT](LICENSE) |

### Available readings

| Group | Readings | Units |
| --- | --- | --- |
| Power | House load, grid, battery, combined solar, PV1, PV2, inverter | W; card scales to kW |
| Battery | State of charge, voltage, current | %, V, A |
| Grid | Frequency | Hz |
| Current limits | Maximum charge and discharge current | A |
| Battery thresholds | Low, shutdown and restart SOC | % |
| Schedule | Minimum/maximum target sensors; six slots in snapshot/card | % and start times |
| Snapshot | Successful response time and card data | Timestamp + attributes |

Power sensors are not cumulative kWh meters for the Home Assistant Energy dashboard.

## Compatibility

**Hardware-tested:** Deye **SUN-5K-SG04LP1-AU** with a **DYDA_WiBLE_1.7.2** logger,
using standard **Modbus TCP on port 502**, unit **1**.

**Home Assistant tested:** Core **2026.9.1**. This is an early custom release,
not an official Deye or Home Assistant integration.

The decoder uses the single-phase **SG0xLP1** register layout. Do not use it for
three-phase, high-voltage or different register-map variants. Other models in
the same family are not independently hardware-verified.

The logger must already provide a local Modbus TCP service. Some WiBLE loggers
expose this through **Link2 → Modbus TCP**. This integration does not enable or
reconfigure the logger. Its existing cloud connection can remain in place.

## Enable local Modbus TCP on the logger

These steps apply to the tested WiBLE logger firmware. Menu labels can differ
on other models. This is a one-time manual logger configuration change; the
integration itself only reads data.

1. Find the logger's current IP in your router's connected-device list. Reserve
   that address so it does not change later.
2. On the same LAN, open `http://<LOGGER_IP>/` in a browser and sign in using your
   own logger credentials. Do not publish passwords or screenshots with credentials.
3. Open the logger's link/connection settings and select **Link2**.
4. Choose **Modbus TCP → Default**. Keep **Link1** on its existing Deye Cloud
   connection. Leave other settings at their existing values unless the logger's
   documentation requires a change.
5. Apply/save the setting. The tested logger warns that applying it restarts the
   logger; wait for it to reconnect to your network.
6. In Deye Live, connect to the logger's LAN IP with **port 502** and **unit 1**.
   A successful setup validates the inverter identity and reads live power registers.

Modbus TCP is unencrypted and can also be used to write settings by other
clients. Enable it only on a trusted LAN; never forward port 502 to the internet.
If Link2 or Modbus TCP is missing, check the logger's own model/firmware
instructions; Solarman V5 and transparent Modbus TCP are different protocols.

## Install with HACS

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/devbadrian-tech/Deye-home-assistant-live` and select **Integration**.
3. Find **Deye Live** in HACS and download it.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration → Deye Live**.
6. Enter your logger's local IP, TCP port and Modbus unit. Start with **502**,
   **1** and a **5-second** update interval. Leave direction reversal off unless
   your installation uses the opposite sign convention.

Setup checks the inverter family, serial and power registers before accepting
the connection. The serial identifies the device; subsequent polls reject an
unexpected device if the IP address changes.

<details>
<summary>Manual installation</summary>

Copy `custom_components/deye_live` into the `custom_components` directory in your
Home Assistant configuration folder, then restart HA and add the integration.
The resulting path must be `/config/custom_components/deye_live/manifest.json`.
Some File editor installations display `/homeassistant` instead of `/config`.

</details>

### Connection settings

After setup, open **Settings → Devices & services → Deye Live → Configure**.

| Setting | Default | Purpose / allowed values |
| --- | --- | --- |
| Host | Required | Logger's local IP address or hostname |
| Port | `502` | TCP service port; 1–65535 |
| Unit | `1` | Modbus unit; 1–247 |
| Update interval | `5` seconds | Power polling; 5–60 seconds |
| Reverse grid direction | Off | Reverse displayed import/export sign |
| Reverse battery direction | Off | Reverse displayed charge/discharge sign |

## Add the card

Refresh your browser after adding the integration. Edit a dashboard, choose
**Add card → Deye Live**, then select the **Live snapshot** sensor for your inverter.
The visual editor lets you choose the card language, set a title and show/hide
solar and battery limits. Under **Card language**, choose **Follow Home Assistant**
(the default), **English**, or **繁體中文**. Each card can use its own language.

The integration serves and registers the card automatically. You normally do
not need a second HACS download or a manual dashboard resource.

```yaml
type: custom:deye-live-card
entity: sensor.deye_live_XXXX_live_snapshot
title: Home energy
language: auto
show_solar: true
show_limits: true
```

Replace `XXXX` with the actual entity ID shown in Home Assistant. If a customized
frontend prevents automatic loading, register `/deye_live/deye-live-card.js?v=0.1.0&dashboard=1`
as a **JavaScript module** under Dashboard Resources, then refresh the browser.

### Card settings

| YAML key | Default | Purpose / choices |
| --- | --- | --- |
| `type` | Required | `custom:deye-live-card` |
| `entity` | Required | Deye Live snapshot sensor |
| `title` | Translated heading | Optional custom title, kept exactly as entered |
| `language` | `auto` | `auto` follows Home Assistant; `en` English; `zh-Hant` Traditional Chinese |
| `show_solar` | `true` | Show or hide solar |
| `show_limits` | `true` | Show or hide battery limits |

For YAML configuration, use `language: auto`, `language: en`, or
`language: zh-Hant`. Automatic mode follows the viewing user's Home Assistant
language and falls back to English for unsupported languages. Language applies
to the card labels, status messages, battery limits, and editor; a custom `title`
is kept exactly as entered. Existing cards without `language` use automatic mode.
This option is prepared for the next release; the published 0.1.0 release does
not include the language selector yet.

## Understanding the readings

- **House:** current load power.
- **Grid:** positive means importing; negative means exporting.
- **Battery:** positive means discharging; negative means charging.
- **Solar:** combined PV1 and PV2 power.
- **Battery level:** the inverter's reported state of charge.

Direction-reversal options only change how values are interpreted. They do not
change inverter operation. Battery discharge has been observed on the tested
hardware. Charging and grid import/export directions are covered by synthetic
tests but have not all been exercised on that hardware.

Power values need not balance exactly: conversion losses and measurement timing
can produce differences. The sensors report power, not cumulative energy; they
are not kWh meters for the Home Assistant Energy dashboard.

### Battery limits are distinct settings

| Displayed value | Meaning |
| --- | --- |
| Maximum charge/discharge current | Configured inverter current limit in amperes |
| Low battery | Configured low-SOC threshold |
| Shutdown | Configured shutdown SOC |
| Restart | Configured restart SOC |
| Scheduled targets | Lowest/highest SOC target and the six configured schedule slots |

**A scheduled SOC target is not a hard maximum-charge protection.** Battery BMS
limits and other operating settings may impose additional constraints. This
release does not claim to read every protection or the instantaneous effective
BMS current allowance. All these settings are displayed read-only.

## What “Live” means

The card uses a timestamp from each successful local response, even when power
values remain unchanged. It does not rely on the sensor's `last_changed` value.

- A failed power poll marks entities unavailable and clears the current values.
- If updates stop, the last sample is marked delayed after three poll intervals
  (at least 15 seconds), and flow animations stop.
- Limits are read once a minute. Missing optional limits do not hide valid power
  readings, and the card rejects limit data older than three minutes.
- Missing readings display a dash, never a fabricated zero.

The logger does not expose the inverter's measurement acquisition timestamp.
“Live” therefore means a fresh local reply; internal logger caching cannot be
independently timed. Sequential register reads are not an atomic snapshot.

## Read-only by design

Every integration request is a Modbus **function 03 read**. The bundled transport
rejects write functions before opening a connection and validates transaction,
unit, function, byte count and response length. It also supports read function 04
for transport tests, but the integration itself uses 03 only.

No control entities or write services are registered. No cloud login, analytics
or telemetry upload is included. Modbus TCP itself is an unencrypted local
protocol; keep it on your trusted LAN and do not expose port 502 to the internet.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Cannot connect | Logger IP, port, Modbus service and HA's network route to the logger |
| Unsupported device | The device must use the supported SG0xLP1 register profile |
| Card is missing | Refresh the browser after integration setup; check the resource instructions above |
| Power direction is reversed | Compare with the inverter display and adjust the relevant integration option |
| Battery limits show a dash | That field may be unsupported, invalid or temporarily unavailable |
| IP address changes | Use a DHCP reservation or update the integration options |

If version 0.1.0 intermittently reports **Custom element doesn't exist:
deye-live-card** after a refresh, edit its Dashboard Resource URL to
`/deye_live/deye-live-card.js?v=0.1.0&dashboard=1` (type: JavaScript module).
The distinct URL makes the dashboard evaluate the card after the frontend is
ready, even if the automatic loader ran too early. No HA restart is needed.
This addresses the [Home Assistant early-module registration race](https://github.com/home-assistant/frontend/issues/53890);
it does not change telemetry or inverter settings. Development builds also wait
for the frontend registry before defining the card and editor.

When reporting a problem, include the inverter model, logger firmware, HA
version and the error text. Remove IPs, serials, credentials and private readings
from anything you publish.

## Development and validation

The offline tests use synthetic data and do not connect to your LAN:

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.js
```

Coverage includes frontend startup, language selection, protocol framing,
rejection of writes, signed decoding,
identity changes, missing optional registers, polling limits, freshness and flow
direction. The initial release was also tested in the official HA 2026.9.1
container with real hardware: setup, **19 sensor entities**, fresh timestamps,
offline handling, recovery, duplicate prevention and unloading passed.

## Register-map references

The single-phase mapping was checked against these primary implementations:

- [SG0xLP1 register definition](https://github.com/davidrapan/ha-solarman/blob/main/custom_components/solarman/inverter_definitions/deye_hybrid.yaml)
- [Deye single-phase reader](https://github.com/kbialek/deye-inverter-mqtt/blob/main/src/deye_sensors_deye_hybrid.py)
- [Home Assistant custom-card documentation](https://contributors.home-assistant.io/frontend/custom-ui/card/)

The screenshot uses synthetic sample readings, not household telemetry.

## License and credits

Released under the [MIT License](LICENSE). You may use, modify and redistribute
this software under the terms in that file.

**Created by Adrian and Codex.**
