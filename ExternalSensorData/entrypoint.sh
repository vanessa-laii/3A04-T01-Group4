#!/bin/sh
mosquitto -p 9999 &
sleep 1
python3 generate_data.py
python3 send_data.py
