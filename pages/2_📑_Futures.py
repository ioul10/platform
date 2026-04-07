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
from scraper import scrape_futures_data, load_history, get_market_status

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
    st.markdown(f"""
<div style="background:rgba(17,24,39,0.5);border-radius:12px;padding:1rem;">
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Cours (MAD)</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c['cours']:,.2f}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Variation</span><span style="color:{var_color};font-family:'Space Mono',monospace;font-size:0.88rem;">{var_sign}{var:.2f}%</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Ouverture</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c.get('ouverture', 'N/A')}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Plus haut</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c.get('plus_haut', 'N/A')}</span></div>
</div>
""", unsafe_allow_html=True)

with detail_right:
    st.markdown(f"""
<div style="background:rgba(17,24,39,0.5);border-radius:12px;padding:1rem;">
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Plus bas</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c.get('plus_bas', 'N/A')}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Clôture veille</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c.get('cloture_veille', c.get('prix_initial', 'N/A'))}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Volume (MAD)</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c.get('volume_mad', 0):,.2f}</span></div>
<div style="display:flex;justify-content:space-between;padding:8px 0;"><span style="color:#6B7280;font-family:'DM Sans',sans-serif;font-size:0.88rem;">Nombre de contrats</span><span style="color:#E5E7EB;font-family:'Space Mono',monospace;font-size:0.88rem;">{c.get('nb_contrats', c.get('volume_titres', 0))}</span></div>
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
        range=[1280, 1340],
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

st.markdown("""
<div style="font-family:'DM Sans',sans-serif; color:#6B7280; font-size:0.85rem; margin-bottom:1rem;">
    L'historique est mis à jour automatiquement à la clôture de chaque séance (15:30).
    Les données du premier jour de cotation (6 avril 2026) sont disponibles ci-dessous.
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
            file_name=f"futures_history_{datetime.now().strftime('%Y%m%d')}.csv",
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

# ─── Footer ───
st.markdown("""
<div style="text-align:center; padding:2rem 0 1rem; margin-top:2rem; border-top:1px solid rgba(212,168,67,0.08);">
    <p style="font-family:'DM Sans',sans-serif; color:#4B5563; font-size:0.78rem;">
        MAT Platform V1.0 — Les données sont mises à jour à chaque clôture de séance (15:30)
    </p>
    <p style="font-family:'DM Sans',sans-serif; color:#4B5563; font-size:0.72rem;">
        ⚠️ Ne constitue pas un conseil en investissement. Données à titre informatif uniquement.
    </p>
</div>
""", unsafe_allow_html=True)
