import json
import paho.mqtt.client as mqtt
import os

# --- CONFIGURARE ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_DATE = "acvacultura/student/bazin1/senzori"
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"

LIMITA_MINIMA = 22.0  # Prea frig
LIMITA_MAXIMA = 24.0  # Destul de cald, opreste incalzirea

FISIER_STATUS = "status_bazin.json"


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


# --- CONECTARE ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Simulare_Server_Central")
client.on_connect = lambda c, u, f, rc: print("[SERVER] Conectat. Monitorizez temperatura...")
client.on_message = on_message

client.connect(BROKER, PORT)
client.subscribe(TOPIC_DATE)
client.loop_forever()