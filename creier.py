import json
import paho.mqtt.client as mqtt
import os

# --- CONFIGURARE ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_DATE = "acvacultura/student/bazin1/senzori"
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"

FISIER_STATUS = "status_bazin.json"
LIMIT_FILE = "limits.json"


# --- HELPER FUNCTIONS ---
def load_limits():
    """Load temperature limits from JSON, fallback to defaults if missing."""
    if os.path.exists(LIMIT_FILE):
        with open(LIMIT_FILE) as f:
            limits = json.load(f)
        return limits['temperatura']['min'], limits['temperatura']['max']
    else:
        # default limits
        return 22.0, 25.0


# --- LOGICA (Ce gandeste serverul) ---
def on_message(client, userdata, msg):
    try:
        continut = msg.payload.decode()
        date = json.loads(continut)
        temp_curenta = date['temperatura']

        # Salvam pe disc pentru site
        with open(FISIER_STATUS, "w") as f:
            json.dump(date, f)

        print(f"[CREIER] Temperatura: {temp_curenta} C")

        # Load limits dynamically
        LIMITA_MINIMA, LIMITA_MAXIMA = load_limits()

        # --- TERMOSTAT AUTOMAT ---
        if temp_curenta < LIMITA_MINIMA:
            print("         [ALERTA] E prea frig! -> Trimit START_INCALZITOR")
            client.publish(TOPIC_COMENZI, "START_INCALZITOR")

        elif temp_curenta > LIMITA_MAXIMA:
            print("         [OK] Temperatura optima atinsa. -> Trimit STOP_INCALZITOR")
            client.publish(TOPIC_COMENZI, "STOP_INCALZITOR")

        else:
            print("         [INFO] Temperatura e in intervalul corect.")

        print("-" * 30)

    except Exception as e:
        print(f"Eroare procesare: {e}")


# --- CONECTARE MQTT ---
client = mqtt.Client(
    client_id="Simulare_Server_Central",
    protocol=mqtt.MQTTv311
)
client.on_connect = lambda c, u, f, rc: print("[SERVER] Conectat. Monitorizez temperatura...")
client.on_message = on_message

client.connect(BROKER, PORT)
client.subscribe(TOPIC_DATE)
client.loop_forever()
