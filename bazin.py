import time
import random
import json
import paho.mqtt.client as mqtt
import config


# -----------------------------
# UTILITARE
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def genereaza_id_bazin():
    return str(random.randint(1000, 9999))


# -----------------------------
# IDENTITATE + TOPICURI
# -----------------------------
TANK_ID = genereaza_id_bazin()
TOPIC_DATE = f"{config.TOPIC_BASE}/{TANK_ID}/senzori"
TOPIC_COMENZI = f"{config.TOPIC_BASE}/{TANK_ID}/comenzi"

print(f"\n{'=' * 40}")
print(f"   🌊 BAZIN INITIALIZAT (Model Stabil + AutoPilot)")
print(f"   🆔 COD UNIC: >> {TANK_ID} <<")
print(f"   (Foloseste acest cod in Interfata!)")
print(f"{'=' * 40}\n")


# -----------------------------
# STARE INITIALA
# -----------------------------
temp_apa = 23.0
ph = 7.2
oxigen = 8.0

# "Camera" (mediul) - apa tinde natural spre asta
TEMP_CAMERA = 21.0
PH_TARGET = 7.0

# Realism: incarcare biologica (mai multi pesti / hranire / murdarie)
BIO_LOAD = 1.0   # 1.0 normal; 1.5 mediu; 2.0 stres (pentru demo)
ROOM_COLD = 0.0  # 0.0 normal; 0.05-0.10 -> "iarna" (camera mai rece)

# actuatori = ce controleaza userul/auto
actuatori = {"incalzitor": False, "aerator": False, "filtru": False}


# -----------------------------
# PARAMETRI MODEL (STABIL)
# -----------------------------
DT = 1.0  # secunde intre citiri

# revenire spre "normal"
K_TEMP_RELAX = 0.09
K_O2_RELAX = 0.06
K_PH_RELAX = 0.03

# efect actuatori
K_HEATER = 0.22
K_AERATOR_GAIN = 0.35
K_AERATOR_BOOST = 0.18
K_FILTER_GAIN = 0.25

# perturbari de baza
FISH_O2_CONSUM = 0.09      # consum pe pas
PH_DIRT_DRIFT = 0.01       # drift pH pe pas

# zgomot mic (senzor)
NOISE_TEMP = 0.03
NOISE_O2 = 0.05
NOISE_PH = 0.01


# -----------------------------
# LIMITE "NATURALE" + HISTERESIS
# (Astea sunt logice pt. acvaristica: stabile, explicabile)
# -----------------------------
SAFE = {
    # temperatura
    "T_MIN_ON": 21.0,   # sub asta -> PORNESTE incalzitor
    "T_MIN_OFF": 22.0,  # peste asta -> OPRESTE incalzitor (histerezis)

    # oxigen
    "O2_MIN_ON": 6.0,   # sub asta -> PORNESTE aerator
    "O2_MIN_OFF": 7.0,  # peste asta -> OPRESTE aerator

    # pH (simplu: daca e prea sus/jos, porneste filtrul)
    "PH_LOW_ON": 6.7,
    "PH_LOW_OFF": 6.9,
    "PH_HIGH_ON": 7.6,
    "PH_HIGH_OFF": 7.4,
}

AUTO_MODE = True  # mereu on; user poate "override" temporar

# Daca user apasa manual, tinem override (pe fiecare actuator) X secunde
MANUAL_OVERRIDE_SECONDS = 60
manual_override_until = {
    "incalzitor": 0.0,
    "aerator": 0.0,
    "filtru": 0.0
}


def is_manual(actuator_name: str) -> bool:
    return time.time() < manual_override_until[actuator_name]


def set_manual(actuator_name: str, state: bool):
    actuatori[actuator_name] = state
    manual_override_until[actuator_name] = time.time() + MANUAL_OVERRIDE_SECONDS
    print(f"[MANUAL] {actuator_name.upper()} -> {'PORNIT' if state else 'OPRIT'} "
          f"(override {MANUAL_OVERRIDE_SECONDS}s)")


def autopilot_step():
    """
    AutoPilot: daca user nu intervine, mentine bazinul in zona safe.
    Folosim histerezis: prag ON si prag OFF ca sa fie stabil (nu clipeste).
    """
    # ---- Incalzitor ----
    if not is_manual("incalzitor"):
        if (not actuatori["incalzitor"]) and (temp_apa <= SAFE["T_MIN_ON"]):
            actuatori["incalzitor"] = True
            print("[AUTO] PORNESC INCALZITOR (temp prea mica)")
        elif actuatori["incalzitor"] and (temp_apa >= SAFE["T_MIN_OFF"]):
            actuatori["incalzitor"] = False
            print("[AUTO] OPRESC INCALZITOR (temp ok)")

    # ---- Aerator ----
    if not is_manual("aerator"):
        if (not actuatori["aerator"]) and (oxigen <= SAFE["O2_MIN_ON"]):
            actuatori["aerator"] = True
            print("[AUTO] PORNESC AERATOR (O2 prea mic)")
        elif actuatori["aerator"] and (oxigen >= SAFE["O2_MIN_OFF"]):
            actuatori["aerator"] = False
            print("[AUTO] OPRESC AERATOR (O2 ok)")

    # ---- Filtru (pH) ----
    if not is_manual("filtru"):
        # pornire daca pH e prea jos sau prea sus
        if (not actuatori["filtru"]) and (ph <= SAFE["PH_LOW_ON"] or ph >= SAFE["PH_HIGH_ON"]):
            actuatori["filtru"] = True
            print("[AUTO] PORNESC FILTRU (pH in afara zonei)")
        # oprire cand revine in zona ok (histerezis)
        elif actuatori["filtru"] and (SAFE["PH_LOW_OFF"] <= ph <= SAFE["PH_HIGH_OFF"]):
            actuatori["filtru"] = False
            print("[AUTO] OPRESC FILTRU (pH ok)")


