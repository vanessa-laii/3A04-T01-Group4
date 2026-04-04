#!/usr/bin/env python3

import json
import math
import random
import sys

CYCLE_SECONDS = 60
OUTPUT_FILE = "sensor_data.txt"

ALERT_START = 30
ALERT_PEAK = 38
ALERT_END = 48

HAMILTON_LAT_MIN, HAMILTON_LAT_MAX = 43.13, 43.42
HAMILTON_LON_MIN, HAMILTON_LON_MAX = -80.15, -79.64

SENSOR_UNITS = {
    "Temperature": "°C",
    "Humidity": "%RH",
    "AirQuality": "AQI",
    "NoiseLevels": "dB",
    "ParticularMatter": "µg/m³",
}

ZONES = {
    "zone-downtown": {
        "zoneID": "550e8400-e29b-41d4-a716-446655440001",
        "zoneName": "Downtown Core",
        "region": "Central Hamilton",
    },
    "zone-harbour": {
        "zoneID": "550e8400-e29b-41d4-a716-446655440002",
        "zoneName": "Hamilton Harbour & Industrial",
        "region": "North Hamilton",
    },
    "zone-mountain": {
        "zoneID": "550e8400-e29b-41d4-a716-446655440003",
        "zoneName": "Hamilton Mountain",
        "region": "Upper Hamilton",
    },
    "zone-eastend": {
        "zoneID": "550e8400-e29b-41d4-a716-446655440004",
        "zoneName": "East End & Stoney Creek",
        "region": "East Hamilton",
    },
    "zone-westend": {
        "zoneID": "550e8400-e29b-41d4-a716-446655440005",
        "zoneName": "West End & Dundas",
        "region": "West Hamilton",
    },
    "zone-ancaster": {
        "zoneID": "550e8400-e29b-41d4-a716-446655440006",
        "zoneName": "Ancaster",
        "region": "Southwest Hamilton",
    },
}

