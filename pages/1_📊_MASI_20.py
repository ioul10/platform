"""
Page 2 — MASI 20: Indice, Graphique & Top Movers
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scraper import scrape_masi_index, scrape_top_movers, generate_masi20_chart_data, get_market_status, get_now_casa

st.set_page_config(page_title="MASI 20 — MAT Platform", page_icon="📊", layout="wide")

# ─── Shared CSS ───
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
    
    .index-card {
        background: linear-gradient(145deg, rgba(17,24,39,0.8), rgba(17,24,39,0.4));
        border: 1px solid rgba(212,168,67,0.15);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
    }
    
    .index-value {
        font-family: 'Space Mono', monospace;
        font-size: 3rem;
        font-weight: 700;
        color: #E5E7EB;
    }
    
    .index-name {
        font-family: 'Space Mono', monospace;
        color: #D4A843;
        font-size: 0.9rem;
        letter-spacing: 2px;
        margin-bottom: 0.5rem;
    }
    
    .var-positive { color: #10B981; font-family: 'Space Mono', monospace; font-size: 1.2rem; }
    .var-negative { color: #EF4444; font-family: 'Space Mono', monospace; font-size: 1.2rem; }
    
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    
    .detail-label { color: #6B7280; font-family: 'DM Sans', sans-serif; font-size: 0.85rem; }
    .detail-value { color: #E5E7EB; font-family: 'Space Mono', monospace; font-size: 0.85rem; }
    
    .mover-card {
        background: rgba(17,24,39,0.6);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 10px 14px;
        margin: 4px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .mover-name {
        font-family: 'DM Sans', sans-serif;
        color: #E5E7EB;
        font-size: 0.88rem;
    }
    
    .mover-ticker {
        font-family: 'Space Mono', monospace;
        color: #6B7280;
        font-size: 0.72rem;
    }
    
    .mover-change {
        font-family: 'Space Mono', monospace;
        font-size: 0.9rem;
        font-weight: 700;
    }
    
    .section-title {
        font-family: 'Space Mono', monospace !important;
        color: #D4A843 !important;
        font-size: 1rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase;
        margin: 2rem 0 1rem !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─── Header ───
st.markdown('<h1 class="page-header">📊 MASI 20</h1>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Indice · Graphique · Top Movers</div>', unsafe_allow_html=True)

# ─── Load data ───
masi_data = scrape_masi_index()
chart_data = generate_masi20_chart_data()
movers = scrape_top_movers()
market = get_market_status()

# ─── Status + Heure GMT+1 ───
status_color = "#10B981" if market["status"] == "OUVERTE" else "#EF4444"
rgb = "16,185,129" if market["status"] == "OUVERTE" else "239,68,68"
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center;
    margin-bottom:1.2rem; flex-wrap:wrap; gap:0.5rem;">
    <span style="font-family:'DM Sans',sans-serif; font-size:0.78rem; color:#4B5563;">
        ⏱ <span id="masi-clock" style="font-family:'Space Mono',monospace; color:#9CA3AF;">--:--:--</span>
        &nbsp;GMT+1
    </span>
    <span style="font-family:'Space Mono',monospace; font-size:0.78rem; color:{status_color};
        background:rgba({rgb},0.1); padding:4px 14px; border-radius:20px;
        border:1px solid {status_color}40;">
        ● Séance {market['status']} &nbsp;·&nbsp; {market.get('message','')}
    </span>
</div>
<script>
(function(){{
    function t(){{
        var n=new Date(),u=n.getTime()+n.getTimezoneOffset()*60000,c=new Date(u+3600000);
        var el=document.getElementById('masi-clock');
        if(el) el.textContent=String(c.getHours()).padStart(2,'0')+':'+
            String(c.getMinutes()).padStart(2,'0')+':'+String(c.getSeconds()).padStart(2,'0');
    }}
    t(); setInterval(t,1000);
}})();
</script>
""", unsafe_allow_html=True)

