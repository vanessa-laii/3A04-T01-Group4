#!/usr/bin/env python3

import datetime
import json
import sys
import time

import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 9999
MQTT_QOS = 1
MQTT_KEEPALIVE = 60
MQTT_TOPIC_PREFIX = "schemas/sensors"

DATA_FILE = "sensor_data.txt"
PUBLISH_INTERVAL = 1.0


def on_connect(client, userdata, flags, reason_code, _properties):
    if reason_code == 0:
        print("Connected to MQTT broker.")
    else:
        print(f"Connection refused — reason code {reason_code}")


def on_disconnect(client, userdata, _flags, reason_code, _properties):
    if reason_code != 0:
        print(f"Unexpected disconnect (reason_code={reason_code})")
    else:
        print("Disconnected from MQTT broker.")


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


def publish_tick(client: mqtt.Client, tick_records: list[dict], tick: int) -> None:
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    for record in tick_records:
        payload = dict(record)
        payload["timestamp"] = timestamp
        del payload["tick"]

        topic = f"{MQTT_TOPIC_PREFIX}/{record['sensorID']}"
        info = client.publish(
            topic,
            json.dumps(payload, ensure_ascii=False),
            qos=MQTT_QOS,
            retain=False,
        )

        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[t={tick:02d}] SENT     {record['sensorID']:<16}  topic={topic}")
        else:
            print(f"[t={tick:02d}] FAILED   {record['sensorID']:<16}  rc={info.rc}")


def main() -> None:
    ticks = load_records(DATA_FILE)
    num_ticks = len(ticks)
    print(f"Loaded {sum(len(t) for t in ticks)} records across {num_ticks} ticks from {DATA_FILE}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id="schemas-sensor-sender-v1",
                         protocol=mqtt.MQTTv311,
                         clean_session=True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    print(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT} ...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
    client.loop_start()

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"--- Cycle {cycle} start ---")
            for tick in range(num_ticks):
                tick_start = time.monotonic()
                publish_tick(client, ticks[tick], tick)
                elapsed = time.monotonic() - tick_start
                sleep_time = max(0.0, PUBLISH_INTERVAL - elapsed)
                time.sleep(sleep_time)
            print(f"--- Cycle {cycle} complete ({num_ticks}s) — restarting ---")
    except KeyboardInterrupt:
        print("Interrupted — shutting down.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
