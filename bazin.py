import time
import random
import json
import paho.mqtt.client as mqtt

# --- CONFIGURARE ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_DATE = "acvacultura/student/bazin1/senzori"
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"

# Stare initiala actuator
incalzitor_pornit = False


# --- ACTUATOR (Ce face bazinul cand primeste comanda) ---
def on_message(client, userdata, msg):
    global incalzitor_pornit  # Folosim variabila globala ca sa o putem modifica
    comanda = msg.payload.decode()
    print(f"\n[ACTUATOR] !!! Am primit comanda: {comanda}")

    if "START_INCALZITOR" in comanda:
        incalzitor_pornit = True
        print("           -> [HARDWARE] REZISTENTA PORNITA (Se incalzeste...)")

    elif "STOP_INCALZITOR" in comanda:
        incalzitor_pornit = False
        print("           -> [HARDWARE] REZISTENTA OPRITA (Racire naturala...)")

    elif "START_AERATOR" in comanda:
        print("           -> [HARDWARE] Aeratorul face bule! Ooo Ooo")


# --- CONECTARE ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Simulare_Bazin_Fizic")
client.on_connect = lambda c, u, f, rc: print("[BAZIN] Conectat. Simulez fizica apei...")
client.on_message = on_message

client.connect(BROKER, PORT)
client.subscribe(TOPIC_COMENZI)
client.loop_start()

# --- SENZORI (Bucla infinita) ---
temp_apa = 24.0

try:
    while True:
        # --- LOGICA DE SIMULARE FIZICA ---
        if incalzitor_pornit == True:
            # Daca incalzitorul e pornit, temperatura CRESTE
            crestere = random.uniform(0.3, 0.6)
            temp_apa += crestere
            print(f"   [FIZICA] Incalzitor ON. Apa se incalzeste (+{crestere:.2f})")
        else:
            # Daca incalzitorul e oprit, temperatura SCADE (natural)
            scadere = random.uniform(0.1, 0.3)
            temp_apa -= scadere
            print(f"   [FIZICA] Incalzitor OFF. Apa se raceste (-{scadere:.2f})")

        # Impachetam si trimitem datele
        pachet = {
            "temperatura": round(temp_apa, 2),
            "ph": 7.0,
            "incalzitor": "PORNIT" if incalzitor_pornit else "OPRIT"
        }

        print(f"[SENZOR] Trimit Temp: {pachet['temperatura']} C")
        client.publish(TOPIC_DATE, json.dumps(pachet))

        time.sleep(3)  # Pauza de 3 secunde

except KeyboardInterrupt:
    client.loop_stop()