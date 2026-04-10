"""
scraper.py — Scraper pour le Marché à Terme de la Bourse de Casablanca

Sources de données (par priorité) :
  1. lematin.ma/bourse-de-casablanca  → MASI, MASI 20, toutes les actions (HTML statique)
  2. boursenews.ma/article/marches/feuille-de-marche → Top 5 hausses/baisses
  3. tradingeconomics.com/morocco/stock-market → MASI fallback
  4. futures.casablanca-bourse.com → Contrats Futures (quand disponible)
  5. Fallback → Données réelles de la 1ère séance (6 avril 2026, source BourseNews)

Cache : 4 heures (14400 secondes) via fichier JSON local
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timedelta
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL_SECONDS = 4 * 60 * 60  # 4 heures

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CONTRACTS = {
    "FUT-MASI20-JUN26": {"label": "Juin 2026", "echeance": "2026-06-19", "code": "JUN26"},
    "FUT-MASI20-SEP26": {"label": "Septembre 2026", "echeance": "2026-09-18", "code": "SEP26"},
    "FUT-MASI20-DEC26": {"label": "Décembre 2026", "echeance": "2026-12-18", "code": "DEC26"},
    "FUT-MASI20-MAR27": {"label": "Mars 2027", "echeance": "2027-03-19", "code": "MAR27"},
}


def _get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _clean_number(text):
    """Nettoie un texte et le convertit en float. Ex: '17 438,95' -> 17438.95"""
    cleaned = text.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return None


# ===================================================================
# CACHE SYSTEM — 4h TTL
# ===================================================================

def _cache_get(key):
    """Recupere une valeur du cache si elle est fraiche (< 4h)."""
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    if not os.path.exists(cache_file):
        return None
    try:
        with open(cache_file, "r") as f:
            cached = json.load(f)
        cached_time = datetime.fromisoformat(cached["_cached_at"])
        if (datetime.now() - cached_time).total_seconds() < CACHE_TTL_SECONDS:
            print(f"[cache] HIT {key} (age: {(datetime.now() - cached_time).total_seconds()/60:.0f}min)")
            return cached["data"]
        else:
            print(f"[cache] STALE {key}")
    except (json.JSONDecodeError, IOError, KeyError, ValueError):
        pass
    return None


def _cache_set(key, data):
    """Stocke une valeur dans le cache avec timestamp."""
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    try:
        with open(cache_file, "w") as f:
            json.dump({
                "_cached_at": datetime.now().isoformat(),
                "data": data,
            }, f, indent=2, ensure_ascii=False)
        print(f"[cache] SET {key}")
    except IOError as e:
        print(f"[cache] Write error: {e}")


def clear_cache():
    """Vide le cache — utilise par le bouton 'Rafraichir'."""
    if os.path.exists(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except OSError:
                pass
    print("[cache] CLEARED")


# ===================================================================
# MASI 20 HISTORY — Snapshots persistants pour le graphique
# ===================================================================

MASI20_HISTORY_FILE = os.path.join(DATA_DIR, "masi20_history.json")


def save_masi20_snapshot(data):
    """
    Sauvegarde un snapshot MASI 20 dans l'historique persistant.
    
    Appelee automatiquement apres chaque scraping reussi.
    Evite les doublons (meme timestamp).
    """
    if not data or not data.get("masi20"):
        return

    # Charger l'historique existant
    history = []
    if os.path.exists(MASI20_HISTORY_FILE):
        try:
            with open(MASI20_HISTORY_FILE, "r") as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    # Creer le snapshot
    now = datetime.now()
    snapshot = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "value": data.get("masi20"),
        "variation": data.get("masi20_var"),
        "open": data.get("masi20_open"),
        "high": data.get("masi20_high"),
        "low": data.get("masi20_low"),
        "veille": data.get("masi20_veille"),
    }

    # Eviter les doublons : si le dernier snapshot est a moins de 30 minutes
    # et a la meme valeur, on remplace au lieu d'ajouter
    if history:
        last = history[-1]
        try:
            last_time = datetime.strptime(last["timestamp"], "%Y-%m-%d %H:%M:%S")
            if (now - last_time).total_seconds() < 1800 and last.get("value") == snapshot["value"]:
                history[-1] = snapshot
                print(f"[history] Snapshot MASI20 remplace (meme valeur, <30min)")
            else:
                history.append(snapshot)
                print(f"[history] Snapshot MASI20 ajoute ({snapshot['timestamp']})")
        except (ValueError, KeyError):
            history.append(snapshot)
    else:
        history.append(snapshot)
        print(f"[history] Premier snapshot MASI20")

    # Limite : garder max 10000 snapshots (~3 ans a 4h de cadence)
    if len(history) > 10000:
        history = history[-10000:]

    try:
        with open(MASI20_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[history] Write error: {e}")


def load_masi20_history(days=None, mode="intraday"):
    """
    Charge l'historique MASI 20 pour le graphique.

    Parameters:
        days (int): Nombre de jours a recuperer (None = tout)
        mode (str): 
          - "intraday" : tous les snapshots (pour graphique du jour en cours)
          - "daily"    : un point par jour (dernier snapshot de chaque jour)

    Returns:
        dict: {
          "times": [liste timestamps],
          "values": [liste valeurs],
          "open": ouverture de la periode,
          "high": plus haut,
          "low": plus bas,
          "close": derniere valeur,
          "is_market_open": bool,
        }
    """
    if not os.path.exists(MASI20_HISTORY_FILE):
        # Pas d'historique -> generer des donnees de demo
        return _generate_demo_chart_data()

    try:
        with open(MASI20_HISTORY_FILE, "r") as f:
            history = json.load(f)
    except (json.JSONDecodeError, IOError):
        return _generate_demo_chart_data()

    if not history:
        return _generate_demo_chart_data()

    # Filtrer par nombre de jours
    if days is not None:
        cutoff = datetime.now() - timedelta(days=days)
        history = [
            h for h in history
            if datetime.strptime(h["timestamp"], "%Y-%m-%d %H:%M:%S") >= cutoff
        ]

    if mode == "intraday":
        # Garder tous les snapshots, trier par timestamp
        history = sorted(history, key=lambda h: h["timestamp"])
        times = [h["time"] if "time" in h else h["timestamp"][-5:] for h in history]
        values = [h["value"] for h in history]
    elif mode == "daily":
        # Garder un seul point par jour (le dernier snapshot de chaque journee)
        by_date = {}
        for h in history:
            by_date[h["date"]] = h  # Last one wins
        sorted_days = sorted(by_date.keys())
        history = [by_date[d] for d in sorted_days]
        times = sorted_days
        values = [h["value"] for h in history]
    else:
        times = []
        values = []

    if not values:
        return _generate_demo_chart_data()

    return {
        "times": times,
        "values": values,
        "open": history[0].get("open") or values[0],
        "high": max(values),
        "low": min(values),
        "close": values[-1],
        "is_market_open": is_market_open(),
        "snapshots_count": len(history),
    }


def _generate_demo_chart_data():
    """
    Genere des donnees de demo quand il n'y a pas encore d'historique.
    A utiliser uniquement au premier lancement.
    """
    base = 1316.68
    times, values = [], []
    current = base
    start = datetime(2026, 4, 6, 9, 30)

    random.seed(42)
    for i in range(78):
        t = start + timedelta(minutes=i * 5)
        times.append(t.strftime("%H:%M"))
        delta = random.gauss(-0.08, 1.2)
        current = max(1295, min(1325, current + delta))
        values.append(round(current, 2))

    values[-1] = 1311.11
    return {
        "times": times,
        "values": values,
        "open": base,
        "high": max(values),
        "low": min(values),
        "close": values[-1],
        "is_market_open": is_market_open(),
        "snapshots_count": 0,
    }


# ===================================================================
# 1. MASI & MASI 20 — Source : lematin.ma (HTML statique, fiable)
# ===================================================================

def scrape_masi_index(force_refresh=False):
    """
    Scrape MASI 20 — avec cache 4h + sauvegarde automatique d'un snapshot.

    Ordre des sources :
      1. Cache (si < 4h)
      2. investing.com/indices/masi-20 (source principale, HTML statique)
      3. lematin.ma (fallback)
      4. Fallback statique
    """
    if not force_refresh:
        cached = _cache_get("masi_index")
        if cached:
            return cached

    # Source principale : investing.com
    data = _scrape_investing_masi20()
    if data and data.get("masi20"):
        print(f"[scraper] MASI20 depuis investing.com: {data['masi20']}")
        _cache_set("masi_index", data)
        save_masi20_snapshot(data)
        return data

    # Fallback : lematin.ma
    data = _scrape_lematin_indices()
    if data and data.get("masi20"):
        print(f"[scraper] MASI20 depuis lematin.ma: {data['masi20']}")
        _cache_set("masi_index", data)
        save_masi20_snapshot(data)
        return data

    print("[scraper] Fallback MASI utilise")
    return _get_masi_fallback()


def _scrape_investing_masi20():
    """
    Scrape MASI 20 depuis investing.com — source principale fiable.
    
    L'URL /indices/masi-20 contient en HTML statique :
      - Dernier cours, variation
      - Ouverture, + Haut, + Bas
      - Cloture precedente
      - Ecart 52 semaines
    """
    try:
        session = _get_session()
        url = "https://fr.investing.com/indices/masi-20"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"[scraper] investing.com status: {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text("\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        data = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        def _find_after_label(label, min_val=None, max_val=None, offset=1):
            """Trouve le premier nombre apres une ligne contenant label."""
            for i, line in enumerate(lines):
                if label.lower() in line.lower():
                    for j in range(i + offset, min(i + 6, len(lines))):
                        val = _clean_number(lines[j])
                        if val is None:
                            continue
                        if min_val is not None and val < min_val:
                            continue
                        if max_val is not None and val > max_val:
                            continue
                        return val
            return None

        # Le cours courant apparait juste apres "MAD" et une balise "Ajout au Portefeuille"
        # Pattern: cherche "1.354,39" (format avec point comme millier, virgule comme decimale)
        # On cherche un nombre dans la plage MASI20 (1000-5000) qui apparait dans les premieres lignes
        for i, line in enumerate(lines[:100]):
            val = _clean_number(line)
            if val and 1000 < val < 5000:
                data["masi20"] = val
                # La variation suit souvent sur la ligne d'apres
                for j in range(i + 1, min(i + 5, len(lines))):
                    # Format: "-3,90(-0,29%)" ou "-0,29%"
                    m = re.search(r"([-+]?\d+[.,]\d+)\s*%", lines[j])
                    if m:
                        data["masi20_var"] = _clean_number(m.group(1))
                        break
                break

        # Cloture precedente
        cloture = _find_after_label("Clôture précédente", 1000, 5000)
        if cloture:
            data["masi20_prev_close"] = cloture

        # Ouverture
        ouverture = _find_after_label("Ouverture", 1000, 5000)
        if ouverture:
            data["masi20_open"] = ouverture

        # Ecart journalier — il apparait sous forme "1.351,901.366,53" (2 nombres colles)
        # Cherche la ligne apres "Ecart journalier"
        for i, line in enumerate(lines):
            if "Ecart journalier" in line:
                for j in range(i + 1, min(i + 4, len(lines))):
                    # Extrait tous les nombres de cette ligne
                    nums = re.findall(r"\d[\d\s.,]*\d", lines[j])
                    for num_str in nums:
                        val = _clean_number(num_str)
                        if val and 1000 < val < 5000:
                            if "masi20_low" not in data:
                                data["masi20_low"] = val
                            elif "masi20_high" not in data:
                                data["masi20_high"] = val
                    if "masi20_low" in data and "masi20_high" in data:
                        break
                break

        # Si ecart inverse, corriger
        if "masi20_low" in data and "masi20_high" in data:
            if data["masi20_low"] > data["masi20_high"]:
                data["masi20_low"], data["masi20_high"] = data["masi20_high"], data["masi20_low"]

        return data if "masi20" in data else None

    except Exception as e:
        print(f"[scraper] investing.com error: {e}")
        return None


def scrape_masi20_historical(days=30, force_refresh=False):
    """
    Scrape l'historique du MASI 20 depuis investing.com.
    Retourne une liste de dicts: [{date, close, open, high, low, change_pct}, ...]
    """
    cache_key = f"masi20_history_{days}"
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    try:
        session = _get_session()
        url = "https://fr.investing.com/indices/masi-20-historical-data"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"[scraper] investing historical status: {resp.status_code}")
            return _get_masi20_history_fallback()

        soup = BeautifulSoup(resp.text, "lxml")
        
        # Le tableau historique a les colonnes : Date | Dernier | Ouv | + Haut | + Bas | Vol | Variation %
        tables = soup.find_all("table")
        history = []
        
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header
                cells = row.find_all("td")
                if len(cells) >= 6:
                    date_str = cells[0].get_text(strip=True)
                    # Verif que c'est bien une date (format DD/MM/YYYY)
                    if not re.match(r"\d{2}/\d{2}/\d{4}", date_str):
                        continue
                    
                    close = _clean_number(cells[1].get_text(strip=True))
                    open_ = _clean_number(cells[2].get_text(strip=True))
                    high = _clean_number(cells[3].get_text(strip=True))
                    low = _clean_number(cells[4].get_text(strip=True))
                    # cells[5] = Vol (souvent vide)
                    change_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""
                    change_pct = _clean_number(change_text.replace("%", "").replace("+", ""))
                    
                    if close and 100 < close < 10000:
                        # Convertir la date en format ISO
                        try:
                            day, month, year = date_str.split("/")
                            iso_date = f"{year}-{month}-{day}"
                        except ValueError:
                            iso_date = date_str
                        
                        history.append({
                            "date": iso_date,
                            "close": close,
                            "open": open_,
                            "high": high,
                            "low": low,
                            "change_pct": change_pct,
                        })
            
            if history:
                break  # On a trouve le bon tableau
        
        # Trier par date croissante (plus ancien -> plus recent)
        history.sort(key=lambda x: x["date"])
        
        # Limiter a N jours
        if days and len(history) > days:
            history = history[-days:]
        
        if history:
            print(f"[scraper] MASI20 history: {len(history)} points depuis investing.com")
            _cache_set(cache_key, history)
            return history

    except Exception as e:
        print(f"[scraper] investing historical error: {e}")

    return _get_masi20_history_fallback()


def _get_masi20_history_fallback():
    """Donnees historiques MASI 20 — fallback basé sur investing.com (mars 2026)."""
    return [
        {"date": "2026-03-03", "close": 1238.53, "open": 1309.34, "high": 1314.39, "low": 1238.53, "change_pct": -5.41},
        {"date": "2026-03-04", "close": 1255.55, "open": 1238.53, "high": 1309.05, "low": 1238.53, "change_pct": 1.37},
        {"date": "2026-03-05", "close": 1316.05, "open": 1255.55, "high": 1316.05, "low": 1255.55, "change_pct": 4.82},
        {"date": "2026-03-06", "close": 1298.99, "open": 1316.05, "high": 1344.49, "low": 1298.99, "change_pct": -1.30},
        {"date": "2026-03-09", "close": 1251.84, "open": 1298.99, "high": 1299.47, "low": 1251.84, "change_pct": -3.63},
        {"date": "2026-03-10", "close": 1284.43, "open": 1251.84, "high": 1321.13, "low": 1251.84, "change_pct": 2.60},
        {"date": "2026-03-11", "close": 1309.94, "open": 1284.43, "high": 1316.71, "low": 1284.43, "change_pct": 1.99},
        {"date": "2026-03-12", "close": 1309.89, "open": 1309.94, "high": 1321.17, "low": 1307.15, "change_pct": 0.00},
        {"date": "2026-03-13", "close": 1285.71, "open": 1309.89, "high": 1314.40, "low": 1285.71, "change_pct": -1.85},
        {"date": "2026-03-16", "close": 1294.30, "open": 1285.71, "high": 1302.96, "low": 1285.49, "change_pct": 0.67},
        {"date": "2026-03-17", "close": 1304.14, "open": 1294.30, "high": 1308.29, "low": 1294.30, "change_pct": 0.76},
        {"date": "2026-03-18", "close": 1342.19, "open": 1304.14, "high": 1342.19, "low": 1303.95, "change_pct": 2.92},
        {"date": "2026-03-19", "close": 1322.41, "open": 1342.19, "high": 1342.19, "low": 1312.27, "change_pct": -1.47},
        {"date": "2026-03-24", "close": 1322.09, "open": 1322.41, "high": 1341.05, "low": 1319.85, "change_pct": -0.02},
        {"date": "2026-03-25", "close": 1348.05, "open": 1322.09, "high": 1348.58, "low": 1321.76, "change_pct": 1.96},
        {"date": "2026-03-26", "close": 1327.91, "open": 1348.05, "high": 1348.86, "low": 1327.91, "change_pct": -1.49},
        {"date": "2026-03-27", "close": 1308.04, "open": 1327.91, "high": 1340.93, "low": 1308.04, "change_pct": -1.50},
        {"date": "2026-03-30", "close": 1317.13, "open": 1308.04, "high": 1329.81, "low": 1307.44, "change_pct": 0.69},
        {"date": "2026-03-31", "close": 1300.97, "open": 1317.13, "high": 1319.97, "low": 1299.69, "change_pct": -1.23},
        {"date": "2026-04-06", "close": 1311.11, "open": 1316.68, "high": 1320.00, "low": 1309.00, "change_pct": -0.42},
        {"date": "2026-04-07", "close": 1308.84, "open": 1311.11, "high": 1315.00, "low": 1307.00, "change_pct": -0.17},
        {"date": "2026-04-09", "close": 1354.39, "open": 1358.29, "high": 1366.53, "low": 1351.90, "change_pct": -0.29},
    ]


def _scrape_lematin_indices():
    """
    Parse les indices depuis lematin.ma.
    
    Strategie: 2 passes
      1. Page principale -> MASI flottant (bloc texte apres "INDICE MASI ® Flottant")
      2. Page dediee MASI 20 -> toutes les donnees (Veille, Ouverture, +Haut, +Bas, Var%)
    """
    data = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    session = _get_session()

    # ==== PASSE 1 : Page principale pour MASI flottant ====
    try:
        url = "https://lematin.ma/bourse-de-casablanca/API/start/"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            text = resp.text
            # Le HTML contient typiquement :
            #   INDICE MASI ® Flottant ... 18063.02 ... -0.22
            # On cherche ce pattern precis
            # On prend la valeur qui SUIT "MASI ® Flottant" ou "MASI Flottant"
            m = re.search(
                r"MASI\s*®?\s*Flottant[^<]*?([\d]{4,6}[.,]?\d*)\s*(?:pts?)?\s*([-+]?\d+[.,]?\d*)?",
                text,
                re.IGNORECASE,
            )
            if m:
                val = _clean_number(m.group(1))
                if val and val > 5000:
                    data["masi"] = val
                    if m.group(2):
                        data["masi_var"] = _clean_number(m.group(2))
    except Exception as e:
        print(f"[scraper] lematin main page error: {e}")

    # ==== PASSE 2 : Page dediee MASI 20 (plus precise) ====
    try:
        url = "https://lematin.ma/bourse-de-casablanca/indice/msi-20"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text("\n", strip=True)

            # La page contient dans l'ordre :
            #   "Valeur" puis la valeur ex "1 354,39"
            #   "Var.%" puis "-0,29 %"
            #   "Veille" puis "1 358,29"
            #   "Ouverture" puis "999,21"
            #   "+ Haut" puis "1 366,53"
            #   "+ Bas" puis "1 351,90"
            #   "Var %" puis "-0,29 %"

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            def _find_next_number(label, after_idx=0, min_val=None, max_val=None):
                """Trouve le premier nombre apres une ligne contenant label."""
                for i, line in enumerate(lines[after_idx:], start=after_idx):
                    if label.lower() in line.lower():
                        # Chercher dans les 3 lignes qui suivent
                        for j in range(i + 1, min(i + 4, len(lines))):
                            val = _clean_number(lines[j])
                            if val is not None:
                                if min_val is not None and val < min_val:
                                    continue
                                if max_val is not None and val > max_val:
                                    continue
                                return val
                return None

            # Valeur courante (entre 100 et 10000 pour MASI 20)
            masi20_val = _find_next_number("Valeur", min_val=100, max_val=10000)
            if masi20_val:
                data["masi20"] = masi20_val

            # Variation (entre -30% et +30%)
            var = _find_next_number("Var.%", min_val=-30, max_val=30)
            if var is not None:
                data["masi20_var"] = var

            # Veille
            veille = _find_next_number("Veille", min_val=100, max_val=10000)
            if veille:
                data["masi20_veille"] = veille

            # Ouverture
            ouverture = _find_next_number("Ouverture", min_val=100, max_val=10000)
            if ouverture:
                data["masi20_open"] = ouverture

            # Plus Haut
            haut = _find_next_number("+ Haut", min_val=100, max_val=10000)
            if haut is None:
                haut = _find_next_number("Haut", min_val=100, max_val=10000)
            if haut:
                data["masi20_high"] = haut

            # Plus Bas
            bas = _find_next_number("+ Bas", min_val=100, max_val=10000)
            if bas is None:
                bas = _find_next_number("Bas", min_val=100, max_val=10000)
            if bas:
                data["masi20_low"] = bas

    except Exception as e:
        print(f"[scraper] lematin msi-20 page error: {e}")

    # ==== PASSE 3 : Page dediee MASI flottant (pour completer si besoin) ====
    if "masi" not in data:
        try:
            url = "https://lematin.ma/bourse-de-casablanca/indice/masi"
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                text = soup.get_text("\n", strip=True)
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                for i, line in enumerate(lines):
                    if "Valeur" in line:
                        for j in range(i + 1, min(i + 4, len(lines))):
                            val = _clean_number(lines[j])
                            if val and val > 5000:
                                data["masi"] = val
                                break
                        break
        except Exception as e:
            print(f"[scraper] lematin masi page error: {e}")

    return data if ("masi" in data or "masi20" in data) else None


def _get_masi_fallback():
    """Donnees reelles de la seance du 9 avril 2026 (investing.com)."""
    return {
        "masi": 18063.02,
        "masi_var": -0.22,
        "masi20": 1354.39,
        "masi20_var": -0.29,
        "masi20_prev_close": 1525.69,
        "masi20_open": 1358.29,
        "masi20_high": 1366.53,
        "masi20_low": 1351.90,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ===================================================================
# 2. TOP MOVERS — Source : boursenews.ma + lematin.ma
# ===================================================================

def scrape_top_movers(force_refresh=False):
    """Scrape top 5 hausses/baisses — avec cache 4h."""
    if not force_refresh:
        cached = _cache_get("top_movers")
        if cached:
            return cached

    data = _scrape_boursenews_movers()
    if data:
        print("[scraper] Top movers depuis boursenews.ma")
        _cache_set("top_movers", data)
        return data

    data = _scrape_lematin_movers()
    if data:
        print("[scraper] Top movers depuis lematin.ma")
        _cache_set("top_movers", data)
        return data

    print("[scraper] Fallback top movers utilise")
    return _get_movers_fallback()


def _scrape_boursenews_movers():
    """Parse la feuille de marche BourseNews — tableaux HTML propres."""
    try:
        session = _get_session()
        url = "https://boursenews.ma/article/marches/feuille-de-marche"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        gainers = []
        losers = []

        tables = soup.find_all("table")
        for table in tables:
            prev = table.find_previous(["h2", "h3", "h4", "p", "strong"])
            prev_text = prev.get_text(strip=True).lower() if prev else ""

            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    name = cells[0].get_text(strip=True)
                    price = _clean_number(cells[1].get_text(strip=True))
                    change_text = cells[2].get_text(strip=True)
                    change = _clean_number(change_text.replace("%", "").replace("+", ""))

                    if change_text.strip().startswith("-") and change and change > 0:
                        change = -change

                    if name and price and change is not None:
                        entry = {"name": name, "price": price, "change": change}
                        if "hausse" in prev_text:
                            gainers.append(entry)
                        elif "baisse" in prev_text:
                            losers.append(entry)
                        elif change > 0:
                            gainers.append(entry)
                        elif change < 0:
                            losers.append(entry)

        if gainers or losers:
            gainers.sort(key=lambda x: x["change"], reverse=True)
            losers.sort(key=lambda x: x["change"])
            return {"gainers": gainers[:5], "losers": losers[:5]}

    except Exception as e:
        print(f"[scraper] boursenews movers error: {e}")
    return None


def _scrape_lematin_movers():
    """Extraire toutes les actions de lematin.ma et trier par variation."""
    try:
        session = _get_session()
        url = "https://lematin.ma/bourse-de-casablanca/API/start/"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        stock_links = soup.find_all("a", href=re.compile(r"/bourse-de-casablanca/societe-cote/"))
        stocks = []

        for link in stock_links:
            text = link.get_text(separator="|", strip=True)
            parts = [p.strip() for p in text.split("|") if p.strip()]

            if len(parts) >= 2:
                name = parts[0]
                price = None
                change = None
                for p in parts[1:]:
                    if "MAD" in p:
                        price = _clean_number(p.replace("MAD", ""))
                    elif "%" in p:
                        change = _clean_number(p.replace("%", ""))

                if name and price and change is not None and price > 0:
                    stocks.append({"name": name, "price": price, "change": change})

        if stocks:
            gainers = sorted([s for s in stocks if s["change"] > 0], key=lambda x: x["change"], reverse=True)
            losers = sorted([s for s in stocks if s["change"] < 0], key=lambda x: x["change"])
            return {"gainers": gainers[:5], "losers": losers[:5]}

    except Exception as e:
        print(f"[scraper] lematin movers error: {e}")
    return None


def _get_movers_fallback():
    """Fallback — donnees de la seance du 7 avril 2026 (lematin.ma)."""
    return {
        "gainers": [
            {"name": "Maghreb Oxygene", "ticker": "MOX", "price": 409.00, "change": 5.96},
            {"name": "Auto Hall", "ticker": "ATH", "price": 83.95, "change": 5.60},
            {"name": "Attijariwafa Bank", "ticker": "ATW", "price": 424.00, "change": 3.92},
            {"name": "Afriquia Gaz", "ticker": "GAZ", "price": 3750.00, "change": 1.35},
            {"name": "Stroc Industrie", "ticker": "STR", "price": 159.95, "change": 1.23},
        ],
        "losers": [
            {"name": "Lesieur Cristal", "ticker": "LES", "price": 391.00, "change": -5.78},
            {"name": "SMI", "ticker": "SMI", "price": 7300.00, "change": -5.19},
            {"name": "Microdata", "ticker": "MIC", "price": 750.00, "change": -5.06},
            {"name": "Alliances", "ticker": "ADI", "price": 406.10, "change": -4.45},
            {"name": "S2M", "ticker": "S2M", "price": 525.00, "change": -4.37},
        ],
    }


# ===================================================================
# 3. FUTURES — Source : futures.casablanca-bourse.com + fallback
# ===================================================================

def scrape_futures_data(force_refresh=False):
    """Scrape les donnees futures — avec cache 4h."""
    if not force_refresh:
        cached = _cache_get("futures_data")
        if cached:
            return cached

    try:
        session = _get_session()
        url = "https://futures.casablanca-bourse.com/"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            data = _parse_futures_page(soup)
            if data:
                _save_history(data)
                _cache_set("futures_data", data)
                return data
    except Exception as e:
        print(f"[scraper] Futures scrape error: {e}")

    fallback = _get_futures_fallback()
    return fallback


def _parse_futures_page(soup):
    """Parse futures data from the Bourse page."""
    contracts = {}
    try:
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                text = " ".join(c.get_text(strip=True) for c in cells)
                for key, info in CONTRACTS.items():
                    if info["code"].lower() in text.lower() or info["label"].lower() in text.lower():
                        nums = []
                        for cell in cells:
                            n = _clean_number(cell.get_text(strip=True))
                            if n is not None:
                                nums.append(n)
                        if len(nums) >= 2:
                            contracts[key] = {
                                "cours": nums[0],
                                "variation": nums[1] if len(nums) > 1 else 0,
                            }
    except Exception as e:
        print(f"[scraper] Futures parse error: {e}")
    return contracts if contracts else None


def _get_futures_fallback():
    """Donnees reelles de la 1ere seance (6 avril 2026).
    Source: BourseNews — Bilan de la premiere seance du marche a terme
    Total: 16,97 MMAD — 1 295 contrats
    """
    now = datetime.now()
    return {
        "FUT-MASI20-JUN26": {
            "label": "Juin 2026", "echeance": "2026-06-19",
            "cours": 1309.70, "variation": -0.52,
            "ouverture": 1308.70, "plus_haut": 1318.00, "plus_bas": 1305.00,
            "cloture_veille": 1316.53,
            "volume_mad": 4420000.00, "volume_titres": 337, "nb_contrats": 337,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "FUT-MASI20-SEP26": {
            "label": "Septembre 2026", "echeance": "2026-09-18",
            "cours": 1299.50, "variation": -1.30,
            "ouverture": 1302.90, "plus_haut": 1312.00, "plus_bas": 1295.00,
            "cloture_veille": 1316.63,
            "volume_mad": 4170000.00, "volume_titres": 321, "nb_contrats": 321,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "FUT-MASI20-DEC26": {
            "label": "Decembre 2026", "echeance": "2026-12-18",
            "cours": 1310.80, "variation": -0.49,
            "ouverture": 1311.30, "plus_haut": 1320.50, "plus_bas": 1305.00,
            "cloture_veille": 1317.20,
            "volume_mad": 4720000.00, "volume_titres": 360, "nb_contrats": 360,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "FUT-MASI20-MAR27": {
            "label": "Mars 2027", "echeance": "2027-03-19",
            "cours": 1322.00, "variation": 0.30,
            "ouverture": 1320.70, "plus_haut": 1325.00, "plus_bas": 1318.00,
            "cloture_veille": 1318.03,
            "volume_mad": 3660000.00, "volume_titres": 277, "nb_contrats": 277,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


# ===================================================================
# 4. HISTORIQUE & UTILITAIRES
# ===================================================================

def _save_history(futures_data):
    """Sauvegarde un snapshot journalier."""
    history_file = os.path.join(DATA_DIR, "futures_history.json")
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    today = datetime.now().strftime("%Y-%m-%d")
    if today not in [h.get("date") for h in history]:
        history.append({
            "date": today,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "contracts": futures_data,
        })
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    return history


def load_history():
    """Charge l'historique des seances futures."""
    history_file = os.path.join(DATA_DIR, "futures_history.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    history = [
        {
            "date": "2026-04-06",
            "timestamp": "2026-04-06 15:30:00",
            "contracts": {
                "FUT-MASI20-JUN26": {"cours": 1309.70, "volume_mad": 4420000, "nb_contrats": 337, "variation": -0.52, "ouverture": 1308.70, "plus_haut": 1318.00, "plus_bas": 1305.00},
                "FUT-MASI20-SEP26": {"cours": 1299.50, "volume_mad": 4170000, "nb_contrats": 321, "variation": -1.30, "ouverture": 1302.90, "plus_haut": 1312.00, "plus_bas": 1295.00},
                "FUT-MASI20-DEC26": {"cours": 1310.80, "volume_mad": 4720000, "nb_contrats": 360, "variation": -0.49, "ouverture": 1311.30, "plus_haut": 1320.50, "plus_bas": 1305.00},
                "FUT-MASI20-MAR27": {"cours": 1322.00, "volume_mad": 3660000, "nb_contrats": 277, "variation": 0.30, "ouverture": 1320.70, "plus_haut": 1325.00, "plus_bas": 1318.00},
            },
        }
    ]
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    return history


