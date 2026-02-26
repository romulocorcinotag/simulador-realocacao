"""
Sistema de Propostas para Clientes Prospects - TAG Investimentos
Entry point for the proposal management application.

Pages:
  - Dashboard Executivo: KPIs, funil, receita projetada
  - Pipeline: Kanban, CRM, interacoes
  - Cadastro: Prospect registration (6 tabs)
  - Carteira Atual: Portfolio upload & diagnostics
  - Proposta com IA: AI-powered proposal generation
  - Visualizar Proposta: Preview, HTML export, scoring
"""
import streamlit as st
import os
import sys
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Load .env file (API keys)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
except ImportError:
    pass

st.set_page_config(
    page_title="Propostas · TAG Investimentos",
    page_icon="https://taginvest.com.br/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

from shared.brand import TAG, inject_css, render_step_indicator, fmt_brl
from database.db import init_db

# Initialize database
init_db()

# Inject branded CSS
inject_css()

# ─────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    logo_path = os.path.join(os.path.dirname(__file__), "logo_sidebar.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown(
            f'<h2 style="color:{TAG["laranja"]};text-align:center;margin-bottom:0">'
            f'TAG</h2>'
            f'<p style="color:{TAG["text_muted"]};text-align:center;font-size:0.8rem;margin-top:0">'
            f'I N V E S T I M E N T O S</p>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    page = st.radio(
        "Navegação",
        [
            "📈 Dashboard",
            "📊 Pipeline",
            "👤 Cadastro de Prospect",
            "💼 Carteira Atual",
            "🤖 Proposta com IA",
            "📄 Visualizar Proposta",
            "🏦 Planejamento Financeiro",
            "📋 Balancos & Estimativas",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick stats
    from database.models import get_pipeline_stats
    stats = get_pipeline_stats()
    if stats["total"] > 0:
        st.caption("RESUMO DO PIPELINE")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Prospects", stats["total"])
        with col2:
            active = sum(
                v["count"]
                for k, v in stats["by_status"].items()
                if k not in ("Cliente", "Perdido")
            )
            st.metric("Ativos", active)

        # Conversion rate
        clientes = stats["by_status"].get("Cliente", {}).get("count", 0)
        if stats["total"] > 0:
            conv_rate = clientes / stats["total"] * 100
            st.caption(f"Taxa de conversao: **{conv_rate:.1f}%**")

        # AUM
        st.caption(f"AUM Pipeline: **{fmt_brl(stats['total_pl'])}**")

    # ── Alerts: upcoming actions ──
    upcoming = stats.get("upcoming_actions", [])
    overdue = []
    today = datetime.now().date()
    for action in upcoming:
        try:
            data = datetime.fromisoformat(action.get("data_proxima_acao", "")).date()
            if data <= today:
                overdue.append(action)
        except Exception:
            pass

    if overdue:
        st.markdown("---")
        st.markdown(
            f'<div style="background:{TAG["rosa"]}20;border:1px solid {TAG["rosa"]}40;'
            f'border-radius:8px;padding:8px 12px">'
            f'<div style="color:{TAG["rosa"]};font-weight:600;font-size:0.8rem;margin-bottom:4px">'
            f'⚠️ {len(overdue)} acao(oes) pendente(s)</div>',
            unsafe_allow_html=True,
        )
        for action in overdue[:3]:
            st.markdown(
                f'<div style="color:{TAG["text_muted"]};font-size:0.72rem">'
                f'• {action.get("prospect_nome", "")}: {action.get("proxima_acao", "")}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption(f"TAG Investimentos · Propostas v3.0")

# ─────────────────────────────────────────────────────────
# PAGE ROUTING
# ─────────────────────────────────────────────────────────
if page == "📈 Dashboard":
    from pages_proposta.p6_dashboard import render_dashboard
    render_dashboard()

elif page == "📊 Pipeline":
    from pages_proposta.p5_pipeline import render_pipeline
    render_pipeline()

elif page == "👤 Cadastro de Prospect":
    from pages_proposta.p1_cadastro import render_cadastro
    render_cadastro()

elif page == "💼 Carteira Atual":
    from pages_proposta.p2_carteira_atual import render_carteira_atual
    render_carteira_atual()

elif page == "🤖 Proposta com IA":
    from pages_proposta.p3_proposta_ia import render_proposta_ia
    render_proposta_ia()

elif page == "📄 Visualizar Proposta":
    from pages_proposta.p4_visualizar import render_visualizar
    render_visualizar()

elif page == "🏦 Planejamento Financeiro":
    from pages_proposta.p7_planejamento import render_planejamento
    render_planejamento()

elif page == "📋 Balancos & Estimativas":
    from pages_proposta.p8_balancos import render_balancos
    render_balancos()
