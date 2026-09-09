import os
import time
import json
import socket
import http.client
import threading
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv # Import the environment loader

# Load variables from the local .env file
load_dotenv(dotenv_path='/home/pijay/solar_monitor/.env')

# Read secret items securely from environment or fall back to defaults if missing
EPEVER_IP_ADDRESS = os.getenv("EPEVER_IP_ADDRESS", "127.0.0.1")
EPEVER_PORT = int(os.getenv("EPEVER_PORT", 9999))
EPEVER_UNIT_ID = 1

LAT = os.getenv("LATITUDE", "34.0522")
LON = os.getenv("LONGITUDE", "-118.2437")
TZ = os.getenv("TIMEZONE", "America%2FLos_Angeles")

# ... (Keep the rest of your Modbus CRC and worker logic exactly the same) ...

def fetch_los_angeles_weather():
    global weather_cache
    host = "://open-meteo.com"
    
    # Secure dynamic URL path construction
    path = f"/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,is_day,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone={TZ}"
    
    # ... (Keep the rest of your weather fetching loop exactly the same) ...

if __name__ == "__main__":
    threading.Thread(target=fetch_los_angeles_weather, daemon=True).start()
    threading.Thread(target=solar_polling_worker, daemon=True).start()
    
    # Use environment configurations to boot your Flask server framework
    host_ip = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port_num = int(os.getenv("FLASK_RUN_PORT", 5001))
    
    app.run(host=host_ip, port=port_num, debug=False, use_reloader=False)
