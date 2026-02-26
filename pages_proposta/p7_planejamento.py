"""
Planejamento Financeiro – Premissas e Configurações
Replicates the TAG 360° planning module with:
  - Premissas PGBL (IRPF, INSS, deductions)
  - Cálculo Atuarial Brasil / Offshore
  - Premissas Sucessório (ITCMD by state, attorney fees)
  - Cenário Macroeconômico (Brazil + Global bullets)
  - Textos do Planejamento
  - Classes de Ativos
"""
import streamlit as st
import copy
import pandas as pd

from shared.brand import TAG, fmt_brl, fmt_pct
from shared.planning_defaults import (
    PGBL_DEFAULTS,
    BRASIL_DEFAULTS,
    OFFSHORE_DEFAULTS,
    SUCESSORIO_DEFAULTS,
    CENARIO_MACRO_DEFAULTS,
    TEXTOS_PLANEJAMENTO_DEFAULTS,
    CLASSES_ATIVOS_DEFAULTS,
)
from database.premissas_models import get_premissa_or_default, upsert_premissa


# ─────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def render_planejamento():
    """Main entry for the Planning Financial module."""

    st.markdown(
        f'<h1 style="color:{TAG["offwhite"]}">🏦 Planejamento Financeiro</h1>',
        unsafe_allow_html=True,
    )
    st.caption("Premissas fiscais, atuariais e macroeconômicas para cálculos de planejamento")

    # Sub-navigation tabs
    tab_sim, tab_pgbl, tab_brasil, tab_offshore, tab_sucessorio, tab_macro, tab_textos, tab_classes = st.tabs([
        "🧮 Simulador PGBL",
        "📋 Premissas PGBL",
        "🇧🇷 Cálc. Brasil",
        "🌍 Cálc. Offshore",
        "⚖️ Sucessório",
        "📊 Cenário Macro",
        "📝 Textos",
        "🏷️ Classes de Ativos",
    ])

    with tab_sim:
        _render_simulador_pgbl()
    with tab_pgbl:
        _render_pgbl()
    with tab_brasil:
        _render_calculo_brasil()
    with tab_offshore:
        _render_calculo_offshore()
    with tab_sucessorio:
        _render_sucessorio()
    with tab_macro:
        _render_cenario_macro()
    with tab_textos:
        _render_textos_planejamento()
    with tab_classes:
        _render_classes_ativos()


# ─────────────────────────────────────────────────────────
# 0. SIMULADOR PGBL INTERATIVO
# ─────────────────────────────────────────────────────────

