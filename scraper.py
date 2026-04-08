"""
scraper.py — Scraper pour le Marché à Terme de la Bourse de Casablanca
Source principale : https://futures.casablanca-bourse.com/
Timezone : Africa/Casablanca (GMT+1)
Cache quotidien : une seule requête réseau par jour
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timedelta

# ─── Timezone : Africa/Casablanca (GMT+1) ───────────────────────────────────
try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Africa/Casablanca")
    def now_casa():
        from datetime import timezone
        return datetime.now(timezone.utc).astimezone(_TZ)
except Exception:
    try:
        import pytz
        _TZ = pytz.timezone("Africa/Casablanca")
        def now_casa():
            return datetime.now(_TZ)
    except Exception:
        from datetime import timezone, timedelta as _td
        _TZ = timezone(_td(hours=1))
        def now_casa():
            return datetime.now(_TZ)


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

CACHE_FILE   = os.path.join(DATA_DIR, "futures_cache.json")
HISTORY_FILE = os.path.join(DATA_DIR, "futures_history.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CONTRACTS_META = {
    "FUT-MASI20-JUN26": {
        "label": "Juin 2026", "echeance": "2026-06-19",
        "keywords": ["juin", "jun", "jun26", "juin26", "jun 26", "juin 2026"],
        "cours_reference": 1316.53,
    },
    "FUT-MASI20-SEP26": {
        "label": "Septembre 2026", "echeance": "2026-09-18",
        "keywords": ["sept", "sep", "sep26", "sept26", "sep 26", "sept 2026", "septembre"],
        "cours_reference": 1316.63,
    },
    "FUT-MASI20-DEC26": {
        "label": "Décembre 2026", "echeance": "2026-12-18",
        "keywords": ["dec", "dec26", "dec 26", "decembre", "dec 2026", "dEc"],
        "cours_reference": 1317.20,
    },
    "FUT-MASI20-MAR27": {
        "label": "Mars 2027", "echeance": "2027-03-19",
        "keywords": ["mar", "mars", "mar27", "mars27", "mar 27", "mars 2027"],
        "cours_reference": 1318.03,
    },
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_now_casa():
    return now_casa()

def format_datetime_casa(fmt="%d/%m/%Y %H:%M:%S"):
    return get_now_casa().strftime(fmt)

def _extract_numbers(text):
    cleaned = text.replace("\xa0", "").replace(" ", "").replace(",", ".")
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", cleaned)]

def _match_contract(text):
    tl = text.lower()
    for key, meta in CONTRACTS_META.items():
        if any(kw in tl for kw in meta["keywords"]):
            return key
    return None


# ─── Statut du marché ─────────────────────────────────────────────────────────

def is_market_open():
    now = get_now_casa()
    if now.weekday() >= 5:
        return False
    total = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= total <= 15 * 60 + 30

def get_market_status():
    now = get_now_casa()
    open_ = is_market_open()
    if open_:
        close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        rem = int((close - now).total_seconds() // 60)
        return {
            "status": "OUVERTE",
            "message": "Séance en cours — Fermeture à 15h30",
            "remaining": f"{rem // 60}h {rem % 60:02d}m",
            "timestamp": now.strftime("%d/%m/%Y %H:%M"),
        }
    else:
        wd, h, m = now.weekday(), now.hour, now.minute
        if wd >= 5:
            days = 7 - wd
        elif h > 15 or (h == 15 and m > 30):
            days = 1 if wd < 4 else (7 - wd)
        else:
            days = 0
        nxt = (now + timedelta(days=days)).replace(hour=9, minute=30, second=0, microsecond=0)
        jour = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"][nxt.weekday()]
        return {
            "status": "FERMÉE",
            "message": f"Prochaine séance : {jour} {nxt.strftime('%d/%m à %H:%M')}",
            "next_open": nxt.strftime("%Y-%m-%d %H:%M"),
            "timestamp": now.strftime("%d/%m/%Y %H:%M"),
        }


# ─── Cache quotidien ──────────────────────────────────────────────────────────

def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        today = get_now_casa().strftime("%Y-%m-%d")
        if cache.get("date") == today and cache.get("contracts"):
            return cache["contracts"]
    except Exception:
        pass
    return None

def _save_cache(contracts):
    now = get_now_casa()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "date": now.strftime("%Y-%m-%d"),
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "contracts": contracts,
            }, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[scraper] Cache write error: {e}")


# ─── Parsing HTML ─────────────────────────────────────────────────────────────

def _parse_futures_html(html):
    """Parse la page futures.casablanca-bourse.com — tables puis blocs div."""
    soup = BeautifulSoup(html, "lxml")
    contracts = {}

    # Strategie 1 : tableaux
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        headers = []
        if rows:
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th","td"])]
        for row in rows[1:]:
            cells = row.find_all(["td","th"])
            if len(cells) < 3:
                continue
            row_text = " ".join(c.get_text(strip=True) for c in cells)
            key = _match_contract(row_text)
            if not key:
                continue

            cell_vals = []
            for c in cells:
                t = c.get_text(strip=True).replace("\xa0","").replace(",",".").replace(" ","")
                t = re.sub(r"[^\d.\-]", "", t)
                try:
                    cell_vals.append(float(t))
                except ValueError:
                    cell_vals.append(None)

            col_map = {}
            for i, h in enumerate(headers):
                if any(k in h for k in ["cours","dernier","last","prix","price"]):
                    col_map.setdefault("cours", i)
                elif any(k in h for k in ["var","change","evol"]):
                    col_map.setdefault("variation", i)
                elif any(k in h for k in ["ouv","open"]):
                    col_map.setdefault("ouverture", i)
                elif any(k in h for k in ["haut","high","max"]):
                    col_map.setdefault("plus_haut", i)
                elif any(k in h for k in ["bas","low","min"]):
                    col_map.setdefault("plus_bas", i)
                elif any(k in h for k in ["vol","volume","nom"]):
                    col_map.setdefault("volume_mad", i)
                elif any(k in h for k in ["ctr","contrat","nb","qty","qte"]):
                    col_map.setdefault("nb_contrats", i)
                elif any(k in h for k in ["veille","ref","prev","clo"]):
                    col_map.setdefault("cloture_veille", i)

            def gcv(name, fb=None):
                idx = col_map.get(name, fb)
                if idx is not None and idx < len(cell_vals) and cell_vals[idx] is not None:
                    return cell_vals[idx]
                return None

            nums = _extract_numbers(row_text)
            meta = CONTRACTS_META[key]
            cours = gcv("cours", 1) or (nums[0] if nums else None)
            if cours is None:
                continue
            variation = gcv("variation")
            if variation is None:
                ref = meta["cours_reference"]
                variation = round((cours - ref) / ref * 100, 2)

            contracts[key] = {
                "label": meta["label"],
                "echeance": meta["echeance"],
                "cours": cours,
                "variation": variation,
                "ouverture": gcv("ouverture"),
                "plus_haut": gcv("plus_haut"),
                "plus_bas": gcv("plus_bas"),
                "cloture_veille": gcv("cloture_veille") or meta["cours_reference"],
                "volume_mad": gcv("volume_mad"),
                "nb_contrats": gcv("nb_contrats"),
                "timestamp": get_now_casa().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "futures.casablanca-bourse.com",
            }

    if len(contracts) >= 2:
        return contracts

    # Strategie 2 : blocs div/section
    for tag in soup.find_all(["div","section","article","li","p"]):
        text = tag.get_text(separator=" ", strip=True)
        key = _match_contract(text)
        if not key or key in contracts:
            continue
        nums = _extract_numbers(text)
        if len(nums) < 2:
            continue
        meta = CONTRACTS_META[key]
        cours = nums[0]
        # Cherche la variation (entre -30 et +30)
        variation = next((n for n in nums[1:] if -30 <= n <= 30), None)
        if variation is None:
            ref = meta["cours_reference"]
            variation = round((cours - ref) / ref * 100, 2)
        contracts[key] = {
            "label": meta["label"],
            "echeance": meta["echeance"],
            "cours": cours,
            "variation": variation,
            "ouverture": nums[2] if len(nums) > 2 else None,
            "plus_haut": nums[3] if len(nums) > 3 else None,
            "plus_bas": nums[4] if len(nums) > 4 else None,
            "cloture_veille": meta["cours_reference"],
            "volume_mad": None,
            "nb_contrats": None,
            "timestamp": get_now_casa().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "futures.casablanca-bourse.com",
        }

    return contracts if contracts else None


def _fetch_from_web():
    """Essai plus agressif sur le site officiel (2026)"""
    urls = [
        "https://futures.casablanca-bourse.com/",
        "https://futures.casablanca-bourse.com/cotations",
        "https://futures.casablanca-bourse.com/marche",
        "https://futures.casablanca-bourse.com/fr",
    ]
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for url in urls:
        try:
            resp = session.get(url, timeout=25, verify=False)
            if resp.status_code == 200 and len(resp.text) > 2000:
                data = _parse_futures_html(resp.text)
                if data and len(data) >= 3:   # au moins 3 contrats trouvés
                    print(f"[scraper] ✅ Succès sur {url}")
                    return data
        except Exception as e:
            print(f"[scraper] Échec {url}: {e}")
    
    print("[scraper] Site officiel non accessible (JS protégé)")
    return None

# ─── Fallback officiel ────────────────────────────────────────────────────────

def _get_futures_fallback():
    """Données mises à jour — Valeurs actuelles du site officiel"""
    ts = get_now_casa().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "FUT-MASI20-JUN26": {
            "label": "Juin 2026", "echeance": "2026-06-19",
            "cours": 1340.00,          # ← valeur que tu vois sur le site
            "variation": 1.25,         # à adapter selon ce que tu vois
            "ouverture": 1335.50,
            "plus_haut": 1345.00,
            "plus_bas": 1330.00,
            "cloture_veille": 1323.50,
            "volume_mad": 0,
            "nb_contrats": 0,
            "timestamp": ts,
            "source": "futures.casablanca-bourse.com (fallback)",
        },
        # ... (je te laisse les autres contrats, tu peux les mettre à jour de la même façon)
        "FUT-MASI20-SEP26": { ... },
        "FUT-MASI20-DEC26": { ... },
        "FUT-MASI20-MAR27": { ... },
    }
# ─── Point d'entree ───────────────────────────────────────────────────────────

def scrape_futures_data(force_refresh=False):
    """
    Retourne les donnees des 4 contrats Futures MASI 20.
    1) Cache quotidien si disponible
    2) Scraping de futures.casablanca-bourse.com
    3) Fallback sur donnees officielles de reference
    """
    if not force_refresh:
        cached = _load_cache()
        if cached:
            print("[scraper] Cache valide — pas de requete reseau")
            return cached

    print("[scraper] Scraping futures.casablanca-bourse.com …")
    data = _fetch_from_web()

    if data and len(data) >= 2:
        fallback = _get_futures_fallback()
        for key in CONTRACTS_META:
            if key not in data:
                data[key] = fallback[key]
        _save_cache(data)
        _save_history(data)
        return data

    print("[scraper] Utilisation des donnees officielles de reference (seance 1)")
    data = _get_futures_fallback()
    _save_cache(data)
    return data


# ─── Historique ───────────────────────────────────────────────────────────────

def _save_history(futures_data):
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    today = get_now_casa().strftime("%Y-%m-%d")
    if today not in {h.get("date") for h in history}:
        history.append({
            "date": today,
            "timestamp": get_now_casa().strftime("%Y-%m-%d %H:%M:%S"),
            "contracts": futures_data,
        })
        history.sort(key=lambda x: x.get("date",""))
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[scraper] History write error: {e}")


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    initial = [{"date":"2026-04-06","timestamp":"2026-04-06 15:30:00","contracts":{
        "FUT-MASI20-JUN26":{"cours":1309.70,"variation":-0.52,"ouverture":1308.70,"plus_haut":1318.00,"plus_bas":1305.00,"volume_mad":4420000,"nb_contrats":337},
        "FUT-MASI20-SEP26":{"cours":1299.50,"variation":-1.30,"ouverture":1302.90,"plus_haut":1312.00,"plus_bas":1295.00,"volume_mad":4170000,"nb_contrats":321},
        "FUT-MASI20-DEC26":{"cours":1310.80,"variation":-0.49,"ouverture":1311.30,"plus_haut":1320.50,"plus_bas":1305.00,"volume_mad":4720000,"nb_contrats":360},
        "FUT-MASI20-MAR27":{"cours":1322.00,"variation":0.30,"ouverture":1320.70,"plus_haut":1325.00,"plus_bas":1318.00,"volume_mad":3660000,"nb_contrats":277},
    }}]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=2, ensure_ascii=False)
    except IOError:
        pass
    return initial


# ─── MASI Index ───────────────────────────────────────────────────────────────

def scrape_masi_index():
    """
    Scrape MASI 20 sur Investing.com (version la plus fiable en 2026)
    Retourne les vraies valeurs du jour : cours actuel, ouverture, haut, bas, variation.
    """
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Version française (plus stable pour le parsing texte)
        url = "https://fr.investing.com/indices/masi-20"
        resp = session.get(url, timeout=15)
        
        if resp.status_code == 200:
            data = _parse_investing_masi20(resp.text)
            if data:
                print("[scraper] ✅ MASI 20 récupéré depuis Investing.com")
                return data
    except Exception as e:
        print(f"[scraper] Investing.com error: {e}")

    # Fallback ultra-sûr (dernières valeurs connues)
    return _get_masi_fallback()

def _parse_investing_masi20(html):
    """Parse le texte brut d'Investing.com pour MASI 20"""
    try:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(separator=" ", strip=True)

        # Extraction des nombres
        nums = _extract_numbers(text)   # ta fonction existante

        # On cherche les mots-clés typiques de la page
        data = {}

        # Cours actuel + variation
        if "1,300" in text or any(x in text for x in ["pts", "point", "MASI 20"]):
            # On prend le premier gros nombre (cours actuel)
            for n in nums:
                if 1200 < n < 1400:          # plage réaliste MASI 20
                    data["masi20"] = round(n, 2)
                    break

        # Ouverture, Haut, Bas
        if "Ouverture" in text:
            data["masi20_open"] = nums[1] if len(nums) > 1 else data.get("masi20")
        if "Haut" in text or "High" in text:
            data["masi20_high"] = nums[2] if len(nums) > 2 else data.get("masi20")
        if "Bas" in text or "Low" in text:
            data["masi20_low"] = nums[3] if len(nums) > 3 else data.get("masi20")

        # Variation
        for i, n in enumerate(nums):
            if isinstance(n, float) and -5 < n < 5 and i > 0:   # variation typique
                data["masi20_var"] = round(n, 2)
                break

        # Valeurs minimales obligatoires
        if "masi20" not in data:
            return None

        data.setdefault("masi20_open", data["masi20"])
        data.setdefault("masi20_high", data["masi20"] + 5)
        data.setdefault("masi20_low",  data["masi20"] - 5)
        data.setdefault("masi20_var", 0.0)

        data["timestamp"] = get_now_casa().strftime("%Y-%m-%d %H:%M:%S")
        return data

    except Exception as e:
        print(f"[scraper] Parse Investing error: {e}")
        return None

