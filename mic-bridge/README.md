# Casa-Poki Party Audio to MQTT Bridge

Real-time audio processing container that captures sound from the host 3.5mm audio jack (or USB microphone), computes music signals (RMS volume, FFT frequency bands: Bass, Mid, Treble, and beat transients), and publishes reactive light signals to the Home Assistant MQTT broker.

---

## Features

- **Direct Hardware Audio Capture**: Connects via ALSA directly to the onboard 3.5mm audio jack (`HDA Intel PCH: ALC283 Analog`, card 1) or USB audio (`MS2109`, card 0).
- **Audio Signal Analysis**:
  - **RMS Volume**: Overall energy and percentage.
  - **FFT Multi-Band Decomposition**:
    - **Bass** (20Hz - 250Hz)
    - **Mid** (250Hz - 2500Hz)
    - **Treble** (2500Hz - 10kHz)
  - **Beat Detection**: Dynamic thresholding on bass transients for rhythm-synced light triggers.
  - **Music Reactive RGB & Brightness**: Generates ready-to-use RGB values (`[r, g, b]`), Hex (`#RRGGBB`), and brightness (`0-255`).
- **Home Assistant MQTT Auto-Discovery**:
  Automatically creates Home Assistant sensors under device **"Casa-Poki Party Audio"**:
  - `sensor.party_audio_rms` (Volume %)
  - `sensor.party_audio_bass` (Bass %)
  - `sensor.party_audio_mid` (Mid %)
  - `sensor.party_audio_treble` (Treble %)
  - `sensor.party_audio_hex_color` (Hex Color)
  - `binary_sensor.party_audio_beat` (Beat detector ON/OFF)
- **Configurable Rate Limiting**: Defaults to 100ms (10 updates/sec) to avoid flooding the Home Assistant event loop or Zigbee mesh.

---

## File Structure

```text
/home/lokesh/Casa-poki/mic-bridge/   (also symlinked to /opt/mic_bridge)
├── bridge.py              # Main Python audio capture & MQTT publishing service
├── Dockerfile             # Container image definition with ALSA & PortAudio
├── docker-compose.yml     # Compose configuration with /dev/snd device mapping
├── requirements.txt       # Python dependencies (sounddevice, numpy, paho-mqtt, python-dotenv)
├── .env                   # Live environment configuration
├── .env.example           # Example environment template
└── README.md              # Documentation and Home Assistant automation examples
```

---

## Configuration (`.env`)

Edit `/home/lokesh/Casa-poki/mic-bridge/.env`:

```bash
# Home Assistant MQTT Broker
MQTT_HOST=192.168.1.251
MQTT_PORT=1883
MQTT_USER=your_ha_mqtt_username
MQTT_PASSWORD=your_ha_mqtt_password
MQTT_TOPIC_PREFIX=party/audio

# Home Assistant Auto-Discovery
HA_DISCOVERY=true
HA_DISCOVERY_PREFIX=homeassistant

# Audio Input Device (1 is ALC283 Analog 3.5mm jack; 0 is MS2109 USB)
AUDIO_DEVICE=1

# Audio Sampling
SAMPLE_RATE=44100
BLOCK_SIZE=2048

# Sensitivity Multipliers
SENSITIVITY=1.5
MIN_VOLUME_GATE=0.005
BEAT_SENSITIVITY=1.30
BEAT_COOLDOWN_MS=120

# Update rate (milliseconds)
PUBLISH_INTERVAL_MS=100
LOG_LEVEL=INFO
```

---

## Management Commands

Navigate to `/home/lokesh/Casa-poki/mic-bridge` (or `/opt/mic_bridge`):

```bash
# View live logs and audio metrics
sudo docker logs -f party-mic-bridge

# Restart container (e.g., after changing credentials in .env)
sudo docker compose restart

# Stop container
sudo docker compose down

# Start container
sudo docker compose up -d
```

---

## MQTT Topics

| Topic | Payload Format | Description |
|---|---|---|
| `party/audio/state` | JSON object | Full metrics object with RMS, Bass, Mid, Treble, Beat, RGB, Hex, Brightness |
| `party/audio/rgb` | `R,G,B` (e.g. `255,80,40`) | Direct RGB string |
| `party/audio/hex` | `#RRGGBB` (e.g. `#FF5028`) | Hex color code |
| `party/audio/brightness` | `0` - `255` | Recommended brightness level |
| `party/audio/beat` | `ON` or `OFF` | Beat transient trigger |
| `party/audio/status` | `online` or `offline` | MQTT availability status |

---

## Home Assistant Automation Examples

### Example 1: Update Living Room Lights on Beat

In Home Assistant (`automations.yaml` or UI Automation Editor):

```yaml
alias: "Party Lights - Flash on Beat"
trigger:
  - platform: state
    entity_id: binary_sensor.party_audio_beat
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room_lights
    data:
      rgb_color: >
        {% set rgb = state_attr('sensor.party_audio_state', 'rgb') %}
        {{ rgb if rgb else [255, 0, 100] }}
      brightness: 255
```

### Example 2: Continuous Music Reactive Light (MQTT Automation)

```yaml
alias: "Party Lights - Music Color Sync"
trigger:
  - platform: mqtt
    topic: "party/audio/state"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room_lights
    data:
      rgb_color: "{{ trigger.payload_json.rgb }}"
      brightness: "{{ trigger.payload_json.brightness }}"
      transition: 0.1
```
