from flask import Flask, render_template, jsonify, request
from neo4j import GraphDatabase
import paho.mqtt.client as mqtt
import uuid  # <--- IMPORT IMPORTANT (pentru ID unic)
import config  # Importam setarile din config.py

app = Flask(__name__)

# --- 1. CONEXIUNI (Cloud & MQTT) ---

# Conexiune Neo4j
driver = GraphDatabase.driver(
    config.NEO4J_URI,
    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
)

# --- REPARATIE CONFLICT MQTT ---
# Generam un ID unic (ex: App_Web_a1b2c3) ca sa nu existe conflicte cu colegul
unique_client_id = f"App_Web_{uuid.uuid4().hex[:6]}"

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, unique_client_id)
mqtt_client.connect(config.MQTT_BROKER, config.MQTT_PORT)
mqtt_client.loop_start()

print(f"[SYSTEM] Web App conectat la MQTT cu ID: {unique_client_id}")


# --- 2. FUNCTII AJUTATOARE ---
def get_latest(tx, tank_id):
    """Cauta ultima citire pentru un bazin specific in baza de date."""
    query = """
    MATCH (t:Tank {id: $tank_id})-[:HAS_READING]->(r:Reading)
    RETURN r ORDER BY r.timestamp DESC LIMIT 1
    """
    result = tx.run(query, tank_id=tank_id)
    record = result.single()
    if record:
        return dict(record["r"])
    return None


# --- 3. RUTE FLASK (Web Endpoints) ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/connect', methods=['POST'])
def connect_tank():
    """
    Verifica daca codul introdus de utilizator exista in baza de date.
    Folosit la ecranul de Login.
    """
    tank_id = request.json.get('tank_id')

    with driver.session() as session:
        data = session.execute_read(get_latest, tank_id)

    if data:
        return jsonify({"status": "success", "message": "Conectat!"})
    return jsonify({"status": "error", "message": "Cod invalid sau fara date."})


@app.route('/api/data')
def get_data():
    """
    Returneaza datele live pentru dashboard (polling la fiecare 2 secunde).
    """
    tank_id = request.args.get('tank_id')

    if not tank_id:
        return jsonify({})

    with driver.session() as session:
        data = session.execute_read(get_latest, tank_id)

    # Returnam datele sau un obiect gol daca nu exista inca
    return jsonify(data if data else {})


@app.route('/api/control', methods=['POST'])
def control():
    """
    Trimite comanda MQTT spre bazin (ex: START_AERATOR).
    """
    data = request.json
    tank_id = data.get('tank_id')
    actiune = data.get('actiune')

    # Construim topicul dinamic pentru acel bazin
    topic = f"{config.TOPIC_BASE}/{tank_id}/comenzi"

    mqtt_client.publish(topic, actiune)
    print(f"[WEB] Comanda {actiune} -> {topic}")

    return jsonify({"status": "ok"})


if __name__ == '__main__':
    try:
        # ATENTIE: use_reloader=False este CRITIC pentru MQTT in Flask
        # Previne pornirea a doua instante si dublarea conexiunii
        app.run(host="0.0.0.0", debug=True, port=5000, use_reloader=False)
    finally:
        # Inchidem conexiunile curat la oprire
        driver.close()
        mqtt_client.loop_stop()