"""
Tela 4: Visualizar Proposta
Preview with ~22 professional sections in 4 parts, covering all PPTX content.
Supports v1 (basic), v2 (15-section), and v3 (full PPTX) formats.

Parts:
  0. Sobre a TAG (slides 1-5)
  I. Estrutura Patrimonial (slides 6-22)
  II. Gestao de Investimentos (slides 23-53) - 15 sections
  III. Governanca (slides 54-60)
  IV. Proposta Comercial (slides 61-64)
"""
import json
import os
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from shared.brand import TAG, PLOTLY_LAYOUT, fmt_brl, fmt_pct
from database.models import (
    list_prospects, get_prospect, list_propostas, get_proposta,
    update_proposta,
)
from proposal_gen.charts import (
    chart_donut, chart_comparativo_barras,
    chart_allocation_comparison, chart_concentration_by_issuer,
    chart_maturity_ladder, chart_liquidity_comparison,
    chart_risk_return_frontier, chart_bottom_up_matrix,
    chart_tax_comparison,
)
from proposal_gen.html_generator import generate_proposal_html, save_proposal_html


def render_visualizar():
    st.title("Visualizar Proposta")

    # ── Select prospect & proposta ──
    prospects = list_prospects()
    if not prospects:
        st.warning("Nenhum prospect cadastrado.")
        return

    names = [f"{p['nome']} ({p['status']})" for p in prospects]
    sel_idx = st.selectbox("Prospect", range(len(names)), format_func=lambda i: names[i])
    prospect = get_prospect(prospects[sel_idx]["id"])

    propostas = list_propostas(prospect["id"])
    if not propostas:
        st.info("Nenhuma proposta criada para este prospect. Va para 'Proposta com IA'.")
        return

    prop_names = [f"v{p.get('versao', '?')} - {p.get('status', '')} ({p.get('created_at', '')[:10]})" for p in propostas]
    prop_idx = st.selectbox("Versao da proposta", range(len(prop_names)), format_func=lambda i: prop_names[i])
    proposta = get_proposta(propostas[prop_idx]["id"])

    if not proposta:
        st.error("Proposta nao encontrada.")
        return

    st.markdown("---")

    # ── Scoring Badge ──
    _render_scoring_badge(prospect, proposta)

    # ── Actions bar ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Gerar HTML", type="primary", use_container_width=True):
            backtest_html = _generate_backtest_html(prospect, proposta)
            html = generate_proposal_html(prospect, proposta, charts_html=backtest_html)
            link_id = proposta.get("link_compartilhamento", "proposta")
            filepath = save_proposal_html(html, link_id)
            update_proposta(proposta["id"], {"html_path": filepath})
            st.success(f"HTML gerado: `propostas_html/{link_id}.html`")
            st.session_state["generated_html"] = html

    with col2:
        if st.session_state.get("generated_html"):
            st.download_button(
                "Baixar HTML",
                data=st.session_state["generated_html"],
                file_name=f"proposta_{prospect['nome'].replace(' ', '_')}.html",
                mime="text/html",
                use_container_width=True,
            )

    with col3:
        if st.button("Marcar como Enviada", use_container_width=True):
            update_proposta(proposta["id"], {"status": "Enviada"})
            from database.models import update_prospect
            update_prospect(prospect["id"], {"status": "Proposta Enviada"})
            st.success("Status atualizado para 'Enviada'!")
            st.rerun()

    with col4:
        st.markdown(
            f'<div style="text-align:center;padding:8px;color:{TAG["text_muted"]};font-size:0.85rem">'
            f'Status: <strong style="color:{TAG["laranja"]}">{proposta.get("status", "")}</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Load proposal data ──
    analytics = proposta.get("analytics_data", {}) or {}
    section_texts = proposta.get("section_texts", {}) or {}
    bottom_up_data = proposta.get("bottom_up_classification", []) or []
    politica_inv = proposta.get("politica_investimentos", {}) or {}
    fundos_sugeridos = proposta.get("fundos_sugeridos", []) or []
    proposta_comercial = proposta.get("proposta_comercial", {}) or {}

    cart_prop = proposta.get("carteira_proposta", [])
    if isinstance(cart_prop, str):
        try:
            cart_prop = json.loads(cart_prop)
        except Exception:
            cart_prop = []

    cart_atual = []
    if prospect.get("carteira_dados"):
        try:
            cart_atual = json.loads(prospect["carteira_dados"]) if isinstance(prospect["carteira_dados"], str) else prospect["carteira_dados"]
        except Exception:
            pass

    has_v3 = bool(politica_inv or fundos_sugeridos or proposta_comercial)
    has_15_sections = bool(section_texts or analytics)

    # ══════════════════════════════════════════════════════════
    # COVER
    # ══════════════════════════════════════════════════════════
    st.markdown(
        f'<div style="text-align:center;padding:40px;'
        f'background:linear-gradient(135deg,{TAG["vermelho_dark"]},{TAG["bg_dark"]} 70%);'
        f'border-radius:16px;border:1px solid {TAG["vermelho"]}30;margin-bottom:24px">'
        f'<h1 style="color:{TAG["offwhite"]};font-size:1.8rem;border:none;padding:0">Proposta de Investimento</h1>'
        f'<div style="color:{TAG["laranja"]};font-size:1.2rem;font-weight:500">{prospect["nome"]}</div>'
        f'<div style="margin-top:8px"><span style="display:inline-block;padding:4px 16px;'
        f'background:{TAG["laranja"]}20;border:1px solid {TAG["laranja"]}40;border-radius:16px;'
        f'color:{TAG["laranja"]};font-size:0.85rem">Perfil {prospect.get("perfil_investidor", "")}</span></div>'
        f'<div style="color:{TAG["text_muted"]};margin-top:12px;font-size:0.9rem">'
        f'{datetime.now().strftime("%d/%m/%Y")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patrimonio", fmt_brl(prospect.get("patrimonio_investivel", 0)))
    with col2:
        st.metric("Perfil", prospect.get("perfil_investidor", ""))
    with col3:
        st.metric("Ativos Propostos", len(cart_prop))
    with col4:
        st.metric("Horizonte", prospect.get("horizonte_investimento", "N/A")[:20])

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # RENDER BASED ON VERSION
    # ══════════════════════════════════════════════════════════

    if has_15_sections or has_v3:
        _render_full_proposal(prospect, proposta, analytics, section_texts,
                              bottom_up_data, cart_atual, cart_prop,
                              politica_inv, fundos_sugeridos, proposta_comercial)
    else:
        _render_legacy_sections(prospect, proposta, cart_prop, cart_atual)

    # Full disclaimer
    _render_disclaimers()


# ══════════════════════════════════════════════════════════
# SECTION HEADER
# ══════════════════════════════════════════════════════════

def _section_header(number, title):
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">'
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:32px;height:32px;background:{TAG["laranja"]};color:white;'
        f'border-radius:50%;font-weight:700;font-size:0.85rem">{number}</span>'
        f'<span style="color:{TAG["offwhite"]};font-size:1.1rem;font-weight:600">{title}</span>'
        f'</div>'
    )


def _part_header(title):
    st.markdown(
        f'<div style="text-align:center;padding:16px;margin:24px 0 8px 0;'
        f'border-top:2px solid {TAG["laranja"]}30;border-bottom:2px solid {TAG["laranja"]}30">'
        f'<span style="color:{TAG["laranja"]};font-size:1rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.15em">{title}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════
# FULL ~22 SECTION RENDER
# ══════════════════════════════════════════════════════════

def _render_full_proposal(prospect, proposta, analytics, section_texts,
                          bottom_up_data, cart_atual, cart_prop,
                          politica_inv, fundos_sugeridos, proposta_comercial):
    """Render the full proposal with all PPTX-equivalent sections."""

    sec_num = 0  # Running section counter

    # ━━━━━━━━━━━━━━━━━━━━━
    # PARTE 0: SOBRE A TAG
    # ━━━━━━━━━━━━━━━━━━━━━
    _part_header("Sobre a TAG Investimentos")
    sec_num += 1
    _render_section_sobre_tag(sec_num)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PARTE I: ESTRUTURA PATRIMONIAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    estrutura_familiar = prospect.get("estrutura_familiar", [])
    estrutura_patrimonial = prospect.get("estrutura_patrimonial", {})
    plano_sucessorio = prospect.get("plano_sucessorio", {})
    has_patrimony = (
        (isinstance(estrutura_familiar, list) and any(m.get("nome") for m in estrutura_familiar))
        or section_texts.get("estrutura_patrimonial_texto")
    )
    if has_patrimony:
        _part_header("Parte I - Estrutura Patrimonial e Sucessoria")

        sec_num += 1
        _render_section_estrutura_familiar(sec_num, prospect, section_texts)

        sec_num += 1
        _render_section_analise_patrimonial(sec_num, prospect, section_texts)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PARTE II: GESTAO DE INVESTIMENTOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _part_header("Parte II - Gestao de Investimentos")

    # Section: Sumario Executivo
    sec_num += 1
    with st.expander(f"{sec_num}. Sumario Executivo", expanded=True):
        st.markdown(_section_header(sec_num, "Sumario Executivo"), unsafe_allow_html=True)
        text = section_texts.get("sumario_executivo", "")
        if text:
            st.markdown(text)
        else:
            st.caption("Texto nao gerado. Gere novamente a proposta com IA.")

    # Section: Premissas e Filosofia
    sec_num += 1
    with st.expander(f"{sec_num}. Premissas e Filosofia de Investimento"):
        st.markdown(_section_header(sec_num, "Premissas e Filosofia de Investimento"), unsafe_allow_html=True)
        text = section_texts.get("premissas_filosofia", "")
        if text:
            st.markdown(text)
        else:
            st.caption("Texto nao gerado.")

    # Section: Diagnostico Top Down
    sec_num += 1
    with st.expander(f"{sec_num}. Diagnostico Top Down"):
        st.markdown(_section_header(sec_num, "Diagnostico Top Down - Alocacao por Classe"), unsafe_allow_html=True)
        diag_text = proposta.get("diagnostico_texto", "")
        if diag_text:
            st.markdown(diag_text)
        allocation = analytics.get("allocation", {})
        if allocation.get("class_breakdown"):
            fig = chart_allocation_comparison(allocation)
            st.plotly_chart(fig, use_container_width=True)
            exposure = allocation.get("exposure_summary", {})
            if exposure:
                st.markdown("**Resumo de Exposicao:**")
                exp_rows = []
                for key, vals in exposure.items():
                    label = key.replace("_", " ").title()
                    exp_rows.append({
                        "Exposicao": label,
                        "Atual (%)": vals.get("atual", 0),
                        "Proposta (%)": vals.get("proposta", 0),
                        "Delta (pp)": round(vals.get("proposta", 0) - vals.get("atual", 0), 2),
                    })
                if exp_rows:
                    exp_df = pd.DataFrame(exp_rows)
                    st.dataframe(
                        exp_df.style.format({
                            "Atual (%)": "{:.1f}%",
                            "Proposta (%)": "{:.1f}%",
                            "Delta (pp)": "{:+.1f}pp",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )
        else:
            _render_donut_comparison(prospect, cart_prop, cart_atual)

    # Section: Diagnostico de Risco
    sec_num += 1
    with st.expander(f"{sec_num}. Diagnostico de Risco e Concentracao"):
        st.markdown(_section_header(sec_num, "Diagnostico de Risco e Concentracao"), unsafe_allow_html=True)
        risk = analytics.get("risk", {})
        if risk:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("HHI por Emissor", f"{risk.get('hhi_issuer', 0):,.0f}")
            with col2:
                st.metric("Top 5 Emissores", f"{risk.get('top5_issuer_pct', 0):.1f}%")
            with col3:
                st.metric("PL Total", fmt_brl(risk.get("total_pl", 0)))
            concentration = analytics.get("concentration", [])
            if concentration:
                st.markdown("**Concentracao por Emissor/Instituicao:**")
                fig = chart_concentration_by_issuer(concentration)
                st.plotly_chart(fig, use_container_width=True)
            strategy_list = risk.get("concentration_by_strategy", [])
            if strategy_list:
                st.markdown("**Concentracao por Estrategia:**")
                strat_df = pd.DataFrame(strategy_list)
                st.dataframe(
                    strat_df.style.format({"financeiro": "R$ {:,.0f}", "pct": "{:.1f}%"}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.caption("Dados de risco nao disponiveis.")

    # Section: Analise Bottom Up
    sec_num += 1
    with st.expander(f"{sec_num}. Analise Bottom Up da Carteira"):
        st.markdown(_section_header(sec_num, "Analise Bottom Up - Matriz de Classificacao"), unsafe_allow_html=True)
        text = section_texts.get("analise_bottom_up_texto", "")
        if text:
            st.markdown(text)
        if bottom_up_data:
            fig = chart_bottom_up_matrix(bottom_up_data)
            st.plotly_chart(fig, use_container_width=True)
            bu_df = pd.DataFrame(bottom_up_data)
            display_cols = ["ativo", "classificacao", "motivo", "pct_atual", "pct_proposta", "financeiro"]
            available = [c for c in display_cols if c in bu_df.columns]
            if available:
                show_df = bu_df[available].rename(columns={
                    "ativo": "Ativo", "classificacao": "Classificacao", "motivo": "Motivo",
                    "pct_atual": "% Atual", "pct_proposta": "% Proposta", "financeiro": "Financeiro",
                })
                fmt = {"% Atual": "{:.2f}%", "% Proposta": "{:.2f}%"}
                if "Financeiro" in show_df.columns:
                    fmt["Financeiro"] = "R$ {:,.0f}"
                st.dataframe(show_df.style.format(fmt), use_container_width=True, hide_index=True, height=400)
        else:
            st.caption("Classificacao bottom-up nao disponivel.")

    # Section: Diagnostico de Eficiencia
    sec_num += 1
    with st.expander(f"{sec_num}. Diagnostico de Eficiencia"):
        st.markdown(_section_header(sec_num, "Diagnostico de Eficiencia - Risco x Retorno"), unsafe_allow_html=True)
        efficiency = analytics.get("efficiency", {})
        eff_windows = efficiency.get("efficiency_by_window", [])
        if eff_windows:
            fig = chart_risk_return_frontier(efficiency)
            st.plotly_chart(fig, use_container_width=True)
            eff_df = pd.DataFrame(eff_windows)
            st.dataframe(
                eff_df.style.format({
                    "retorno": "{:.2f}%", "volatilidade": "{:.2f}%",
                    "sharpe": "{:.2f}", "sortino": "{:.2f}",
                    "retorno_por_vol": "{:.2f}", "alpha_cdi": "{:.2f}%",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("Execute o backtest para ver metricas de eficiencia.")

    # Section: Objetivos da Proposta
    sec_num += 1
    with st.expander(f"{sec_num}. Objetivos da Carteira Proposta"):
        st.markdown(_section_header(sec_num, "Objetivos da Carteira Proposta"), unsafe_allow_html=True)
        text = section_texts.get("objetivos_proposta", "")
        if text:
            st.markdown(text)
        else:
            st.caption("Texto nao gerado.")

    # Section: Proposta Top Down
    sec_num += 1
    with st.expander(f"{sec_num}. Carteira Proposta - Visao Top Down"):
        st.markdown(_section_header(sec_num, "Carteira Proposta - Visao Top Down"), unsafe_allow_html=True)
        text = section_texts.get("proposta_top_down_texto", "")
        if text:
            st.markdown(text)
        _render_donut_comparison(prospect, cart_prop, cart_atual)

    # Section: Proposta Bottom Up (DETAILED TABLE)
    sec_num += 1
    with st.expander(f"{sec_num}. Carteira Proposta - Detalhamento por Ativo"):
        st.markdown(_section_header(sec_num, "Carteira Proposta - Detalhamento por Ativo"), unsafe_allow_html=True)
        text = section_texts.get("proposta_bottom_up_texto", "")
        if text:
            st.markdown(text)
            st.markdown("---")
        _render_portfolio_detail_table(cart_prop, prospect)

    # Section: Ativos Sugeridos (Fund Cards)
    sec_num += 1
    with st.expander(f"{sec_num}. Ativos Sugeridos - Detalhamento"):
        st.markdown(_section_header(sec_num, "Ativos Sugeridos - Fund Cards"), unsafe_allow_html=True)
        _render_fund_cards(fundos_sugeridos, section_texts.get("fund_cards_texto", ""))

    # Section: Historico de Retornos
    sec_num += 1
    with st.expander(f"{sec_num}. Historico de Retornos"):
        st.markdown(_section_header(sec_num, "Historico de Retornos"), unsafe_allow_html=True)
        bt_data = proposta.get("backtest_data", {}) or {}
        if bt_data and bt_data.get("windows"):
            _render_backtest_metrics_only(bt_data)
        else:
            st.caption("Execute o backtest para ver metricas historicas.")
        st.caption("Retornos calculados com proxies de mercado. Rentabilidade passada nao e garantia de rentabilidade futura.")

    # Section: Backtest
    sec_num += 1
    with st.expander(f"{sec_num}. Backtest - Simulacao Historica"):
        st.markdown(_section_header(sec_num, "Backtest - Simulacao Historica"), unsafe_allow_html=True)
        _render_backtest_section(prospect, proposta, cart_prop)

    # Section: Liquidez e Vencimentos
    sec_num += 1
    with st.expander(f"{sec_num}. Liquidez e Vencimentos"):
        st.markdown(_section_header(sec_num, "Liquidez e Escalonamento de Vencimentos"), unsafe_allow_html=True)
        liquidity = analytics.get("liquidity", {})
        if liquidity:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Caixa Rapido (D+5) - Atual", f"{liquidity.get('pct_cash_quickly_atual', 0):.1f}%")
            with col2:
                st.metric("Caixa Rapido (D+5) - Proposta", f"{liquidity.get('pct_cash_quickly_proposta', 0):.1f}%")
            atual_buckets = liquidity.get("atual_buckets", {})
            proposta_buckets = liquidity.get("proposta_buckets", {})
            if atual_buckets and proposta_buckets:
                fig = chart_liquidity_comparison(atual_buckets, proposta_buckets)
                st.plotly_chart(fig, use_container_width=True)
        maturity = analytics.get("maturity", [])
        if maturity:
            st.markdown("**Escalonamento de Vencimentos:**")
            fig = chart_maturity_ladder(maturity)
            st.plotly_chart(fig, use_container_width=True)
        if not liquidity and not maturity:
            st.caption("Dados de liquidez nao disponiveis.")

    # Section: Eficiencia Tributaria
    sec_num += 1
    with st.expander(f"{sec_num}. Eficiencia Tributaria"):
        st.markdown(_section_header(sec_num, "Eficiencia Tributaria"), unsafe_allow_html=True)
        tax = analytics.get("tax", {})
        if tax:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("% Isentos - Atual", f"{tax.get('atual_isentos_pct', 0):.1f}%")
            with col2:
                st.metric("% Isentos - Proposta", f"{tax.get('proposta_isentos_pct', 0):.1f}%")
            with col3:
                delta = tax.get("delta_isentos", 0)
                st.metric("Delta", f"{delta:+.1f}pp",
                          delta=f"{'Melhora' if delta > 0 else 'Piora' if delta < 0 else 'Neutro'}",
                          delta_color="normal" if delta >= 0 else "inverse")
            fig = chart_tax_comparison(tax)
            st.plotly_chart(fig, use_container_width=True)
            turnover = tax.get("turnover", {})
            if turnover:
                st.markdown("**Giro da Carteira:**")
                st.markdown(
                    f"- Ativos saindo: **{turnover.get('saindo', 0)}**\n"
                    f"- Ativos entrando: **{turnover.get('entrando', 0)}**\n"
                    f"- Ativos mantidos: **{turnover.get('mantidos', 0)}**"
                )
        else:
            st.caption("Dados tributarios nao disponiveis.")

    # Section: Plano de Implementacao
    sec_num += 1
    with st.expander(f"{sec_num}. Plano de Implementacao"):
        st.markdown(_section_header(sec_num, "Plano de Implementacao"), unsafe_allow_html=True)
        plano = proposta.get("plano_transicao", [])
        if isinstance(plano, str):
            try:
                plano = json.loads(plano)
            except Exception:
                plano = []
        if plano:
            plano_df = pd.DataFrame(plano)
            st.dataframe(plano_df, use_container_width=True, hide_index=True, height=400)
        else:
            rec_text = proposta.get("recomendacao_texto", "")
            if rec_text:
                st.markdown("**Recomendacao de Implementacao:**")
                st.markdown(rec_text)
            else:
                st.caption("Plano de transicao nao definido.")

    # ━━━━━━━━━━━━━━━━━━━━━━━
    # PARTE III: GOVERNANCA
    # ━━━━━━━━━━━━━━━━━━━━━━━
    _part_header("Parte III - Governanca e Politica de Investimentos")

    # Section: Politica de Investimentos
    sec_num += 1
    _render_section_politica(sec_num, politica_inv, section_texts, prospect)

    # Section: Monitoramento e Governanca
    sec_num += 1
    with st.expander(f"{sec_num}. Monitoramento e Governanca"):
        st.markdown(_section_header(sec_num, "Monitoramento e Governanca"), unsafe_allow_html=True)
        text = section_texts.get("monitoramento_governanca", "")
        if text:
            st.markdown(text)
        gov_text = section_texts.get("governanca_texto", "")
        if gov_text:
            st.markdown("---")
            st.markdown(gov_text)
        if not text and not gov_text:
            st.caption("Texto nao gerado.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PARTE IV: PROPOSTA COMERCIAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _part_header("Parte IV - Proposta Comercial")

    # Section: Proposta Comercial (Fee Table)
    sec_num += 1
    _render_section_comercial(sec_num, proposta_comercial, prospect)

    # Section: Contato
    sec_num += 1
    _render_section_contato(sec_num)


# ══════════════════════════════════════════════════════════
# INDIVIDUAL SECTION RENDERS
# ══════════════════════════════════════════════════════════

def _render_section_sobre_tag(sec_num):
    """Render 'About TAG' section from institutional data."""
    with st.expander(f"{sec_num}. A TAG Investimentos", expanded=True):
        st.markdown(_section_header(sec_num, "A TAG Investimentos"), unsafe_allow_html=True)
        try:
            from shared.tag_institucional import TAG_INFO, SOLUCOES_360
            info = TAG_INFO
            st.markdown(info.get("descricao_jornada", info.get("descricao_curta", "")))

            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Anos de Historia", f"{info.get('anos_historia', 20)}+")
            with col2:
                st.metric("AUM", info.get("aum", "R$ 15 bilhoes"))
            with col3:
                st.metric("Familias", info.get("familias", 100))
            with col4:
                st.metric("Profissionais", info.get("profissionais", 60))

            # 360 solutions
            st.markdown("---")
            st.markdown("**Solucoes 360 graus:**")
            cols = st.columns(len(SOLUCOES_360))
            for i, (key, solucao) in enumerate(SOLUCOES_360.items()):
                with cols[i % len(cols)]:
                    st.markdown(f"**{solucao['titulo']}**")
                    for item in solucao["itens"][:4]:
                        st.markdown(f"- {item}")
        except ImportError:
            st.markdown(
                "A TAG Investimentos e uma gestora independente com mais de 20 anos de historia, "
                "R$ 15 bilhoes sob gestao e uma equipe de 60 profissionais dedicados."
            )


def _render_section_estrutura_familiar(sec_num, prospect, section_texts):
    """Render family structure section."""
    with st.expander(f"{sec_num}. Estrutura Familiar e Sucessoria"):
        st.markdown(_section_header(sec_num, "Estrutura Familiar e Sucessoria"), unsafe_allow_html=True)

        familia = prospect.get("estrutura_familiar", [])
        if isinstance(familia, list) and familia:
            valid = [m for m in familia if m.get("nome")]
            if valid:
                fam_df = pd.DataFrame(valid)
                rename_map = {"nome": "Nome", "relacao": "Relacao", "idade": "Idade", "regime_casamento": "Regime"}
                fam_df = fam_df.rename(columns={k: v for k, v in rename_map.items() if k in fam_df.columns})
                st.dataframe(fam_df, use_container_width=True, hide_index=True)

        # Patrimonio para sucessao
        estr = prospect.get("estrutura_patrimonial", {})
        if isinstance(estr, dict) and estr.get("patrimonio_sucessao"):
            st.metric("Patrimonio para Sucessao", fmt_brl(estr["patrimonio_sucessao"]))

        # Plano sucessorio
        plano = prospect.get("plano_sucessorio", {})
        if isinstance(plano, dict) and any(plano.values()):
            st.markdown("**Instrumentos de Planejamento Atuais:**")
            instruments = []
            if plano.get("testamento"):
                instruments.append("Testamento")
            if plano.get("doacao_antecipada"):
                instruments.append("Doacao em adiantamento de legitima")
            if plano.get("seguro_vida"):
                instruments.append("Seguro de vida / Previdencia")
            if plano.get("trust"):
                instruments.append("Trust / PIC")
            if plano.get("holding_familiar"):
                instruments.append("Holding familiar")
            if plano.get("protocolo_familiar"):
                instruments.append("Protocolo familiar")
            if instruments:
                for instr in instruments:
                    st.markdown(f"- {instr}")
            if plano.get("observacoes"):
                st.markdown(f"**Observacoes:** {plano['observacoes']}")

        # AI text
        text = section_texts.get("estrutura_patrimonial_texto", "")
        if text:
            st.markdown("---")
            st.markdown(text)


def _render_section_analise_patrimonial(sec_num, prospect, section_texts):
    """Render patrimonial analysis section."""
    with st.expander(f"{sec_num}. Analise Patrimonial e Alternativas"):
        st.markdown(_section_header(sec_num, "Analise Patrimonial e Alternativas de Reestruturacao"), unsafe_allow_html=True)

        estr = prospect.get("estrutura_patrimonial", {})
        if isinstance(estr, dict) and estr.get("tipo"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Tipo de estrutura:** {estr.get('tipo', 'N/A')}")
                if estr.get("possui_offshore"):
                    st.markdown(f"**Offshore:** {estr.get('jurisdicao', '')} - {estr.get('tipo_offshore', '')}")
            with col2:
                if estr.get("patrimonio_offshore"):
                    st.metric("Patrimonio Offshore (USD)", f"US$ {estr['patrimonio_offshore']:,.0f}")

            if estr.get("holdings_texto"):
                st.markdown(f"**Holdings / PICs:** {estr['holdings_texto']}")

        # AI alternatives
        text = section_texts.get("alternativas_sucessao_texto", "")
        if text:
            st.markdown("---")
            st.markdown(text)
        elif not estr or not estr.get("tipo"):
            st.caption("Dados patrimoniais nao cadastrados. Preencha na aba 'Estrutura Patrimonial' do cadastro.")


def _render_portfolio_detail_table(cart_prop, prospect):
    """Render the detailed portfolio table (slides 34-36 style)."""
    if not cart_prop:
        st.caption("Nenhuma carteira proposta disponivel.")
        return

    patrimonio = float(prospect.get("patrimonio_investivel", 0))
    rows = []
    for item in cart_prop:
        name = item.get("ativo", item.get("Ativo", ""))
        classe = item.get("classe", item.get("Classe", ""))
        pct = item.get("pct_alvo", item.get("% Alvo", 0))
        inst = item.get("instituicao", item.get("gestor", ""))
        resgate = item.get("resgate", "")
        ret_alvo = item.get("retorno_alvo", "")
        ret_12m = item.get("retorno_12m", 0)
        vol = item.get("volatilidade", 0)
        acao = item.get("acao_recomendada", "Aplicar")
        rs = item.get("proposta_rs", 0)
        if rs == 0 and patrimonio > 0 and pct > 0:
            rs = patrimonio * pct / 100

        rows.append({
            "Ativo": name,
            "Classe": classe,
            "Instituicao": inst,
            "Liquidez": resgate,
            "R$ Proposta": rs,
            "% Alvo": pct,
            "Retorno Alvo": ret_alvo,
            "Ret 12m (%)": ret_12m,
            "Vol (%)": vol,
            "Acao": acao,
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.format({
            "R$ Proposta": "R$ {:,.0f}",
            "% Alvo": "{:.1f}%",
            "Ret 12m (%)": "{:.2f}%",
            "Vol (%)": "{:.2f}%",
        }),
        use_container_width=True,
        hide_index=True,
        height=min(600, 35 * len(df) + 40),
    )

    # Summary
    total_pct = sum(r["% Alvo"] for r in rows)
    total_rs = sum(r["R$ Proposta"] for r in rows)
    st.caption(f"Total: {total_pct:.1f}% | R$ {total_rs:,.0f} | {len(rows)} ativos")


def _render_fund_cards(fundos_sugeridos, fund_cards_texto):
    """Render fund cards section (slides 42-53)."""
    if fund_cards_texto:
        st.markdown(fund_cards_texto)
        st.markdown("---")

    if not fundos_sugeridos:
        st.caption("Dados de fundos nao disponiveis. Gere uma nova proposta para incluir fund cards.")
        return

    # Render cards in grid
    cards_per_row = 2
    for i in range(0, len(fundos_sugeridos), cards_per_row):
        cols = st.columns(cards_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(fundos_sugeridos):
                break
            fund = fundos_sugeridos[idx]
            with col:
                tipo = fund.get("tipo", fund.get("classe", ""))
                subtipo = fund.get("subtipo", "")
                tag_text = f"{tipo}" + (f" - {subtipo}" if subtipo else "")

                st.markdown(
                    f'<div style="background:{TAG["bg_card_alt"]};border-radius:10px;padding:16px;'
                    f'border-left:4px solid {TAG["laranja"]};border:1px solid {TAG["vermelho"]}20;'
                    f'margin-bottom:12px;min-height:180px">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">'
                    f'<strong style="color:{TAG["offwhite"]};font-size:0.9rem">{fund.get("nome", "")}</strong>'
                    f'<span style="background:{TAG["laranja"]}20;color:{TAG["laranja"]};padding:2px 10px;'
                    f'border-radius:12px;font-size:0.8rem;font-weight:600">{fund.get("pct_alvo", 0):.1f}%</span>'
                    f'</div>'
                    f'<div style="color:{TAG["text_muted"]};font-size:0.75rem;text-transform:uppercase;'
                    f'letter-spacing:0.03em;margin-bottom:6px">{tag_text}</div>'
                    + (f'<div style="color:{TAG["offwhite"]};font-size:0.82rem;opacity:0.85;margin-bottom:4px">'
                       f'Gestor: {fund.get("gestor", "N/A")} | Resgate: {fund.get("resgate", "N/A")}</div>'
                       if fund.get("gestor") else '')
                    + (f'<div style="color:{TAG["laranja"]};font-size:0.82rem;font-weight:500">'
                       f'Retorno-alvo: {fund.get("retorno_alvo", "N/A")}'
                       + (f' | Ret 12m: {fund["retorno_12m"]:.2f}%' if fund.get("retorno_12m") else '')
                       + f'</div>' if fund.get("retorno_alvo") else '')
                    + (f'<div style="color:{TAG["text_muted"]};font-size:0.78rem;margin-top:4px">'
                       f'{fund.get("estrategia", "")[:200]}</div>'
                       if fund.get("estrategia") else '')
                    + f'</div>',
                    unsafe_allow_html=True,
                )


def _render_section_politica(sec_num, politica_inv, section_texts, prospect):
    """Render investment policy section (slides 54-60)."""
    with st.expander(f"{sec_num}. Politica de Investimentos"):
        st.markdown(_section_header(sec_num, "Politica de Investimentos"), unsafe_allow_html=True)

        # AI-generated policy text
        pol_text = ""
        if isinstance(politica_inv, dict):
            pol_text = politica_inv.get("texto", "")
        if not pol_text:
            pol_text = section_texts.get("politica_investimentos_texto", "")
        if pol_text:
            st.markdown(pol_text)

        # Limits table
        limites = {}
        if isinstance(politica_inv, dict):
            limites = politica_inv.get("limites", {})
        if not limites:
            try:
                from shared.tag_institucional import LIMITES_POLITICA_DEFAULT
                perfil = prospect.get("perfil_investidor", "Moderado")
                limites = LIMITES_POLITICA_DEFAULT.get(perfil, {})
            except Exception:
                pass

        if limites:
            st.markdown("---")
            st.markdown("**Limites da Politica:**")
            lim_data = []
            label_map = {
                "max_por_emissor": "Max por emissor (%)",
                "max_por_gestor": "Max por gestor (%)",
                "max_renda_variavel": "Max renda variavel (%)",
                "max_credito_privado": "Max credito privado (%)",
                "max_alternativos": "Max alternativos (%)",
                "min_liquidez_d5": "Min liquidez D+5 (%)",
                "rating_minimo": "Rating minimo",
            }
            for key, label in label_map.items():
                val = limites.get(key, "")
                if val != "" and val is not None:
                    lim_data.append({"Limite": label, "Valor": f"{val}%" if isinstance(val, (int, float)) else val})
            if lim_data:
                st.dataframe(pd.DataFrame(lim_data), use_container_width=True, hide_index=True)

        # S1/S2 classification
        try:
            from shared.tag_institucional import BACEN_S1, BACEN_S2
            st.markdown("---")
            st.markdown("**Classificacao BACEN - Instituicoes Autorizadas:**")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**S1:** {', '.join(BACEN_S1)}")
            with col2:
                st.markdown(f"**S2:** {', '.join(BACEN_S2)}")
        except Exception:
            pass


def _render_section_comercial(sec_num, proposta_comercial, prospect):
    """Render commercial proposal section (slides 61-64)."""
    with st.expander(f"{sec_num}. Proposta Comercial"):
        st.markdown(_section_header(sec_num, "Proposta Comercial"), unsafe_allow_html=True)

        fee_table = []
        servicos = []
        if isinstance(proposta_comercial, dict):
            fee_table = proposta_comercial.get("fee_table", [])
            servicos = proposta_comercial.get("servicos", [])

        if not fee_table:
            try:
                from shared.tag_institucional import FEE_TABLE_DEFAULT, SERVICOS_DISPONIVEIS
                fee_table = FEE_TABLE_DEFAULT
                if not servicos:
                    servicos = SERVICOS_DISPONIVEIS
            except Exception:
                pass

        if fee_table:
            st.markdown("**Tabela de Taxas:**")
            fee_df = pd.DataFrame(fee_table)
            fee_df = fee_df.rename(columns={"faixa": "Faixa", "taxa_adm": "Taxa Adm (% a.a.)"})
            st.dataframe(fee_df.style.format({"Taxa Adm (% a.a.)": "{:.2f}%"}),
                         use_container_width=True, hide_index=True)

        taxa_perf = proposta_comercial.get("taxa_performance", 0) if isinstance(proposta_comercial, dict) else 0
        if taxa_perf > 0:
            st.markdown(f"**Taxa de Performance:** {taxa_perf:.1f}%")

        if servicos:
            st.markdown("---")
            st.markdown("**Servicos Incluidos:**")
            for svc in servicos:
                st.markdown(f"- {svc}")

        condicoes = proposta_comercial.get("condicoes_especiais", "") if isinstance(proposta_comercial, dict) else ""
        if condicoes:
            st.markdown("---")
            st.markdown(f"**Condicoes Especiais:** {condicoes}")


def _render_section_contato(sec_num):
    """Render contact section."""
    with st.expander(f"{sec_num}. Contato"):
        st.markdown(_section_header(sec_num, "Contato"), unsafe_allow_html=True)
        try:
            from shared.tag_institucional import TAG_INFO
            info = TAG_INFO
            st.markdown(
                f"**{info.get('nome', 'TAG Investimentos')}**\n\n"
                f"{info.get('endereco', '')}\n\n"
                f"CEP: {info.get('cep', '')} - {info.get('cidade', '')}/{info.get('uf', '')}\n\n"
                f"Telefone: {info.get('telefone', '')}\n\n"
                f"Email: {info.get('email', '')}"
            )
        except Exception:
            st.markdown("TAG Investimentos\n\nAv. Brig. Faria Lima, 3.311 - 12 andar\n\nSao Paulo/SP")


def _render_disclaimers():
    """Render full disclaimers."""
    st.markdown("---")
    try:
        from shared.tag_institucional import DISCLAIMERS, DISCLAIMER_RESUMIDO
        with st.expander("Consideracoes Importantes (Disclaimers)"):
            for d in DISCLAIMERS:
                st.caption(d)
    except Exception:
        st.caption(
            "Este documento e uma proposta de investimento e nao constitui oferta, solicitacao ou "
            "recomendacao de compra ou venda de ativos. Rentabilidade passada nao garante rentabilidade futura. "
            "Investimentos envolvem riscos."
        )
    st.caption(f"TAG Investimentos - {datetime.now().year}")


# ══════════════════════════════════════════════════════════
# HELPER RENDERS
# ══════════════════════════════════════════════════════════

def _render_donut_comparison(prospect, cart_prop, cart_atual):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Carteira Atual**")
        if cart_atual:
            try:
                cart_df = pd.DataFrame(cart_atual)
                if "Financeiro" in cart_df.columns:
                    total = cart_df["Financeiro"].sum()
                    if total > 0:
                        cart_df["pct"] = cart_df["Financeiro"] / total * 100
                        name_col = "Ativo" if "Ativo" in cart_df.columns else cart_df.columns[0]
                        fig = chart_donut(cart_df[name_col].astype(str).str[:25].tolist(), cart_df["pct"].tolist())
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.caption("PL total = 0")
                else:
                    st.caption("Coluna 'Financeiro' nao encontrada.")
            except Exception:
                st.caption("Dados nao disponiveis")
        else:
            st.caption("Carteira atual nao cadastrada.")

    with col2:
        st.markdown("**Carteira Proposta TAG**")
        if cart_prop:
            labels = [c.get("ativo", c.get("Ativo", ""))[:25] for c in cart_prop]
            values = [c.get("pct_alvo", c.get("% Alvo", 0)) for c in cart_prop]
            fig = chart_donut(labels, values)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Carteira proposta nao definida.")


def _render_backtest_metrics_only(bt_data):
    try:
        from shared.backtest import chart_backtest_metrics_table
        fig = chart_backtest_metrics_table(bt_data)
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        windows = bt_data.get("windows", {})
        if windows:
            rows = []
            for label, w in sorted(windows.items(), key=lambda x: x[1].get("months", 0)):
                rows.append({
                    "Janela": label,
                    "Retorno": f"{w.get('total_return', 0) * 100:.2f}%",
                    "Vol (a.a.)": f"{w.get('volatility', 0) * 100:.2f}%",
                    "Sharpe": f"{w.get('sharpe', 0):.2f}",
                    "CDI": f"{w.get('cdi_return', 0) * 100:.2f}%",
                    "% CDI": f"{w.get('pct_cdi', 0):.0f}%",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════
# LEGACY RENDER (proposals without 15-section data)
# ══════════════════════════════════════════════════════════

def _render_legacy_sections(prospect, proposta, cart_prop, cart_atual):
    st.markdown(
        f'<div class="proposal-section">'
        f'<h3 style="color:{TAG["laranja"]}">Diagnostico da Carteira Atual</h3>'
        f'</div>',
        unsafe_allow_html=True,
    )
    diag_text = proposta.get("diagnostico_texto", "")
    if diag_text:
        st.markdown(diag_text)
    else:
        st.caption("Sem diagnostico disponivel.")

    st.markdown("---")
    st.markdown(f'<h3 style="color:{TAG["laranja"]}">Alocacao: Atual vs Proposta</h3>', unsafe_allow_html=True)
    _render_donut_comparison(prospect, cart_prop, cart_atual)

    st.markdown("---")
    st.markdown(f'<h3 style="color:{TAG["laranja"]}">Backtest Historico</h3>', unsafe_allow_html=True)
    _render_backtest_section(prospect, proposta, cart_prop)

    st.markdown("---")
    st.markdown(
        f'<div class="proposal-section">'
        f'<h3 style="color:{TAG["laranja"]}">Nossa Recomendacao</h3>'
        f'</div>',
        unsafe_allow_html=True,
    )
    rec_text = proposta.get("recomendacao_texto", "")
    if rec_text:
        st.markdown(rec_text)
    else:
        st.caption("Sem recomendacao disponivel.")

    st.markdown("---")
    st.markdown(f'<h3 style="color:{TAG["laranja"]}">Carteira Proposta - Detalhamento</h3>', unsafe_allow_html=True)
    if cart_prop:
        prop_df = pd.DataFrame(cart_prop)
        display_cols = {}
        if "classe" in prop_df.columns:
            display_cols["classe"] = "Classe"
        if "ativo" in prop_df.columns:
            display_cols["ativo"] = "Ativo"
        elif "Ativo" in prop_df.columns:
            display_cols["Ativo"] = "Ativo"
        if "pct_alvo" in prop_df.columns:
            display_cols["pct_alvo"] = "% Alvo"
        elif "% Alvo" in prop_df.columns:
            display_cols["% Alvo"] = "% Alvo"
        if "estrategia" in prop_df.columns:
            display_cols["estrategia"] = "Estrategia"
        if "justificativa" in prop_df.columns:
            display_cols["justificativa"] = "Justificativa"
        if display_cols:
            show_df = prop_df[list(display_cols.keys())].rename(columns=display_cols)
            st.dataframe(
                show_df.style.format({"% Alvo": "{:.1f}%"} if "% Alvo" in show_df.columns else {}),
                use_container_width=True, hide_index=True,
            )


# ══════════════════════════════════════════════════════════
# BACKTEST
# ══════════════════════════════════════════════════════════

def _render_backtest_section(prospect, proposta, cart_prop):
    from shared.backtest import (
        calculate_portfolio_backtest, compare_portfolios_backtest,
        chart_backtest_cumulative, chart_backtest_comparison,
        chart_backtest_metrics_table, chart_risk_return_scatter,
        chart_drawdown,
    )

    if not cart_prop:
        st.info("Sem carteira proposta para backtest.")
        return

    cache_key = f"backtest_{proposta['id']}"
    if cache_key in st.session_state:
        bt_result = st.session_state[cache_key]
    else:
        bt_result = None

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        run_bt = st.button("Executar Backtest", type="primary", use_container_width=True)
    with col_btn2:
        windows_sel = st.multiselect(
            "Janelas",
            options=[6, 12, 24, 36, 60],
            default=[12, 36, 60],
            format_func=lambda x: {6: "6M", 12: "1A", 24: "2A", 36: "3A", 60: "5A"}[x],
        )

    if run_bt:
        with st.spinner("Calculando backtest..."):
            cart_atual = []
            if prospect.get("carteira_dados"):
                try:
                    cart_atual = json.loads(prospect["carteira_dados"]) if isinstance(prospect["carteira_dados"], str) else prospect["carteira_dados"]
                except Exception:
                    pass
            if cart_atual:
                comparison = compare_portfolios_backtest(cart_atual, cart_prop, windows_sel)
                st.session_state[cache_key] = {"type": "comparison", "data": comparison}
                bt_result = st.session_state[cache_key]
            else:
                bt_proposed = calculate_portfolio_backtest(cart_prop, windows_sel)
                st.session_state[cache_key] = {"type": "single", "data": bt_proposed}
                bt_result = st.session_state[cache_key]

    if not bt_result:
        st.info("Clique em 'Executar Backtest' para performance historica.")
        return

    if bt_result["type"] == "comparison":
        comparison = bt_result["data"]
        fig_comp = chart_backtest_comparison(comparison)
        st.plotly_chart(fig_comp, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Carteira Atual**")
            bt_curr = comparison.get("current", {})
            if bt_curr.get("windows"):
                fig = chart_backtest_metrics_table(bt_curr, "Metricas - Atual")
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.markdown("**Proposta TAG**")
            bt_prop = comparison.get("proposed", {})
            if bt_prop.get("windows"):
                fig = chart_backtest_metrics_table(bt_prop, "Metricas - Proposta")
                st.plotly_chart(fig, use_container_width=True)
        fig_scatter = chart_risk_return_scatter(comparison)
        st.plotly_chart(fig_scatter, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            if bt_curr.get("windows"):
                fig_dd = chart_drawdown(bt_curr, "Drawdown - Atual")
                st.plotly_chart(fig_dd, use_container_width=True)
        with col2:
            if bt_prop.get("windows"):
                fig_dd = chart_drawdown(bt_prop, "Drawdown - Proposta")
                st.plotly_chart(fig_dd, use_container_width=True)
    else:
        bt_data = bt_result["data"]
        if bt_data.get("error"):
            st.warning(f"Backtest: {bt_data['error']}")
            return
        fig_cum = chart_backtest_cumulative(bt_data)
        st.plotly_chart(fig_cum, use_container_width=True)
        fig_metrics = chart_backtest_metrics_table(bt_data)
        st.plotly_chart(fig_metrics, use_container_width=True)
        fig_dd = chart_drawdown(bt_data)
        st.plotly_chart(fig_dd, use_container_width=True)


def _generate_backtest_html(prospect, proposta):
    try:
        from shared.backtest import calculate_portfolio_backtest, backtest_metrics_to_html
        cart_prop = proposta.get("carteira_proposta", [])
        if isinstance(cart_prop, str):
            try:
                cart_prop = json.loads(cart_prop)
            except Exception:
                cart_prop = []
        if not cart_prop:
            return ""
        bt = calculate_portfolio_backtest(cart_prop, [12, 36, 60])
        if bt.get("error"):
            return ""
        html = '<h3 style="margin-top:24px;">Backtest Historico - Proposta TAG</h3>'
        html += backtest_metrics_to_html(bt)
        html += '<p style="font-size:0.8rem;color:#999;margin-top:8px;">Backtest com proxies. Rentabilidade passada nao garante futura.</p>'
        return html
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════
# SCORING BADGE
# ══════════════════════════════════════════════════════════

def _render_scoring_badge(prospect, proposta):
    """Render proposal adequacy scoring badge at the top of the page."""
    try:
        from shared.scoring import score_proposal, score_color
        from shared.validators import validate_prospect_completeness, validate_proposal_readiness

        analytics = proposta.get("analytics_data", {}) or {}
        result = score_proposal(prospect, proposta, analytics)
        score = result["score_total"]
        selo = result["selo"]
        color = score_color(score)

        # Readiness check
        ready_score, ready_issues, ready = validate_proposal_readiness(prospect, proposta)

        # Completeness check
        comp_score, missing_fields, recommendations = validate_prospect_completeness(prospect)

        # ── Main badge row ──
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])

        with col1:
            st.markdown(
                f'<div style="text-align:center;padding:12px;background:{TAG["bg_card"]};'
                f'border-radius:12px;border:2px solid {color}">'
                f'<div style="font-size:2rem;font-weight:700;color:{color}">{score}</div>'
                f'<div style="color:{TAG["text_muted"]};font-size:0.75rem;text-transform:uppercase">'
                f'Score de Adequacao</div>'
                f'<div style="color:{color};font-weight:600;font-size:0.85rem;margin-top:4px">{selo}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f'<div style="text-align:center;padding:12px;background:{TAG["bg_card"]};'
                f'border-radius:12px;border:1px solid {TAG["vermelho"]}20">'
                f'<div style="font-size:1.5rem;font-weight:600;color:{TAG["laranja"]}">{ready_score}%</div>'
                f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">Prontidao p/ Entrega</div>'
                f'<div style="color:{"#6BDE97" if ready else "#ED5A6E"};font-size:0.82rem;margin-top:4px">'
                f'{"Pronta" if ready else "Incompleta"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f'<div style="text-align:center;padding:12px;background:{TAG["bg_card"]};'
                f'border-radius:12px;border:1px solid {TAG["vermelho"]}20">'
                f'<div style="font-size:1.5rem;font-weight:600;color:{TAG["azul"]}">{comp_score}%</div>'
                f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">Cadastro Completo</div>'
                f'<div style="color:{TAG["text_muted"]};font-size:0.78rem;margin-top:4px">'
                f'{len(missing_fields)} campo(s) faltando</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col4:
            # Dimension bars
            for dim in result["dimensoes"]:
                pct = (dim["score"] / dim["max"] * 100) if dim["max"] > 0 else 0
                bar_color = score_color(pct)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">'
                    f'<span style="color:{TAG["text_muted"]};font-size:0.7rem;min-width:85px">'
                    f'{dim["nome"]}</span>'
                    f'<div style="flex:1;background:{TAG["bg_card"]};border-radius:3px;height:14px;overflow:hidden">'
                    f'<div style="width:{max(3, pct)}%;background:{bar_color};height:100%;border-radius:3px;'
                    f'display:flex;align-items:center;justify-content:center">'
                    f'<span style="color:white;font-size:0.6rem;font-weight:600">'
                    f'{dim["nota"]}</span>'
                    f'</div></div>'
                    f'<span style="color:{TAG["text_muted"]};font-size:0.65rem;min-width:40px;text-align:right">'
                    f'{dim["score"]:.0f}/{dim["max"]:.0f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── Alerts (collapsible) ──
        if result["alertas"]:
            with st.expander(f"⚠️ {len(result['alertas'])} alerta(s) de adequacao", expanded=False):
                for alerta in result["alertas"]:
                    st.markdown(f"- {alerta}")

    except Exception as e:
        # Fail silently - scoring is optional
        st.caption(f"Scoring nao disponivel: {e}")