def _render_simulador_pgbl():
    """Interactive PGBL tax deduction simulator."""
    from shared.pgbl_calculator import simular_pgbl

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">🧮 Simulador de Dedução PGBL</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Calcule a economia tributária com aportes em PGBL usando as premissas fiscais atuais</p></div>',
        unsafe_allow_html=True,
    )

    # Input form
    st.markdown("### Dados do Cliente")

    col1, col2, col3 = st.columns(3)
    with col1:
        renda_mensal = st.number_input(
            "Renda Bruta Mensal (R$)",
            value=30000.0,
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            key="sim_renda",
        )
    with col2:
        num_dep = st.number_input(
            "Número de Dependentes",
            value=2,
            min_value=0,
            max_value=20,
            step=1,
            key="sim_dep",
        )
    with col3:
        gastos_educ = st.number_input(
            "Gastos com Educação (anual R$)",
            value=15000.0,
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            key="sim_educ",
        )

    col4, col5, col6 = st.columns(3)
    with col4:
        gastos_saude = st.number_input(
            "Gastos com Saúde (anual R$)",
            value=10000.0,
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            key="sim_saude",
        )
    with col5:
        usar_limite = st.checkbox("Usar limite máximo de PGBL (12%)", value=True, key="sim_max")
    with col6:
        if not usar_limite:
            aporte_custom = st.number_input(
                "Aporte PGBL Anual (R$)",
                value=30000.0,
                min_value=0.0,
                step=1000.0,
                format="%.2f",
                key="sim_aporte_custom",
            )
        else:
            aporte_custom = None

    renda_anual = renda_mensal * 12

    if renda_anual > 0:
        # Run simulation
        resultado = simular_pgbl(
            renda_bruta_anual=renda_anual,
            num_dependentes=num_dep,
            gastos_educacao=gastos_educ,
            gastos_saude=gastos_saude,
            aporte_pgbl=aporte_custom,
        )

        st.markdown("---")

        # ── Key Metrics ──
        st.markdown("### Resultado da Simulação")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "💰 Economia de IR",
            fmt_brl(resultado["economia_ir"]),
            f"{resultado['economia_pct']:.1f}% de redução",
        )
        m2.metric(
            "📅 Economia Mensal",
            fmt_brl(resultado["economia_ir_mensal"]),
        )
        m3.metric(
            "🏦 Aporte PGBL Sugerido",
            fmt_brl(resultado["pgbl_aporte"]),
            f"{resultado['pgbl_aporte_mensal']:,.0f}/mês",
        )
        m4.metric(
            "📊 Alíquota Efetiva",
            f"{resultado['aliquota_efetiva_com_pgbl']:.1f}%",
            f"{resultado['aliquota_efetiva_com_pgbl'] - resultado['aliquota_efetiva_sem_pgbl']:.1f}pp",
            delta_color="inverse",
        )

        st.markdown("---")

        # ── Comparison Table ──
        st.markdown("### Comparativo: Sem PGBL vs Com PGBL")

        comp_data = {
            "": [
                "Renda Bruta Anual",
                "(-) INSS",
                "(-) Deduções Legais",
                "(-) PGBL",
                "= Base Tributável",
                "Alíquota Marginal",
                "Alíquota Efetiva",
                "**IR Devido**",
            ],
            "Sem PGBL": [
                fmt_brl(resultado["renda_bruta_anual"]),
                fmt_brl(resultado["inss_anual"]),
                fmt_brl(resultado["deducoes_total"]),
                "R$ 0",
                fmt_brl(resultado["base_tributavel_sem_pgbl"]),
                f"{resultado['aliquota_marginal_sem_pgbl']:.1f}%",
                f"{resultado['aliquota_efetiva_sem_pgbl']:.1f}%",
                fmt_brl(resultado["ir_sem_pgbl"]),
            ],
            "Com PGBL": [
                fmt_brl(resultado["renda_bruta_anual"]),
                fmt_brl(resultado["inss_anual"]),
                fmt_brl(resultado["deducoes_total"]),
                fmt_brl(resultado["pgbl_aporte"]),
                fmt_brl(resultado["base_tributavel_com_pgbl"]),
                f"{resultado['aliquota_marginal_com_pgbl']:.1f}%",
                f"{resultado['aliquota_efetiva_com_pgbl']:.1f}%",
                fmt_brl(resultado["ir_com_pgbl"]),
            ],
        }
        comp_df = pd.DataFrame(comp_data)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        # ── Visual comparison ──
        eco = resultado["economia_ir"]
        ir_sem = resultado["ir_sem_pgbl"]
        ir_com = resultado["ir_com_pgbl"]
        aporte = resultado["pgbl_aporte"]

        if ir_sem > 0:
            pct_sem = 100
            pct_com = (ir_com / ir_sem) * 100

            st.markdown(
                f'<div style="margin-top:16px">'
                f'<div style="display:flex;align-items:center;margin-bottom:8px">'
                f'<span style="color:{TAG["text_muted"]};width:100px;font-size:0.85rem">Sem PGBL</span>'
                f'<div style="flex:1;background:{TAG["bg_card"]};border-radius:6px;height:32px;overflow:hidden">'
                f'<div style="width:{pct_sem:.0f}%;background:linear-gradient(90deg,{TAG["rosa"]},{TAG["vermelho"]});'
                f'height:100%;border-radius:6px;display:flex;align-items:center;padding:0 12px">'
                f'<span style="color:white;font-size:0.8rem;font-weight:600">{fmt_brl(ir_sem)}</span></div></div></div>'
                f'<div style="display:flex;align-items:center;margin-bottom:8px">'
                f'<span style="color:{TAG["text_muted"]};width:100px;font-size:0.85rem">Com PGBL</span>'
                f'<div style="flex:1;background:{TAG["bg_card"]};border-radius:6px;height:32px;overflow:hidden">'
                f'<div style="width:{pct_com:.0f}%;background:linear-gradient(90deg,{TAG["verde"]},#3a9e5c);'
                f'height:100%;border-radius:6px;display:flex;align-items:center;padding:0 12px">'
                f'<span style="color:white;font-size:0.8rem;font-weight:600">{fmt_brl(ir_com)}</span></div></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Deduction Details ──
        with st.expander("📋 Detalhamento das Deduções"):
            det = resultado["deducoes_detalhamento"]
            dep_info = det.get("dependentes", {})
            educ_info = det.get("educacao", {})
            saude_info = det.get("saude", {})

            st.markdown(f"""
            | Dedução | Valor |
            |---------|-------|
            | Dependentes ({dep_info.get('qtd', 0)} × {fmt_brl(dep_info.get('valor_unitario', 0))}) | {fmt_brl(dep_info.get('total', 0))} |
            | Educação (limite aplicado) | {fmt_brl(educ_info.get('deduzido', 0))} |
            | Saúde (sem limite) | {fmt_brl(saude_info.get('deduzido', 0))} |
            | **Total Deduções** | **{fmt_brl(det.get('total', 0))}** |
            | INSS Anual | {fmt_brl(resultado['inss_anual'])} |
            | PGBL (até {resultado['pct_max_pgbl']:.0f}%) | {fmt_brl(resultado['pgbl_aporte'])} |
            """)

        # ── Advisory Note ──
        st.markdown(
            f'<div class="tag-card" style="border-left:3px solid {TAG["laranja"]}">'
            f'<p style="color:{TAG["laranja"]};font-weight:600;font-size:0.85rem;margin-bottom:8px">'
            f'💡 Nota do Consultor</p>'
            f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
            f'A dedução de PGBL só se aplica para quem faz a <strong>declaração completa</strong> do IR. '
            f'O aporte sugerido de <strong>{fmt_brl(resultado["pgbl_aporte"])}/ano</strong> '
            f'({fmt_brl(resultado["pgbl_aporte_mensal"])}/mês) '
            f'gera uma economia fiscal de <strong>{fmt_brl(resultado["economia_ir"])}</strong>, '
            f'equivalente a um retorno imediato de '
            f'<strong style="color:{TAG["verde"]}">'
            f'{(resultado["economia_ir"]/resultado["pgbl_aporte"]*100) if resultado["pgbl_aporte"] > 0 else 0:.1f}%</strong> '
            f'sobre o valor aplicado.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Insira a renda bruta mensal para calcular a simulação PGBL.")


# ─────────────────────────────────────────────────────────
# 1. PREMISSAS PGBL
# ─────────────────────────────────────────────────────────

def _render_pgbl():
    """PGBL premissas: IRPF table, INSS table, deductions, rules."""

    data = get_premissa_or_default("pgbl", PGBL_DEFAULTS)

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">Premissas PGBL</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Premissas fiscais e legais para cálculos de IRPF e deduções com PGBL (Legislação 2025)</p></div>',
        unsafe_allow_html=True,
    )

    # ── Section 1: IRPF Table ──
    st.markdown(f'### 1. Tabela de Imposto de Renda Pessoa Física (IRPF)')
    st.caption("Faixas de renda anual, alíquotas e parcelas a deduzir")

    irpf_faixas = data.get("irpf_faixas", PGBL_DEFAULTS["irpf_faixas"])

    # Convert to editable dataframe
    irpf_df = pd.DataFrame(irpf_faixas)
    irpf_df["faixa_max"] = irpf_df["faixa_max"].fillna(0)  # None -> 0 for editing

    edited_irpf = st.data_editor(
        irpf_df,
        column_config={
            "faixa_min": st.column_config.NumberColumn("Faixa Mínima (R$)", format="R$ %.2f", min_value=0),
            "faixa_max": st.column_config.NumberColumn("Faixa Máxima (R$)", format="R$ %.2f", min_value=0, help="0 = Sem limite"),
            "aliquota": st.column_config.NumberColumn("Alíquota (%)", format="%.1f%%", min_value=0, max_value=100),
            "parcela_deduzir": st.column_config.NumberColumn("Parcela a Deduzir (R$)", format="R$ %.2f", min_value=0),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="irpf_editor",
    )

    st.markdown("---")

    # ── Section 2: INSS Table ──
    st.markdown(f'### 2. Tabela de INSS')
    st.caption("Faixas de remuneração e alíquotas de contribuição")

    inss_faixas = data.get("inss_faixas", PGBL_DEFAULTS["inss_faixas"])
    inss_df = pd.DataFrame(inss_faixas)

    edited_inss = st.data_editor(
        inss_df,
        column_config={
            "faixa_min": st.column_config.NumberColumn("Faixa Mínima (R$)", format="R$ %.2f", min_value=0),
            "faixa_max": st.column_config.NumberColumn("Faixa Máxima (R$)", format="R$ %.2f", min_value=0),
            "aliquota": st.column_config.NumberColumn("Alíquota (%)", format="%.1f%%", min_value=0, max_value=100),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="inss_editor",
    )

    teto_inss = st.number_input(
        "Teto Máximo Anual de Contribuição INSS (R$)",
        value=float(data.get("teto_inss_anual", PGBL_DEFAULTS["teto_inss_anual"])),
        step=100.0,
        format="%.2f",
        key="teto_inss",
    )

    st.markdown("---")

    # ── Section 3: Deduction Limits ──
    st.markdown(f'### 3. Limites Legais de Deduções')
    st.caption("Valores anuais dedutíveis para IR")

    col1, col2 = st.columns(2)
    with col1:
        ded_dependente = st.number_input(
            "Valor Anual Dedutível por Dependente (R$)",
            value=float(data.get("deducao_por_dependente", PGBL_DEFAULTS["deducao_por_dependente"])),
            step=10.0,
            format="%.2f",
            key="ded_dependente",
        )
    with col2:
        lim_educacao = st.number_input(
            "Limite Anual de Dedução com Educação (R$)",
            value=float(data.get("limite_educacao", PGBL_DEFAULTS["limite_educacao"])),
            step=10.0,
            format="%.2f",
            key="lim_educacao",
        )

    regra_saude = st.text_area(
        "Regra de Dedução de Gastos com Saúde",
        value=data.get("regra_saude", PGBL_DEFAULTS["regra_saude"]),
        height=80,
        key="regra_saude",
    )

    st.markdown("---")

    # ── Section 4: PGBL Rules ──
    st.markdown(f'### 4. Regras de PGBL')
    st.caption("Limites e observações sobre dedução de PGBL")

    pct_pgbl = st.number_input(
        "Percentual Máximo Dedutível da Renda Bruta Tributável (%)",
        value=float(data.get("pct_maximo_pgbl", PGBL_DEFAULTS["pct_maximo_pgbl"])),
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        format="%.1f",
        key="pct_pgbl",
    )

    obs_pgbl = st.text_area(
        "Observação sobre Declaração",
        value=data.get("obs_pgbl", PGBL_DEFAULTS["obs_pgbl"]),
        height=80,
        key="obs_pgbl",
    )

    # ── Save button ──
    st.markdown("---")
    if st.button("💾 Salvar Premissas PGBL", type="primary", key="save_pgbl"):
        # Build data from edited values
        irpf_records = edited_irpf.to_dict("records")
        for r in irpf_records:
            if r.get("faixa_max", 0) == 0:
                r["faixa_max"] = None  # 0 means "sem limite"

        inss_records = edited_inss.to_dict("records")

        save_data = {
            "irpf_faixas": irpf_records,
            "inss_faixas": inss_records,
            "teto_inss_anual": teto_inss,
            "deducao_por_dependente": ded_dependente,
            "limite_educacao": lim_educacao,
            "regra_saude": regra_saude,
            "pct_maximo_pgbl": pct_pgbl,
            "obs_pgbl": obs_pgbl,
        }
        upsert_premissa("pgbl", save_data)
        st.success("✅ Premissas PGBL salvas com sucesso!")
        st.rerun()


# ─────────────────────────────────────────────────────────
# 2. CÁLCULO ATUARIAL - BRASIL
# ─────────────────────────────────────────────────────────

def _render_calculo_brasil():
    """Brazil actuarial premissas."""

    data = get_premissa_or_default("brasil", BRASIL_DEFAULTS)

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">Premissas de Cálculo — Brasil</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Valores utilizados nos cálculos de planejamento financeiro para investimentos no Brasil</p></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        selic = st.number_input(
            "SELIC Média Últimos 10 Anos (% a.a.)",
            value=float(data.get("selic_media_10a", BRASIL_DEFAULTS["selic_media_10a"])),
            min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
            key="br_selic",
        )
        idade_usufruto = st.number_input(
            "Idade Final Fase Usufruto",
            value=int(data.get("idade_final_usufruto", BRASIL_DEFAULTS["idade_final_usufruto"])),
            min_value=60, max_value=120, step=1,
            key="br_usufruto",
        )
        aliq_ir = st.number_input(
            "Alíquota Imposto de Renda (% sobre rendimento)",
            value=float(data.get("aliquota_ir", BRASIL_DEFAULTS["aliquota_ir"])),
            min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
            key="br_ir",
        )
    with col2:
        inflacao = st.number_input(
            "Inflação Média Últimos 10 Anos (% a.a.)",
            value=float(data.get("inflacao_media_10a", BRASIL_DEFAULTS["inflacao_media_10a"])),
            min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
            key="br_inflacao",
        )
        idade_apos = st.number_input(
            "Idade Aposentadoria",
            value=int(data.get("idade_aposentadoria", BRASIL_DEFAULTS["idade_aposentadoria"])),
            min_value=40, max_value=100, step=1,
            key="br_apos",
        )

    # Info card with calculated values
    retorno_real = selic - inflacao
    st.markdown(
        f'<div class="tag-card">'
        f'<p style="color:{TAG["text_muted"]};font-size:0.8rem;margin-bottom:8px">VALORES CALCULADOS</p>'
        f'<p style="color:{TAG["offwhite"]}">Retorno real estimado: '
        f'<strong style="color:{TAG["verde"]}">{retorno_real:.1f}% a.a.</strong></p>'
        f'<p style="color:{TAG["offwhite"]}">Período de acumulação: '
        f'<strong>{idade_apos - 30} anos</strong> (estimando início aos 30)</p>'
        f'<p style="color:{TAG["offwhite"]}">Período de usufruto: '
        f'<strong>{idade_usufruto - idade_apos} anos</strong></p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    if st.button("💾 Salvar Premissas Brasil", type="primary", key="save_brasil"):
        save_data = {
            "selic_media_10a": selic,
            "inflacao_media_10a": inflacao,
            "idade_final_usufruto": idade_usufruto,
            "idade_aposentadoria": idade_apos,
            "aliquota_ir": aliq_ir,
        }
        upsert_premissa("brasil", save_data)
        st.success("✅ Premissas Brasil salvas com sucesso!")
        st.rerun()


# ─────────────────────────────────────────────────────────
# 3. CÁLCULO ATUARIAL - OFFSHORE
# ─────────────────────────────────────────────────────────

def _render_calculo_offshore():
    """Offshore actuarial premissas."""

    data = get_premissa_or_default("offshore", OFFSHORE_DEFAULTS)

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">Premissas de Cálculo — Offshore</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Valores utilizados nos cálculos de planejamento financeiro para investimentos no exterior (em USD)</p></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        risk_free = st.number_input(
            "Taxa Livre de Risco Média 10 Anos (% a.a.)",
            value=float(data.get("taxa_risk_free_10a", OFFSHORE_DEFAULTS["taxa_risk_free_10a"])),
            min_value=0.0, max_value=20.0, step=0.25, format="%.2f",
            key="off_rf",
        )
        idade_usufruto = st.number_input(
            "Idade Final Fase Usufruto",
            value=int(data.get("idade_final_usufruto", OFFSHORE_DEFAULTS["idade_final_usufruto"])),
            min_value=60, max_value=120, step=1,
            key="off_usufruto",
        )
        aliq_ir = st.number_input(
            "Alíquota Imposto de Renda (% sobre rendimento)",
            value=float(data.get("aliquota_ir", OFFSHORE_DEFAULTS["aliquota_ir"])),
            min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
            key="off_ir",
        )
    with col2:
        inflacao = st.number_input(
            "Inflação Média Últimos 10 Anos (% a.a.)",
            value=float(data.get("inflacao_media_10a", OFFSHORE_DEFAULTS["inflacao_media_10a"])),
            min_value=0.0, max_value=20.0, step=0.25, format="%.2f",
            key="off_inflacao",
        )
        idade_apos = st.number_input(
            "Idade Aposentadoria",
            value=int(data.get("idade_aposentadoria", OFFSHORE_DEFAULTS["idade_aposentadoria"])),
            min_value=40, max_value=100, step=1,
            key="off_apos",
        )
        cambio = st.number_input(
            "Câmbio USD/BRL",
            value=float(data.get("cambio_usd_brl", OFFSHORE_DEFAULTS["cambio_usd_brl"])),
            min_value=1.0, max_value=20.0, step=0.1, format="%.2f",
            key="off_cambio",
        )

    # Info card
    retorno_real_usd = risk_free - inflacao
    st.markdown(
        f'<div class="tag-card">'
        f'<p style="color:{TAG["text_muted"]};font-size:0.8rem;margin-bottom:8px">VALORES CALCULADOS</p>'
        f'<p style="color:{TAG["offwhite"]}">Retorno real estimado (USD): '
        f'<strong style="color:{TAG["verde"]}">{retorno_real_usd:.2f}% a.a.</strong></p>'
        f'<p style="color:{TAG["offwhite"]}">Câmbio: '
        f'<strong>USD 1 = R$ {cambio:.2f}</strong></p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.info("ℹ️ Este módulo será integrado com os cálculos de planejamento financeiro offshore.", icon="ℹ️")

    st.markdown("---")
    if st.button("💾 Salvar Premissas Offshore", type="primary", key="save_offshore"):
        save_data = {
            "taxa_risk_free_10a": risk_free,
            "inflacao_media_10a": inflacao,
            "idade_final_usufruto": idade_usufruto,
            "idade_aposentadoria": idade_apos,
            "aliquota_ir": aliq_ir,
            "cambio_usd_brl": cambio,
        }
        upsert_premissa("offshore", save_data)
        st.success("✅ Premissas Offshore salvas com sucesso!")
        st.rerun()


# ─────────────────────────────────────────────────────────
# 4. PREMISSAS SUCESSÓRIO
# ─────────────────────────────────────────────────────────

def _render_sucessorio():
    """Succession premissas: ITCMD by state, attorney fees."""

    data = get_premissa_or_default("sucessorio", SUCESSORIO_DEFAULTS)

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">Premissas Sucessório</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Alíquotas de ITCMD por estado e honorários advocatícios</p></div>',
        unsafe_allow_html=True,
    )

    # Honorários
    st.markdown("### Honorários Advocatícios")
    st.caption("Percentual padrão de honorários advocatícios para processos de inventário")

    honorarios = st.number_input(
        "Honorários Advocatícios (%)",
        value=float(data.get("honorarios_advocaticios", SUCESSORIO_DEFAULTS["honorarios_advocaticios"])),
        min_value=0.0, max_value=30.0, step=0.5, format="%.1f",
        key="honorarios",
    )

    st.markdown("---")

    # ITCMD Table
    st.markdown("### Tabela de ITCMD por Estado")
    st.caption("Alíquotas do Imposto sobre Transmissão Causa Mortis e Doação por unidade federativa")

    itcmd_data = data.get("itcmd_por_estado", SUCESSORIO_DEFAULTS["itcmd_por_estado"])

    # Build editable dataframe
    rows = []
    for uf, info in sorted(itcmd_data.items()):
        if isinstance(info, dict):
            rows.append({"UF": uf, "Estado": info.get("nome", uf), "Alíquota (%)": info.get("aliquota", 4)})
        else:
            rows.append({"UF": uf, "Estado": uf, "Alíquota (%)": info})

    itcmd_df = pd.DataFrame(rows)

    edited_itcmd = st.data_editor(
        itcmd_df,
        column_config={
            "UF": st.column_config.TextColumn("UF", width="small", disabled=True),
            "Estado": st.column_config.TextColumn("Estado", disabled=True),
            "Alíquota (%)": st.column_config.NumberColumn(
                "Alíquota (%)", format="%.0f%%", min_value=0, max_value=20, step=1,
            ),
        },
        use_container_width=True,
        hide_index=True,
        key="itcmd_editor",
    )

    # Quick stats
    avg_itcmd = edited_itcmd["Alíquota (%)"].mean()
    max_itcmd = edited_itcmd["Alíquota (%)"].max()
    min_itcmd = edited_itcmd["Alíquota (%)"].min()

    c1, c2, c3 = st.columns(3)
    c1.metric("Média Nacional", f"{avg_itcmd:.1f}%")
    c2.metric("Maior Alíquota", f"{max_itcmd:.0f}%")
    c3.metric("Menor Alíquota", f"{min_itcmd:.0f}%")

    st.markdown("---")
    if st.button("💾 Salvar Premissas Sucessório", type="primary", key="save_sucessorio"):
        # Rebuild ITCMD dict from edited dataframe
        itcmd_dict = {}
        for _, row in edited_itcmd.iterrows():
            itcmd_dict[row["UF"]] = {
                "nome": row["Estado"],
                "aliquota": row["Alíquota (%)"],
            }

        save_data = {
            "honorarios_advocaticios": honorarios,
            "itcmd_por_estado": itcmd_dict,
        }
        upsert_premissa("sucessorio", save_data)
        st.success("✅ Premissas Sucessório salvas com sucesso!")
        st.rerun()


# ─────────────────────────────────────────────────────────
# 5. CENÁRIO MACROECONÔMICO
# ─────────────────────────────────────────────────────────

def _render_cenario_macro():
    """Macro scenario bullets for Brazil and Global."""

    data = get_premissa_or_default("cenario_macro", CENARIO_MACRO_DEFAULTS)

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">Cenário Macroeconômico</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Bullet points do cenário macro (máximo 3 por cenário)</p></div>',
        unsafe_allow_html=True,
    )

    # ── Brazil Scenario ──
    st.markdown(f'### 🇧🇷 Cenário Brasil')

    brasil_bullets = data.get("brasil", CENARIO_MACRO_DEFAULTS["brasil"])
    # Ensure we have 3 slots
    while len(brasil_bullets) < 3:
        brasil_bullets.append("")

    br_inputs = []
    for i in range(3):
        val = st.text_area(
            f"Bullet {i+1} — Brasil",
            value=brasil_bullets[i] if i < len(brasil_bullets) else "",
            height=80,
            key=f"macro_br_{i}",
        )
        br_inputs.append(val)

    st.markdown("---")

    # ── Global Scenario ──
    st.markdown(f'### 🌍 Cenário Global')

    global_bullets = data.get("global", CENARIO_MACRO_DEFAULTS["global"])
    while len(global_bullets) < 3:
        global_bullets.append("")

    gl_inputs = []
    for i in range(3):
        val = st.text_area(
            f"Bullet {i+1} — Global",
            value=global_bullets[i] if i < len(global_bullets) else "",
            height=80,
            key=f"macro_gl_{i}",
        )
        gl_inputs.append(val)

    # Preview cards
    st.markdown("---")
    st.markdown("#### Preview")

    col1, col2 = st.columns(2)
    with col1:
        html_br = f'<div class="tag-card"><h3 style="color:{TAG["azul"]}">🇧🇷 Brasil</h3><ol style="color:{TAG["offwhite"]};font-size:0.9rem">'
        for b in br_inputs:
            if b.strip():
                html_br += f'<li style="margin-bottom:8px">{b}</li>'
        html_br += "</ol></div>"
        st.markdown(html_br, unsafe_allow_html=True)

    with col2:
        html_gl = f'<div class="tag-card"><h3 style="color:{TAG["verde"]}">🌍 Global</h3><ol style="color:{TAG["offwhite"]};font-size:0.9rem">'
        for b in gl_inputs:
            if b.strip():
                html_gl += f'<li style="margin-bottom:8px">{b}</li>'
        html_gl += "</ol></div>"
        st.markdown(html_gl, unsafe_allow_html=True)

    st.markdown("---")
    if st.button("💾 Salvar Cenário Macro", type="primary", key="save_macro"):
        save_data = {
            "brasil": [b for b in br_inputs if b.strip()],
            "global": [b for b in gl_inputs if b.strip()],
        }
        upsert_premissa("cenario_macro", save_data)
        st.success("✅ Cenário Macro salvo com sucesso!")
        st.rerun()


# ─────────────────────────────────────────────────────────
# 6. TEXTOS DO PLANEJAMENTO
# ─────────────────────────────────────────────────────────

def _render_textos_planejamento():
    """Editable texts for financial planning phases."""

    data = get_premissa_or_default("textos_planejamento", TEXTOS_PLANEJAMENTO_DEFAULTS)

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">Textos do Planejamento</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Textos exibidos nas páginas de planejamento financeiro das propostas</p></div>',
        unsafe_allow_html=True,
    )

    phases = [
        ("contribuicao", "Contribuição", "Texto sobre a fase de contribuição (construção de patrimônio)..."),
        ("acumulacao", "Acumulação", "Texto sobre a fase de acumulação (crescimento)..."),
        ("sucessao", "Sucessão", "Texto sobre a fase de sucessão (transferência)..."),
        ("pgbl", "PGBL", "Texto sobre a dedução fiscal via PGBL..."),
    ]

    inputs = {}
    for key, label, placeholder in phases:
        st.markdown(f"#### {label}")
        inputs[key] = st.text_area(
            f"Texto — {label}",
            value=data.get(key, TEXTOS_PLANEJAMENTO_DEFAULTS.get(key, "")),
            placeholder=placeholder,
            height=100,
            key=f"texto_{key}",
            label_visibility="collapsed",
        )

    st.markdown("---")
    if st.button("💾 Salvar Textos", type="primary", key="save_textos"):
        upsert_premissa("textos_planejamento", inputs)
        st.success("✅ Textos do planejamento salvos com sucesso!")
        st.rerun()


