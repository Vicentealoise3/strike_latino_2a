import standings_cascade_points_desc as standings
import json
import os
import time
from datetime import datetime

CACHE_FILE = "standings_cache.json"

def update_data_cache():
    """Fetches and saves standings and today's games data to a JSON cache file."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando actualización del cache...")
    try:
        # Aquí se ejecuta toda la lógica pesada de la API
        rows = standings.compute_rows()
        games_today = standings.games_played_today_scl()
        
        data_to_cache = {
            "standings": rows,
            "games_today": games_today
        }
        
        # Guarda el resultado en un archivo JSON
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_cache, f, ensure_ascii=False, indent=2)
            
        print("Actualización completada exitosamente.")
        
    except Exception as e:
        print(f"ERROR durante la actualización del cache: {e}")
        # Considera notificar de alguna forma si esto falla
        
if __name__ == "__main__":
    # Para un entorno de producción, usa un scheduler como 'cron' (Linux) o 'Task Scheduler' (Windows).
    # Este bucle es para desarrollo/demostración.
    UPDATE_INTERVAL_SECONDS = 300  # 5 minutos
    
    while True:
        update_data_cache()
        print(f"Esperando {UPDATE_INTERVAL_SECONDS} segundos para la próxima actualización...")
        time.sleep(UPDATE_INTERVAL_SECONDS)