import json
import paho.mqtt.client as mqtt
import os

# --- CONFIGURARE ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_DATE = "acvacultura/student/bazin1/senzori"
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"

FISIER_STATUS = "status_bazin.json"
# IMPORTANT: Acesta trebuie sa fie acelasi fisier scris de app.py
FISIER_LIMITE = "config_limite.json"


# --- HELPER FUNCTIONS ---
def citeste_limite():
    """Citeste limitele setate din interfata web. Daca nu exista, foloseste valori default."""
    default_limits = {
        "temp_min": 21.0, "temp_max": 24.0,
        "oxigen_min": 6.0, "oxigen_max": 9.0,
        "ph_min": 6.0, "ph_max": 8.0
    }

    if os.path.exists(FISIER_LIMITE):
        try:
            with open(FISIER_LIMITE, "r") as f:
                # Actualizam valorile default cu ce gasim in fisier
                saved_limits = json.load(f)
                default_limits.update(saved_limits)
        except Exception as e:
            print(f"[EROARE] Nu am putut citi limitele: {e}")

    return default_limits


# --- LOGICA (Ce gandeste serverul) ---
def on_message(client, userdata, msg):
    try:
        continut = msg.payload.decode()
        date = json.loads(continut)

        # 1. Salvam starea curenta pe disc pentru site
        with open(FISIER_STATUS, "w") as f:
            json.dump(date, f)

        # Extragem valorile primite de la senzori
        # Folosim .get() ca sa nu crape daca lipseste vreo valoare
        temp_curenta = float(date.get('temperatura', 0))
        oxigen_curent = float(date.get('oxigen', 0))
        ph_curent = float(date.get('ph', 7))

        print(f"[CREIER] Date primite: T={temp_curenta}°C | O2={oxigen_curent}mg/L | pH={ph_curent}")

        # 2. Incarcam regulile (limitele) setate de tine in Web
        limite = citeste_limite()

        # --- LOGICA TEMPERATURA ---
        if temp_curenta < float(limite['temp_min']):
            print(f"   [ALERTA] Temp {temp_curenta} < Min {limite['temp_min']} -> START INCALZITOR")
            client.publish(TOPIC_COMENZI, "START_INCALZITOR")
        elif temp_curenta > float(limite['temp_max']):
            print(f"   [OK] Temp {temp_curenta} > Max {limite['temp_max']} -> STOP INCALZITOR")
            client.publish(TOPIC_COMENZI, "STOP_INCALZITOR")

        # --- LOGICA OXIGEN (Aici rezolvam problema cu scaderea la 0) ---
        if oxigen_curent < float(limite['oxigen_min']):
            print(f"   [ALERTA] Oxigen {oxigen_curent} < Min {limite['oxigen_min']} -> START AERATOR")
            client.publish(TOPIC_COMENZI, "START_AERATOR")
        elif oxigen_curent > float(limite['oxigen_max']):
            print(f"   [OK] Oxigen {oxigen_curent} > Max {limite['oxigen_max']} -> STOP AERATOR")
            client.publish(TOPIC_COMENZI, "STOP_AERATOR")

        # --- LOGICA PH ---
        if ph_curent < float(limite['ph_min']) or ph_curent > float(limite['ph_max']):
            # Daca pH-ul e in afara limitelor, pornim filtrul pentru stabilizare
            print(f"   [ALERTA] pH {ph_curent} instabil -> START FILTRU")
            client.publish(TOPIC_COMENZI, "START_FILTRU")
        else:
            # Daca e in limite, oprim filtrul (sau il lasam, depinde de logica dorita)
            # Aici il oprim ca sa economisim energie
            client.publish(TOPIC_COMENZI, "STOP_FILTRU")

        print("-" * 30)

    except Exception as e:
        print(f"Eroare procesare: {e}")


# --- CONECTARE MQTT ---
client = mqtt.Client(
    client_id="Simulare_Server_Central",
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION1
)

client.on_connect = lambda c, u, f, rc: print("[SERVER] Conectat. Monitorizez T, O2 si pH...")
client.on_message = on_message

client.connect(BROKER, PORT)
client.subscribe(TOPIC_DATE)
client.loop_forever()