# ─────────────────────────────────────────────────────────
# 7. CLASSES DE ATIVOS
# ─────────────────────────────────────────────────────────

def _render_classes_ativos():
    """Asset class definitions and objectives."""

    data = get_premissa_or_default("classes_ativos", CLASSES_ATIVOS_DEFAULTS)

    st.markdown(
        f'<div class="tag-card"><h3 style="color:{TAG["laranja"]}">Classes de Ativos</h3>'
        f'<p style="color:{TAG["text_muted"]};font-size:0.85rem">'
        f'Gerencie as classes disponíveis para categorizar ativos</p></div>',
        unsafe_allow_html=True,
    )

    # Ensure data is a list
    if isinstance(data, dict):
        data = CLASSES_ATIVOS_DEFAULTS

    classes_df = pd.DataFrame(data)
    if "ordem" not in classes_df.columns:
        classes_df.insert(0, "ordem", range(1, len(classes_df) + 1))

    edited_classes = st.data_editor(
        classes_df,
        column_config={
            "ordem": st.column_config.NumberColumn("Ordem", min_value=1, step=1, width="small"),
            "nome": st.column_config.TextColumn("Nome da Classe", width="medium"),
            "objetivo": st.column_config.TextColumn("Objetivo", width="large"),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="classes_editor",
    )

    # Visual preview
    st.markdown("---")
    st.markdown("#### Preview das Classes")

    chart_colors = TAG["chart"]
    for i, (_, row) in enumerate(edited_classes.iterrows()):
        color = chart_colors[i % len(chart_colors)]
        st.markdown(
            f'<div style="background:{TAG["bg_card"]};border-left:4px solid {color};'
            f'border-radius:8px;padding:12px 16px;margin-bottom:8px">'
            f'<strong style="color:{color}">{row.get("nome", "")}</strong>'
            f'<p style="color:{TAG["text_muted"]};font-size:0.82rem;margin:4px 0 0 0">'
            f'{row.get("objetivo", "")}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.button("💾 Salvar Classes de Ativos", type="primary", key="save_classes"):
        records = edited_classes.to_dict("records")
        upsert_premissa("classes_ativos", records)
        st.success("✅ Classes de ativos salvas com sucesso!")
        st.rerun()
