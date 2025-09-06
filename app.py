# app.py
from flask import Flask, render_template, jsonify
import json, threading, time, os
from datetime import datetime

app = Flask(__name__)

CACHE_FILE = "standings_cache.json"
CACHE_INTERVAL_SEC = 300  # 5 minutos

# ==========================
# AQUÍ PEGAS TU LÓGICA REAL DE update_cache.py
# (bajar datos de la API, procesar y guardar en standings_cache.json)
# ==========================
def actualizar_cache():
    """
    Reemplaza el contenido de este ejemplo por tu lógica real.
    Debe escribir un JSON en CACHE_FILE con al menos:
      {
        "standings": [...],
        "games_today": [...],
        "last_update": "2025-09-06 12:34:56"
      }
    """
    print("[cache] Actualizando cache...")
    datos = {
        "standings": [
            # EJEMPLO — remplázalo por los standings reales
            {"team": "Yankees", "user": "demo", "played": 15, "wins": 10, "losses": 5, "remaining": 33, "points": 25}
        ],
        "games_today": [
            # EJEMPLO — remplázalo por la lista real de juegos de hoy
            "Yankees 4 - Red Sox 2 - 06-09-2025 - 11:10 am (hora Chile)"
        ],
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print("[cache] OK")

def tarea_recurrente():
    """Hilo en segundo plano que refresca el cache cada X minutos."""
    while True:
        try:
            actualizar_cache()
        except Exception as e:
            print(f"[cache] Error: {e}")
        time.sleep(CACHE_INTERVAL_SEC)

# Nota: en Gunicorn no se ejecuta el bloque __main__, por eso usamos este hook.
@app.before_first_request
def iniciar_hilo_cache():
    # 1) Crear el cache una vez (rápido) para que la página tenga algo que mostrar
    try:
        if not os.path.exists(CACHE_FILE):
            actualizar_cache()
    except Exception as e:
        print(f"[cache] Error inicial: {e}")

    # 2) Lanzar el hilo recurrente (daemon)
    hilo = threading.Thread(target=tarea_recurrente, daemon=True)
    hilo.start()
    print("[cache] Hilo recurrente iniciado")

# ==========================
# RUTAS
# ==========================
@app.route("/")
def index():
    # Renderiza la plantilla; tu index.html hará fetch a /api/full si así lo tienes
    return render_template("index.html")

@app.route("/api/full")
def api_full():
    if not os.path.exists(CACHE_FILE):
        return jsonify({"error": "Cache no disponible"}), 503
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Para correr localmente con `python app.py`
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
