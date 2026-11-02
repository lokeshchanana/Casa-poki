#!/usr/bin/env python3
"""
Party Audio to MQTT Bridge for Home Assistant
Captures audio from host sound devices (e.g. 3.5mm jack or USB microphone),
analyzes amplitude, frequency spectrum (bass, mid, treble), and beats,
and publishes real-time light signals to MQTT.
"""

import os
import sys
import time
import json
import queue
import signal
import colorsys
import logging
import numpy as np
import sounddevice as sd
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("party_mic_bridge")

# Configuration from environment variables
MQTT_HOST = os.getenv("MQTT_HOST", "192.168.1.251")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "party/audio").rstrip("/")
HA_DISCOVERY = os.getenv("HA_DISCOVERY", "true").lower() in ("true", "1", "yes")
HA_DISCOVERY_PREFIX = os.getenv("HA_DISCOVERY_PREFIX", "homeassistant").rstrip("/")

AUDIO_DEVICE = os.getenv("AUDIO_DEVICE", "auto")  # index, name substring, or 'auto'
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "44100"))
BLOCK_SIZE = int(os.getenv("BLOCK_SIZE", "2048"))  # ~46ms at 44.1kHz
PUBLISH_INTERVAL_MS = int(os.getenv("PUBLISH_INTERVAL_MS", "100"))  # 10 updates/sec
BEAT_COOLDOWN_MS = int(os.getenv("BEAT_COOLDOWN_MS", "140"))
BEAT_SENSITIVITY = float(os.getenv("BEAT_SENSITIVITY", "1.30"))
SENSITIVITY = float(os.getenv("SENSITIVITY", "1.5"))  # Gain multiplier
MIN_VOLUME_GATE = float(os.getenv("MIN_VOLUME_GATE", "0.035"))  # 3.5% noise floor gate

# Global control
running = True
mqtt_connected = False
party_mode_enabled = True  # Controlled via Home Assistant switch
audio_queue = queue.Queue(maxsize=30)

def handle_sigterm(signum, frame):
    global running
    logger.info("Received termination signal. Exiting gracefully...")
    running = False

signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)


def find_audio_device(target):
    """Find the best matching ALSA input device."""
    devices = sd.query_devices()
    logger.info("Available audio devices:")
    for idx, d in enumerate(devices):
        max_in = d.get("max_input_channels", 0)
        logger.info(f"  [{idx}] {d.get('name')} (inputs: {max_in}, default_samplerate: {d.get('default_samplerate')})")

    # If numeric index was provided
    if target.isdigit():
        idx = int(target)
        if idx < len(devices) and devices[idx].get("max_input_channels", 0) > 0:
            return idx
        logger.warning(f"Device index {idx} not valid or has 0 inputs. Falling back.")

    # If target is specific name substring
    if target.lower() not in ("auto", "default", ""):
        for idx, d in enumerate(devices):
            if target.lower() in d.get("name", "").lower() and d.get("max_input_channels", 0) > 0:
                logger.info(f"Matched target '{target}' to device [{idx}]: {d.get('name')}")
                return idx

    # Auto mode: Prefer ALC283 / Analog 3.5mm jack
    for idx, d in enumerate(devices):
        name = d.get("name", "").lower()
        if ("alc283" in name or "analog" in name) and d.get("max_input_channels", 0) > 0:
            logger.info(f"Auto-selected 3.5mm Analog input device [{idx}]: {d.get('name')}")
            return idx

    # Next prefer USB audio if present
    for idx, d in enumerate(devices):
        name = d.get("name", "").lower()
        if "usb" in name and d.get("max_input_channels", 0) > 0:
            logger.info(f"Auto-selected USB audio device [{idx}]: {d.get('name')}")
            return idx

    # Fallback to default input device
    default_dev = sd.default.device[0]
    if default_dev is not None and default_dev >= 0:
        logger.info(f"Using default system input device [{default_dev}]: {devices[default_dev].get('name')}")
        return default_dev

    # Any device with input channels
    for idx, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            logger.info(f"Fallback to input device [{idx}]: {d.get('name')}")
            return idx

    return None


