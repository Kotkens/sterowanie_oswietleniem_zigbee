from flask import Flask, jsonify, request, abort, render_template
import requests
import os
import threading
import time
import json
import paho.mqtt.client as mqtt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
  
# ——— your existing config ———
ESP_IP     = os.environ.get("ESP_IP", "192.168.0.37")
ESP_PORT   = int(os.environ.get("ESP_PORT", 5554))
ESP_URL    = f"http://{ESP_IP}:{ESP_PORT}/var"

API_KEY    = os.environ.get("MY_API_KEY", "1234")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT   = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC  = "zigbee2mqtt/lampa/set"

app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["20 per second"])

# ——— MQTT init ———
def init_mqtt():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()
    return client

mqtt_client = init_mqtt()

latest_value = 0
value_lock   = threading.Lock()

def update_lamp(value):
    state = "ON" if isinstance(value, (int, float)) and value > 0 else "OFF"
    mqtt_client.publish(MQTT_TOPIC, json.dumps({"state": state}))
    
# --------------------------------- dodanie sterowanie zarowka 21.05.2025
    
# Funkcja do sterowania stanem żarówki  
def zmien_stan_swiatla(state):
    state_value = "ON" if state in [True, "ON"] else "OFF"
    mqtt_client.publish(MQTT_TOPIC, json.dumps({"state": state_value}))
     
def natezenie_swiatla(natezenie): # 254
    """
    Zmienia natężenie światła żarówki
    """
    if natezenie > 0 and natezenie < 255:
        mqtt_client.publish(MQTT_TOPIC, json.dumps({"brightness": natezenie}))
    else:
        return "Podane źle natężenie światła"
    
def zmiana_koloru_swiatla(kolor):
    """
    Zmienia kolor światła żarówki
    """
    match kolor:
        case "1":  # niebieski z RGB (46,102,150)
            payload = json.dumps({"color": {"h": 210,"hue": 210,"s": 69,"saturation": 69,"x": 0.169,"y": 0.118}})
        case "2":  # czerwony
            payload = json.dumps({"color": {"h": 0,"hue": 0,"s": 100,"saturation": 100,"x": 0.64,"y": 0.33}})
        case "3":  # zielony
            payload = json.dumps({"color": {"h": 120,"hue": 120,"s": 100,"saturation": 100,"x": 0.3,"y": 0.6}})
        case "4":  # żółty
           payload = json.dumps({"color": {"h": 50,"hue": 50,"s": 100,"saturation": 100,"x": 0.43,"y": 0.5}})
    mqtt_client.publish(MQTT_TOPIC, payload)

# ---------------------------------

def require_api_key(fn):
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            abort(401, description="Invalid or missing API key")
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

# ——— serve the single‐page UI ———
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ——— GET returns full JSON from ESP ———
@app.route("/count", methods=["GET"])
@limiter.limit("20 per second")
@require_api_key
def get_count():
    resp = requests.get(ESP_URL)
    resp.raise_for_status()
    return jsonify(resp.json()), 200

# ——— POST can accept any ESP keys ———
@app.route("/count", methods=["POST"])
@limiter.limit("20 per second")
@require_api_key
def set_count():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    resp = requests.post(ESP_URL, json=data)
    resp.raise_for_status()

    if "value" in data:
        with value_lock:
            global latest_value
            latest_value = data["value"]
            update_lamp(latest_value)

    return jsonify(resp.json()), resp.status_code

# ——— Webhook from ESP to force-refresh lamp immediately ———
@app.route("/esp_update", methods=["POST"])
def esp_update():
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "Missing 'value'"}), 400

    with value_lock:
        global latest_value
        latest_value = data["value"]
        update_lamp(latest_value)

    return jsonify({"status": "OK"}), 200

# ——— Polling thread: fetch every second and re-publish state ———
def poll_esp():
    global latest_value
    while True:
        try:
            resp = requests.get(ESP_URL)
            resp.raise_for_status()
            data = resp.json()
            value = data.get("value", 0)

            with value_lock:
                latest_value = value

            # always publish, even if unchanged
            update_lamp(value)

        except Exception as e:
            app.logger.error(f"Poll error: {e}")

        time.sleep(1)

# start polling thread
poll_thread = threading.Thread(target=poll_esp, daemon=True)
poll_thread.start()

@app.route("/light/brightness_form", methods=["POST"])
def brightness_form():
    brightness = request.form.get("brightness", type=int)
    if brightness is None:
        return "Brak wartości", 400
    natezenie_swiatla(brightness)
    return f"Ustawiono natężenie na {brightness}. <a href='/'>Powrót</a>"

@app.route("/light/color_form", methods=["POST"])
def color_form():
    color = request.form.get("color")
    if not color:
        return "Brak koloru", 400
    zmiana_koloru_swiatla(color)
    return f"Zmieniono kolor na opcję {color}. <a href='/'>Powrót</a>"

if __name__ == "__main__":
    # in prod, set debug=False
    app.run(host="0.0.0.0", port=5555, debug=False)


