# HomePort - Homey Pro Client for Sailfish OS

HomePort is a CLI and a native Sailfish OS application for interacting with and controlling **Homey Pro** and **Homey Cloud** smart home hubs.

The SailfishOS app follows the official [Homey Web API HTTP & Socket.IO specifications](https://api.developer.homey.app/http-and-socket.io/http-specification) and standard [Sailfish OS Application Development & Harbour guidelines](https://docs.sailfishos.org/Develop/Apps/).

---

## AI Usage

I heavily used AI to create this app - I was more in the product owner role, defining what it should do, testing it on my Jolla phone and handing over adaption, fix and feature request back to the JetBrains AI.
As this app is 80 percent mapping QML widgets to a Web API, this is the way to go for me in this case as that is mainly tedious, not interesting work and AI is mucher better in handling such work than I am.

The second reason is fo the AI use is speed to deployment - I want to use as few Android apps as possible on my Jolla phone and creating native SailfishOS apps to fill gaps in low-hanging fruit cases is a good approach for me here.

As I created this app out of personal need, you do not need to worry too much that I'll abandon it tomorrow, but of course I don't give any guarantees.

## Scope

Neither the CLI nor the app are meant to fully replace the official apps - if you need full control, use the web interface or the Android app.
The scope is to allow controlling already existing devices and flows.

---

## Features

- **Connection & Authentication**:
  - **Direct Local Connection**: Connect to Homey Pro on your local Wi-Fi network via local IP / hostname (`localUrlSecure` or `localUrl`) and a session token / API key.
  - **Athom Cloud OAuth2**: Connect via Athom Developer Client ID and secret to discover all Homey Pros associated with your Athom account, obtain delegation tokens, and create authenticated sessions.
  - **Automatic Failover**: Supports `local_secure` (`https://<ip-dashed>.homey.homeylocal.com`), `local` (`http://<ip>`), and `remote` (`https://<homey-id>.homey.eu-west-1.homeypro.net`) URLs.

- **Real-Time Updates via Socket.IO**:
  - Implements the Homey Socket.IO / Engine.IO protocol over WebSockets (`handshakeClient`, event subscriptions).
  - Subscribes to `homey:manager:flow`, `homey:manager:devices`, and individual `homey:device:<id>` capability streams for real-time UI state synchronization without polling.

- **Device Controls & Sensor Monitoring**:
  - Overview of all devices with fast search and category filtering (Lights, Sockets & Switches, Sensors, Thermostats, Speakers, etc.).
  - Quick inline controls: On/off toggles, brightness dimming sliders.
  - Dynamic Capability-Tailored Device Detail View:
    - Automatically matches each device's real capabilities without showing extraneous or incorrect controls.
    - Speakers / Media Players: Volume level slider, mute switch, playback controls (Play/Pause), and track navigation.
    - Thermostats: Target temperature controls with device-defined minimums and maximums, climate sensors.
    - Lights: Power toggles, brightness dimmers, color temperature (warm/cold), hue, and saturation.
    - Window Coverings & Blinds: Position sliders and state controls (Up, Stop, Down).
    - Locks & Switches: Smart door lock toggles and power socket controls.
    - Dynamic Sensor Readings: Temperature (°C), Humidity (%), Power consumption (W), Total energy (kWh), Battery (%), Atmospheric pressure (mbar), Luminance (lx), CO2 (ppm), CO (ppm), PM2.5 (µg/m³), Voltage (V), Current (A), Water/Gas meters, Wind speed/direction, and Rain.
    - Alarm Indicators: Motion detection, Contact/Door sensors, Smoke detectors, Water leakage, Tampering, CO/CO2 alarms, Heat alarms.

- **Security & Storage**:
  - Remembers user email/username, API tokens, client secrets, and direct connection URLs across app sessions.
  - Complies with official Sailfish OS storage security standards with restricted POSIX permissions (`0700` directories, `0600` files) in `$XDG_CONFIG_HOME/harbour-homeport` and atomic persistence.
  - Features configuration schema versioning and automatic migration from older config formats without data loss.
  - Supports `.env` and environment variables for local testing and CI/CD pipelines against live Homey backends.

- **Rooms & Zones**:
  - Browse your smart home by Zone / Room (Living Room, Kitchen, Bedroom, etc.) with device counts and room filtering.

- **Flows & Automations**:
  - List and trigger Homey flows with instant execution buttons.

- **Sailfish OS Native Integration**:
  - Sailfish Silica QML UI adhering to Jolla design guidelines.
  - PyOtherSide bridge connecting asynchronous Python backend with Qt/QML.
  - Multitasking **Cover Page** with live device & light status counters and quick refresh actions.
  - Sailjail sandboxing permissions (`Internet`, `Network`, `UserDirs`).

- **CLI Interface**:
  - Full-featured command-line interface for headless usage, debugging, and desktop testing.

---

## Project Structure

```
HomePort/
├── harbour-homeport.pro         # Qt / Sailfish QMake project configuration
├── harbour-homeport.desktop     # Sailfish OS desktop launcher & Sailjail metadata
├── rpm/
│   └── harbour-homeport.spec    # RPM packaging specification for Sailfish Harbour
├── src/
│   ├── harbour-homeport.cpp     # C++ SailfishApp entry point
│   ├── main.py                  # CLI Python entry point
│   └── homeport/
│       ├── __init__.py          # Package exports & version
│       ├── api.py               # Homey HTTP API client & Athom OAuth2
│       ├── socket.py            # Homey Socket.IO & WebSocket real-time client
│       ├── models.py            # Data models (Device, Zone, Flow, Capability)
│       ├── storage.py           # Persistent settings & token storage
│       ├── bridge.py            # PyOtherSide bridge for Silica QML
│       └── cli.py               # Command-line interface
├── qml/
│   ├── harbour-homeport.qml     # ApplicationWindow & PyOtherSide event handlers
│   ├── cover/
│   │   └── CoverPage.qml        # Sailfish multitasking cover
│   └── pages/
│       ├── MainPage.qml         # Dashboard & favorite devices
│       ├── DevicesPage.qml      # Device browser with search & filter
│       ├── DeviceDetailPage.qml # Deep capability & sensor inspector
│       ├── ZonesPage.qml        # Room & zone browser
│       ├── FlowsPage.qml        # Flow triggers
│       └── SettingsPage.qml     # OAuth & Direct connection setup
├── icons/                       # Application icons (86x86, 108x108, 128x128, 172x172)
├── tests/                       # Unit test suite
└── pyproject.toml               # Python project configuration
```

---

## Building for Sailfish OS

Using the official [Sailfish OS SDK (`sfdk`)](https://docs.sailfishos.org/Develop/Apps/):

```bash
# Set build target (e.g. 4.5.0.24 for aarch64 or i486 emulator)
sfdk config target=SailfishOS-4.5.0.24-aarch64

# Build RPM package
sfdk build

# Deploy to connected device or emulator
sfdk deploy --sdk
```

---

## Running the CLI

You can interact with your Homey Pro directly via the CLI:

```bash
# Check status
python3 -m homeport.cli status

# Connect directly to local Homey
python3 -m homeport.cli login --url "http://192.168.1.100" --token "<session-token>"

# List all devices
python3 -m homeport.cli devices

# Toggle a device on/off
python3 -m homeport.cli toggle <device-id>

# Set capability (e.g., dimming or target temperature)
python3 -m homeport.cli set-capability <device-id> dim 0.5
python3 -m homeport.cli set-capability <device-id> target_temperature 21.5

# List and trigger flows
python3 -m homeport.cli flows
python3 -m homeport.cli trigger-flow <flow-id>

# Stream real-time events over Socket.IO
python3 -m homeport.cli listen
```

---

## Running Tests

Run the complete unit test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

To run integration tests against a live Homey Pro backend, copy `EXAMPLE.env` to `.env` and set your credentials:

```bash
cp EXAMPLE.env .env
# Edit .env with your HOMEY_BASE_URL and HOMEY_SESSION_TOKEN
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

---

## License

MIT License.