def setup_mqtt():
    """Configure and connect MQTT client."""
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2 if hasattr(mqtt, "CallbackAPIVersion") else None,
        client_id=f"party-mic-bridge-{os.getpid()}"
    )

    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    # Last Will and Testament
    client.will_set(f"{MQTT_TOPIC_PREFIX}/status", payload="offline", qos=1, retain=True)

    def on_connect(c, userdata, flags, rc, properties=None):
        global mqtt_connected
        rc_val = getattr(rc, "value", rc)
        if rc_val == 0:
            mqtt_connected = True
            logger.info(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
            c.publish(f"{MQTT_TOPIC_PREFIX}/status", payload="online", qos=1, retain=True)
            c.publish(f"{MQTT_TOPIC_PREFIX}/enabled", payload="ON" if party_mode_enabled else "OFF", qos=1, retain=True)
            c.subscribe(f"{MQTT_TOPIC_PREFIX}/enabled/set", qos=1)
            if HA_DISCOVERY:
                publish_ha_discovery(c)
        else:
            mqtt_connected = False
            logger.error(f"MQTT connection failed with code: {rc}. Check MQTT_USER and MQTT_PASSWORD in .env")

    def on_message(c, userdata, msg):
        global party_mode_enabled
        payload = msg.payload.decode("utf-8").strip().upper()
        if msg.topic == f"{MQTT_TOPIC_PREFIX}/enabled/set":
            if payload in ("ON", "TRUE", "1"):
                party_mode_enabled = True
                logger.info("Party Mode turned ON via Home Assistant switch")
            else:
                party_mode_enabled = False
                logger.info("Party Mode turned OFF via Home Assistant switch")
            c.publish(f"{MQTT_TOPIC_PREFIX}/enabled", payload="ON" if party_mode_enabled else "OFF", qos=1, retain=True)

    def on_disconnect(c, userdata, flags, rc, properties=None):
        global mqtt_connected
        mqtt_connected = False
        logger.warning(f"Disconnected from MQTT broker (rc: {rc}). Retrying connection...")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=2, max_delay=15)

    logger.info(f"Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT} (User: {'[configured]' if MQTT_USER else '[none]'})")
    try:
        client.connect_async(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Failed to initiate MQTT connection: {e}")

    return client


def safe_publish(client, topic, payload, qos=0, retain=False):
    """Safely publish message if MQTT is connected."""
    if mqtt_connected:
        try:
            client.publish(topic, payload=payload, qos=qos, retain=retain)
        except Exception as e:
            logger.debug(f"Publish error on {topic}: {e}")


def publish_ha_discovery(client):
    """Publish Home Assistant MQTT Auto-Discovery entities."""
    device_info = {
        "identifiers": ["casa_poki_party_audio"],
        "name": "Casa-Poki Party Audio",
        "model": "ALSA Audio Reactive Bridge",
        "manufacturer": "Casa-Poki",
        "sw_version": "1.2.0"
    }

    # 1. Party Mode Switch
    safe_publish(
        client,
        f"{HA_DISCOVERY_PREFIX}/switch/party_audio/mode/config",
        payload=json.dumps({
            "name": "Party Mode",
            "unique_id": "party_audio_mode_switch",
            "state_topic": f"{MQTT_TOPIC_PREFIX}/enabled",
            "command_topic": f"{MQTT_TOPIC_PREFIX}/enabled/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:party-popper",
            "device": device_info
        }),
        retain=True
    )

    # 2. Music Active Sensor (ON when music plays, OFF when silent)
    safe_publish(
        client,
        f"{HA_DISCOVERY_PREFIX}/binary_sensor/party_audio/music_active/config",
        payload=json.dumps({
            "name": "Music Playing",
            "unique_id": "party_audio_music_active",
            "state_topic": f"{MQTT_TOPIC_PREFIX}/music_active",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:music",
            "device": device_info
        }),
        retain=True
    )

    # 3. Beat Binary Sensor
    safe_publish(
        client,
        f"{HA_DISCOVERY_PREFIX}/binary_sensor/party_audio/beat/config",
        payload=json.dumps({
            "name": "Audio Beat Detector",
            "unique_id": "party_audio_beat",
            "state_topic": f"{MQTT_TOPIC_PREFIX}/beat",
            "payload_on": "ON",
            "payload_off": "OFF",
            "icon": "mdi:music-note-eighth",
            "device": device_info
        }),
        retain=True
    )

    # 4. Color Sensor (HEX)
    safe_publish(
        client,
        f"{HA_DISCOVERY_PREFIX}/sensor/party_audio/hex_color/config",
        payload=json.dumps({
            "name": "Party Light Color",
            "unique_id": "party_audio_hex_color",
            "state_topic": f"{MQTT_TOPIC_PREFIX}/state",
            "value_template": "{{ value_json.hex }}",
            "icon": "mdi:palette",
            "device": device_info
        }),
        retain=True
    )

    # 5. Brightness Sensor
    safe_publish(
        client,
        f"{HA_DISCOVERY_PREFIX}/sensor/party_audio/brightness/config",
        payload=json.dumps({
            "name": "Party Audio Brightness",
            "unique_id": "party_audio_brightness",
            "state_topic": f"{MQTT_TOPIC_PREFIX}/state",
            "value_template": "{{ value_json.brightness }}",
            "icon": "mdi:brightness-6",
            "device": device_info
        }),
        retain=True
    )

    # 6. RMS Level Sensor
    safe_publish(
        client,
        f"{HA_DISCOVERY_PREFIX}/sensor/party_audio/rms/config",
        payload=json.dumps({
            "name": "Audio Volume RMS",
            "unique_id": "party_audio_rms",
            "state_topic": f"{MQTT_TOPIC_PREFIX}/state",
            "value_template": "{{ value_json.rms_pct }}",
            "unit_of_measurement": "%",
            "icon": "mdi:volume-high",
            "device": device_info
        }),
        retain=True
    )

    logger.info("Published Home Assistant MQTT Auto-Discovery entities")


def audio_callback(indata, frames, time_info, status):
    """Low-overhead sounddevice input stream callback."""
    if status:
        logger.debug(f"Audio status flag: {status}")
    if not audio_queue.full():
        audio_queue.put(indata.copy())


def main():
    logger.info("Starting Casa-Poki Party Audio Bridge...")
    device_idx = find_audio_device(AUDIO_DEVICE)
    if device_idx is None:
        logger.critical("No suitable ALSA input device found! Exiting.")
        sys.exit(1)

    mqtt_client = setup_mqtt()

    # Audio analysis state
    bass_history = []
    last_beat_time = 0.0
    last_publish_time = 0.0
    last_music_time = 0.0
    last_stat_log_time = time.time()
    color_hue_phase = 0.0
    music_active = False

    # Start audio input stream
    try:
        stream = sd.InputStream(
            device=device_idx,
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            callback=audio_callback
        )
    except Exception as e:
        logger.critical(f"Failed to open audio input stream on device [{device_idx}]: {e}")
        sys.exit(1)

    logger.info(f"Capturing audio stream on device [{device_idx}] at {SAMPLE_RATE} Hz (block size: {BLOCK_SIZE})...")

    with stream:
        while running:
            try:
                block = audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            # If Party Mode is turned OFF from Home Assistant, skip processing
            if not party_mode_enabled:
                time.sleep(0.05)
                continue

            now = time.time()

            # Flatten to 1D float32 array and apply sensitivity
            samples = block[:, 0] * SENSITIVITY

            # Calculate RMS
            rms = float(np.sqrt(np.mean(samples ** 2)))
            peak = float(np.max(np.abs(samples)))

            # Noise Gate: Check if signal is above background ambient noise
            is_above_noise = (rms >= MIN_VOLUME_GATE)

            if is_above_noise:
                last_music_time = now

            # Music playing state hysteresis (stays active for 1.2s after last audible sound)
            new_music_active = (now - last_music_time) < 1.2
            if new_music_active != music_active:
                music_active = new_music_active
                safe_publish(
                    mqtt_client,
                    f"{MQTT_TOPIC_PREFIX}/music_active",
                    payload="ON" if music_active else "OFF",
                    qos=1,
                    retain=True
                )
                logger.info(f"Music status changed: {'PLAYING' if music_active else 'STOPPED (Silence)'}")

            if not music_active:
                # Complete silence / song stopped
                bass, mid, treble = 0.0, 0.0, 0.0
                brightness = 0
                r, g, b = 0, 0, 0
                beat = False
            else:
                # FFT frequency band decomposition
                fft_vals = np.abs(np.fft.rfft(samples))
                freqs = np.fft.rfftfreq(len(samples), 1.0 / SAMPLE_RATE)

                # Frequency bands:
                # Bass: 20Hz - 250Hz
                # Mid: 250Hz - 2500Hz
                # Treble: 2500Hz - 10000Hz
                bass_mask = (freqs >= 20) & (freqs <= 250)
                mid_mask = (freqs > 250) & (freqs <= 2500)
                treble_mask = (freqs > 2500) & (freqs <= 10000)

                bass = float(np.mean(fft_vals[bass_mask])) if np.any(bass_mask) else 0.0
                mid = float(np.mean(fft_vals[mid_mask])) if np.any(mid_mask) else 0.0
                treble = float(np.mean(fft_vals[treble_mask])) if np.any(treble_mask) else 0.0

                # Normalization
                max_fft = max(bass, mid, treble, 1e-4)
                bass_norm = min(1.0, bass / max_fft)
                mid_norm = min(1.0, mid / max_fft)
                treble_norm = min(1.0, treble / max_fft)

                # Beat Detection (Only when audible sound is present)
                bass_history.append(bass)
                if len(bass_history) > 20:  # ~1 second history
                    bass_history.pop(0)

                avg_bass = np.mean(bass_history) if bass_history else 0.0
                beat = False
                if is_above_noise and (now - last_beat_time) > (BEAT_COOLDOWN_MS / 1000.0):
                    if bass > (avg_bass * BEAT_SENSITIVITY) and bass > 0.015:
                        beat = True
                        last_beat_time = now
                        # Advance color hue on beat for rhythmic visual variety
                        color_hue_phase = (color_hue_phase + 0.15) % 1.0

                # Dynamic Volume Scaling (subtracted noise floor)
                effective_vol = min(1.0, max(0.0, (rms - MIN_VOLUME_GATE) / (0.35 - MIN_VOLUME_GATE)))

                # Brightness: 0 when silent, scales from 50 to 255 with music volume
                brightness = int(50 + effective_vol * 205)

                # Color Synthesis
                r = int(min(255, max(0, bass_norm * 255 * (0.4 + effective_vol * 0.6))))
                g = int(min(255, max(0, mid_norm * 255 * (0.4 + effective_vol * 0.6))))
                b = int(min(255, max(0, treble_norm * 255 * (0.4 + effective_vol * 0.6))))

                # If pure RGB is too dim or unbalanced, blend with dynamic vibrant hue
                if (r + g + b) < 60:
                    hue_r, hue_g, hue_b = colorsys.hsv_to_rgb(color_hue_phase, 0.95, 1.0)
                    r = max(r, int(hue_r * 255 * (0.5 + effective_vol * 0.5)))
                    g = max(g, int(hue_g * 255 * (0.5 + effective_vol * 0.5)))
                    b = max(b, int(hue_b * 255 * (0.5 + effective_vol * 0.5)))

            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            rgb_list = [r, g, b]

            # Immediate beat publish
            if beat:
                safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/beat", payload="ON", qos=0)

            # Throttled state publish
            if (now - last_publish_time) >= (PUBLISH_INTERVAL_MS / 1000.0) or beat:
                last_publish_time = now

                payload = {
                    "rms": round(rms, 4),
                    "rms_pct": round(min(100.0, rms * 100 * 2), 1),
                    "peak": round(peak, 4),
                    "music_active": music_active,
                    "beat": beat,
                    "brightness": brightness,
                    "brightness_pct": round((brightness / 255.0) * 100, 1),
                    "rgb": rgb_list,
                    "rgb_str": f"{r},{g},{b}",
                    "hex": hex_color,
                    "timestamp": now
                }

                safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/state", payload=json.dumps(payload), qos=0)
                safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/rgb", payload=f"{r},{g},{b}", qos=0)
                safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/hex", payload=hex_color, qos=0)
                safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/brightness", payload=str(brightness), qos=0)

                # Reset beat signal
                if not beat:
                    safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/beat", payload="OFF", qos=0)

            # Periodic status log every 5 seconds
            if (now - last_stat_log_time) >= 5.0:
                last_stat_log_time = now
                mqtt_status = "Connected" if mqtt_connected else "Connecting/Awaiting Auth"
                logger.info(
                    f"[Audio Status] RMS: {round(min(100.0, rms * 100 * 2), 1)}% | "
                    f"Music: {'PLAYING' if music_active else 'SILENT'} | "
                    f"Brightness: {brightness}/255 | "
                    f"Color: {hex_color} | "
                    f"MQTT: {mqtt_status}"
                )

    # Cleanup
    logger.info("Stopping MQTT client...")
    safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/music_active", payload="OFF", qos=1, retain=True)
    safe_publish(mqtt_client, f"{MQTT_TOPIC_PREFIX}/status", payload="offline", qos=1, retain=True)
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    logger.info("Party Audio Bridge cleanly stopped.")

if __name__ == "__main__":
    main()
