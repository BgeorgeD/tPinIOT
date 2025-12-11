import time
import random
import json
import paho.mqtt.client as mqtt
import config  # Importam setarile


# --- GENERARE IDENTITATE ---
def genereaza_id_bazin():
    return str(random.randint(1000, 9999))


TANK_ID = genereaza_id_bazin()
TOPIC_DATE = f"{config.TOPIC_BASE}/{TANK_ID}/senzori"
TOPIC_COMENZI = f"{config.TOPIC_BASE}/{TANK_ID}/comenzi"

print(f"\n{'=' * 40}")
print(f"   🌊 BAZIN INITIALIZAT")
print(f"   🆔 COD UNIC: >> {TANK_ID} <<")
print(f"   (Noteaza acest cod pentru site!)")
print(f"{'=' * 40}\n")

# --- PARAMETRI INITIALI ---
temp_apa = 22.5  # Pornim de la o temperatura ok
ph = 7.0
oxigen = 7.5

# Limite naturale (fizica)
TEMP_CAMERA = 20.0  # Apa nu se raceste sub temperatura camerei

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


# --- MQTT SETUP ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f"Bazin_{TANK_ID}")
client.on_connect = lambda c, u, f, rc: print(f"[SISTEM] Conectat la HiveMQ.")
client.on_message = on_message
client.connect(config.MQTT_BROKER, config.MQTT_PORT)
client.subscribe(TOPIC_COMENZI)
client.loop_start()

# --- BUCLA PRINCIPALA ---
try:
    while True:
        # --- 1. FIZICA TEMPERATURA ---
        if actuatori["incalzitor"]:
            # Daca incalzim, creste vizibil
            temp_apa += random.uniform(0.2, 0.5)
        else:
            # Daca NU incalzim, tinde spre temperatura camerei (20 grade)
            if temp_apa > TEMP_CAMERA:
                # Scade INCET (0.05 - 0.1 grade)
                temp_apa -= random.uniform(0.05, 0.1)
            else:
                # Daca e deja rece, fluctueaza foarte putin in jurul lui 20
                temp_apa += random.uniform(-0.05, 0.05)

        # --- 2. FIZICA OXIGEN ---
        if actuatori["aerator"]:
            # Creste rapid cand pornim aeratorul
            oxigen += random.uniform(0.3, 0.6)
        else:
            # Scade lent (pestii respira)
            oxigen -= random.uniform(0.05, 0.15)

        # Limite hard (nu poate fi negativ sau peste saturatie)
        oxigen = max(0.5, min(14.0, oxigen))  # Minim 0.5 ca sa nu moara pestii instant

        # --- 3. FIZICA pH ---
        if actuatori["filtru"]:
            # Filtrul stabilizeaza pH-ul spre 7.0 (neutru)
            if ph > 7.1:
                ph -= 0.05
            elif ph < 6.9:
                ph += 0.05
        else:
            # Fara filtru, pH-ul devine instabil (drift usor)
            ph += random.uniform(-0.05, 0.05)

        # Limite pH
        ph = max(5.0, min(9.0, ph))

        # --- PREGATIRE DATE ---
        payload = {
            "id_bazin": TANK_ID,
            "temperatura": round(temp_apa, 2),
            "ph": round(ph, 2),
            "oxigen": round(oxigen, 2),
            "status_actuatori": {k: ("PORNIT" if v else "OPRIT") for k, v in actuatori.items()}
        }

        print(f"[SENZOR {TANK_ID}] T:{payload['temperatura']} | O2:{payload['oxigen']} -> Cloud")
        client.publish(TOPIC_DATE, json.dumps(payload))

        # Trimitem date la fiecare 3 secunde
        time.sleep(3)

except KeyboardInterrupt:
    client.loop_stop()