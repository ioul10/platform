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
from scraper import scrape_futures_data, load_history, get_market_status, get_now_casa

st.set_page_config(page_title="Futures MASI 20 — MAT Platform", page_icon="📑", layout="wide")

# ─── CSS ───
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
    
    .contract-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .contract-card {
        background: linear-gradient(145deg, rgba(17,24,39,0.9), rgba(17,24,39,0.5));
        border: 1px solid rgba(212,168,67,0.12);
        border-radius: 14px;
        padding: 1.5rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .contract-card:hover {
        border-color: rgba(212,168,67,0.4);
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(212,168,67,0.1);
    }
    
    .contract-card.active {
        border-color: #D4A843;
        box-shadow: 0 0 20px rgba(212,168,67,0.15);
    }
    
    .contract-label {
        font-family: 'Space Mono', monospace;
        color: #D4A843;
        font-size: 0.78rem;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }
    
    .contract-price {
        font-family: 'Space Mono', monospace;
        color: #E5E7EB;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    .contract-change {
        font-family: 'Space Mono', monospace;
        font-size: 0.95rem;
        font-weight: 700;
    }
    
    .up { color: #10B981; }
    .down { color: #EF4444; }
    
    .contract-echeance {
        font-family: 'DM Sans', sans-serif;
        color: #4B5563;
        font-size: 0.72rem;
        margin-top: 0.5rem;
    }
    
    /* Detail rows */
    .detail-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    
    .detail-label {
        color: #6B7280;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.88rem;
    }
    
    .detail-value {
        color: #E5E7EB;
        font-family: 'Space Mono', monospace;
        font-size: 0.88rem;
        font-weight: 500;
    }
    
    .section-title {
        font-family: 'Space Mono', monospace !important;
        color: #D4A843 !important;
        font-size: 1rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase;
        margin: 2rem 0 1rem !important;
    }
    
    /* History table */
    .history-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 1rem 0;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─── Header ───
st.markdown('<h1 class="page-header">📑 Contrats Futures</h1>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Future MASI 20 · 4 Échéances · Historique</div>', unsafe_allow_html=True)

# ─── Load Data ───
futures = scrape_futures_data()
history = load_history()
market = get_market_status()

# Déterminer la source des données
sample_source = next(iter(futures.values()), {}).get("source", "")
source_label = "futures.casablanca-bourse.com" if "futures.casablanca" in sample_source else "Données officielles — Séance inaugurale"
source_color = "#10B981" if "futures.casablanca" in sample_source else "#F59E0B"
source_icon  = "🟢" if "futures.casablanca" in sample_source else "🟡"

# Timestamp de la dernière mise à jour
last_ts = next(iter(futures.values()), {}).get("timestamp", market.get("timestamp",""))

# Status bar
status_color = "#10B981" if market["status"] == "OUVERTE" else "#EF4444"
rgb_status = "16,185,129" if market["status"] == "OUVERTE" else "239,68,68"

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:0.5rem;">
    <div style="display:flex; align-items:center; gap:0.8rem;">
        <span style="font-family:'Space Mono',monospace; font-size:0.72rem; color:{source_color};
            background:rgba(0,0,0,0.3); padding:4px 10px; border-radius:20px;
            border:1px solid {source_color}40;">
            {source_icon} Source : {source_label}
        </span>
        <span style="font-family:'DM Sans',sans-serif; font-size:0.72rem; color:#4B5563;">
            Mis à jour : {last_ts}
        </span>
    </div>
    <span style="font-family:'Space Mono',monospace; font-size:0.78rem; color:{status_color}; 
        background:rgba({rgb_status},0.1);
        padding:4px 12px; border-radius:20px; border:1px solid {status_color}40;">
        ● Séance {market['status']} &nbsp;·&nbsp; {market.get('message','')}
    </span>
</div>
<div style="margin-bottom:0.5rem;">
    <span style="font-family:'DM Sans',sans-serif; font-size:0.75rem; color:#4B5563;">
        ⏱ Heure de Casablanca (GMT+1) : 
        <span id="fut-clock" style="font-family:'Space Mono',monospace; color:#9CA3AF;">--:--:--</span>
    </span>
</div>
<script>
(function(){{
    function tick(){{
        var now = new Date();
        var utc = now.getTime() + now.getTimezoneOffset()*60000;
        var casa = new Date(utc + 3600000);
        var h = String(casa.getHours()).padStart(2,'0');
        var m = String(casa.getMinutes()).padStart(2,'0');
        var s = String(casa.getSeconds()).padStart(2,'0');
        var el = document.getElementById('fut-clock');
        if(el) el.textContent = h+':'+m+':'+s;
    }}
    tick(); setInterval(tick, 1000);
}})();
</script>
""", unsafe_allow_html=True)

# Bouton refresh
col_ref, _ = st.columns([1, 5])
with col_ref:
    if st.button("🔄 Actualiser", key="refresh_futures"):
        scrape_futures_data(force_refresh=True)
        st.rerun()

# ─── KPI Summary Strip ───
_total_vol = sum(v.get("volume_mad") or 0 for v in futures.values())
_total_ctr = sum(v.get("nb_contrats") or 0 for v in futures.values())
_avg_cours = sum(v.get("cours", 0) for v in futures.values()) / len(futures)
_variations = [v.get("variation", 0) for v in futures.values()]
_var_positives = sum(1 for v in _variations if v > 0)

st.markdown(f"""
<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:0.8rem; margin:1rem 0 1.5rem;">
    <div style="background:rgba(17,24,39,0.6); border:1px solid rgba(212,168,67,0.12);
        border-radius:12px; padding:1rem; text-align:center;">
        <div style="font-family:'Space Mono',monospace; color:#D4A843; font-size:0.7rem;
            letter-spacing:1.5px; text-transform:uppercase; margin-bottom:0.4rem;">Volume Total</div>
        <div style="font-family:'Space Mono',monospace; color:#E5E7EB; font-size:1.3rem; font-weight:700;">
            {_total_vol/1_000_000:.2f} <span style="font-size:0.75rem; color:#6B7280;">MMAD</span>
        </div>
    </div>
    <div style="background:rgba(17,24,39,0.6); border:1px solid rgba(212,168,67,0.12);
        border-radius:12px; padding:1rem; text-align:center;">
        <div style="font-family:'Space Mono',monospace; color:#D4A843; font-size:0.7rem;
            letter-spacing:1.5px; text-transform:uppercase; margin-bottom:0.4rem;">Contrats Échangés</div>
        <div style="font-family:'Space Mono',monospace; color:#E5E7EB; font-size:1.3rem; font-weight:700;">
            {_total_ctr:,}
        </div>
    </div>
    <div style="background:rgba(17,24,39,0.6); border:1px solid rgba(212,168,67,0.12);
        border-radius:12px; padding:1rem; text-align:center;">
        <div style="font-family:'Space Mono',monospace; color:#D4A843; font-size:0.7rem;
            letter-spacing:1.5px; text-transform:uppercase; margin-bottom:0.4rem;">Cours Moyen</div>
        <div style="font-family:'Space Mono',monospace; color:#E5E7EB; font-size:1.3rem; font-weight:700;">
            {_avg_cours:,.2f} <span style="font-size:0.75rem; color:#6B7280;">pts</span>
        </div>
    </div>
    <div style="background:rgba(17,24,39,0.6); border:1px solid rgba(212,168,67,0.12);
        border-radius:12px; padding:1rem; text-align:center;">
        <div style="font-family:'Space Mono',monospace; color:#D4A843; font-size:0.7rem;
            letter-spacing:1.5px; text-transform:uppercase; margin-bottom:0.4rem;">Échéances ↑</div>
        <div style="font-family:'Space Mono',monospace; font-size:1.3rem; font-weight:700;
            color:{'#10B981' if _var_positives > 0 else '#EF4444'};">
            {_var_positives} / {len(futures)}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Contract Overview Cards ───
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

# ─── Contract Selector ───
st.markdown('<h3 class="section-title">🔍 Détails du Contrat</h3>', unsafe_allow_html=True)

selected = st.selectbox(
    "Sélectionner un contrat",
    options=contract_keys,
    format_func=lambda x: f"Future MASI 20 — {futures[x].get('label', x.split('-')[-1])}",
    label_visibility="collapsed",
)

# ─── Detail Panel ───
c = futures[selected]
var = c.get("variation", 0)
var_class = "up" if var >= 0 else "down"
var_sign = "+" if var >= 0 else ""
var_color = "#10B981" if var >= 0 else "#EF4444"

# Header section
st.markdown(f"""
<div style="background:linear-gradient(145deg,rgba(17,24,39,0.8),rgba(17,24,39,0.4));border:1px solid rgba(212,168,67,0.15);border-radius:16px;padding:2rem;margin:1rem 0;text-align:center;">
<div style="font-family:'Space Mono',monospace;color:#D4A843;font-size:1.1rem;letter-spacing:2px;">FUTURE MASI 20 — {c.get('label', selected.split('-')[-1]).upper()}</div>
<div style="font-family:'Space Mono',monospace;color:#E5E7EB;font-size:2.5rem;font-weight:700;margin:0.5rem 0;">{c['cours']:,.2f} <span style="font-size:1rem;color:#6B7280;">MAD</span></div>
<div style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;color:{var_color};">{var_sign}{var:.2f}%</div>
</div>
""", unsafe_allow_html=True)

# Detail rows using st.columns
detail_left, detail_right = st.columns(2)

with detail_left:
    def _fmt(val, decimals=2):
        if val is None: return "—"
        try: return f"{float(val):,.{decimals}f}"
        except: return str(val)

    st.markdown(f"""
<div style="background:rgba(17,24,39,0.5);border-radius:12px;padding:1rem;">
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Cours (MAD)</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{_fmt(c['cours'])}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Variation</span><span style="color:{var_color};font-family:'Space Mono',monospace;font-size:0.88rem;">{var_sign}{var:.2f}%</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Ouverture</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{_fmt(c.get('ouverture'))}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Plus haut</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{_fmt(c.get('plus_haut'))}</span></div>
</div>
""", unsafe_allow_html=True)

with detail_right:
    st.markdown(f"""
<div style="background:rgba(17,24,39,0.5);border-radius:12px;padding:1rem;">
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Plus bas</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{_fmt(c.get('plus_bas'))}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Clôture veille</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{_fmt(c.get('cloture_veille'))}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Volume (MAD)</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{_fmt(c.get('volume_mad'), 0) if c.get('volume_mad') else '—'}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Nb contrats</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c.get('nb_contrats') or '—'}</span></div>
</div>
""", unsafe_allow_html=True)


# ─── Comparative Chart ───
st.markdown('<h3 class="section-title">📊 Comparaison des Contrats</h3>', unsafe_allow_html=True)

fig = go.Figure()

for i, key in enumerate(contract_keys):
    c_data = futures[key]
    label = c_data.get("label", key.split("-")[-1])
    
    # Create bar with custom color
    fig.add_trace(go.Bar(
        x=[label],
        y=[c_data["cours"]],
        name=label,
        marker=dict(
            color=colors[i],
            opacity=0.85,
            line=dict(color=colors[i], width=1.5),
        ),
        text=[f"{c_data['cours']:,.2f}"],
        textposition="outside",
        textfont=dict(family="Space Mono", size=12, color="#E5E7EB"),
        hovertemplate=f"<b>{label}</b><br>Cours: %{{y:,.2f}} pts<br>Var: {c_data.get('variation', 0):+.2f}%<extra></extra>",
    ))

fig.update_layout(
    height=350,
    showlegend=False,
    margin=dict(l=0, r=0, t=20, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(
        showgrid=False,
        color="#6B7280",
        tickfont=dict(family="Space Mono", size=11, color="#6B7280"),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="rgba(212,168,67,0.06)",
        color="#4B5563",
        tickfont=dict(family="Space Mono", size=10, color="#4B5563"),
        range=[
            min(futures[k]["cours"] for k in contract_keys) * 0.995,
            max(futures[k]["cours"] for k in contract_keys) * 1.005,
        ],
    ),
    hoverlabel=dict(
        bgcolor="#111827",
        bordercolor="#D4A843",
        font=dict(family="DM Sans", color="#E5E7EB"),
    ),
)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─── Volume Distribution ───
st.markdown('<h3 class="section-title">📦 Répartition des Volumes</h3>', unsafe_allow_html=True)

vol_data = []
for key in contract_keys:
    c_data = futures[key]
    vol_data.append({
        "Contrat": c_data.get("label", key),
        "Volume (MAD)": c_data.get("volume_mad", 0),
        "Nb Contrats": c_data.get("nb_contrats", c_data.get("volume_titres", 0)),
    })

fig_vol = go.Figure()
fig_vol.add_trace(go.Pie(
    labels=[v["Contrat"] for v in vol_data],
    values=[v["Volume (MAD)"] for v in vol_data],
    marker=dict(colors=colors),
    textfont=dict(family="Space Mono", size=12, color="#E5E7EB"),
    hole=0.55,
    hovertemplate="<b>%{label}</b><br>Volume: %{value:,.0f} MAD<br>Part: %{percent}<extra></extra>",
))

fig_vol.update_layout(
    height=320,
    margin=dict(l=0, r=0, t=10, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(
        font=dict(family="DM Sans", size=12, color="#9CA3AF"),
        bgcolor="rgba(0,0,0,0)",
    ),
    hoverlabel=dict(
        bgcolor="#111827",
        bordercolor="#D4A843",
        font=dict(family="DM Sans", color="#E5E7EB"),
    ),
    annotations=[dict(
        text="<b>Volume</b>",
        x=0.5, y=0.5,
        font=dict(family="Space Mono", size=14, color="#D4A843"),
        showarrow=False,
    )],
)

st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})


# ─── History Section ───
st.markdown('<h3 class="section-title">📜 Historique des Séances</h3>', unsafe_allow_html=True)

_nb_seances = len(history) if history else 0
_date_debut = history[0]["date"] if history else "—"
_date_fin   = history[-1]["date"] if history else "—"

st.markdown(f"""
<div style="display:flex; gap:1.5rem; margin-bottom:1rem; flex-wrap:wrap;">
    <div style="font-family:'DM Sans',sans-serif; color:#6B7280; font-size:0.82rem;">
        📅 <strong style="color:#9CA3AF;">{_nb_seances}</strong> séance(s) enregistrée(s)
        &nbsp;·&nbsp; Du <strong style="color:#9CA3AF;">{_date_debut}</strong>
        au <strong style="color:#9CA3AF;">{_date_fin}</strong>
    </div>
    <div style="font-family:'DM Sans',sans-serif; color:#4B5563; font-size:0.82rem;">
        ⏱ Mise à jour automatique à 15h35 (GMT+1) via GitHub Actions
    </div>
</div>
""", unsafe_allow_html=True)

# Build history dataframe
if history:
    hist_rows = []
    for snapshot in history:
        date = snapshot["date"]
        contracts = snapshot.get("contracts", {})
        for key, data in contracts.items():
            label = futures.get(key, {}).get("label", key.split("-")[-1])
            hist_rows.append({
                "Date": date,
                "Contrat": label if isinstance(label, str) else key,
                "Cours": data.get("cours", 0),
                "Variation (%)": data.get("variation", 0),
                "Ouverture": data.get("ouverture", "-"),
                "Plus Haut": data.get("plus_haut", "-"),
                "Plus Bas": data.get("plus_bas", "-"),
                "Volume (MAD)": data.get("volume_mad", 0),
                "Nb Contrats": data.get("nb_contrats", 0),
            })
    
    if hist_rows:
        df_hist = pd.DataFrame(hist_rows)
        
        # Filter by contract
        hist_filter = st.selectbox(
            "Filtrer par contrat",
            options=["Tous"] + [futures[k].get("label", k) for k in contract_keys],
            key="hist_filter",
        )
        
        if hist_filter != "Tous":
            df_display = df_hist[df_hist["Contrat"] == hist_filter]
        else:
            df_display = df_hist
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.TextColumn("Date", width=100),
                "Contrat": st.column_config.TextColumn("Contrat", width=130),
                "Cours": st.column_config.NumberColumn("Cours", format="%.2f"),
                "Variation (%)": st.column_config.NumberColumn("Var %", format="%.2f"),
                "Ouverture": st.column_config.NumberColumn("Ouverture", format="%.2f"),
                "Plus Haut": st.column_config.NumberColumn("+ Haut", format="%.2f"),
                "Plus Bas": st.column_config.NumberColumn("+ Bas", format="%.2f"),
                "Volume (MAD)": st.column_config.NumberColumn("Volume MAD", format="%,.0f"),
                "Nb Contrats": st.column_config.NumberColumn("Contrats", format="%d"),
            },
        )
        
        # Download history
        csv = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger l'historique (CSV)",
            data=csv,
            file_name=f"futures_history_{get_now_casa().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

        # History Chart
        st.markdown('<h3 class="section-title">📈 Évolution Historique des Cours</h3>', unsafe_allow_html=True)
        
        fig_hist = go.Figure()
        for i, key in enumerate(contract_keys):
            label = futures[key].get("label", key)
            df_contract = df_hist[df_hist["Contrat"] == label]
            if not df_contract.empty:
                fig_hist.add_trace(go.Scatter(
                    x=df_contract["Date"],
                    y=df_contract["Cours"],
                    mode="lines+markers",
                    name=label,
                    line=dict(color=colors[i], width=2),
                    marker=dict(size=8, color=colors[i]),
                    hovertemplate=f"<b>{label}</b><br>Date: %{{x}}<br>Cours: %{{y:,.2f}}<extra></extra>",
                ))
        
        fig_hist.update_layout(
            height=380,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                showgrid=False,
                color="#6B7280",
                tickfont=dict(family="Space Mono", size=10, color="#4B5563"),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(212,168,67,0.06)",
                tickfont=dict(family="Space Mono", size=10, color="#4B5563"),
            ),
            legend=dict(
                font=dict(family="DM Sans", size=11, color="#9CA3AF"),
                bgcolor="rgba(0,0,0,0)",
            ),
            hoverlabel=dict(
                bgcolor="#111827",
                bordercolor="#D4A843",
                font=dict(family="DM Sans", color="#E5E7EB"),
            ),
        )
        
        st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})

        # Graphique volume historique par séance
        if len(history) > 0:
            st.markdown('<h3 class="section-title">📦 Volume Quotidien (MMAD)</h3>', unsafe_allow_html=True)
            vol_dates = []
            vol_totals = []
            for snap in history:
                d = snap.get("date","")
                vt = sum(
                    (snap.get("contracts",{}).get(k,{}).get("volume_mad") or 0)
                    for k in contract_keys
                )
                if vt > 0:
                    vol_dates.append(d)
                    vol_totals.append(round(vt / 1_000_000, 3))

            if vol_dates:
                fig_vol_hist = go.Figure()
                fig_vol_hist.add_trace(go.Bar(
                    x=vol_dates,
                    y=vol_totals,
                    marker=dict(color="#D4A843", opacity=0.8),
                    text=[f"{v:.2f} M" for v in vol_totals],
                    textposition="outside",
                    textfont=dict(family="Space Mono", size=11, color="#E5E7EB"),
                    hovertemplate="<b>%{x}</b><br>Volume: %{y:.3f} MMAD<extra></extra>",
                ))
                fig_vol_hist.update_layout(
                    height=280,
                    margin=dict(l=0, r=0, t=20, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False, tickfont=dict(family="Space Mono", size=10, color="#4B5563")),
                    yaxis=dict(
                        showgrid=True, gridcolor="rgba(212,168,67,0.06)",
                        tickfont=dict(family="Space Mono", size=10, color="#4B5563"),
                        title=dict(text="MMAD", font=dict(color="#6B7280", size=10)),
                    ),
                    hoverlabel=dict(bgcolor="#111827", bordercolor="#D4A843", font=dict(family="DM Sans", color="#E5E7EB")),
                )
                st.plotly_chart(fig_vol_hist, use_container_width=True, config={"displayModeBar": False})

