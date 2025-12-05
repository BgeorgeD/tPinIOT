import time
import random
import json
import paho.mqtt.client as mqtt

# --- CONFIGURARE ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_DATE = "acvacultura/student/bazin1/senzori"
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"

# --- STARE INITIALA ACTUATORI ---
incalzitor_pornit = False
filtru_pornit = False
aerator_pornit = False


# --- SENZORI INITIALI ---
temp_apa = 24.0
ph = 7.0
oxigen = 7.5

# --- ACTUATOR (Ce face bazinul cand primeste comanda) ---
def on_message(client, userdata, msg):
    global incalzitor_pornit, filtru_pornit, aerator_pornit
    comanda = msg.payload.decode()
    print(f"\n[ACTUATOR] !!! Am primit comanda: {comanda}")

    if "START_INCALZITOR" in comanda:
        incalzitor_pornit = True
        print("           -> [HARDWARE] REZISTENTA PORNITA (Se incalzeste...)")
    elif "STOP_INCALZITOR" in comanda:
        incalzitor_pornit = False
        print("           -> [HARDWARE] REZISTENTA OPRITA (Racire naturala...)")
    elif "START_AERATOR" in comanda:
        aerator_pornit = True
        print("           -> [HARDWARE] Aerator PORNIT! ")
    elif "STOP_AERATOR" in comanda:
        aerator_pornit = False
        print("           -> [HARDWARE] Aerator OPRIT.")
    elif "START_FILTRU" in comanda:
        filtru_pornit = True
        print("           -> [HARDWARE] Filtrul PORNIT, apa se stabilizeaza...")
    elif "STOP_FILTRU" in comanda:
        filtru_pornit = False
        print("           -> [HARDWARE] Filtrul OPRIT.")

# --- CONECTARE MQTT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Simulare_Bazin_Fizic")
client.on_connect = lambda c, u, f, rc: print("[BAZIN] Conectat. Simulez fizica apei...")
client.on_message = on_message
client.connect(BROKER, PORT)
client.subscribe(TOPIC_COMENZI)
client.loop_start()

# --- SENZORI (Bucla infinita) ---
try:
    while True:
        # --- TEMPERATURA ---
        if incalzitor_pornit:
            temp_apa += random.uniform(0.3, 0.6)
        else:
            temp_apa -= random.uniform(0.1, 0.3)

        # --- pH dinamic, influentat de filtru ---
        ph += random.uniform(-0.05, 0.05)
        if filtru_pornit:
            ph += (7.0 - ph) * 0.2  # stabilizare pH
        ph = max(6.0, min(ph, 9.0))

        # --- Oxigen dinamic, influentat de aerator ---
        oxigen += random.uniform(-0.1, 0.1)
        # Oxigen
        if aerator_pornit:
            # Aeratorul crește oxigenul
            crestere_oxigen = random.uniform(0.5, 1.0)
            oxigen += crestere_oxigen
            print(f"   [FIZICA] Aerator ON. Oxigenul crește (+{crestere_oxigen:.2f})")
        else:
            # Oxigenul scade natural
            scadere_oxigen = random.uniform(0.2, 0.5)
            oxigen -= scadere_oxigen
            print(f"   [FIZICA] Aerator OFF. Oxigenul scade (-{scadere_oxigen:.2f})")

        # Limite fizice
        if oxigen < 0: oxigen = 0
        if oxigen > 15: oxigen = 15

        # --- Trimitem datele ---
        pachet = {
            "temperatura": round(temp_apa, 2),
            "ph": round(ph, 2),
            "oxigen": round(oxigen, 2),
            "incalzitor": "PORNIT" if incalzitor_pornit else "OPRIT",
            "aerator": "PORNIT" if aerator_pornit else "OPRIT",
            "filtru": "PORNIT" if filtru_pornit else "OPRIT"
        }

        print(f"[SENZOR] Temp: {pachet['temperatura']}°C | pH: {pachet['ph']} | Oxigen: {pachet['oxigen']} mg/L")
        client.publish(TOPIC_DATE, json.dumps(pachet))

        time.sleep(3)




except KeyboardInterrupt:
    client.loop_stop()
