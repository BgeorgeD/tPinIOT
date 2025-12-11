from neo4j import GraphDatabase

# --- ZONA DE MODIFICAT ---

# 1. ADRESA (URI). Trebuie neapărat să înceapă cu "neo4j+s://"
# Exemplu: "neo4j+s://a1b2c3d4.databases.neo4j.io"
URI_TEST = "neo4j+s://0bb0201c.databases.neo4j.io"  # ⬅️ PUNE LINK-UL TĂU AICI

# 2. PAROLA. Pune parola lungă primită la creare, între ghilimele.
# Userul rămâne "neo4j"
AUTH_TEST = ("neo4j", "lq16qwHksFuvZxCN6twI5bMLaYav42a2jb9v_fbuOyE")  # ⬅️ PUNE PAROLA AICI

# -------------------------

print("\n🚀 Încep testul de conexiune...")
print(f"📡 Încerc conectarea la: {URI_TEST}")

try:
    # Încercăm conectarea
    driver = GraphDatabase.driver(URI_TEST, auth=AUTH_TEST)

    # Verificăm dacă serverul răspunde
    driver.verify_connectivity()

    print("\n✅ SUCCES! Conexiunea funcționează perfect.")
    print("    Problema nu este la Python, nici la rețea.")
    print("    Poți copia aceste date în config.py și va merge.")

    driver.close()

except Exception as e:
    print("\n❌ EROARE DE CONECTARE:")
    print(f"Mesaj eroare: {e}")
    print("-" * 30)

    if "Routing" in str(e) or "ServiceUnavailable" in str(e):
        print("🔍 Sfat: Verifica dacă ai pus 'neo4j+s://' la început.")
        print("🔍 Sfat: Dacă ești pe Wi-Fi-ul facultății, încearcă pe Hotspot de pe telefon.")
    elif "Authentication" in str(e) or "Auth" in str(e):
        print("🔑 Sfat: Parola este greșită.")