def generate_masi20_chart_data():
    """
    Genere les donnees du graphique MASI 20 a partir du vrai historique investing.com.
    Retourne 30 derniers jours de donnees journalieres (pas intraday).
    """
    history = scrape_masi20_historical(days=30)
    
    if not history:
        history = _get_masi20_history_fallback()
    
    times = [h["date"] for h in history]
    values = [h["close"] for h in history]
    
    return {
        "times": times,
        "values": values,
        "open": history[-1]["open"] if history else 1316.68,
        "high": max((h["high"] for h in history if h.get("high")), default=max(values)),
        "low": min((h["low"] for h in history if h.get("low")), default=min(values)),
        "close": values[-1] if values else 1311.11,
        "is_market_open": is_market_open(),
        "history": history,  # Dispo pour analyses supplementaires
    }


def get_now_casa():
    """Retourne l'heure actuelle a Casablanca (UTC+1, pas de DST)."""
    # Casablanca est en UTC+1 toute l'annee (pas de changement d'heure depuis 2018)
    utc_now = datetime.utcnow()
    return utc_now + timedelta(hours=1)


def is_market_open():
    now = get_now_casa()
    if now.weekday() >= 5:
        return False
    h, m = now.hour, now.minute
    return (h == 9 and m >= 30) or (10 <= h <= 14) or (h == 15 and m <= 30)


def get_market_status():
    now = get_now_casa()
    if is_market_open():
        close_time = now.replace(hour=15, minute=30, second=0)
        remaining = close_time - now
        return {
            "status": "OUVERTE",
            "message": "Seance en cours - Fermeture a 15:30",
            "remaining": str(remaining).split(".")[0],
        }
    else:
        wd = now.weekday()
        if wd >= 5:
            days = 7 - wd
        elif now.hour >= 16:
            days = 1 if wd < 4 else (7 - wd)
        else:
            days = 0
        nxt = (now + timedelta(days=days)).replace(hour=9, minute=30, second=0)
        return {
            "status": "FERMEE",
            "message": f"Prochaine seance: {nxt.strftime('%A %d %B a %H:%M')}",
            "next_open": nxt.strftime("%Y-%m-%d %H:%M"),
        }