# ─── Index Cards ───
col1, col2 = st.columns(2)

with col1:
    var_class = "var-positive" if masi_data.get("masi_var", 0) >= 0 else "var-negative"
    sign = "▲ +" if masi_data.get("masi_var", 0) >= 0 else "▼ "
    st.markdown(f"""
    <div class="index-card">
        <div class="index-name">MASI</div>
        <div class="index-value">{masi_data.get('masi', 17525.32):,.2f}</div>
        <div class="{var_class}">{sign}{masi_data.get('masi_var', -0.06):.2f}%</div>
        <div style="margin-top:1rem;">
            <div class="detail-row">
                <span class="detail-label">Ouverture</span>
                <span class="detail-value">{masi_data.get('masi_open', 17545.07):,.2f}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Plus haut</span>
                <span class="detail-value">{masi_data.get('masi_high', 17589.41):,.2f}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Plus bas</span>
                <span class="detail-value">{masi_data.get('masi_low', 17424.69):,.2f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    var20_class = "var-positive" if masi_data.get("masi20_var", 0) >= 0 else "var-negative"
    sign20 = "▲ +" if masi_data.get("masi20_var", 0) >= 0 else "▼ "
    st.markdown(f"""
    <div class="index-card">
        <div class="index-name">MASI 20</div>
        <div class="index-value">{masi_data.get('masi20', 1316.68):,.2f}</div>
        <div class="{var20_class}">{sign20}{masi_data.get('masi20_var', -0.77):.2f}%</div>
        <div style="margin-top:1rem;">
            <div class="detail-row">
                <span class="detail-label">Ouverture</span>
                <span class="detail-value">{masi_data.get('masi20_open', 1326.50):,.2f}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Plus haut</span>
                <span class="detail-value">{masi_data.get('masi20_high', 1327.80):,.2f}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Plus bas</span>
                <span class="detail-value">{masi_data.get('masi20_low', 1309.90):,.2f}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Graphique journalier (ce que tu as déjà)
chart = generate_masi20_chart_data()
# ou directement : scrape_masi20_historical(days=30)

# Graphique intraday (nouveau, accumule dans le temps)
intraday = load_masi20_history(days=1, mode="intraday")
# → {"times": ["09:35", "12:05", "15:35"], "values": [1354.39, 1358.12, 1361.45], ...}


# ─── Chart Intraday MASI 20 (Dynamique) ───
st.markdown('<h3 class="section-title">📈 Évolution intraday — MASI 20</h3>', unsafe_allow_html=True)

chart_data = generate_masi20_chart_data()

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=chart_data["times"],
    y=chart_data["values"],
    mode="lines",
    fill="tozeroy",
    fillcolor="rgba(212, 168, 67, 0.12)",
    line=dict(color="#D4A843", width=3),
    hovertemplate="<b>%{x}</b><br>MASI 20: %{y:,.2f} pts<extra></extra>",
))

# Ligne ouverture
fig.add_hline(y=chart_data["open"], line_dash="dot", line_color="rgba(107,114,128,0.5)",
              annotation_text=f"Ouverture {chart_data['open']:,.2f}", annotation_position="top right")

# Ligne valeur actuelle (seulement si marché ouvert)
if chart_data["is_market_open"]:
    fig.add_hline(y=chart_data["current"], line_dash="dash", line_color="#10B981",
                  annotation_text=f"Maintenant {chart_data['current']:,.2f}", annotation_position="bottom right")

fig.update_layout(
    height=420,
    margin=dict(l=0, r=0, t=30, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False, color="#4B5563", tickfont=dict(family="Space Mono", size=10)),
    yaxis=dict(showgrid=True, gridcolor="rgba(212,168,67,0.06)", tickformat=","),
)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
# ─── Top Movers ───
st.markdown('<h3 class="section-title">🔥 Top 5 Hausses & Baisses</h3>', unsafe_allow_html=True)