SENSOR_DEFINITIONS = [
    {
        "sensorID": "SENSOR-DT-001",
        "zoneKey": "zone-downtown",
        "latitude": 43.2569,
        "longitude": -79.8713,
        "readings": {
            "Temperature": {"base": 9.2, "noise_std": 0.30},
            "Humidity": {"base": 64.0, "noise_std": 1.20},
            "AirQuality": {"base": 35.0, "noise_std": 2.50},
            "NoiseLevels": {"base": 69.0, "noise_std": 2.50},
            "ParticularMatter": {"base": 9.8, "noise_std": 1.00},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-DT-002",
        "zoneKey": "zone-downtown",
        "latitude": 43.2568,
        "longitude": -79.8700,
        "readings": {
            "Temperature": {"base": 9.0, "noise_std": 0.30},
            "Humidity": {"base": 66.0, "noise_std": 1.10},
            "AirQuality": {"base": 33.0, "noise_std": 2.00},
            "NoiseLevels": {"base": 63.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 9.2, "noise_std": 0.90},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-DT-003",
        "zoneKey": "zone-downtown",
        "latitude": 43.2561,
        "longitude": -79.8697,
        "readings": {
            "Temperature": {"base": 9.3, "noise_std": 0.30},
            "Humidity": {"base": 63.0, "noise_std": 1.20},
            "AirQuality": {"base": 40.0, "noise_std": 3.00},
            "NoiseLevels": {"base": 74.0, "noise_std": 3.00},
            "ParticularMatter": {"base": 11.5, "noise_std": 1.20},
        },
        "alerts": {
            "NoiseLevels": {"alertValue": 94.0},
        },
    },
    {
        "sensorID": "SENSOR-HR-001",
        "zoneKey": "zone-harbour",
        "latitude": 43.2762,
        "longitude": -79.8645,
        "readings": {
            "Temperature": {"base": 8.0, "noise_std": 0.35},
            "Humidity": {"base": 74.0, "noise_std": 1.40},
            "AirQuality": {"base": 50.0, "noise_std": 3.50},
            "NoiseLevels": {"base": 74.0, "noise_std": 3.00},
            "ParticularMatter": {"base": 15.0, "noise_std": 1.60},
        },
        "alerts": {
            "Humidity": {"alertValue": 97.4},
        },
    },
    {
        "sensorID": "SENSOR-HR-002",
        "zoneKey": "zone-harbour",
        "latitude": 43.2779,
        "longitude": -79.8692,
        "readings": {
            "Temperature": {"base": 8.2, "noise_std": 0.35},
            "Humidity": {"base": 72.0, "noise_std": 1.30},
            "AirQuality": {"base": 55.0, "noise_std": 4.00},
            "NoiseLevels": {"base": 78.0, "noise_std": 3.50},
            "ParticularMatter": {"base": 17.5, "noise_std": 1.80},
        },
        "alerts": {
            "AirQuality": {"alertValue": 178.0},
        },
    },
    {
        "sensorID": "SENSOR-HR-003",
        "zoneKey": "zone-harbour",
        "latitude": 43.2810,
        "longitude": -79.8615,
        "readings": {
            "Temperature": {"base": 7.9, "noise_std": 0.35},
            "Humidity": {"base": 76.0, "noise_std": 1.50},
            "AirQuality": {"base": 48.0, "noise_std": 3.50},
            "NoiseLevels": {"base": 76.0, "noise_std": 3.50},
            "ParticularMatter": {"base": 14.5, "noise_std": 1.50},
        },
        "alerts": {
            "ParticularMatter": {"alertValue": 67.3},
        },
    },
    {
        "sensorID": "SENSOR-MT-001",
        "zoneKey": "zone-mountain",
        "latitude": 43.2204,
        "longitude": -79.8742,
        "readings": {
            "Temperature": {"base": 6.8, "noise_std": 0.40},
            "Humidity": {"base": 72.0, "noise_std": 1.20},
            "AirQuality": {"base": 28.0, "noise_std": 2.00},
            "NoiseLevels": {"base": 50.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 7.5, "noise_std": 0.90},
        },
        "alerts": {
            "Temperature": {"alertValue": -3.2},
        },
    },
    {
        "sensorID": "SENSOR-MT-002",
        "zoneKey": "zone-mountain",
        "latitude": 43.2180,
        "longitude": -79.8800,
        "readings": {
            "Temperature": {"base": 7.1, "noise_std": 0.35},
            "Humidity": {"base": 70.0, "noise_std": 1.10},
            "AirQuality": {"base": 29.0, "noise_std": 2.00},
            "NoiseLevels": {"base": 52.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 7.8, "noise_std": 0.90},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-MT-003",
        "zoneKey": "zone-mountain",
        "latitude": 43.2230,
        "longitude": -79.8655,
        "readings": {
            "Temperature": {"base": 7.4, "noise_std": 0.35},
            "Humidity": {"base": 68.0, "noise_std": 1.10},
            "AirQuality": {"base": 27.0, "noise_std": 1.80},
            "NoiseLevels": {"base": 55.0, "noise_std": 2.50},
            "ParticularMatter": {"base": 7.2, "noise_std": 0.85},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-EC-001",
        "zoneKey": "zone-eastend",
        "latitude": 43.2233,
        "longitude": -79.7571,
        "readings": {
            "Temperature": {"base": 10.1, "noise_std": 0.30},
            "Humidity": {"base": 62.0, "noise_std": 1.00},
            "AirQuality": {"base": 32.0, "noise_std": 2.00},
            "NoiseLevels": {"base": 58.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 11.2, "noise_std": 1.20},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-EC-002",
        "zoneKey": "zone-eastend",
        "latitude": 43.2291,
        "longitude": -79.7528,
        "readings": {
            "Temperature": {"base": 9.8, "noise_std": 0.30},
            "Humidity": {"base": 63.0, "noise_std": 1.00},
            "AirQuality": {"base": 34.0, "noise_std": 2.20},
            "NoiseLevels": {"base": 62.0, "noise_std": 2.50},
            "ParticularMatter": {"base": 12.0, "noise_std": 1.30},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-EC-003",
        "zoneKey": "zone-eastend",
        "latitude": 43.2350,
        "longitude": -79.7620,
        "readings": {
            "Temperature": {"base": 10.3, "noise_std": 0.30},
            "Humidity": {"base": 61.0, "noise_std": 1.00},
            "AirQuality": {"base": 30.0, "noise_std": 2.00},
            "NoiseLevels": {"base": 56.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 10.5, "noise_std": 1.10},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-WE-001",
        "zoneKey": "zone-westend",
        "latitude": 43.2692,
        "longitude": -79.9555,
        "readings": {
            "Temperature": {"base": 8.9, "noise_std": 0.35},
            "Humidity": {"base": 69.5, "noise_std": 1.00},
            "AirQuality": {"base": 28.0, "noise_std": 1.80},
            "NoiseLevels": {"base": 54.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 8.5, "noise_std": 0.90},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-WE-002",
        "zoneKey": "zone-westend",
        "latitude": 43.2701,
        "longitude": -79.9582,
        "readings": {
            "Temperature": {"base": 8.7, "noise_std": 0.35},
            "Humidity": {"base": 71.0, "noise_std": 1.10},
            "AirQuality": {"base": 27.0, "noise_std": 1.80},
            "NoiseLevels": {"base": 51.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 8.2, "noise_std": 0.90},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-WE-003",
        "zoneKey": "zone-westend",
        "latitude": 43.2730,
        "longitude": -79.9610,
        "readings": {
            "Temperature": {"base": 9.1, "noise_std": 0.35},
            "Humidity": {"base": 68.0, "noise_std": 1.00},
            "AirQuality": {"base": 29.0, "noise_std": 1.80},
            "NoiseLevels": {"base": 53.0, "noise_std": 2.00},
            "ParticularMatter": {"base": 8.7, "noise_std": 0.90},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-AN-001",
        "zoneKey": "zone-ancaster",
        "latitude": 43.2108,
        "longitude": -79.9915,
        "readings": {
            "Temperature": {"base": 8.5, "noise_std": 0.30},
            "Humidity": {"base": 64.0, "noise_std": 0.90},
            "AirQuality": {"base": 25.0, "noise_std": 1.50},
            "NoiseLevels": {"base": 46.0, "noise_std": 1.80},
            "ParticularMatter": {"base": 7.0, "noise_std": 0.80},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-AN-002",
        "zoneKey": "zone-ancaster",
        "latitude": 43.2132,
        "longitude": -79.9870,
        "readings": {
            "Temperature": {"base": 8.6, "noise_std": 0.30},
            "Humidity": {"base": 63.0, "noise_std": 0.90},
            "AirQuality": {"base": 24.0, "noise_std": 1.50},
            "NoiseLevels": {"base": 44.0, "noise_std": 1.80},
            "ParticularMatter": {"base": 6.8, "noise_std": 0.80},
        },
        "alerts": {},
    },
    {
        "sensorID": "SENSOR-AN-003",
        "zoneKey": "zone-ancaster",
        "latitude": 43.2085,
        "longitude": -79.9945,
        "readings": {
            "Temperature": {"base": 8.4, "noise_std": 0.30},
            "Humidity": {"base": 65.0, "noise_std": 0.90},
            "AirQuality": {"base": 26.0, "noise_std": 1.50},
            "NoiseLevels": {"base": 45.0, "noise_std": 1.80},
            "ParticularMatter": {"base": 7.1, "noise_std": 0.80},
        },
        "alerts": {},
    },
]


def within_hamilton(lat: float, lon: float) -> bool:
    return (HAMILTON_LAT_MIN <= lat <= HAMILTON_LAT_MAX
            and HAMILTON_LON_MIN <= lon <= HAMILTON_LON_MAX)


def cosine_weight(progress: float) -> float:
    return (1.0 - math.cos(progress * math.pi)) / 2.0


def generate_value(base: float, noise_std: float, alert_value: float | None, tick: int) -> float:
    if alert_value is not None and ALERT_START <= tick <= ALERT_END:
        if tick <= ALERT_PEAK:
            progress = (tick - ALERT_START) / max(1, ALERT_PEAK - ALERT_START)
            weight = cosine_weight(progress)
            val = base + (alert_value - base) * weight
        else:
            progress = (tick - ALERT_PEAK) / max(1, ALERT_END - ALERT_PEAK)
            weight = cosine_weight(progress)
            val = alert_value + (base - alert_value) * weight
    else:
        val = base

    return round(val + random.gauss(0.0, noise_std), 2)


def build_record(sensor: dict, tick: int) -> dict:
    zone = ZONES[sensor["zoneKey"]]
    readings = {}
    for sensor_type, params in sensor["readings"].items():
        alert_cfg = sensor["alerts"].get(sensor_type)
        alert_value = alert_cfg["alertValue"] if alert_cfg else None
        readings[sensor_type] = {
            "sensorType": sensor_type,
            "sensorData": generate_value(params["base"], params["noise_std"], alert_value, tick),
            "unit": SENSOR_UNITS[sensor_type],
        }

    return {
        "sensorID": sensor["sensorID"],
        "zoneID": zone["zoneID"],
        "region": zone["region"],
        "zone": zone["zoneName"],
        "latitude": sensor["latitude"],
        "longitude": sensor["longitude"],
        "tick": tick,
        "readings": readings,
    }


def main() -> None:
    invalid = [s for s in SENSOR_DEFINITIONS if not within_hamilton(s["latitude"], s["longitude"])]
    if invalid:
        for s in invalid:
            print(f"ERROR: {s['sensorID']} ({s['latitude']}, {s['longitude']}) is outside Hamilton city bounds")
        sys.exit(1)

    print(f"GPS validation passed — all {len(SENSOR_DEFINITIONS)} sensors within Hamilton bounds.")
    print(f"Generating {CYCLE_SECONDS} ticks x {len(SENSOR_DEFINITIONS)} sensors = "
          f"{CYCLE_SECONDS * len(SENSOR_DEFINITIONS)} records ...")

    lines = []
    for tick in range(CYCLE_SECONDS):
        for sensor in SENSOR_DEFINITIONS:
            record = build_record(sensor, tick)
            lines.append(json.dumps(record, ensure_ascii=False))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Done — {len(lines)} records written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
