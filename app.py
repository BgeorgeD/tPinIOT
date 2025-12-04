from flask import Flask, render_template, jsonify, request
import json
import os
import random
import paho.mqtt.client as mqtt

app = Flask(__name__)

FISIER_STATUS = "status_bazin.json"
LIMIT_FILE = "limits.json"

# --- CONFIGURARE MQTT PENTRU WEB ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"


# --- HELPER FUNCTIONS ---
def load_limits():
    """Load limits from JSON file, return default if missing."""
    if os.path.exists(LIMIT_FILE):
        with open(LIMIT_FILE, "r") as f:
            return json.load(f)
    return {
        "temperatura": {"min": 20, "max": 30},
        "oxigen": {"min": 6, "max": 9},
        "ph": {"min": 6, "max": 9}
    }

def save_limits(new_limits):
    """Save limits to JSON file."""
    with open(LIMIT_FILE, "w") as f:
        json.dump(new_limits, f, indent=4)


def trimite_comanda_mqtt(comanda):
    try:
        client = mqtt.Client("Web_Interface")
        client.connect(BROKER, PORT)
        client.publish(TOPIC_COMENZI, comanda)
        client.disconnect()
        return True
    except Exception as e:
        print(f"Eroare MQTT Web: {e}")
        return False


# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    # Load limits
    LIMITE = load_limits()

    if os.path.exists(FISIER_STATUS):
        try:
            with open(FISIER_STATUS, "r") as f:
                data = json.load(f)
            if 'oxigen' not in data:
                data['oxigen'] = round(random.uniform(6.5, 8.0), 2)
            data['limite'] = LIMITE
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)})
    else:
        return jsonify({"temperatura": 0, "ph": 0, "oxigen": 0, "limite": LIMITE})


@app.route('/api/control', methods=['POST'])
def control_bazin():
    data = request.json
    actiune = data.get('actiune')
    print(f"[WEB] Utilizatorul a apasat butonul. Trimit: {actiune}")
    trimite_comanda_mqtt(actiune)
    return jsonify({"status": "Comanda Trimisa!", "comanda": actiune})


@app.route('/api/limits', methods=['POST'])
def api_save_limits():
    try:
        new_limits = request.json
        save_limits(new_limits)
        return jsonify({"status": "success", "limite": new_limits})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
