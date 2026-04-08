"""
🏛️ MAT Platform — Marché à Terme de la Bourse de Casablanca
V1 — Plateforme de suivi des Futures MASI 20
"""

import streamlit as st
from datetime import datetime
import locale
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from scraper import get_now_casa, get_market_status, scrape_masi_index, scrape_futures_data

# ─── Page Config ───
st.set_page_config(
    page_title="MAT Platform — Marché à Terme",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono:wght@400;700&display=swap');
    
    /* Global */
    .stApp {
        background: linear-gradient(180deg, #060A13 0%, #0A0E17 50%, #0D1220 100%);
    }
    
    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }
    
    /* Header brand */
    .mat-hero {
        text-align: center;
        padding: 3rem 2rem 2rem;
        position: relative;
    }
    
    .mat-hero::before {
        content: '';
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 200px;
        height: 3px;
        background: linear-gradient(90deg, transparent, #D4A843, transparent);
    }
    
    .mat-hero h1 {
        font-family: 'Space Mono', monospace !important;
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #D4A843 0%, #F0D78C 50%, #D4A843 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin-bottom: 0.3rem !important;
    }
    
    .mat-subtitle {
        font-family: 'DM Sans', sans-serif;
        color: #6B7280;
        font-size: 1.1rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 12px 28px;
        border-radius: 50px;
        font-family: 'Space Mono', monospace;
        font-size: 0.95rem;
        font-weight: 700;
        letter-spacing: 1px;
        margin: 1rem auto;
    }
    
    .status-open {
        background: rgba(16, 185, 129, 0.12);
        border: 1.5px solid rgba(16, 185, 129, 0.3);
        color: #10B981;
    }
    
    .status-closed {
        background: rgba(239, 68, 68, 0.10);
        border: 1.5px solid rgba(239, 68, 68, 0.25);
        color: #EF4444;
    }
    
    .pulse-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        animation: pulse 2s ease-in-out infinite;
    }
    
    .pulse-green {
        background: #10B981;
        box-shadow: 0 0 8px #10B981;
    }
    
    .pulse-red {
        background: #EF4444;
        box-shadow: 0 0 8px #EF4444;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
    }
    
    /* Clock */
    .mat-clock {
        font-family: 'Space Mono', monospace;
        font-size: 3.5rem;
        font-weight: 700;
        color: #E5E7EB;
        text-align: center;
        padding: 1rem 0;
        letter-spacing: 4px;
    }
    
    .mat-date {
        font-family: 'DM Sans', sans-serif;
        color: #6B7280;
        text-align: center;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Info cards */
    .info-card {
        background: linear-gradient(145deg, rgba(17, 24, 39, 0.8), rgba(17, 24, 39, 0.4));
        border: 1px solid rgba(212, 168, 67, 0.15);
        border-radius: 16px;
        padding: 2rem;
        margin: 0.5rem 0;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .info-card:hover {
        border-color: rgba(212, 168, 67, 0.35);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(212, 168, 67, 0.08);
    }
    
    .info-card h3 {
        font-family: 'Space Mono', monospace !important;
        color: #D4A843 !important;
        font-size: 1.1rem !important;
        margin-bottom: 0.8rem !important;
        letter-spacing: 1px;
    }
    
    .info-card p {
        font-family: 'DM Sans', sans-serif;
        color: #9CA3AF;
        font-size: 0.92rem;
        line-height: 1.7;
    }
    
    .info-card a {
        color: #D4A843;
        text-decoration: none;
        border-bottom: 1px dotted rgba(212, 168, 67, 0.4);
        transition: all 0.2s ease;
    }
    
    .info-card a:hover {
        color: #F0D78C;
        border-bottom-color: #F0D78C;
    }
    
    /* Key metrics strip */
    .metric-strip {
        display: flex;
        justify-content: center;
        gap: 3rem;
        padding: 1.5rem 0;
        margin: 1.5rem 0;
        border-top: 1px solid rgba(212, 168, 67, 0.1);
        border-bottom: 1px solid rgba(212, 168, 67, 0.1);
    }
    
    .metric-item {
        text-align: center;
    }
    
    .metric-value {
        font-family: 'Space Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #E5E7EB;
    }
    
    .metric-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 4px;
    }
    
    .metric-change-up { color: #10B981; }
    .metric-change-down { color: #EF4444; }
    
    /* Footer */
    .mat-footer {
        text-align: center;
        padding: 3rem 0 1rem;
        border-top: 1px solid rgba(212, 168, 67, 0.08);
        margin-top: 3rem;
    }
    
    .mat-footer p {
        font-family: 'DM Sans', sans-serif;
        color: #4B5563;
        font-size: 0.8rem;
    }
    
    /* Ecosystem logos */
    .eco-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .eco-item {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid rgba(212, 168, 67, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .eco-item:hover {
        border-color: rgba(212, 168, 67, 0.3);
        background: rgba(17, 24, 39, 0.8);
    }
    
    .eco-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .eco-name {
        font-family: 'Space Mono', monospace;
        color: #D4A843;
        font-size: 0.85rem;
        font-weight: 700;
    }
    
    .eco-desc {
        font-family: 'DM Sans', sans-serif;
        color: #6B7280;
        font-size: 0.78rem;
        margin-top: 0.3rem;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #080C15 0%, #0A0E17 100%);
        border-right: 1px solid rgba(212, 168, 67, 0.1);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1 {
        font-family: 'Space Mono', monospace !important;
        color: #D4A843 !important;
        font-size: 1.2rem !important;
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Key features strip */
    .features-strip {
        display: flex;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
        margin: 2rem 0;
    }
    
    .feature-tag {
        font-family: 'Space Mono', monospace;
        font-size: 0.72rem;
        color: #9CA3AF;
        background: rgba(212, 168, 67, 0.06);
        border: 1px solid rgba(212, 168, 67, 0.12);
        padding: 6px 14px;
        border-radius: 20px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ───
with st.sidebar:
    st.markdown("# 🏛️ MAT Platform")
    st.markdown("---")
    st.markdown("**V1.0** — Marché à Terme")
    st.markdown("")
    st.markdown("📊 Pages:")
    st.markdown("- **Accueil** — Vue d'ensemble")
    st.markdown("- **MASI 20** — Indice & Top movers")
    st.markdown("- **Futures** — Contrats & Historique")
    st.markdown("---")

    # Heure dynamique dans la sidebar
    st.markdown("""
<div style="font-family:'Space Mono',monospace; font-size:0.75rem; color:#6B7280; text-align:center;">
    🕐 Heure de Casablanca (GMT+1)
</div>
<div id="sb-clock" style="font-family:'Space Mono',monospace; font-size:1.1rem; color:#D4A843;
    text-align:center; letter-spacing:2px; margin:0.3rem 0;">--:--:--</div>
<script>
(function(){
    function t(){
        var n=new Date(), u=n.getTime()+n.getTimezoneOffset()*60000, c=new Date(u+3600000);
        var el=document.getElementById('sb-clock');
        if(el) el.textContent=String(c.getHours()).padStart(2,'0')+':'+
            String(c.getMinutes()).padStart(2,'0')+':'+String(c.getSeconds()).padStart(2,'0');
    }
    t(); setInterval(t,1000);
})();
</script>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("⏰ **Horaires de séance**")
    st.markdown("Lun-Ven: 09:30 → 15:30")

    # Statut marché dans sidebar
    _sb_mkt = get_market_status()
    _sb_col = "#10B981" if _sb_mkt["status"] == "OUVERTE" else "#EF4444"
    st.markdown(f"""
<div style="font-family:'Space Mono',monospace; font-size:0.75rem; color:{_sb_col};
    background:rgba(0,0,0,0.3); border:1px solid {_sb_col}40; border-radius:8px;
    padding:6px 10px; text-align:center; margin-top:0.5rem;">
    ● {_sb_mkt['status']}
</div>
<div style="font-family:'DM Sans',sans-serif; font-size:0.7rem; color:#4B5563;
    text-align:center; margin-top:0.3rem;">{_sb_mkt.get('message','')}</div>
""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Source : futures.casablanca-bourse.com")
    if st.button("🔄 Rafraîchir les données"):
        st.cache_data.clear()
        st.rerun()

# ─── Hero Section ───
st.markdown("""
<div class="mat-hero">
    <h1>MAT PLATFORM</h1>
    <div class="mat-subtitle">Marché à Terme · Bourse de Casablanca</div>
</div>
""", unsafe_allow_html=True)

# ─── Clock & Status (GMT+1 Casablanca) ───
now = get_now_casa()
market = get_market_status()
# Charger futures ici pour le ticker (sera réutilisé plus bas)
futures_ticker = scrape_futures_data()

status_class = "status-open" if market["status"] == "OUVERTE" else "status-closed"
dot_class = "pulse-green" if market["status"] == "OUVERTE" else "pulse-red"

# Horloge dynamique JS (mise à jour chaque seconde, heure Casa GMT+1)
st.markdown("""
<div id="casa-clock" style="font-family:'Space Mono',monospace;font-size:3rem;font-weight:700;
     color:#E5E7EB;text-align:center;letter-spacing:4px;margin:0.5rem 0;">
     --:--:--
</div>
<div id="casa-date" style="font-family:'DM Sans',sans-serif;font-size:0.9rem;color:#6B7280;
     text-align:center;letter-spacing:2px;text-transform:uppercase;margin-bottom:0.5rem;">
</div>
<script>
(function() {
    const DAYS_FR = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"];
    const MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
                       "Juillet","Août","Septembre","Octobre","Novembre","Décembre"];
    function tick() {
        // Heure Casa = UTC+1 (Africa/Casablanca)
        const now = new Date();
        const utc = now.getTime() + now.getTimezoneOffset() * 60000;
        const casa = new Date(utc + 3600000); // GMT+1
        const h = String(casa.getHours()).padStart(2,'0');
        const m = String(casa.getMinutes()).padStart(2,'0');
        const s = String(casa.getSeconds()).padStart(2,'0');
        const el = document.getElementById('casa-clock');
        const el2 = document.getElementById('casa-date');
        if (el) el.textContent = h + ':' + m + ':' + s;
        if (el2) {
            const day = DAYS_FR[casa.getDay()];
            const date = casa.getDate();
            const month = MONTHS_FR[casa.getMonth()];
            const year = casa.getFullYear();
            el2.textContent = day + ' ' + date + ' ' + month + ' ' + year;
        }
    }
    tick();
    setInterval(tick, 1000);
})();
</script>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align:center;">
    <div class="status-badge {status_class}">
        <span class="pulse-dot {dot_class}"></span>
        SÉANCE {market["status"]}
    </div>
</div>
<p style="text-align:center; color:#6B7280; font-family:'DM Sans',sans-serif; font-size:0.85rem; margin-top:0.8rem;">
    {market["message"]} &nbsp;·&nbsp; <span style="color:#4B5563;">Heure de Casablanca (GMT+1)</span>
</p>
""", unsafe_allow_html=True)

# ─── Futures Ticker Strip ───
_ticker_items = []
for _k, _v in futures_ticker.items():
    _var = _v.get("variation", 0)
    _col = "#10B981" if _var >= 0 else "#EF4444"
    _arr = "▲" if _var >= 0 else "▼"
    _sign = "+" if _var >= 0 else ""
    _label = _v.get("label", _k)
    _cours = _v.get("cours", 0)
    _ticker_items.append(
        f'<span style="margin:0 2rem; white-space:nowrap;">'
        f'<span style="color:#D4A843; font-weight:700;">FUT MASI20 {_label}</span>'
        f' &nbsp; <span style="color:#E5E7EB;">{_cours:,.2f}</span>'
        f' &nbsp; <span style="color:{_col};">{_arr} {_sign}{_var:.2f}%</span>'
        f'</span>'
    )
_ticker_html = " &nbsp;·&nbsp; ".join(_ticker_items)
# Dupliquer pour l'animation loop
_ticker_full = _ticker_html + " &nbsp;&nbsp;&nbsp; " + _ticker_html

st.markdown(f"""
<style>
@keyframes ticker-scroll {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
}}
.futures-ticker-wrap {{
    overflow: hidden;
    background: rgba(212,168,67,0.05);
    border-top: 1px solid rgba(212,168,67,0.15);
    border-bottom: 1px solid rgba(212,168,67,0.15);
    padding: 8px 0;
    margin: 1.2rem 0;
}}
.futures-ticker-inner {{
    display: inline-flex;
    animation: ticker-scroll 22s linear infinite;
    font-family: 'Space Mono', monospace;
    font-size: 0.82rem;
    white-space: nowrap;
}}
.futures-ticker-wrap:hover .futures-ticker-inner {{
    animation-play-state: paused;
}}
</style>
<div class="futures-ticker-wrap">
    <div class="futures-ticker-inner">{_ticker_full}</div>
</div>
""", unsafe_allow_html=True)

# ─── Key Metrics ───
masi_data = scrape_masi_index()
futures_data = futures_ticker  # déjà chargé plus haut

masi_change_class = "metric-change-up" if masi_data.get("masi_var", 0) >= 0 else "metric-change-down"
masi20_change_class = "metric-change-up" if masi_data.get("masi20_var", 0) >= 0 else "metric-change-down"
masi_sign = "+" if masi_data.get("masi_var", 0) >= 0 else ""
masi20_sign = "+" if masi_data.get("masi20_var", 0) >= 0 else ""

# Calculer les totaux depuis les données futures
total_contrats = sum(v.get("nb_contrats") or 0 for v in futures_data.values())
total_volume   = sum(v.get("volume_mad") or 0 for v in futures_data.values())
total_vol_str  = f"{total_volume/1_000_000:.2f} M" if total_volume >= 1_000_000 else f"{total_volume:,.0f}"

st.markdown(f"""
<div class="metric-strip">
    <div class="metric-item">
        <div class="metric-value">{masi_data.get('masi', 17525.32):,.2f}</div>
        <div class="metric-label">MASI</div>
        <div class="{masi_change_class}" style="font-family:'Space Mono',monospace; font-size:0.85rem;">
            {masi_sign}{masi_data.get('masi_var', -0.06):.2f}%
        </div>
    </div>
    <div class="metric-item">
        <div class="metric-value">{masi_data.get('masi20', 1311.11):,.2f}</div>
        <div class="metric-label">MASI 20</div>
        <div class="{masi20_change_class}" style="font-family:'Space Mono',monospace; font-size:0.85rem;">
            {masi20_sign}{masi_data.get('masi20_var', -0.42):.2f}%
        </div>
    </div>
    <div class="metric-item">
        <div class="metric-value">4</div>
        <div class="metric-label">Contrats Futures</div>
    </div>
    <div class="metric-item">
        <div class="metric-value">{total_contrats:,}</div>
        <div class="metric-label">Contrats échangés</div>
    </div>
    <div class="metric-item">
        <div class="metric-value">{total_vol_str}</div>
        <div class="metric-label">Volume (MAD)</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── About Section ───
st.markdown("")
st.markdown("")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="info-card">
        <h3>📈 LE MARCHÉ À TERME</h3>
        <p>
            Le 6 avril 2026 marque un tournant historique pour la Bourse de Casablanca 
            avec le lancement du <strong style="color:#D4A843;">premier contrat Future sur l'indice MASI 20</strong>.
        </p>
        <p>
            Ce nouveau compartiment permet aux investisseurs de prendre position sur 
            l'évolution de l'indice via des contrats standardisés à quatre échéances 
            trimestrielles: <strong style="color:#E5E7EB;">Juin 2026, Septembre 2026, Décembre 2026 et Mars 2027</strong>.
        </p>
        <p>
            Chaque contrat représente <strong style="color:#E5E7EB;">10 MAD par point d'indice</strong>, 
            avec un pas de cotation de 0.1 point (1 MAD). Le dénouement se fait en cash.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-card">
        <h3>⚙️ SPÉCIFICATIONS DU CONTRAT</h3>
        <p>
            <strong style="color:#E5E7EB;">Sous-jacent:</strong> Indice MASI 20 (20 valeurs les plus liquides)<br>
            <strong style="color:#E5E7EB;">Taille:</strong> 10 MAD × point d'indice<br>
            <strong style="color:#E5E7EB;">Pas de cotation:</strong> 0.1 point (≈ 1 MAD)<br>
            <strong style="color:#E5E7EB;">Mode:</strong> Cotation en continu<br>
            <strong style="color:#E5E7EB;">Échéances:</strong> Trimestrielles (Mar, Jun, Sep, Dec)<br>
            <strong style="color:#E5E7EB;">Dénouement:</strong> Cash settlement<br>
            <strong style="color:#E5E7EB;">Dernier jour:</strong> 3ème vendredi du mois d'échéance<br>
            <strong style="color:#E5E7EB;">Horaire:</strong> 09:30 — 15:30
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─── Ecosystem ───
st.markdown("")
st.markdown("<h3 style='text-align:center; font-family:Space Mono,monospace; color:#D4A843; letter-spacing:2px; font-size:1rem;'>ÉCOSYSTÈME</h3>", unsafe_allow_html=True)

st.markdown("""
<div class="eco-grid">
    <div class="eco-item">
        <div class="eco-icon">🏛️</div>
        <div class="eco-name">Bourse de Casablanca</div>
        <div class="eco-desc">Société gestionnaire du marché à terme & plateforme de négociation</div>
        <a href="https://www.casablanca-bourse.com" target="_blank" style="color:#D4A843; font-size:0.75rem; font-family:'DM Sans',sans-serif;">casablanca-bourse.com →</a>
    </div>
    <div class="eco-item">
        <div class="eco-icon">⚖️</div>
        <div class="eco-name">AMMC</div>
        <div class="eco-desc">Autorité Marocaine du Marché des Capitaux — Régulateur & superviseur</div>
        <a href="https://www.ammc.ma" target="_blank" style="color:#D4A843; font-size:0.75rem; font-family:'DM Sans',sans-serif;">ammc.ma →</a>
    </div>
    <div class="eco-item">
        <div class="eco-icon">🏦</div>
        <div class="eco-name">ICMAT</div>
        <div class="eco-desc">Instance de Coordination du Marché à Terme (BAM & AMMC)</div>
        <a href="https://futures.casablanca-bourse.com" target="_blank" style="color:#D4A843; font-size:0.75rem; font-family:'DM Sans',sans-serif;">futures.casablanca-bourse.com →</a>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Key features ───
st.markdown("""
<div class="features-strip">
    <span class="feature-tag">Effet de levier</span>
    <span class="feature-tag">Couverture de risque</span>
    <span class="feature-tag">Cash settlement</span>
    <span class="feature-tag">Cotation continue</span>
    <span class="feature-tag">Marges & appels</span>
</div>
""", unsafe_allow_html=True)

# ─── Members ───
st.markdown("")
col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class="info-card">
        <h3>🔑 MEMBRES COMPENSATEURS</h3>
        <p>
            • <strong style="color:#E5E7EB;">CFG Marchés</strong><br>
            • <strong style="color:#E5E7EB;">BMCE Capital Bourse</strong><br>
            • <strong style="color:#E5E7EB;">CDG Capital Bourse</strong><br>
            • <strong style="color:#E5E7EB;">Attijariwafa Bank</strong> (négociateur-compensateur)
        </p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="info-card">
        <h3>📅 ÉCHÉANCES ACTIVES</h3>
        <p>
            🟢 <strong style="color:#E5E7EB;">Juin 2026</strong> — Échéance 19/06/2026<br>
            🟡 <strong style="color:#E5E7EB;">Septembre 2026</strong> — Échéance 18/09/2026<br>
            🟠 <strong style="color:#E5E7EB;">Décembre 2026</strong> — Échéance 18/12/2026<br>
            🔴 <strong style="color:#E5E7EB;">Mars 2027</strong> — Échéance 19/03/2027
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─── Footer ───
st.markdown("""
<div class="mat-footer">
    <p>MAT Platform V1.0 — Données issues de la Bourse de Casablanca & Investing.com</p>
    <p>⚠️ Les données peuvent être différées. Ne constitue pas un conseil en investissement.</p>
</div>
""", unsafe_allow_html=True)
