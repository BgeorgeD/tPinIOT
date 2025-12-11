from flask import Flask, render_template, jsonify, request
from neo4j import GraphDatabase
import paho.mqtt.client as mqtt
import config  # Importam setarile din config.py

app = Flask(__name__)

# --- 1. CONEXIUNI (Cloud & MQTT) ---
# Ne conectam la Neo4j folosind datele din config.py
# (Atentie: asigura-te ca in config.py ai pus 'neo4j+ssc://' daca esti pe retea restrictionata)
driver = GraphDatabase.driver(
    config.NEO4J_URI,
    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
)

# Ne conectam la MQTT pentru a putea trimite comenzi
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "App_Web_Controller")
mqtt_client.connect(config.MQTT_BROKER, config.MQTT_PORT)
mqtt_client.loop_start()


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
        # Rulam serverul pe portul 5000
        app.run(debug=True, port=5000)
    finally:
        # Inchidem conexiunile curat la oprire
        driver.close()
        mqtt_client.loop_stop()