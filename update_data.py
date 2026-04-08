#!/usr/bin/env python3
"""
update_data.py — Script de mise à jour manuelle des données Futures MASI 20
Usage:
    python update_data.py              # Scraping normal (cache respecté)
    python update_data.py --force      # Force le scraping même si cache valide
    python update_data.py --status     # Affiche uniquement le statut du marché
    python update_data.py --history    # Affiche l'historique des séances
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from scraper import (
    scrape_futures_data, load_history, _save_history,
    get_market_status, get_now_casa, CACHE_FILE, HISTORY_FILE
)

def print_banner():
    print("=" * 60)
    print("  MAT Platform — Mise à jour des données Futures MASI 20")
    print(f"  {get_now_casa().strftime('%d/%m/%Y %H:%M:%S')} (GMT+1, Casablanca)")
    print("=" * 60)

def show_status():
    mkt = get_market_status()
    color = "\033[92m" if mkt["status"] == "OUVERTE" else "\033[91m"
    reset = "\033[0m"
    print(f"\n  Statut séance : {color}{mkt['status']}{reset}")
    print(f"  {mkt['message']}")
    print()

def show_futures(data):
    print("\n  Contrats Futures MASI 20 :")
    print("  " + "-" * 56)
    total_vol = 0
    total_ctr = 0
    for k, v in data.items():
        cours = v.get("cours", 0)
        var   = v.get("variation", 0)
        vol   = v.get("volume_mad") or 0
        nb    = v.get("nb_contrats") or 0
        src   = v.get("source", "?")
        sign  = "+" if var >= 0 else ""
        col   = "\033[92m" if var >= 0 else "\033[91m"
        reset = "\033[0m"
        total_vol += vol
        total_ctr += nb
        print(f"  {v.get('label',''):20s}  {cours:>10,.2f} pts  {col}{sign}{var:.2f}%{reset}  Vol: {vol:>12,.0f} MAD  Ctr: {nb}")
    print("  " + "-" * 56)
    print(f"  {'TOTAL':20s}  {'':>10}       {'':>8}  Vol: {total_vol:>12,.0f} MAD  Ctr: {total_ctr}")
    print()

def show_history():
    hist = load_history()
    if not hist:
        print("  Aucun historique disponible.\n")
        return
    print(f"\n  Historique : {len(hist)} séance(s)\n")
    print(f"  {'Date':12s}  {'JUN26':>10}  {'SEP26':>10}  {'DEC26':>10}  {'MAR27':>10}  {'Vol Total':>14}")
    print("  " + "-" * 75)
    for snap in hist:
        date = snap.get("date", "?")
        cs = snap.get("contracts", {})
        def cv(key):
            c = cs.get(key, {})
            return c.get("cours", 0)
        def vol(key):
            c = cs.get(key, {})
            return c.get("volume_mad") or 0
        total_v = sum(vol(k) for k in ["FUT-MASI20-JUN26","FUT-MASI20-SEP26","FUT-MASI20-DEC26","FUT-MASI20-MAR27"])
        print(f"  {date:12s}  {cv('FUT-MASI20-JUN26'):>10,.2f}  {cv('FUT-MASI20-SEP26'):>10,.2f}  {cv('FUT-MASI20-DEC26'):>10,.2f}  {cv('FUT-MASI20-MAR27'):>10,.2f}  {total_v:>14,.0f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="MAT Platform — Mise à jour des données")
    parser.add_argument("--force",   action="store_true", help="Forcer le scraping (ignore le cache)")
    parser.add_argument("--status",  action="store_true", help="Afficher uniquement le statut du marché")
    parser.add_argument("--history", action="store_true", help="Afficher l'historique des séances")
    args = parser.parse_args()

    print_banner()
    show_status()

    if args.status:
        return

    if args.history:
        show_history()
        return

    # Scraping
    force = args.force
    if force:
        print("  Mode : FORCE REFRESH (cache ignoré)\n")
    else:
        print("  Mode : normal (cache quotidien actif)\n")

    try:
        data = scrape_futures_data(force_refresh=force)
        show_futures(data)

        # Sauvegarder dans l'historique si données fraîches
        src = next(iter(data.values()), {}).get("source", "")
        if "futures.casablanca" in src:
            _save_history(data)
            print("  ✓ Historique mis à jour")
        else:
            print("  ℹ Données de référence utilisées (pas de mise à jour historique)")

        # Afficher les fichiers data
        print(f"\n  Fichiers data :")
        for f in [CACHE_FILE, HISTORY_FILE]:
            if os.path.exists(f):
                size = os.path.getsize(f)
                print(f"    {os.path.basename(f):30s}  {size:,} bytes")

        print("\n  ✓ Terminé\n")

    except Exception as e:
        print(f"\n  ✗ Erreur : {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