# -----------------------------
# MQTT COMENZI
# -----------------------------
def on_message(client, userdata, msg):
    global BIO_LOAD, ROOM_COLD
    try:
        cmd = msg.payload.decode().strip()
        print(f"[COMANDA] {cmd}")

        # --- MANUAL (override temporar) ---
        if cmd == "START_INCALZITOR":
            set_manual("incalzitor", True)
        elif cmd == "STOP_INCALZITOR":
            set_manual("incalzitor", False)

        elif cmd == "START_AERATOR":
            set_manual("aerator", True)
        elif cmd == "STOP_AERATOR":
            set_manual("aerator", False)

        elif cmd == "START_FILTRU":
            set_manual("filtru", True)
        elif cmd == "STOP_FILTRU":
            set_manual("filtru", False)

        # --- DEMO: stress control (optional, safe) ---
        # Ex: SET_LOAD_2  / SET_LOAD_1.5
        elif cmd.startswith("SET_LOAD_"):
            val = float(cmd.replace("SET_LOAD_", "").strip())
            BIO_LOAD = clamp(val, 0.5, 3.0)
            print(f"[DEMO] BIO_LOAD setat la {BIO_LOAD}")

        # Ex: SET_COLD_0.08 (iarna)
        elif cmd.startswith("SET_COLD_"):
            val = float(cmd.replace("SET_COLD_", "").strip())
            ROOM_COLD = clamp(val, 0.0, 0.15)
            print(f"[DEMO] ROOM_COLD setat la {ROOM_COLD}")

    except Exception as e:
        print(f"[EROARE MQTT] {e}")


# -----------------------------
# CONECTARE MQTT
# -----------------------------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f"Bazin_{TANK_ID}")
client.on_connect = lambda c, u, f, rc: print("[SISTEM] Conectat la MQTT.")
client.on_message = on_message
client.connect(config.MQTT_BROKER, config.MQTT_PORT)
client.subscribe(TOPIC_COMENZI)
client.loop_start()


# -----------------------------
# BUCLE SIMULARE (STABIL + AUTO)
# -----------------------------
try:
    while True:
        # 0) AutoPilot (inainte de model, ca sa reactioneze la starea curenta)
        if AUTO_MODE:
            autopilot_step()

        # -----------------------------
        # TEMPERATURA
        # -----------------------------
        # camera efectiva (iarna = camera mai rece)
        temp_camera_eff = TEMP_CAMERA - (ROOM_COLD * 20.0)  # 0.08 => -0.8C aprox

        # revine lent spre camera
        temp_apa += K_TEMP_RELAX * (temp_camera_eff - temp_apa)

        # incalzitor = impuls controlat
        if actuatori["incalzitor"]:
            temp_apa += K_HEATER

        temp_apa += random.uniform(-NOISE_TEMP, NOISE_TEMP)
        temp_apa = clamp(temp_apa, 15.0, 32.0)

        # -----------------------------
        # OXIGEN
        # -----------------------------
        # normalul depinde usor de temperatura
        o2_normal = 8.5 - 0.05 * max(0.0, temp_apa - 20.0)
        o2_normal = clamp(o2_normal, 6.8, 9.0)

        # revine spre normal + consum biologic
        oxigen += K_O2_RELAX * (o2_normal - oxigen)
        oxigen -= (FISH_O2_CONSUM * BIO_LOAD)

        # aerator accelereaza revenirea + boost
        if actuatori["aerator"]:
            oxigen += K_AERATOR_GAIN * (o2_normal - oxigen) + K_AERATOR_BOOST

        oxigen += random.uniform(-NOISE_O2, NOISE_O2)
        oxigen = clamp(oxigen, 0.5, 15.0)

        # -----------------------------
        # pH
        # -----------------------------
        ph += K_PH_RELAX * (PH_TARGET - ph)

        if actuatori["filtru"]:
            ph += K_FILTER_GAIN * (PH_TARGET - ph)
        else:
            ph += random.uniform(-PH_DIRT_DRIFT * BIO_LOAD, PH_DIRT_DRIFT * BIO_LOAD)

        ph += random.uniform(-NOISE_PH, NOISE_PH)
        ph = clamp(ph, 5.5, 8.5)

        # -----------------------------
        # PAYLOAD
        # -----------------------------
        payload = {
            "id_bazin": TANK_ID,
            "temperatura": round(temp_apa, 2),
            "ph": round(ph, 2),
            "oxigen": round(oxigen, 2),
            "status_actuatori": {k: ("PORNIT" if v else "OPRIT") for k, v in actuatori.items()},
            "demo": {
                "bio_load": round(BIO_LOAD, 2),
                "room_cold": round(ROOM_COLD, 2)
            }
        }

        print(
            f"[SENZOR {TANK_ID}] "
            f"T:{payload['temperatura']} | pH:{payload['ph']} | O2:{payload['oxigen']} | "
            f"H:{payload['status_actuatori']['incalzitor']} A:{payload['status_actuatori']['aerator']} F:{payload['status_actuatori']['filtru']} "
            f"(LOAD:{payload['demo']['bio_load']}, COLD:{payload['demo']['room_cold']}) -> Cloud"
        )

        client.publish(TOPIC_DATE, json.dumps(payload))
        time.sleep(DT)

except KeyboardInterrupt:
    client.loop_stop()
    print("\n[SISTEM] Oprit manual.")
