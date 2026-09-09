import time
import json
import socket
import select
import http.client
import threading
from flask import Flask, render_template, jsonify

# Global cache holding our isolated weather data records
weather_cache = {
    "temp_f": 0,
    "condition": "Connecting...",
    "is_day": 1,
    "online": False
}
last_weather_fetch = 0

app = Flask(__name__, template_folder='/home/pijay/solar_monitor/templates')

@app.route('/')
def home(): 
    return render_template('index.html')
def fetch_los_angeles_weather():
    """Queries Open-Meteo for Los Angeles using direct HTTP frames and prints diagnostics to the console."""
    global weather_cache, last_weather_fetch
    current_time = time.time()
    
    # Check if cache is fresh (only fetches once every 30 seconds during debugging)
    if current_time - last_weather_fetch < 30 and last_weather_fetch != 0:
        return

    try:
        host = "api.open-meteo.com"
        # Calibrated Los Angeles latitude/longitude query path using universal current_weather metrics
        path = "/v1/forecast?latitude=34.0522&longitude=-118.2437&current_weather=true&temperature_unit=fahrenheit"
        
        print(f"\n📡 [DIAGNOSTIC]: Contacting Host: {host}")
        conn = http.client.HTTPSConnection(host, timeout=4)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        
        print(f"📡 [DIAGNOSTIC]: Server responded with HTTP status code: {res.status}")
        
        if res.status == 200:
            raw_body = res.read().decode('utf-8')
            data = json.loads(raw_body)
            
            # Extract out the current weather sub-dictionary payload
            current = data["current_weather"]
            wmo_code = current["weathercode"]
            
            condition = "Clear Sky"
            if 1 <= wmo_code <= 3:
                condition = "Partly Cloudy"
            elif 45 <= wmo_code <= 48:
                condition = "Foggy"
            elif (51 <= wmo_code <= 67) or (80 <= wmo_code <= 82):
                condition = "Rainy"
            elif (71 <= wmo_code <= 77) or (85 <= wmo_code <= 86):
                condition = "Snowy"
            elif wmo_code >= 95:
                condition = "Thunderstorm"

            weather_cache.update({
                "temp_f": round(current["temperature"]),
                "condition": condition,
                "is_day": current["is_day"],
                "online": True
            })
            last_weather_fetch = current_time
            print(f"✅ [SUCCESS]: Parsed Data -> {weather_cache['temp_f']}°F, Condition: {weather_cache['condition']}")
        else:
            weather_cache["online"] = False
            print(f"❌ [API REFUSAL]: HTTP server returned error frame.")
        conn.close()
    except Exception as e:
        weather_cache["online"] = False
        print(f"❌ [CRITICAL SYSTEM ERROR]: Fetch stalled. Details: {e}")
@app.route('/api/data', methods=['GET'])
def get_telemetry():
    # Force a direct real-time weather query execution whenever the page updates
    fetch_los_angeles_weather()
    
    # Hardware configurations are mocked out as True for this test to bypass dependencies
    return jsonify({
        "hardware": {
            "epever_online": True,
            "bms_online": True,
            "weather_online": weather_cache["online"]
        },
        "weather": {
            "temp": f"{weather_cache['temp_f']}°F",
            "meta": weather_cache["condition"],
            "is_day": weather_cache["is_day"]
        },
        "metrics": {
            "pv_power_w": 450,
            "mppt_power_w": 436,
            "inverter_power_w": 120,
            "home_load_w": 108,
            "battery_net_w": 316,
            "battery_soc": 85,
            "battery_v": 13.2
        }
    })

if __name__ == "__main__":
    # Boot Flask directly on Port 5001
    app.run(host='192.168.1.242', port=5001, debug=False, use_reloader=False)
