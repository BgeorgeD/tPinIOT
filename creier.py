import json
import time
import paho.mqtt.client as mqtt
from neo4j import GraphDatabase
import uuid  # <--- 1. IMPORT NECESAR PENTRU ID UNIC
import config  # Importam setarile

# Asculta toate bazinele
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


def save_reading(tx, payload):
    tank_id = payload.pop("id_bazin")
    timestamp = int(time.time() * 1000)

    # 1. Asigura ca exista Bazinul
    tx.run("MERGE (t:Tank {id: $tank_id})", tank_id=tank_id)

    # 2. Creeaza Citirea NOUA
    query_insert = """
    MATCH (t:Tank {id: $tank_id})
    CREATE (r:Reading {
        temperatura: $temp, ph: $ph, oxigen: $oxigen, timestamp: $timestamp,
        incalzitor: $heat, aerator: $air, filtru: $filt
    })
    CREATE (t)-[:HAS_READING]->(r)
    """

    # Extragem statusurile
    stats = payload.get("status_actuatori", {})

    tx.run(query_insert, tank_id=tank_id, temp=payload["temperatura"],
           ph=payload["ph"], oxigen=payload["oxigen"], timestamp=timestamp,
           heat=stats.get("incalzitor", "N/A"),
           air=stats.get("aerator", "N/A"),
           filt=stats.get("filtru", "N/A"))

    # 3. CURATENIE AUTOMATA (Sterge datele vechi pentru a mentine baza rapida)
    # Pastram doar ultimele 200 de citiri. Stergem restul.
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
    except Exception as e:
        print(f"Eroare procesare: {e}")


# --- MAIN ---
init_neo4j()

# --- REPARATIE CONFLICT ---
# Generam un ID unic (ex: Creier_Cloud_Writer_f4a2b1)
unique_client_id = f"Creier_Cloud_Writer_{uuid.uuid4().hex[:6]}"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, unique_client_id)
client.on_connect = lambda c, u, f, rc: print(f"🟢 [MQTT] Conectat cu ID: {unique_client_id}")
client.on_message = on_message

client.connect(config.MQTT_BROKER, config.MQTT_PORT)
client.subscribe(TOPIC_LISTEN)
client.loop_forever()