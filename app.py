import os
import time
import json
import socket
import http.client
import threading
import asyncio
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
from bleak import BleakClient

# Initialize tracking and configuration maps
load_dotenv(dotenv_path='/home/pijay/solar_monitor/.env')

EPEVER_IP_ADDRESS = os.getenv("EPEVER_IP_ADDRESS", "127.0.0.1")
EPEVER_PORT = int(os.getenv("EPEVER_PORT", 9999))
EPEVER_UNIT_ID = 1

LAT = os.getenv("LATITUDE", "34.0522")
LON = os.getenv("LONGITUDE", "-118.2437")
TZ = os.getenv("TIMEZONE", "America%2FLos_Angeles")

BATTERY_1_ADDRESS = os.getenv("BATTERY_1_ADDRESS", "00:00:00:00:00:00")
BATTERY_2_ADDRESS = os.getenv("BATTERY_2_ADDRESS", "00:00:00:00:00:00")

# Xiaoxiang / JBD BMS Protocol Register Maps
RX_CHAR = "0000ff01-0000-1000-8000-00805f9b34fb"  
TX_CHAR = "0000ff02-0000-1000-8000-00805f9b34fb"  
QUERY_INFO_COMMAND = bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77])

# Global telemetry storage caches
weather_cache = {
    "current": {"temp_f": 0, "condition": "Connecting...", "wmo_code": 0, "is_day": 1, "humidity": 0, "wind_speed": 0.0},
    "forecast": [], "online": False
}

solar_cache = {
    "status": "Disconnected ❌", "state": "OFFLINE",
    "v_pv": 0.0, "a_pv": 0.0, "w_pv": 0.0,
    "v_bat": 0.0, "a_bat": 0.0, "w_bat": 0.0,
    "device_t": 0.0, "battery_t": 0.0, "total_kwh": 0.0
}

bms_cache = {
    "system_status": "Connecting...", "avg_voltage": 0.0, "total_current": 0.0,
    "total_wattage": 0.0, "combined_capacity": 0.0, "avg_soc": 0,
    "bat1": {"voltage": 0.0, "current": 0.0, "capacity": 0.0, "soc": 0, "status": "Connecting...", "buffer": bytearray()},
    "bat2": {"voltage": 0.0, "current": 0.0, "capacity": 0.0, "soc": 0, "status": "Connecting...", "buffer": bytearray()}
}

app = Flask(__name__, 
            template_folder='/home/pijay/solar_monitor/templates',
            static_folder='/home/pijay/solar_monitor/static')

@app.route('/')
def home():
    return render_template('index.html')
# ==============================================================================
# 🔋 ASYNC BLUETOOTH JBD BMS POLLING INFRASTRUCTURE
# ==============================================================================
def create_notification_handler(bat_id):
    def handler(sender, data):
        bat = bms_cache[bat_id]
        bat["buffer"].extend(data)
        if 0xDD in bat["buffer"]:
            start_idx = bat["buffer"].index(0xDD)
            if start_idx > 0: bat["buffer"] = bat["buffer"][start_idx:]
        else:
            bat["buffer"].clear()
            return
        if len(bat["buffer"]) >= 4:
            data_length = bat["buffer"][3]
            total_expected_length = data_length + 7
            if len(bat["buffer"]) >= total_expected_length:
                complete_packet = bat["buffer"][:total_expected_length]
                bat["buffer"] = bat["buffer"][total_expected_length:]
                parse_bms_data(bat_id, complete_packet)
    return handler

def parse_bms_data(bat_id, packet):
    try:
        if len(packet) < 7 or packet[1] != 0x03 or packet[2] != 0x00: return
        total_voltage_raw = (packet[4] << 8) | packet[5]
        current_raw       = (packet[6] << 8) | packet[7]
        remaining_cap_raw = (packet[8] << 8) | packet[9]
        soc_percentage    = packet[23]
        
        bms_cache[bat_id]["voltage"] = total_voltage_raw / 100.0
        bms_cache[bat_id]["soc"] = int(soc_percentage)
        bms_cache[bat_id]["capacity"] = remaining_cap_raw / 100.0
        
        if current_raw > 32767: current_raw -= 65536
        bms_cache[bat_id]["current"] = current_raw / 100.0
        compute_combined_bms_metrics()
    except Exception: pass

def compute_combined_bms_metrics():
    b1, b2 = bms_cache["bat1"], bms_cache["bat2"]
    avg_v = (b1["voltage"] + b2["voltage"]) / 2.0 if (b1["voltage"] > 0 and b2["voltage"] > 0) else (b1["voltage"] or b2["voltage"])
    total_a = b1["current"] + b2["current"]
    
    valid_socs = [b["soc"] for b in [b1, b2] if b["voltage"] > 0]
    avg_soc = int(sum(valid_socs) / len(valid_socs)) if valid_socs else 0
    
    state = "IDLE 💤"
    if total_a > 0.1: state = "CHARGING ⚡"
    elif total_a < -0.1: state = "DISCHARGING 🔋"

    bms_cache.update({
        "system_status": state, "avg_voltage": round(avg_v, 2), "total_current": round(total_a, 2),
        "total_wattage": round(avg_v * total_a, 1), "combined_capacity": round(b1["capacity"] + b2["capacity"], 1),
        "avg_soc": avg_soc
    })