else:
    st.info("Aucun historique disponible. Les données seront enregistrées à la clôture de chaque séance.")

# ─── Summary table ───
st.markdown('<h3 class="section-title">📋 Résumé de la Séance</h3>', unsafe_allow_html=True)

summary_data = []
for key in contract_keys:
    c_data = futures[key]
    summary_data.append({
        "Contrat": f"Future MASI 20 — {c_data.get('label', key)}",
        "Cours": c_data["cours"],
        "Var (%)": c_data.get("variation", 0),
        "Ouverture": c_data.get("ouverture", "-"),
        "Haut": c_data.get("plus_haut", "-"),
        "Bas": c_data.get("plus_bas", "-"),
        "Vol. (MAD)": c_data.get("volume_mad", 0),
        "Contrats": c_data.get("nb_contrats", c_data.get("volume_titres", 0)),
        "Échéance": c_data.get("echeance", "-"),
    })

df_summary = pd.DataFrame(summary_data)
st.dataframe(
    df_summary,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Contrat": st.column_config.TextColumn("Contrat", width=220),
        "Cours": st.column_config.NumberColumn("Cours", format="%.2f"),
        "Var (%)": st.column_config.NumberColumn("Var %", format="%+.2f"),
        "Ouverture": st.column_config.NumberColumn("Ouverture", format="%.2f"),
        "Haut": st.column_config.NumberColumn("+ Haut", format="%.2f"),
        "Bas": st.column_config.NumberColumn("+ Bas", format="%.2f"),
        "Vol. (MAD)": st.column_config.NumberColumn("Volume", format="%,.0f"),
        "Contrats": st.column_config.NumberColumn("Contrats", format="%d"),
        "Échéance": st.column_config.TextColumn("Échéance", width=100),
    },
)
# ─── RAPPORT DE CLÔTURE / SÉANCE ───
st.markdown('<h3 class="section-title">📄 Rapport de Clôture — Dernière Séance</h3>', unsafe_allow_html=True)

