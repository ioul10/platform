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
# 1. MASI & MASI 20 — Source : lematin.ma (HTML statique, fiable)
# ===================================================================

def scrape_masi_index(force_refresh=False):
    """
    Scrape MASI et MASI 20 — avec cache 4h.

    Ordre des sources :
      1. Cache (si < 4h)
      2. lematin.ma (HTML statique, fiable)
      3. tradingeconomics.com (fallback MASI seulement)
      4. Fallback statique
    """
    # 1. Cache
    if not force_refresh:
        cached = _cache_get("masi_index")
        if cached:
            return cached

    # 2. lematin.ma
    data = _scrape_lematin_indices()
    if data and data.get("masi") and data.get("masi20"):
        print(f"[scraper] MASI depuis lematin.ma: {data['masi']} / MASI20: {data['masi20']}")
        _cache_set("masi_index", data)
        return data

    # 3. tradingeconomics.com (MASI seulement)
    te_data = _scrape_tradingeconomics_masi()
    if te_data:
        # Combiner avec fallback pour MASI 20
        fallback = _get_masi_fallback()
        merged = {**fallback, **te_data}
        print(f"[scraper] MASI depuis tradingeconomics.com: {te_data.get('masi')}")
        _cache_set("masi_index", merged)
        return merged

    # 4. Fallback statique
    print("[scraper] Fallback MASI utilise")
    return _get_masi_fallback()


def _scrape_tradingeconomics_masi():
    """Scrape MASI depuis tradingeconomics.com (source de secours)."""
    try:
        session = _get_session()
        url = "https://tradingeconomics.com/morocco/stock-market"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        # TradingEconomics affiche la valeur dans un <span id="p"> ou similaire
        # Chercher le premier grand nombre > 10000 dans la page
        text = soup.get_text()
        m = re.search(r"([\d]{2},?\d{3}\.\d{2})\s*(?:points?|pts)?", text)
        if m:
            val = _clean_number(m.group(1))
            if val and 10000 < val < 30000:
                return {
                    "masi": val,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
    except Exception as e:
        print(f"[scraper] tradingeconomics error: {e}")
    return None


def _scrape_lematin_indices():
    """Parse les indices depuis lematin.ma/bourse-de-casablanca/API/start/"""
    try:
        session = _get_session()
        url = "https://lematin.ma/bourse-de-casablanca/API/start/"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"[scraper] lematin.ma status: {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        data = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        # Les indices sont dans des liens <a href="/bourse-de-casablanca/indice/...">
        index_blocks = soup.find_all("a", href=re.compile(r"/bourse-de-casablanca/indice/"))
        for block in index_blocks:
            block_text = block.get_text(separator="|", strip=True)
            parts = [p.strip() for p in block_text.split("|") if p.strip()]

            is_masi20 = any("MASI 20" in p or "MSI 20" in p for p in parts)
            is_masi_main = any(("MASI" in p and "Flottant" in p) for p in parts)

            nums = []
            for p in parts:
                # Chercher les parties qui ressemblent a des nombres
                cleaned = p.replace("pts", "").replace("%", "").strip()
                n = _clean_number(cleaned)
                if n is not None:
                    nums.append(n)

            if is_masi20 and nums:
                data["masi20"] = nums[0]
                if len(nums) >= 2:
                    data["masi20_var"] = nums[1]

            elif is_masi_main and nums:
                data["masi"] = nums[0]
                if len(nums) >= 2:
                    data["masi_var"] = nums[1]

        # Fallback regex si les liens n'ont pas marche
        if "masi" not in data:
            text = soup.get_text()
            m = re.search(r"MASI\s*[®]?\s*Flottant[^\d]*([\d]+[.\d]*)", text)
            if m:
                val = _clean_number(m.group(1))
                if val and val > 1000:
                    data["masi"] = val

        if "masi20" not in data:
            text = soup.get_text()
            m = re.search(r"MASI\s*20[^\d]*([\d]+[.\d]*)", text)
            if m:
                val = _clean_number(m.group(1))
                if val and val > 100:
                    data["masi20"] = val

        return data if ("masi" in data or "masi20" in data) else None

    except Exception as e:
        print(f"[scraper] lematin.ma error: {e}")
        return None


def _get_masi_fallback():
    """Donnees reelles de la seance du 7 avril 2026 (lematin.ma)."""
    return {
        "masi": 17438.95,
        "masi_var": -0.91,
        "masi20": 1308.84,
        "masi20_var": -0.17,
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
    """Genere les donnees intraday MASI 20 pour le graphique."""
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
    values[-2] = 1311.50
    values[-3] = 1312.00
    return {
        "times": times,
        "values": values,
        "open": base,
        "high": max(values),
        "low": min(values),
        "close": values[-1],
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
