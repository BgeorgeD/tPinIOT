import time
import random
import json
import paho.mqtt.client as mqtt

# --- CONFIGURARE ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_DATE = "acvacultura/student/bazin1/senzori"
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"


# --- ACTUATOR (Ce face bazinul cand primeste comanda) ---
def on_message(client, userdata, msg):
    comanda = msg.payload.decode()
    print(f"\n[ACTUATOR] !!! Am primit comanda: {comanda}")

    if "START_INCALZITOR" in comanda:
        print("           -> PORNESC REZISTENTA DE INCALZIRE (CLIC-CLIC)")
        print("           -> Apa incepe sa se incalzeasca...\n")


# --- CONECTARE ---
# AICI ERA EROAREA - AM CORECTAT LINIA DE MAI JOS:
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Simulare_Bazin_Fizic")

client.on_connect = lambda c, u, f, rc: print("[BAZIN] Conectat la reteaua de test.")
client.on_message = on_message

client.connect(BROKER, PORT)
client.subscribe(TOPIC_COMENZI)
client.loop_start()

# --- SENZORI (Bucla infinita) ---
temp_apa = 24.0

try:
    while True:
        # 1. Simulam natura: temperatura scade incet
        scadere = random.uniform(0.1, 0.4)
        temp_apa -= scadere

        # 2. Impachetam datele
        pachet = {
            "temperatura": round(temp_apa, 2),
            "ph": 7.0
        }

        # 3. Trimitem datele (PUBLICAM)
        print(f"[SENZOR] Temperatura a scazut la: {pachet['temperatura']} C -> Trimit date...")
        client.publish(TOPIC_DATE, json.dumps(pachet))

        time.sleep(3)

except KeyboardInterrupt:
    client.loop_stop()