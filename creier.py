import json
import paho.mqtt.client as mqtt

# --- CONFIGURARE ---
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_DATE = "acvacultura/student/bazin1/senzori"
TOPIC_COMENZI = "acvacultura/student/bazin1/comenzi"

LIMITA_PERICOL = 22.0


# --- LOGICA (Ce gandeste serverul) ---
def on_message(client, userdata, msg):
    try:
        # 1. Despachetam mesajul primit
        continut = msg.payload.decode()
        date = json.loads(continut)
        temp_curenta = date['temperatura']

        print(f"[CREIER] Analizez: Temperatura e {temp_curenta} C")

        # 2. Luam decizia
        if temp_curenta < LIMITA_PERICOL:
            print("         [ALERTA] E prea frig! Pestii sufera!")
            print("         -> Trimit comanda de incalzire...")
            client.publish(TOPIC_COMENZI, "START_INCALZITOR")
        else:
            print("         [OK] Parametri normali.")
        print("-" * 30)
    except Exception as e:
        print(f"Eroare procesare: {e}")


# --- CONECTARE ---
# AICI ERA EROAREA - AM CORECTAT LINIA DE MAI JOS:
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Simulare_Server_Central")

client.on_connect = lambda c, u, f, rc: print("[SERVER] Conectat. Astept date...")
client.on_message = on_message

client.connect(BROKER, PORT)
client.subscribe(TOPIC_DATE)

# --- RAMANE PORNIT MEREU ---
client.loop_forever()