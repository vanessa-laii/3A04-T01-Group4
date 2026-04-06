#!/usr/bin/env python3

import datetime
import json
import os
import sys
import time
import urllib.request
import urllib.error

import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "9999"))
MQTT_TOPIC = "sensors/ingest"

API_URL = os.getenv("API_URL", "http://localhost:8003/api/v1/sensor/ingest")
DATA_FILE = "sensor_data.txt"
PUBLISH_INTERVAL = 1.0


def build_payload(record: dict) -> dict:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "source_id": record["sensorID"],
        "sensor_data": {
            "recorded_at": timestamp,
            "geographic_zone": record["region"],
            "gps_location": f"{record['latitude']},{record['longitude']}",
            "zone": record["zone"],
            "zoneID": record["zoneID"],
            "metrics": [
                {
                    "metric_type": reading["sensorType"],
                    "value": reading["sensorData"],
                    "unit": reading["unit"],
                }
                for reading in record["readings"].values()
            ],
        },
    }


def forward_to_api(payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[API]  SENT     {payload['source_id']:<16}  status={resp.status}")
    except urllib.error.HTTPError as e:
        print(f"[API]  FAILED   {payload['source_id']:<16}  status={e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"[API]  FAILED   {payload['source_id']:<16}  error={e.reason}")


def on_connect(client, _userdata, _flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected to broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[MQTT] Connection failed, rc={rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        forward_to_api(payload)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[MQTT] Bad message: {e}")


def load_records(path: str) -> list[list[dict]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: {path} not found. Run generate_data.py first.")
        sys.exit(1)

    records = [json.loads(line) for line in raw_lines]

    ticks: dict[int, list] = {}
    for record in records:
        t = record["tick"]
        ticks.setdefault(t, []).append(record)

    num_ticks = max(ticks.keys()) + 1
    return [ticks[t] for t in range(num_ticks)]


def main() -> None:
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()

    # Allow broker handshake and subscription to complete
    time.sleep(0.5)

    ticks = load_records(DATA_FILE)
    num_ticks = len(ticks)
    print(f"Loaded {sum(len(t) for t in ticks)} records across {num_ticks} ticks from {DATA_FILE}")
    print(f"Publishing to MQTT {MQTT_BROKER}:{MQTT_PORT}  topic={MQTT_TOPIC}")
    print(f"Forwarding to {API_URL}")

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"--- Cycle {cycle} start ---")
            for tick in range(num_ticks):
                tick_start = time.monotonic()
                for record in ticks[tick]:
                    payload = build_payload(record)
                    result = client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
                    print(f"[t={tick:02d}] PUBLISH  {record['sensorID']:<16}  mid={result.mid}")
                elapsed = time.monotonic() - tick_start
                time.sleep(max(0.0, PUBLISH_INTERVAL - elapsed))
            print(f"--- Cycle {cycle} complete ({num_ticks}s) — restarting ---")
    except KeyboardInterrupt:
        print("Interrupted — shutting down.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
