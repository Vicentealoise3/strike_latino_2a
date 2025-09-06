# standings_cascade_points_desc.py
# Tabla de posiciones con puntos y reporte de juegos del “día” (Chile)

import requests, time, re, os, json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ===== Config general =====

# ===== MODO DE EJECUCIÓN (switch) =====
# Valores posibles: "DEBUG" o "ONLINE"
MODE = "ONLINE"  # DEBUG u ONLINE

CFG = {
    "DEBUG": dict(
        PRINT_DETAILS=False,
        PRINT_CAPTURE_SUMMARY=True,
        PRINT_CAPTURE_LIST=False,
        DUMP_ENABLED=True,
        STOP_AFTER_N=None,
        DAY_WINDOW_MODE="calendar",   # 00:00–23:59 Chile
    ),
    "ONLINE": dict(
        PRINT_DETAILS=False,
        PRINT_CAPTURE_SUMMARY=False,
        PRINT_CAPTURE_LIST=False,
        DUMP_ENABLED=False,
        STOP_AFTER_N=None,
        DAY_WINDOW_MODE="sports",     # 06:00–05:59 Chile
    ),
}

# === Aplicar la config del modo seleccionado ===
conf = CFG.get(MODE, CFG["DEBUG"])

PRINT_DETAILS = conf["PRINT_DETAILS"]
PRINT_CAPTURE_SUMMARY = conf["PRINT_CAPTURE_SUMMARY"]
PRINT_CAPTURE_LIST = conf["PRINT_CAPTURE_LIST"]
DUMP_ENABLED = conf["DUMP_ENABLED"]
STOP_AFTER_N = conf["STOP_AFTER_N"]
DAY_WINDOW_MODE = conf["DAY_WINDOW_MODE"]  # "calendar" o "sports"

API = "https://mlb25.theshow.com/apis/game_history.json"
PLATFORM = "psn"
MODE_FILTER = "LEAGUE"
SINCE = datetime(2025, 8, 30)
PAGES = (1, 2, 3)          # ajusta según necesites
TIMEOUT = 20
RETRIES = 2

# === Capturas / dumps ===
DUMP_DIR = "out"

# ===== Liga (username EXACTO → equipo) =====
LEAGUE_ORDER = [
    ("THELSURICATO", "Mets"),
    ("machado_seba-03", "Reds"),
    ("zancudo99", "Rangers"),
    ("havanavcr10", "Brewers"),
    ("Solbbracho", "Tigers"),
    ("WILZULIA", "Royals"),
    ("Daviddiaz030425", "Guardians"),
    ("Juanchojs28", "Giants"),
    ("me_dicencarlitos", "Marlins"),
    ("Bufon3-0", "Athletics"),
    ("edwar13-21", "Blue Jays"),
    ("mrguerrillas", "Pirates"),
    ("Diamondmanager", "Astros"),
    ("Tu_Pauta2000", "Braves"),
]

# ====== IDs alternativos por participante (para sumar sin duplicar) ======
FETCH_ALIASES = {
    "Tu_Pauta2000": ["Lachi_1991"],
}

# ===== Ajustes algebraicos por equipo (resets W/L) =====
TEAM_RECORD_ADJUSTMENTS = {
    "Blue Jays": (0, -1),
    "Brewers": (-1, 0),
}

# ===== Ajustes manuales de PUNTOS =====
TEAM_POINT_ADJUSTMENTS = {
    # "Padres": (-1, "Desconexión vs X"),
}

# ===== Miembros de liga (para filtro de rival) =====
LEAGUE_USERS = {u for (u, _t) in LEAGUE_ORDER}
for base, alts in FETCH_ALIASES.items():
    LEAGUE_USERS.add(base)
    LEAGUE_USERS.update(alts)
LEAGUE_USERS.update({"AiramReynoso_", "Yosoyreynoso_"})
LEAGUE_USERS_NORM = {u.lower() for u in LEAGUE_USERS}

# ===== Utilidades =====
BXX_RE = re.compile(r"\^(b\d+)\^", flags=re.IGNORECASE)

def _safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s or "")