col_up, col_down = st.columns(2)

with col_up:
    st.markdown("""<div style="font-family:'Space Mono',monospace; color:#10B981; font-size:0.8rem; 
        letter-spacing:2px; margin-bottom:0.8rem;">▲ TOP HAUSSES</div>""", unsafe_allow_html=True)
    
    for g in movers["gainers"]:
        ticker = g.get("ticker", g["name"][:3].upper())
        st.markdown(f"""
        <div class="mover-card" style="border-left: 3px solid #10B981;">
            <div>
                <div class="mover-name">{g['name']}</div>
                <div class="mover-ticker">{ticker} · {g['price']:,.2f} MAD</div>
            </div>
            <div class="mover-change" style="color:#10B981;">+{g['change']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

with col_down:
    st.markdown("""<div style="font-family:'Space Mono',monospace; color:#EF4444; font-size:0.8rem; 
        letter-spacing:2px; margin-bottom:0.8rem;">▼ TOP BAISSES</div>""", unsafe_allow_html=True)
    
    for l in movers["losers"]:
        ticker = l.get("ticker", l["name"][:3].upper())
        st.markdown(f"""
        <div class="mover-card" style="border-left: 3px solid #EF4444;">
            <div>
                <div class="mover-name">{l['name']}</div>
                <div class="mover-ticker">{ticker} · {l['price']:,.2f} MAD</div>
            </div>
            <div class="mover-change" style="color:#EF4444;">{l['change']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

# ─── Composition MASI 20 ───
st.markdown('<h3 class="section-title">🏛️ Composition MASI 20</h3>', unsafe_allow_html=True)

masi20_components = [
    {"Ticker": "ATW", "Société": "Attijariwafa Bank", "Secteur": "Banques"},
    {"Ticker": "IAM", "Société": "Itissalat Al-Maghrib", "Secteur": "Télécoms"},
    {"Ticker": "BCP", "Société": "Banque Centrale Populaire", "Secteur": "Banques"},
    {"Ticker": "BOA", "Société": "Bank of Africa", "Secteur": "Banques"},
    {"Ticker": "LBV", "Société": "Label'Vie", "Secteur": "Distribution"},
    {"Ticker": "CMA", "Société": "Ciments du Maroc", "Secteur": "BTP"},
    {"Ticker": "MSA", "Société": "Marsa Maroc", "Secteur": "Transport"},
    {"Ticker": "MNG", "Société": "Managem", "Secteur": "Mines"},
    {"Ticker": "ADI", "Société": "Addoha", "Secteur": "Immobilier"},
    {"Ticker": "TQM", "Société": "TotalEnergies Marketing", "Secteur": "Énergie"},
    {"Ticker": "SID", "Société": "Sonasid", "Secteur": "Sidérurgie"},
    {"Ticker": "CDM", "Société": "Crédit du Maroc", "Secteur": "Banques"},
    {"Ticker": "CSR", "Société": "Cosumar", "Secteur": "Agro-alimentaire"},
    {"Ticker": "LHM", "Société": "LafargeHolcim Maroc", "Secteur": "BTP"},
    {"Ticker": "ADH", "Société": "Douja Prom Addoha", "Secteur": "Immobilier"},
    {"Ticker": "RDS", "Société": "Résidences Dar Saada", "Secteur": "Immobilier"},
    {"Ticker": "AKT", "Société": "Akdital", "Secteur": "Santé"},
    {"Ticker": "TGC", "Société": "TGCC", "Secteur": "BTP"},
    {"Ticker": "CFG", "Société": "CFG Bank", "Secteur": "Banques"},
    {"Ticker": "JET", "Société": "Jet Contractors", "Secteur": "BTP"},
]

df_comp = pd.DataFrame(masi20_components)
st.dataframe(
    df_comp, 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width=80),
        "Société": st.column_config.TextColumn("Société", width=250),
        "Secteur": st.column_config.TextColumn("Secteur", width=180),
    }
)