report_date, total_mad, total_ctr, df_report = get_daily_report()

if report_date:
    st.markdown(f"""
    <div style="background:rgba(17,24,39,0.8); border:1px solid rgba(212,168,67,0.25); 
                border-radius:16px; padding:1.5rem; margin-bottom:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="color:#D4A843; font-family:'Space Mono'; font-size:1.1rem;">Séance du</span><br>
                <span style="color:#E5E7EB; font-size:1.8rem; font-weight:700;">{report_date}</span>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'Space Mono'; color:#10B981; font-size:1.3rem; font-weight:700;">
                    {total_mad:,.0f} <span style="font-size:0.9rem; color:#6B7280;">MAD</span>
                </div>
                <div style="font-size:0.95rem; color:#6B7280;">Volume total</div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'Space Mono'; color:#E5E7EB; font-size:1.3rem; font-weight:700;">
                    {total_ctr:,}
                </div>
                <div style="font-size:0.95rem; color:#6B7280;">Contrats échangés</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        df_report,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Contrat": st.column_config.TextColumn("Contrat", width=220),
            "Cours": st.column_config.NumberColumn("Cours", format="%.2f"),
            "Variation (%)": st.column_config.NumberColumn("Var %", format="%+.2f"),
            "Ouverture": st.column_config.NumberColumn("Ouverture", format="%.2f"),
            "Plus Haut": st.column_config.NumberColumn("+ Haut", format="%.2f"),
            "Plus Bas": st.column_config.NumberColumn("+ Bas", format="%.2f"),
            "Volume (MAD)": st.column_config.NumberColumn("Volume", format="%,.0f"),
            "Contrats": st.column_config.NumberColumn("Contrats", format="%d"),
        }
    )

    # Téléchargement Excel + CSV
    csv = df_report.to_csv(index=False).encode("utf-8")
    excel = df_report.to_excel(index=False).encode("utf-8") if hasattr(df_report, 'to_excel') else csv

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Télécharger en CSV",
            data=csv,
            file_name=f"rapport_futures_{report_date}.csv",
            mime="text/csv"
        )
    with col2:
        st.download_button(
            label="📊 Télécharger en Excel",
            data=excel,
            file_name=f"rapport_futures_{report_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Aucun rapport de clôture disponible pour le moment.")

# ─── Footer ───
st.markdown("""
<div style="text-align:center; padding:2rem 0 1rem; margin-top:2rem; border-top:1px solid rgba(212,168,67,0.08);">
    <p style="font-family:'DM Sans',sans-serif; color:#4B5563; font-size:0.78rem;">
        MAT Platform V1.0 — Données : <a href="https://futures.casablanca-bourse.com/" target="_blank" style="color:#D4A843; text-decoration:none;">futures.casablanca-bourse.com</a> · Scraping quotidien à 15h35 (GMT+1)
    </p>
    <p style="font-family:'DM Sans',sans-serif; color:#4B5563; font-size:0.72rem;">
        ⚠️ Ne constitue pas un conseil en investissement. Données à titre informatif uniquement.
    </p>
</div>
""", unsafe_allow_html=True)