def _dump_json(filename: str, data):
    if not DUMP_ENABLED:
        return
    os.makedirs(DUMP_DIR, exist_ok=True)
    path = os.path.join(DUMP_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path

def normalize_user_for_compare(raw: str) -> str:
    if not raw: return ""
    return BXX_RE.sub("", raw).strip().lower()

def is_cpu(raw: str) -> bool:
    return normalize_user_for_compare(raw) == "cpu"

def parse_date(s: str):
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    return None

def fetch_page(username: str, page: int):
    params = {"username": username, "platform": PLATFORM, "page": page}
    last = None
    for _ in range(RETRIES):
        try:
            r = requests.get(API, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return (r.json() or {}).get("game_history") or []
        except Exception as e:
            last = e
            time.sleep(0.4)
    print(f"[WARN] {username} p{page} sin datos ({last})")
    return []

def dedup_by_id(gs):
    seen = set(); out = []
    for g in gs:
        gid = str(g.get("id") or "")
        if gid and gid in seen:
            continue
        if gid:
            seen.add(gid)
        out.append(g)
    return out

def norm_team(s: str) -> str:
    return (s or "").strip().lower()

# ==== Core: conteo W/L y puntos por equipo ====
def compute_team_record_for_user(username_exact: str, team_name: str):
    # 1) Descargar principal + alias; dedup global por id
    pages_raw = []
    usernames_to_fetch = [username_exact] + FETCH_ALIASES.get(username_exact, [])
    for uname in usernames_to_fetch:
        for p in PAGES:
            page_items = fetch_page(uname, p)
            pages_raw += page_items
            if PRINT_CAPTURE_LIST:
                for g in page_items:
                    print(f"    [cap] {uname} p{p} id={g.get('id')}  {g.get('away_full_name','')} @ {g.get('home_full_name','')}  {g.get('display_date','')}")
    pages_dedup = dedup_by_id(pages_raw)

    # 2) Filtro: modo + fecha + equipo + (ambos miembros o CPU + miembro)
    considered = []
    for g in pages_dedup:
        if (g.get("game_mode") or "").strip().upper() != MODE_FILTER:
            continue
        d = parse_date(g.get("display_date",""))
        if not d or d < SINCE:
            continue

        home = (g.get("home_full_name") or "").strip()
        away = (g.get("away_full_name") or "").strip()
        if norm_team(team_name) not in (norm_team(home), norm_team(away)):
            continue

        home_name_raw = g.get("home_name","")
        away_name_raw = g.get("away_name","")
        h_norm = normalize_user_for_compare(home_name_raw)
        a_norm = normalize_user_for_compare(away_name_raw)
        h_mem = h_norm in LEAGUE_USERS_NORM
        a_mem = a_norm in LEAGUE_USERS_NORM
        if not ( (h_mem and a_mem) or (is_cpu(home_name_raw) and a_mem) or (is_cpu(away_name_raw) and h_mem) ):
            continue

        considered.append(g)

    # === Capturas / dumps por usuario principal ===
    if PRINT_CAPTURE_SUMMARY:
        print(f"    [capturas] {team_name} ({username_exact}): raw={len(pages_raw)}  dedup={len(pages_dedup)}  considerados={len(considered)}")
    if DUMP_ENABLED:
        base = _safe_name(username_exact)
        _dump_json(f"{base}_raw.json", pages_raw)
        _dump_json(f"{base}_dedup.json", pages_dedup)
        _dump_json(f"{base}_considered.json", considered)

    # 3) Contar W/L
    wins = losses = 0
    detail_lines = []
    for g in considered:
        home = (g.get("home_full_name") or "").strip()
        away = (g.get("away_full_name") or "").strip()
        hr = (g.get("home_display_result") or "").strip().upper()
        ar = (g.get("away_display_result") or "").strip().upper()
        dt = g.get("display_date","")
        if hr == "W":
            win, lose = home, away
        elif ar == "W":
            win, lose = away, home
        else:
            continue

        if norm_team(win) == norm_team(team_name):
            wins += 1
        elif norm_team(lose) == norm_team(team_name):
            losses += 1

        if PRINT_DETAILS:
            detail_lines.append(f"{dt}  {away} @ {home} -> ganó {win}")

    # 4) Ajuste algebraico del equipo (W/L)
    adj_w, adj_l = TEAM_RECORD_ADJUSTMENTS.get(team_name, (0, 0))
    wins_adj, losses_adj = wins + adj_w, losses + adj_l

    # 5) Puntos y métricas de tabla  (CAMBIA aquí si quieres 2/1 en lugar de 3/2)
    scheduled = 13
    played = max(wins_adj + losses_adj, 0)
    remaining = max(scheduled - played, 0)

    # PUNTAJE: 3*W + 2*L  (para 2*W + 1*L cambia esta línea)
    points_base = 3 * wins_adj + 2 * losses_adj

    # 6) Ajuste manual de PUNTOS
    pts_extra, pts_reason = TEAM_POINT_ADJUSTMENTS.get(team_name, (0, ""))
    points_final = points_base + pts_extra

    return {
        "user": username_exact,
        "team": team_name,
        "scheduled": scheduled,
        "played": played,
        "wins": wins_adj,
        "losses": losses_adj,
        "remaining": remaining,
        "points": points_final,
        "points_base": points_base,
        "points_extra": pts_extra,
        "points_reason": pts_reason,
        "detail": detail_lines,
    }

# ==============================
# Compatibilidad: filas completas
# ==============================
def compute_rows():
    rows = []
    take = len(LEAGUE_ORDER) if STOP_AFTER_N is None else min(STOP_AFTER_N, len(LEAGUE_ORDER))
    for user_exact, team_name in LEAGUE_ORDER[:take]:
        rows.append(compute_team_record_for_user(user_exact, team_name))
    rows.sort(key=lambda r: (-r.get("points", 0), -r.get("wins", 0), r.get("losses", 0)))
    _dump_json("standings.json", rows)
    return rows

# -------------------------------
# Ventana del “día” en Chile
# -------------------------------
def _get_day_window_chile(now=None):
    tz = ZoneInfo("America/Santiago")
    now = (now or datetime.now(tz)).astimezone(tz)

    if DAY_WINDOW_MODE == "calendar":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end

    if DAY_WINDOW_MODE == "sports":
        ref = now.replace(minute=0, second=0, microsecond=0)
        if now.hour < 6:
            start = (ref - timedelta(days=1)).replace(hour=6)
            end = ref.replace(hour=6)
        else:
            start = ref.replace(hour=6)
            end = (ref + timedelta(days=1)).replace(hour=6)
        return start, end

    raise ValueError(f"DAY_WINDOW_MODE inválido: {DAY_WINDOW_MODE}")

# -------------------------------
# Juegos jugados HOY (Chile)
# -------------------------------
def games_played_today_scl():
    """
    Lista juegos del “día” (Chile) en formato:
      'Yankees 1 - Brewers 2  - 30-08-2025 - 3:28 pm (hora Chile)'

    Dedup:
      - por id
      - por (home, away, hr, ar, pitcher_info)
    """
    tz_scl = ZoneInfo("America/Santiago")
    tz_utc = ZoneInfo("UTC")
    start, end = _get_day_window_chile()

    # Traer páginas de TODOS (principales + alias)
    usernames_pool = {u for (u, _t) in LEAGUE_ORDER}
    for base, alts in FETCH_ALIASES.items():
        usernames_pool.add(base)
        usernames_pool.update(alts)

    all_pages = []
    for username_exact in usernames_pool:
        for p in PAGES:
            all_pages += fetch_page(username_exact, p)

    # Deduplicadores
    seen_ids = set()
    seen_keys = set()  # (home, away, hr, ar, pitcher_info)
    items = []

    for g in dedup_by_id(all_pages):
        if (g.get("game_mode") or "").strip().upper() != MODE_FILTER:
            continue

        d = parse_date(g.get("display_date", ""))
        if not d:
            continue

        # Asumir UTC si es naive, luego convertir a SCL
        if d.tzinfo is None:
            d = d.replace(tzinfo=tz_utc)
        d_local = d.astimezone(tz_scl)

        # Ventana del día
        if not (start <= d_local < end):
            continue

        # Ambos jugadores deben pertenecer a la liga
        home_name_raw = (g.get("home_name") or "")
        away_name_raw = (g.get("away_name") or "")
        h_norm = normalize_user_for_compare(home_name_raw)
        a_norm = normalize_user_for_compare(away_name_raw)
        if not (h_norm in LEAGUE_USERS_NORM and a_norm in LEAGUE_USERS_NORM):
            continue

        # Dedup por id
        gid = str(g.get("id") or "")
        if gid and gid in seen_ids:
            continue

        home = (g.get("home_full_name") or "").strip()
        away = (g.get("away_full_name") or "").strip()
        hr = str(g.get("home_runs") or "0")
        ar = str(g.get("away_runs") or "0")
        pitcher_info = (g.get("display_pitcher_info") or "").strip()

        # Clave canónica robusta
        canon_key = (home, away, hr, ar, pitcher_info)
        if canon_key in seen_keys:
            continue

        # Marcar vistos
        if gid:
            seen_ids.add(gid)
        seen_keys.add(canon_key)

        # Formato de salida
        try:
            fecha_hora = d_local.strftime("%d-%m-%Y - %-I:%M %p").lower()
        except Exception:
            fecha_hora = d_local.strftime("%d-%m-%Y - %#I:%M %p").lower()

        items.append((d_local, f"{home} {hr} - {away} {ar}  - {fecha_hora} (hora Chile)"))

    items.sort(key=lambda x: x[0])
    out = [s for _, s in items]
    _dump_json("games_today.json", {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "items": out})
    return out

# ====== Alias simples (opcional) ======
def get_standings():
    return compute_rows()

def games_today():
    return games_played_today_scl()

# ====== Para correr este archivo solo (opcional) ======
if __name__ == "__main__":
    print("Calculando standings y juegos de hoy...")
    print(len(compute_rows()), "filas en standings")
    print(len(games_played_today_scl()), "juegos hoy")
