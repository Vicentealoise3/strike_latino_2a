# app.py
from flask import Flask, render_template, jsonify
import json, threading, time, os
from datetime import datetime

app = Flask(__name__)

CACHE_FILE = "standings_cache.json"
CACHE_INTERVAL_SEC = 300  # 5 minutos

# ==========================
# LÓGICA DE ACTUALIZACIÓN DE CACHÉ
# ==========================
def actualizar_cache():
    """
    Llama a tu módulo de standings, arma el JSON y lo guarda en disco.
    """
    print("[cache] Actualizando cache...")
    try:
        import standings_cascade_points_desc as standings

        rows = standings.compute_rows()                  # tabla de posiciones
        juegos_hoy = standings.games_played_today_scl()  # juegos del “día” (Chile)

        datos = {
            "standings": rows,
            "games_today": juegos_hoy,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print("[cache] OK")
    except Exception as e:
        print(f"[cache] Error: {e}")

def tarea_recurrente():
    """Hilo en segundo plano que refresca el cache cada X minutos."""
    while True:
        actualizar_cache()
        time.sleep(CACHE_INTERVAL_SEC)

# ===== Iniciar el hilo de caché SIN decoradores (compatible con Render/Gunicorn) =====
_bg_started = False
_bg_lock = threading.Lock()

def _start_background_updater():
    global _bg_started
    with _bg_lock:
        if _bg_started:
            return
        # 1) Generar cache inicial si no existe (así /api/full tiene algo)
        try:
            if not os.path.exists(CACHE_FILE):
                actualizar_cache()
        except Exception as e:
            print(f"[cache] Error inicial: {e}")

        # 2) Lanzar el hilo daemon
        t = threading.Thread(target=tarea_recurrente, daemon=True)
        t.start()
        _bg_started = True
        print("[cache] Hilo recurrente iniciado")

# Llamamos al iniciador en import time (cada worker de gunicorn tendrá su hilo, está bien)
_start_background_updater()

# ==========================
# RUTAS
# ==========================
@app.route("/")
def index():
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
