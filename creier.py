import json
import time
import paho.mqtt.client as mqtt
from neo4j import GraphDatabase
import uuid
import config  # setari: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MQTT_BROKER, MQTT_PORT, TOPIC_BASE

# Asculta toate bazinele: TOPIC_BASE/<tank_id>/senzori
TOPIC_LISTEN = f"{config.TOPIC_BASE}/+/senzori"

driver = None


def init_neo4j():
    global driver
    try:
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
        print("🟢 [NEO4J] Conectat la Cloud Database.")
    except Exception as e:
        print(f"❌ [NEO4J] EROARE: {e}")
        driver = None


def save_reading(tx, payload):
    # extragem tank_id si nu il punem ca proprietate pe Reading
    tank_id = payload.pop("id_bazin")
    timestamp = int(time.time() * 1000)

    # 1) asigura Tank
    tx.run("MERGE (t:Tank {id: $tank_id})", tank_id=tank_id)

    # 2) creeaza Reading + relatie
    query_insert = """
    MATCH (t:Tank {id: $tank_id})
    CREATE (r:Reading {
        temperatura: $temp,
        ph: $ph,
        oxigen: $oxigen,
        timestamp: $timestamp,
        incalzitor: $heat,
        aerator: $air,
        filtru: $filt
    })
    CREATE (t)-[:HAS_READING]->(r)
    """

    stats = payload.get("status_actuatori", {})

    tx.run(
        query_insert,
        tank_id=tank_id,
        temp=payload.get("temperatura"),
        ph=payload.get("ph"),
        oxigen=payload.get("oxigen"),
        timestamp=timestamp,
        heat=stats.get("incalzitor", "N/A"),
        air=stats.get("aerator", "N/A"),
        filt=stats.get("filtru", "N/A"),
    )

    # 3) curatenie: pastreaza ultimele 200 citiri
    query_cleanup = """
    MATCH (t:Tank {id: $tank_id})-[:HAS_READING]->(r:Reading)
    WITH r ORDER BY r.timestamp DESC SKIP 200
    DETACH DELETE r
    """
    tx.run(query_cleanup, tank_id=tank_id)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        tank_id = payload.get("id_bazin", "Unknown")
        print(f"[MQTT] Primit de la {tank_id}. Salvez...")

        if driver:
            with driver.session() as session:
                session.execute_write(save_reading, payload)
                print("💾 [DB] Salvat cu succes!")
        else:
            print("⚠️ [NEO4J] Driver indisponibil, nu salvez.")
    except Exception as e:
        print(f"❌ Eroare procesare: {e}")


# --- MAIN ---
init_neo4j()

unique_client_id = f"Creier_Cloud_Writer_{uuid.uuid4().hex[:6]}"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, unique_client_id)
client.on_connect = lambda c, u, f, rc: print(f"🟢 [MQTT] Conectat cu ID: {unique_client_id}")
client.on_message = on_message

client.connect(config.MQTT_BROKER, config.MQTT_PORT)
client.subscribe(TOPIC_LISTEN)
client.loop_forever()