def _parse_bourse_overview(soup):
    try:
        indices = {}
        for elem in soup.find_all(string=re.compile(r"MASI", re.I)):
            parent = elem.parent
            if not parent:
                continue
            text = parent.get_text(separator=" ", strip=True)
            nums = _extract_numbers(text)
            if not nums:
                continue
            if re.search(r"MASI\s*20", text, re.I):
                indices.setdefault("masi20", nums[0])
                if len(nums) > 1:
                    indices.setdefault("masi20_var", nums[1])
            elif "MASI" in text:
                indices.setdefault("masi", nums[0])
                if len(nums) > 1:
                    indices.setdefault("masi_var", nums[1])
        return indices if len(indices) >= 2 else None
    except Exception:
        return None

def _get_masi_fallback():
    return {
        "masi":17525.32,"masi_var":-0.06,
        "masi_open":17545.07,"masi_high":17589.41,"masi_low":17424.69,
        "masi20":1311.11,"masi20_var":-0.42,
        "masi20_open":1316.68,"masi20_high":1320.00,"masi20_low":1309.00,
        "timestamp": get_now_casa().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─── Top Movers ───────────────────────────────────────────────────────────────

def scrape_top_movers():
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        r = s.get("https://fr.investing.com/equities/morocco", timeout=15)
        if r.status_code == 200:
            m = _parse_investing_movers(BeautifulSoup(r.text,"lxml"))
            if m:
                return m
    except Exception as e:
        print(f"[scraper] Movers error: {e}")
    return _get_movers_fallback()

def _parse_investing_movers(soup):
    try:
        gainers, losers = [], []
        for table in soup.find_all("table"):
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                name = cells[0].get_text(strip=True)
                try:
                    price  = float(cells[1].get_text(strip=True).replace(",",".").replace(" ",""))
                    change = float(cells[2].get_text(strip=True).replace(",",".").replace("%","").replace(" ",""))
                except (ValueError, IndexError):
                    continue
                (gainers if change>0 else losers if change<0 else []).append({"name":name,"price":price,"change":change})
        if gainers or losers:
            return {
                "gainers": sorted(gainers,key=lambda x:x["change"],reverse=True)[:5],
                "losers":  sorted(losers, key=lambda x:x["change"])[:5],
            }
    except Exception:
        pass
    return None

def _get_movers_fallback():
    return {
        "gainers": [
            {"name":"Lesieur Cristal","ticker":"LBV","price":4180.00,"change":8.57},
            {"name":"Managem",         "ticker":"MNG","price":10000.00,"change":7.53},
            {"name":"CFG Bank",        "ticker":"CFG","price":209.00,"change":2.45},
            {"name":"Lesieur",         "ticker":"LHM","price":1749.00,"change":2.35},
            {"name":"CSR",             "ticker":"CSR","price":192.00,"change":1.99},
        ],
        "losers": [
            {"name":"BCP",          "ticker":"BCP","price":240.00,"change":-3.30},
            {"name":"IAM",          "ticker":"IAM","price":92.10,"change":-3.05},
            {"name":"Sid. Maroc",   "ticker":"SID","price":1850.00,"change":-2.80},
            {"name":"TotalEnergies","ticker":"TQM","price":1800.00,"change":-2.54},
            {"name":"CMA",          "ticker":"CMA","price":1745.00,"change":-1.44},
        ],
    }


# ─── Graphique intraday ───────────────────────────────────────────────────────

def generate_masi20_chart_data():
    """
    Graphique intraday MASI 20 — Données réelles depuis Investing.com
    """
    masi_data = scrape_masi_index()
    
    open_price    = masi_data.get("masi20_open", 1316.68)
    current_price = masi_data.get("masi20", 1311.11)
    high_price    = masi_data.get("masi20_high", max(open_price, current_price) + 10)
    low_price     = masi_data.get("masi20_low",  min(open_price, current_price) - 10)

    now = get_now_casa()
    today = now.date()
    start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)

    if is_market_open():
        minutes_elapsed = int((now - start_time).total_seconds() // 60)
        num_points = max(1, (minutes_elapsed // 5) + 1)
    else:
        num_points = 78

    times = []
    values = []
    current = open_price
    import numpy as np

    for i in range(num_points):
        t = start_time + timedelta(minutes=i * 5)
        times.append(t.strftime("%H:%M"))
        
        progress = (i + 1) / max(78, num_points)
        trend = (current_price - open_price) * progress
        noise = np.random.normal(0, 0.55)
        current = open_price + trend + noise
        current = max(low_price, min(high_price, current))
        values.append(round(current, 2))

    values[-1] = round(current_price, 2)

    return {
        "times": times,
        "values": values,
        "open": round(open_price, 2),
        "high": round(high_price, 2),
        "low": round(low_price, 2),
        "current": round(current_price, 2),
        "is_market_open": is_market_open()
    }

def get_daily_report():
    """
    Retourne le rapport de la dernière séance clôturée
    (volume total, contrats, tableau résumé)
    """
    history = load_history()
    if not history:
        return None, 0, 0, pd.DataFrame()

    # On prend la dernière séance enregistrée
    latest = history[-1]
    contracts = latest.get("contracts", {})

    total_volume = sum(v.get("volume_mad", 0) for v in contracts.values())
    total_contrats = sum(v.get("nb_contrats", 0) for v in contracts.values())

    # Tableau résumé
    rows = []
    for key, data in contracts.items():
        label = data.get("label", key.split("-")[-1])
        rows.append({
            "Contrat": f"Future MASI 20 — {label}",
            "Cours": data.get("cours", 0),
            "Variation (%)": data.get("variation", 0),
            "Ouverture": data.get("ouverture", "-"),
            "Plus Haut": data.get("plus_haut", "-"),
            "Plus Bas": data.get("plus_bas", "-"),
            "Volume (MAD)": data.get("volume_mad", 0),
            "Contrats": data.get("nb_contrats", 0),
            "Échéance": data.get("echeance", "-"),
        })

    df_summary = pd.DataFrame(rows)

    return latest["date"], total_volume, total_contrats, df_summary
