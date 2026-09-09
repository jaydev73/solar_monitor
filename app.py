import time
import json
import http.client
import threading
from flask import Flask, render_template, jsonify

# Global cache holding our isolated weather data records
weather_cache = {
    "temp_f": 0,
    "condition": "Connecting...",
    "is_day": 1,
    "wmo_code": 0,
    "online": False
}

app = Flask(__name__, 
            template_folder='/home/pijay/solar_monitor/templates',
            static_folder='/home/pijay/solar_monitor/static')

@app.route('/')
def home():
    return render_template('index.html')

def fetch_los_angeles_weather():
    """Queries Open-Meteo for Los Angeles using a background thread loop."""
    global weather_cache
    host = "api.open-meteo.com"
    path = "/v1/forecast?latitude=34.0522&longitude=-118.2437&current_weather=true&temperature_unit=fahrenheit"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Accept': 'application/json'
    }

    while True:
        try:
            print(f"\n📡 [DIAGNOSTIC]: Contacting Host: {host}")
            conn = http.client.HTTPSConnection(host, timeout=4)
            conn.request("GET", path, headers=headers)
            res = conn.getresponse()
            
            if res.status == 200:
                raw_body = res.read().decode('utf-8')
                data = json.loads(raw_body)
                current = data["current_weather"]
                wmo_code = current["weathercode"]
                
                # Determine text condition
                condition = "Clear Sky"
                if 1 <= wmo_code <= 3: condition = "Partly Cloudy"
                elif 45 <= wmo_code <= 48: condition = "Foggy"
                elif (51 <= wmo_code <= 67) or (80 <= wmo_code <= 82): condition = "Rainy"
                elif (71 <= wmo_code <= 77) or (85 <= wmo_code <= 86): condition = "Snowy"
                elif wmo_code >= 95: condition = "Thunderstorm"

                weather_cache.update({
                    "temp_f": round(current["temperature"]),
                    "condition": condition,
                    "wmo_code": wmo_code,
                    "is_day": current["is_day"],
                    "online": True
                })
                print(f"✅ [SUCCESS]: Parsed Data -> {weather_cache['temp_f']}°F, WMO: {wmo_code}")
            else:
                weather_cache["online"] = False
                print(f"❌ [API REFUSAL]: HTTP server error frame.")
            conn.close()
        except Exception as e:
            weather_cache["online"] = False
            print(f"❌ [CRITICAL SYSTEM ERROR]: Fetch stalled: {e}")
        
        # Poll weather data every 10 minutes (600 seconds) to prevent API bans
        time.sleep(600)

@app.route('/api/data', methods=['GET'])
def get_telemetry():
    # Instantly returns cached telemetry data to keep the web application fluid
    return jsonify({
        "hardware": {
            "epever_online": True,
            "bms_online": True,
            "weather_online": weather_cache["online"]
        },
        "weather": {
            "temp": f"{weather_cache['temp_f']}°F",
            "meta": weather_cache["condition"],
            "wmo_code": weather_cache["wmo_code"],
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
    # Start the background weather tracking thread before running the server
    weather_thread = threading.Thread(target=fetch_los_angeles_weather, daemon=True)
    weather_thread.start()
    
    # Boot Flask directly on Port 5001
    app.run(host='192.168.1.242', port=5001, debug=False, use_reloader=False)
