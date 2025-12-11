import time
import random
import json
import paho.mqtt.client as mqtt
import config  # Importam setarile din config.py


# --- GENERARE IDENTITATE UNICA ---
def genereaza_id_bazin():
    return str(random.randint(1000, 9999))


TANK_ID = genereaza_id_bazin()
TOPIC_DATE = f"{config.TOPIC_BASE}/{TANK_ID}/senzori"
TOPIC_COMENZI = f"{config.TOPIC_BASE}/{TANK_ID}/comenzi"

print(f"\n{'=' * 40}")
print(f"   🌊 BAZIN INITIALIZAT (Calibrat)")
print(f"   🆔 COD UNIC: >> {TANK_ID} <<")
print(f"   (Foloseste acest cod in Interfata!)")
print(f"{'=' * 40}\n")

# --- PARAMETRI INITIALI (Ideali) ---
temp_apa = 23.0
ph = 7.2
oxigen = 8.0  # Pornim cu oxigen perfect

# Limite fizice simulate
TEMP_CAMERA = 21.0  # Temperatura sub care nu scade apa natural

actuatori = {"incalzitor": False, "aerator": False, "filtru": False}


# --- PROCESSARE COMENZI ---
def on_message(client, userdata, msg):
    global actuatori
    try:
        cmd = msg.payload.decode()
        print(f"[COMANDA] {cmd}")

        if "START_INCALZITOR" in cmd:
            actuatori["incalzitor"] = True
        elif "STOP_INCALZITOR" in cmd:
            actuatori["incalzitor"] = False
        elif "START_AERATOR" in cmd:
            actuatori["aerator"] = True
        elif "STOP_AERATOR" in cmd:
            actuatori["aerator"] = False
        elif "START_FILTRU" in cmd:
            actuatori["filtru"] = True
        elif "STOP_FILTRU" in cmd:
            actuatori["filtru"] = False
    except:
        pass


# --- CONECTARE MQTT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f"Bazin_{TANK_ID}")
client.on_connect = lambda c, u, f, rc: print(f"[SISTEM] Conectat la HiveMQ.")
client.on_message = on_message
client.connect(config.MQTT_BROKER, config.MQTT_PORT)
client.subscribe(TOPIC_COMENZI)
client.loop_start()

# --- BUCLA PRINCIPALA (SIMULARE FIZICA) ---
try:
    while True:
        # ---------------------------------------------------------
        # 1. FIZICA TEMPERATURA (Reglata anterior)
        # ---------------------------------------------------------
        if actuatori["incalzitor"]:
            temp_apa += random.uniform(0.1, 0.3)  # Incalzire
        else:
            # Racire naturala spre temperatura camerei
            if temp_apa > TEMP_CAMERA:
                temp_apa -= random.uniform(0.02, 0.08)  # Racire FOARTE lenta
            else:
                # Fluctuatie minora la echilibru
                temp_apa += random.uniform(-0.02, 0.02)

        # ---------------------------------------------------------
        # 2. FIZICA OXIGEN (AICI AM FACUT SCHIMBARILE MARI)
        # ---------------------------------------------------------
        if actuatori["aerator"]:
            # Cand primesti comanda, oxigenul creste VIZIBIL
            oxigen += random.uniform(0.4, 0.8)
        else:
            # Cand e oprit, scade FOARTE LENT (consumul pestilor)
            # Inainte scadea cu 0.2, acum scade cu maxim 0.08
            oxigen -= random.uniform(0.01, 0.08)

        # Limite realiste (nu trece de 15, nu scade sub 1 fara motiv extrem)
        oxigen = max(0.5, min(15.0, oxigen))

        # ---------------------------------------------------------
        # 3. FIZICA pH
        # ---------------------------------------------------------
        if actuatori["filtru"]:
            # Filtrul trage pH-ul spre 7.0 (neutru)
            if ph > 7.05:
                ph -= 0.05
            elif ph < 6.95:
                ph += 0.05
        else:
            # Fara filtru, pH-ul are un drift usor (murdarire)
            ph += random.uniform(-0.03, 0.03)

        ph = max(5.5, min(8.5, ph))

        # --- IMPACHETARE SI TRIMITERE ---
        payload = {
            "id_bazin": TANK_ID,
            "temperatura": round(temp_apa, 2),
            "ph": round(ph, 2),
            "oxigen": round(oxigen, 2),
            "status_actuatori": {k: ("PORNIT" if v else "OPRIT") for k, v in actuatori.items()}
        }

        print(f"[SENZOR {TANK_ID}] T:{payload['temperatura']} | O2:{payload['oxigen']} -> Cloud")
        client.publish(TOPIC_DATE, json.dumps(payload))

        # Pauza de 3 secunde intre citiri
        time.sleep(3)

except KeyboardInterrupt:
    client.loop_stop()