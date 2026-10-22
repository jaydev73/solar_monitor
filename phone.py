"""Optional phone control (Fully Kiosk Browser REST API).

Wakes the wall-mounted phone and speaks alerts through it (and through the Echo Dot
it is paired with). Screen-off is handled by Fully's own screen-off timer.
Disabled unless PHONE_URL is set in .env. Nothing here ever touches the solar equipment.
"""
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request


def _cfg():
    return (os.getenv("PHONE_URL", "").rstrip("/"), os.getenv("PHONE_PASSWORD", ""))


def enabled():
    return bool(_cfg()[0])


def _call(cmd, **params):
    base, pw = _cfg()
    if not base:
        return False
    q = urllib.parse.urlencode({"cmd": cmd, "password": pw, **params})
    try:
        with urllib.request.urlopen(f"{base}/?{q}", timeout=3) as r:
            return 200 <= r.status < 300
    except Exception as e:                      # never log the URL: it contains the password
        print(f"[PHONE] {cmd} failed: {type(e).__name__}")
        return False


def screen_on():
    return _call("screenOn")


def screen_off():
    return _call("screenOff")


def reload_page():
    return _call("loadStartURL")


def status():
    """Phone health for the control page. The page URL is never returned (it holds the display key)."""
    base, pw = _cfg()
    if not base:
        return {"configured": False}
    q = urllib.parse.urlencode({"cmd": "deviceInfo", "type": "json", "password": pw})
    try:
        with urllib.request.urlopen(f"{base}/?{q}", timeout=3) as r:
            d = json.loads(r.read().decode())
    except Exception:
        return {"configured": True, "online": False}
    return {"configured": True, "online": True, "screen_on": d.get("screenOn"),
            "battery": d.get("batteryLevel"), "plugged": d.get("isPlugged")}


def say(text):
    return _call("textToSpeech", text=text, locale=os.getenv("PHONE_LOCALE", "en_US"))


class EventState:
    def __init__(self):
        self.low_armed = True
        self.hot_armed = True
        self.offline_since = None
        self.offline_alerted = False


def evaluate(st, solar, bms, now, low=20.0, hot=50.0):
    """Pure decision logic: returns the messages to announce. Each alert has hysteresis."""
    msgs = []
    soc = float(bms.get("avg_soc") or 0)
    if soc > 0:
        if st.low_armed and soc <= low:
            msgs.append(f"Battery is low at {soc:.0f} percent.")
            st.low_armed = False
        elif not st.low_armed and soc >= low + 10:
            st.low_armed = True
    temp = float(solar.get("device_t") or 0)
    if st.hot_armed and temp >= hot:
        msgs.append(f"The charge controller is hot at {temp:.0f} degrees Celsius.")
        st.hot_armed = False
    elif not st.hot_armed and temp <= hot - 5:
        st.hot_armed = True
    if solar.get("status") == "Online ✅":
        if st.offline_alerted:
            msgs.append("The charge controller is back online.")
        st.offline_since, st.offline_alerted = None, False
    elif st.offline_since is None:
        st.offline_since = now
    elif not st.offline_alerted and now - st.offline_since >= 120:
        msgs.append("The charge controller connection was lost.")
        st.offline_alerted = True
    return msgs


def start_events(solar_cache, bms_cache):
    if not enabled():
        return
    low = float(os.getenv("PHONE_LOW_SOC", "20"))
    hot = float(os.getenv("PHONE_HIGH_TEMP", "50"))
    speak = os.getenv("PHONE_SPEAK", "1") == "1"

    def run():
        st = EventState()
        while True:
            time.sleep(10)
            try:
                msgs = evaluate(st, solar_cache, bms_cache, time.time(), low, hot)
            except Exception as e:
                print(f"[PHONE] event check error: {type(e).__name__}")
                continue
            if msgs:
                screen_on()
                time.sleep(1)
                for m in msgs:
                    if speak:
                        say(m)
                    time.sleep(5)

    threading.Thread(target=run, daemon=True).start()
    print("📱 [PHONE] event worker started")


if __name__ == "__main__":
    # Usage on the Pi:  python phone.py wake | sleep | reload | status | say "Hello there"
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    a = sys.argv[1:]
    if not enabled():
        sys.exit("PHONE_URL is not set in .env")
    if a[:1] == ["wake"]:
        print("ok" if screen_on() else "failed")
    elif a[:1] == ["sleep"]:
        print("ok" if screen_off() else "failed")
    elif a[:1] == ["reload"]:
        print("ok" if reload_page() else "failed")
    elif a[:1] == ["status"]:
        print(status())
    elif a[:1] == ["say"] and len(a) > 1:
        print("ok" if say(" ".join(a[1:])) else "failed")
    else:
        sys.exit('usage: python phone.py wake | sleep | reload | status | say "text"')