async def connect_and_poll_battery(bat_id, address):
    while True:
        try:
            bms_cache[bat_id]["status"] = "Connecting..."
            async with BleakClient(address, dangerous_use_bleak_mtu_negotiation=False) as client:
                bms_cache[bat_id]["status"] = "Online ✅"
                await client.start_notify(RX_CHAR, create_notification_handler(bat_id))
                while client.is_connected:
                    await client.write_gatt_char(TX_CHAR, QUERY_INFO_COMMAND, response=False)
                    await asyncio.sleep(2)
        except Exception:
            bms_cache[bat_id].update({"status": "Retrying...", "voltage": 0.0, "current": 0.0, "soc": 0})
            bms_cache[bat_id]["buffer"].clear()
            await asyncio.sleep(4)
def bms_asyncio_thread_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(
        connect_and_poll_battery("bat1", BATTERY_1_ADDRESS),
        connect_and_poll_battery("bat2", BATTERY_2_ADDRESS)
    ))
# ==============================================================================
# 🌞 EPEVER MODBUS BACKGROUND TRACKING ENGINE
# ==============================================================================
def calculate_crc(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if (crc & 1) != 0:
                crc >>= 1; crc ^= 0xA001
            else: crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

def execute_modbus_query(start_reg, count):
    """Sends a Modbus command over TCP socket streams safely."""
    high_block, low_block = divmod(start_reg, 256)
    count_high, count_low = divmod(count, 256)
    base_frame = bytes([EPEVER_UNIT_ID, 0x04, high_block, low_block, count_high, count_low])
    modbus_cmd = base_frame + calculate_crc(base_frame)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((EPEVER_IP_ADDRESS, EPEVER_PORT))
        s.sendall(modbus_cmd)
        response = bytearray()
        start = time.time()
        expected_len = 5 + (count * 2)
        while (time.time() - start) < 1.0:
            chunk = s.recv(1024)
            if not chunk: break
            response.extend(chunk)
            if len(response) >= expected_len: break
        s.close()
        
        # FIXED: Explicitly validate the individual array index offsets
        if len(response) >= expected_len and response[0] == EPEVER_UNIT_ID and response[1] == 0x04: 
            return response
    except Exception: pass
    return None
def solar_polling_worker():
    """Thread worker that loops indefinitely to poll the Epever controller."""
    global solar_cache
    while True:
        # Split into smaller query chunks to avoid overflowing the Wi-Fi dongle buffer
        res_live = execute_modbus_query(0x3100, 18)    # Real-time metrics
        res_status = execute_modbus_query(0x3201, 1)  # Charging status word
        res_history = execute_modbus_query(0x3312, 2) # Cumulative totals
        
        # Validate that the core metrics frame is intact (3 bytes header + 36 bytes data)
        if res_live and res_history and len(res_live) >= 39:
            try:
                # --- SOLAR ARRAY (PV) INPUT METRICS ---
                pv_v = ((res_live[3] << 8) | res_live[4]) / 100.0
                pv_a = ((res_live[5] << 8) | res_live[6]) / 100.0
                pv_w_low = (res_live[7] << 8) | res_live[8]
                pv_w_high = (res_live[9] << 8) | res_live[10]
                pv_w = ((pv_w_high << 16) | pv_w_low) / 100.0
                
                # --- CHARGER TERMINAL METRICS (BATTERY SIDE) ---
                batt_v = ((res_live[11] << 8) | res_live[12]) / 100.0
                batt_a = ((res_live[13] << 8) | res_live[14]) / 100.0
                batt_w_low = (res_live[15] << 8) | res_live[16]
                batt_w_high = (res_live[17] << 8) | res_live[18]
                batt_w = ((batt_w_high << 16) | batt_w_low) / 100.0
                
                # --- TEMPERATURE METRICS ---
                device_temp = ((res_live[37] << 8) | res_live[38]) / 100.0
                
                # --- HISTORICAL GENERATION ---
                total_gen_low = (res_history[3] << 8) | res_history[4]
                total_gen_high = (res_history[5] << 8) | res_history[6]
                total_kwh = ((total_gen_high << 16) | total_gen_low) / 100.0

                # --- ADVANCED CHARGING STATE DECODER ---
                # Default safety fallback state configuration
                mppt_state = "Harvest Active" if pv_w > 5.0 else "Night / Idle"
                
                # Process state flags only if the independent status query returned data safely
                if res_status and len(res_status) >= 5:
                    status_word = (res_status[3] << 8) | res_status[4]
                    charging_stage_bits = (status_word >> 2) & 0x03
                    is_equalizing = (status_word >> 1) & 0x01

                    if charging_stage_bits == 0x01:
                        mppt_state = "Bulk Charging ⚡"
                    elif charging_stage_bits == 0x02:
                        mppt_state = "Boost Charging 🚀" if not is_equalizing else "Equalize Charging 🔥"
                    elif charging_stage_bits == 0x03:
                        mppt_state = "Float Charging 💤"

                solar_cache.update({
                    "status": "Online ✅", "state": mppt_state,
                    "v_pv": round(pv_v, 1), "a_pv": round(pv_a, 1), "w_pv": round(pv_w, 0),
                    "v_bat": round(batt_v, 2), "a_bat": round(batt_a, 1), "w_bat": round(batt_w, 0),
                    "device_t": round(device_temp, 1), "total_kwh": round(total_kwh, 2)
                })
            except Exception as e:
                print(f"⚠️ [PARSING ERROR]: Metric decoding failure: {e}")
        else:
            solar_cache.update({
                "status": "Disconnected ❌", "state": "OFFLINE", 
                "v_pv": 0.0, "a_pv": 0.0, "w_pv": 0.0, "v_bat": 0.0, "a_bat": 0.0, "w_bat": 0.0, "device_t": 0.0
            })
        
        # Wait 3 seconds before requesting data from the Wi-Fi card again
        time.sleep(3)

# ==============================================================================
# ☁️ CLOUD OPEN-METEO WEATHER ENGINE
# ==============================================================================
def fetch_los_angeles_weather():
    global weather_cache
    host = "api.open-meteo.com"
    path = f"/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,is_day,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone={TZ}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    while True:
        try:
            conn = http.client.HTTPSConnection(host, timeout=4)
            conn.request("GET", path, headers=headers)
            res = conn.getresponse()
            if res.status == 200:
                data = json.loads(res.read().decode('utf-8'))
                current = data["current"]
                wmo_code = current["weather_code"]
                condition_map = {0: "Clear Sky", 1: "Partly Cloudy", 2: "Partly Cloudy", 3: "Partly Cloudy", 45: "Foggy", 48: "Foggy", 51: "Rainy", 53: "Rainy", 55: "Rainy", 61: "Rainy", 63: "Rainy", 65: "Rainy", 80: "Rainy", 81: "Rainy", 82: "Rainy", 71: "Snowy", 73: "Snowy", 75: "Snowy", 85: "Snowy", 86: "Snowy", 95: "Thunderstorm"}
                weather_cache.update({
                    "current": {"temp_f": round(current["temperature_2m"]), "condition": condition_map.get(wmo_code, "Clear Sky"), "wmo_code": wmo_code, "is_day": current["is_day"], "humidity": current["relative_humidity_2m"], "wind_speed": round(current["wind_speed_10m"], 1)},
                    "forecast": [{"date_raw": data["daily"]["time"][i], "wmo_code": data["daily"]["weather_code"][i], "max_temp": round(data["daily"]["temperature_2m_max"][i]), "min_temp": round(data["daily"]["temperature_2m_min"][i])} for i in range(7)],
                    "online": True
                })
            else: weather_cache["online"] = False
        except Exception: weather_cache["online"] = False
        time.sleep(600)


# ==============================================================================
# 🔌 FLASK ENDPOINTS & RUNNER
# ==============================================================================
@app.route('/api/data', methods=['GET'])
def get_telemetry():
    # Use 25°C baseline fallback if batteries haven't broadcast a voltage yet
    display_battery_temp = 25.0 
    solar_cache["battery_t"] = display_battery_temp
    
    return jsonify({
        "hardware": {
            "epever_online": solar_cache["status"] == "Online ✅",
            "bms_online": bms_cache["bat1"]["status"] == "Online ✅" or bms_cache["bat2"]["status"] == "Online ✅",
            "weather_online": weather_cache["online"]
        },
        "weather": weather_cache["current"],
        "forecast": weather_cache["forecast"],
        "solar": solar_cache,
        "bms": {
            "status": bms_cache["system_status"], "v_combined": bms_cache["avg_voltage"],
            "a_total": bms_cache["total_current"], "w_total": bms_cache["total_wattage"],
            "ah_total": bms_cache["combined_capacity"], "soc_avg": bms_cache["avg_soc"],
            "b1_soc": bms_cache["bat1"]["soc"], "b1_v": bms_cache["bat1"]["voltage"], "b1_a": bms_cache["bat1"]["current"], "b1_status": bms_cache["bat1"]["status"],
            "b2_soc": bms_cache["bat2"]["soc"], "b2_v": bms_cache["bat2"]["voltage"], "b2_a": bms_cache["bat2"]["current"], "b2_status": bms_cache["bat2"]["status"]
        }
    })

if __name__ == "__main__":
    threading.Thread(target=fetch_los_angeles_weather, daemon=True).start()
    threading.Thread(target=solar_polling_worker, daemon=True).start()
    threading.Thread(target=bms_asyncio_thread_worker, daemon=True).start()
    
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    host_ip = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port_num = int(os.getenv("FLASK_RUN_PORT", 5001))
    app.run(host=host_ip, port=port_num, debug=False, use_reloader=False)
