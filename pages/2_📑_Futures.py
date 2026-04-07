"""
Page 3 — Contrats Futures MASI 20 & Historique
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scraper import scrape_futures_data, load_history, get_market_status, get_daily_futures_table

st.set_page_config(page_title="Futures MASI 20 — MAT Platform", page_icon="📑", layout="wide")

# ─── CSS (inchangé) ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');
   
    .stApp { background: linear-gradient(180deg, #060A13 0%, #0A0E17 50%, #0D1220 100%); }
    .main .block-container { padding-top: 1.5rem; max-width: 1200px; }
   
    .page-header {
        font-family: 'Space Mono', monospace !important;
        font-size: 2rem !important;
        background: linear-gradient(135deg, #D4A843, #F0D78C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem !important;
    }
   
    .page-sub {
        font-family: 'DM Sans', sans-serif;
        color: #6B7280;
        font-size: 0.9rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }
   
    .contract-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1.5rem 0; }
    .contract-card { /* ... ton CSS existant ... */ }
    /* (je garde tout ton CSS original pour ne rien casser) */
    .section-title {
        font-family: 'Space Mono', monospace !important;
        color: #D4A843 !important;
        font-size: 1rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase;
        margin: 2rem 0 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ───
st.markdown('<h1 class="page-header">📑 Contrats Futures</h1>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Future MASI 20 · 4 Échéances · Historique</div>', unsafe_allow_html=True)

# ─── Load Data ───
futures = scrape_futures_data()
history = load_history()
market = get_market_status()

# === NOUVEAU : Tableau Journalier ===
df_journalier, total_mad, total_contrats = get_daily_futures_table()

# Status indicator
status_color = "#10B981" if market["status"] == "OUVERTE" else "#EF4444"
st.markdown(f"""
<div style="text-align:right; margin-bottom:1rem;">
    <span style="font-family:'Space Mono',monospace; font-size:0.78rem; color:{status_color};
        background:rgba({','.join(['16,185,129' if market['status']=='OUVERTE' else '239,68,68'])},0.1);
        padding:4px 12px; border-radius:20px; border:1px solid {status_color}40;">
        ● Séance {market['status']}
    </span>
</div>
""", unsafe_allow_html=True)

# ─── Contract Overview Cards (inchangé) ───
# ... (tout ton code des 4 cartes reste exactement le même)

contract_keys = list(futures.keys())
labels = ["Juin 2026", "Septembre 2026", "Décembre 2026", "Mars 2027"]
colors = ["#10B981", "#3B82F6", "#F59E0B", "#EF4444"]
cols = st.columns(4)
for i, (key, col) in enumerate(zip(contract_keys, cols)):
    c = futures[key]
    var = c.get("variation", 0)
    var_class = "up" if var >= 0 else "down"
    var_sign = "▲ +" if var >= 0 else "▼ "
   
    with col:
        st.markdown(f"""
        <div class="contract-card">
            <div class="contract-label">{labels[i]}</div>
            <div class="contract-price">{c['cours']:,.2f}</div>
            <div class="contract-change {var_class}">{var_sign}{abs(var):.2f}%</div>
            <div class="contract-echeance">Échéance: {c.get('echeance', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)

# ─── NOUVEAU TABLEAU JOURNALIER ───
st.markdown('<h3 class="section-title">📊 Tableau Journalier des Futures</h3>', unsafe_allow_html=True)

st.markdown(f"""
<div style="background: linear-gradient(145deg, rgba(17,24,39,0.9), rgba(17,24,39,0.6)); 
            border: 1px solid rgba(212,168,67,0.2); border-radius: 16px; padding: 1.2rem; margin-bottom: 1.5rem;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="font-family:'Space Mono'; color:#D4A843; font-size:1.1rem;">Total échangé aujourd’hui</span><br>
            <span style="font-size:2rem; font-weight:700; color:#E5E7EB;">{total_mad:,.0f} MAD</span>
        </div>
        <div style="text-align:right;">
            <span style="font-family:'Space Mono'; color:#D4A843; font-size:1.1rem;">Contrats négociés</span><br>
            <span style="font-size:2rem; font-weight:700; color:#E5E7EB;">{total_contrats}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.dataframe(
    df_journalier,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Contrat": st.column_config.TextColumn("Contrat", width=160),
        "Échéance": st.column_config.TextColumn("Échéance", width=110),
        "Cours": st.column_config.NumberColumn("Cours", format="%.2f"),
        "Variation": st.column_config.TextColumn("Variation", width=100),
        "Ouverture": st.column_config.NumberColumn("Ouverture", format="%.2f"),
        "Plus Haut": st.column_config.NumberColumn("Plus Haut", format="%.2f"),
        "Plus Bas": st.column_config.NumberColumn("Plus Bas", format="%.2f"),
        "Volume (MAD)": st.column_config.NumberColumn("Volume (MAD)", format="%,.0f"),
        "Contrats": st.column_config.NumberColumn("Contrats", format="%d"),
    }
)

# ─── Le reste de ta page (Détails du Contrat, Graphiques, Historique, etc.) reste inchangé ───
# (je ne recopie pas tout pour ne pas alourdir, mais tout ce qui suit après les cartes reste identique)

# ... [Ton code existant à partir de "# ─── Contract Selector ───" jusqu'à la fin reste exactement le même]

# Tu peux supprimer l’ancienne section "# ─── Summary table ───" à la toute fin si tu veux,
# car le nouveau tableau journalier la remplace avantageusement.
