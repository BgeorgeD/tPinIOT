from flask import Flask, render_template, jsonify, request
import json
import os
import random
import paho.mqtt.client as mqtt  # <--- NOU: Importam MQTT si aici

app = Flask(__name__)

FISIER_STATUS = "status_bazin.json"

# --- CONFIGURARE MQTT PENTRU WEB ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"


def trimite_comanda_mqtt(comanda):
    try:
        # Cream un client rapid doar pentru a trimite mesajul
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Web_Interface")
        client.connect(BROKER, PORT)
        client.publish(TOPIC_COMENZI, comanda)
        client.disconnect()
        return True
    except Exception as e:
        print(f"Eroare MQTT Web: {e}")
        return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    if os.path.exists(FISIER_STATUS):
        try:
            with open(FISIER_STATUS, "r") as f:
                data = json.load(f)
            if 'oxigen' not in data:
                data['oxigen'] = round(random.uniform(6.5, 8.0), 2)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)})
    else:
        return jsonify({"temperatura": 0, "ph": 0, "oxigen": 0})


# --- RUTA NOUA: Primeste comanda de la butonul din HTML ---
@app.route('/api/control', methods=['POST'])
def control_bazin():
    # Aici primim cererea de la buton
    data = request.json
    actiune = data.get('actiune')  # Ex: "START_AERATOR"

    print(f"[WEB] Utilizatorul a apasat butonul. Trimit: {actiune}")

    # Trimitem prin MQTT catre bazin.py
    trimite_comanda_mqtt(actiune)

    return jsonify({"status": "Comanda Trimisa!", "comanda": actiune})


if __name__ == '__main__':
    app.run(debug=True, port=5000)