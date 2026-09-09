import time
import json
import http.client
import threading
from flask import Flask, render_template, jsonify

# Global cache holding our weather data records
weather_cache = {
    "current": {
        "temp_f": 0,
        "condition": "Connecting...",
        "wmo_code": 0,
        "is_day": 1,
        "humidity": 0,
        "wind_speed": 0.0
    },
    "forecast": [], # List of dictionaries for the 7-day forecast
    "online": False
}

app = Flask(__name__, 
            template_folder='/home/pijay/solar_monitor/templates',
            static_folder='/home/pijay/solar_monitor/static')

@app.route('/')
def home():
    return render_template('index.html')

def fetch_los_angeles_weather():
    """Queries Open-Meteo for LA weather & 7-day forecast using a background loop."""
    global weather_cache
    host = "api.open-meteo.com"
    
    # Expanded query path to include current humidity, wind speed, and 7-day daily forecast metrics
    path = (
        "/v1/forecast?latitude=34.0522&longitude=-118.2437"
        "&current=temperature_2m,relative_humidity_2m,is_day,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FLos_Angeles"
    )
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Accept': 'application/json'
    }

    while True:
        try:
            print(f"\n📡 [DIAGNOSTIC]: Contacting Host for deep forecast: {host}")
            conn = http.client.HTTPSConnection(host, timeout=4)
            conn.request("GET", path, headers=headers)
            res = conn.getresponse()
            
            if res.status == 200:
                raw_body = res.read().decode('utf-8')
                data = json.loads(raw_body)
                
                # Parse current conditions
                current = data["current"]
                wmo_code = current["weather_code"]
                
                condition_map = {
                    0: "Clear Sky", 1: "Partly Cloudy", 2: "Partly Cloudy", 3: "Partly Cloudy",
                    45: "Foggy", 48: "Foggy", 51: "Rainy", 53: "Rainy", 55: "Rainy", 
                    61: "Rainy", 63: "Rainy", 65: "Rainy", 80: "Rainy", 81: "Rainy", 82: "Rainy",
                    71: "Snowy", 73: "Snowy", 75: "Snowy", 85: "Snowy", 86: "Snowy",
                    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"
                }
                condition = condition_map.get(wmo_code, "Clear Sky")

                current_parsed = {
                    "temp_f": round(current["temperature_2m"]),
                    "condition": condition,
                    "wmo_code": wmo_code,
                    "is_day": current["is_day"],
                    "humidity": current["relative_humidity_2m"],
                    "wind_speed": round(current["wind_speed_10m"], 1)
                }
                
                # Parse 7-Day Forecast arrays
                daily = data["daily"]
                forecast_parsed = []
                
                for i in range(len(daily["time"])):
                    forecast_parsed.append({
                        "date_raw": daily["time"][i], # format: "YYYY-MM-DD"
                        "wmo_code": daily["weather_code"][i],
                        "max_temp": round(daily["temperature_2m_max"][i]),
                        "min_temp": round(daily["temperature_2m_min"][i])
                    })

                weather_cache.update({
                    "current": current_parsed,
                    "forecast": forecast_parsed,
                    "online": True
                })
                print(f"✅ [SUCCESS]: Current Temp: {current_parsed['temp_f']}°F | Humidity: {current_parsed['humidity']}%")
            else:
                weather_cache["online"] = False
                print(f"❌ [API REFUSAL]: HTTP server error frame.")
            conn.close()
        except Exception as e:
            weather_cache["online"] = False
            print(f"❌ [CRITICAL SYSTEM ERROR]: Fetch stalled: {e}")
        
        time.sleep(600) # Poll every 10 minutes

@app.route('/api/data', methods=['GET'])
def get_telemetry():
    return jsonify({
        "hardware": {
            "epever_online": True,
            "bms_online": True,
            "weather_online": weather_cache["online"]
        },
        "weather": weather_cache["current"],
        "forecast": weather_cache["forecast"],
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
    weather_thread = threading.Thread(target=fetch_los_angeles_weather, daemon=True)
    weather_thread.start()
    app.run(host='192.168.1.242', port=5001, debug=False, use_reloader=False)
