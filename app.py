from flask import Flask, render_template, jsonify
import standings_cascade_points_desc as standings

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/full")
def api_full():
    rows = standings.compute_rows()
    games_today = standings.games_played_today_scl()
    return jsonify({
        "standings": rows,
        "games_today": games_today
    })

if __name__ == "__main__":
    app.run(debug=True)
