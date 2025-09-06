from flask import Flask, render_template, jsonify
import json
import os
from datetime import datetime, timedelta
import pytz

from standings_cascade_points_desc import compute_rows, games_played_today_scl

app = Flask(__name__)

CACHE_TTL = 60 * 5  # 5 minutos
CACHE = {
    "rows": None,
    "last_update": datetime.min
}

# --------------------------
# Manejo de caché en memoria
# --------------------------
def get_cached_standings():
    global CACHE
    now = datetime.now()
    if CACHE["rows"] is None or (now - CACHE["last_update"]).total_seconds() > CACHE_TTL:
        rows = compute_rows()
        CACHE["rows"] = rows
        CACHE["last_update"] = now
        print(f"[CACHE] Refrescado en {now}")
    return CACHE["rows"]

# --------------------------
# Rutas Flask
# --------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/standings")
def api_standings():
    rows = get_cached_standings()
    return jsonify({
        "rows": rows,
        "last_refresh": CACHE["last_update"].strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/api/games_today")
def api_games_today():
    try:
        games = games_played_today_scl()
        return jsonify(games)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------------
# Mantener la caché activa en Render
# --------------------------
@app.before_request
def refresh_cache_background():
    """Forza a que la caché se actualice si ya venció"""
    get_cached_standings()

if __name__ == "__main__":
    app.run(debug=True)
