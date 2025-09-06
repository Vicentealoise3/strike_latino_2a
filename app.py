import threading
import time
from flask import Flask, render_template, jsonify
from standings_cascade_points_desc import calculate_standings, get_games_today

app = Flask(__name__)

# Aquí guardamos los datos en memoria
standings_cache = []
games_today_cache = []

# -----------------------------
# 🔹 Función que actualiza la caché
# -----------------------------
def update_cache():
    global standings_cache, games_today_cache
    try:
        standings_cache = calculate_standings()
        games_today_cache = get_games_today()
        print("[OK] Cache actualizada")
    except Exception as e:
        print("[ERROR] al actualizar cache:", e)

# -----------------------------
# 🔹 Hilo en segundo plano que repite cada 5 min
# -----------------------------
def updater_loop():
    while True:
        update_cache()
        time.sleep(300)  # 300 segundos = 5 minutos

# -----------------------------
# 🔹 Rutas de la web
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/standings")
def api_standings():
    return jsonify(standings_cache)

@app.route("/api/games_today")
def api_games_today():
    return jsonify(games_today_cache)

# -----------------------------
# 🔹 Inicio de la app
# -----------------------------
if __name__ == "__main__":
    # Primero actualizamos la cache una vez
    update_cache()

    # Arrancamos el hilo que actualiza cada 5 minutos
    t = threading.Thread(target=updater_loop, daemon=True)
    t.start()

    # Iniciar Flask
    app.run(debug=True, host="0.0.0.0", port=5000)
