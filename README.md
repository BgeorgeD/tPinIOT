# 🌊 WaterSight: Sistem Distribuit de Monitorizare Acvacultură (IoT + Cloud)

Acest proiect reprezintă o soluție de cercetare pentru monitorizarea și controlul distribuit al parametrilor apei (Temperatură, Oxigen Dizolvat, pH) în bazinele de acvacultură.

Sistemul utilizează o arhitectură modernă bazată pe **Cloud Computing**, separând zona de achiziție de date (Edge) de zona de stocare și procesare (Cloud), facilitate prin middleware MQTT.

---

## 🛠️ Arhitectura Sistemului

Sistemul este compus din 4 module interconectate:

1.  **Simularea Fizică (`bazin.py`)**:
    * Simulează comportamentul fizic al apei și reacția la actuatori.
    * Generează o **Identitate Unică (Tank ID)** la fiecare rulare.
    * Comunică prin protocolul **MQTT**.

2.  **Middleware & Procesare (`creier.py`)**:
    * Acționează ca un "Gateway".
    * Interceptează datele de la senzori via MQTT.
    * Salvează datele persistent în baza de date orientată pe grafuri **Neo4j AuraDB (Cloud)**.

3.  **Backend Web (`app.py`)**:
    * Server Flask care interoghează Cloud-ul Neo4j pentru date istorice și live.
    * Gestionează comenzile utilizatorului și le trimite înapoi la bazin.

4.  **Frontend (`index.html`)**:
    * Interfață grafică cu autentificare pe bază de cod (Tank ID).
    * Vizualizare grafică în timp real (Chart.js).

---

## 📋 Cerințe (Prerequisites)

* **Python 3.10+**
* Conexiune activă la Internet (pentru MQTT Broker și Neo4j Cloud).
* Un cont activ (gratuit) pe **Neo4j AuraDB**.

---

## ⚙️ Instalare și Configurare

### Pasul 1: Clonarea proiectului
Descarcă proiectul și deschide terminalul în folderul principal.

### Pasul 2: Instalarea Dependințelor
Rulează următoarea comandă pentru a instala bibliotecile necesare:
```bash
pip install -r requirements.txt