"""
Tela 3: Proposta com IA
AI-powered proposal generation with model selection and restriction application.
Supports rich model portfolios with asset classes, subcategories, and min/max bands.
"""
import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from shared.brand import TAG, PLOTLY_LAYOUT, fmt_brl, fmt_pct, render_step_indicator
from shared.fund_utils import load_liquidation_data
from shared.portfolio_utils import parse_model_portfolio
from database.models import (
    list_prospects, get_prospect, create_proposta, update_proposta,
    get_proposta, list_propostas,
)
from ai.client import is_ai_available, render_api_key_input
from ai.diagnostico import generate_diagnostico
from ai.recomendacao import generate_recomendacao, generate_texto_recomendacao


MODELOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modelos_carteira")

# Mapping perfil to expected file name
PERFIL_FILE_MAP = {
    "Conservador": "conservador",
    "Moderado": "moderado",
    "Arrojado": "agressivo",
    "Agressivo": "agressivo",
    "Renda Fixa": "renda_fixa",
}


def _load_modelos_disponiveis():
    """Load available model portfolios from files.
    Returns dict: {nome: {df: DataFrame, records: list, is_rich: bool}}
    """
    modelos = {}
    if not os.path.exists(MODELOS_DIR):
        return modelos

    for f in os.listdir(MODELOS_DIR):
        if not f.endswith((".xlsx", ".xls")):
            continue
        if f.startswith("_"):  # skip master file
            continue

        nome = os.path.splitext(f)[0].replace("_", " ").title()
        path = os.path.join(MODELOS_DIR, f)
        try:
            df = parse_model_portfolio(path)
            is_rich = "Classe" in df.columns
            modelos[nome] = {
                "df": df,
                "records": df.to_dict(orient="records"),
                "is_rich": is_rich,
                "filename": f,
            }
        except Exception:
            pass

    return modelos


def _render_modelo_rico(df):
    """Render a rich model portfolio with classes and bands as a styled table."""
    if df.empty:
        return

    # Group by Classe for a more visual display
    display_df = df.copy()

    # Format columns
    col_config = {
        "% Alvo": st.column_config.NumberColumn("% Alvo", format="%.1f%%"),
    }
    if "Min %" in display_df.columns:
        col_config["Min %"] = st.column_config.NumberColumn("Min", format="%.0f%%")
    if "Max %" in display_df.columns:
        col_config["Max %"] = st.column_config.NumberColumn("Max", format="%.0f%%")

    # Remove Codigo if empty
    if "Codigo" in display_df.columns and (display_df["Codigo"] == "").all():
        display_df = display_df.drop(columns=["Codigo"])

    st.dataframe(
        display_df,
        use_container_width=True,
        height=min(400, 35 * len(display_df) + 40),
        column_config=col_config,
        hide_index=True,
    )

    # Show total
    total = display_df["% Alvo"].sum()
    st.caption(f"Total: **{total:.1f}%** | {len(display_df)} ativos com alocacao")


def _suggest_modelo_for_perfil(modelos, perfil):
    """Suggest the best model based on prospect profile."""
    if not perfil or not modelos:
        return None

    perfil_key = PERFIL_FILE_MAP.get(perfil, "").replace("_", " ").title()
    if perfil_key in modelos:
        return perfil_key

    # Fuzzy match
    perfil_lower = perfil.lower()
    for nome in modelos:
        if perfil_lower in nome.lower():
            return nome

    return None


def _build_donut_chart(labels, values, title=""):
    """Create a consistent donut chart."""
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=10, color=TAG["offwhite"]),
        marker=dict(
            colors=TAG["chart"],
            line=dict(color=TAG["bg_dark"], width=1),
        ),
    ))
    layout = dict(PLOTLY_LAYOUT)
    layout["height"] = 380
    layout["showlegend"] = False
    if title:
        layout["title"] = dict(text=title, font=dict(color=TAG["offwhite"], size=14))
    fig.update_layout(**layout)
    return fig


def render_proposta_ia():
    st.title("Proposta com IA")

    # AI status
    render_api_key_input()

    # ── Select prospect ──
    prospects = list_prospects()
    if not prospects:
        st.warning("Nenhum prospect cadastrado. Va para 'Cadastro' primeiro.")
        return

    # Filter prospects with portfolio data
    prospects_with_data = [p for p in prospects if p.get("carteira_dados")]
    if not prospects_with_data:
        st.warning("Nenhum prospect tem carteira cadastrada. Va para 'Carteira Atual' primeiro.")
        return

    names = [f"{p['nome']} - {p.get('perfil_investidor', 'N/A')}" for p in prospects_with_data]
    sel_idx = st.selectbox("Selecionar prospect", range(len(names)), format_func=lambda i: names[i])
    prospect = get_prospect(prospects_with_data[sel_idx]["id"])

    # Load carteira
    try:
        carteira_data = json.loads(prospect["carteira_dados"]) if isinstance(prospect["carteira_dados"], str) else prospect["carteira_dados"]
    except Exception:
        st.error("Erro ao carregar carteira do prospect.")
        return

    # Step indicator
    steps = ["Perfil", "Modelo Base", "IA Analisa", "Revisao", "Aprovacao"]
    current_step = st.session_state.get("proposta_step", 0)
    st.markdown(render_step_indicator(steps, current_step), unsafe_allow_html=True)

    st.markdown("---")

    # ── STEP 1: Show prospect profile ──
    st.subheader("1. Perfil do Prospect")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patrimonio", fmt_brl(prospect.get("patrimonio_investivel", 0)))
    with col2:
        st.metric("Perfil", prospect.get("perfil_investidor", "N/A"))
    with col3:
        st.metric("Horizonte", prospect.get("horizonte_investimento", "N/A"))
    with col4:
        st.metric("Ativos Atuais", len(carteira_data))

    # Show restrictions
    restricoes = prospect.get("restricoes", [])
    if isinstance(restricoes, str):
        try:
            restricoes = json.loads(restricoes)
        except Exception:
            restricoes = [restricoes] if restricoes else []

    if restricoes:
        restricoes_str = ", ".join(restricoes) if isinstance(restricoes, list) else str(restricoes)
        st.markdown(f"**Restricoes:** {restricoes_str}")
    if prospect.get("restricoes_texto"):
        st.markdown(f"**Restricoes adicionais:** {prospect['restricoes_texto']}")
    if prospect.get("objetivos"):
        obj = prospect["objetivos"]
        if isinstance(obj, str):
            try:
                obj = json.loads(obj)
            except Exception:
                obj = [obj]
        if obj:
            st.markdown(f"**Objetivos:** {', '.join(obj) if isinstance(obj, list) else obj}")

    st.markdown("---")

    # ── STEP 2: Select model portfolio ──
    st.subheader("2. Carteira Modelo Base")

    modelos = _load_modelos_disponiveis()

    tab_file, tab_upload, tab_manual = st.tabs([
        "Modelos TAG (Salvos)", "Upload de Modelo", "Modelo Manual",
    ])

    modelo_base = None
    modelo_nome = None

    with tab_file:
        if modelos:
            # Auto-suggest based on profile
            suggested = _suggest_modelo_for_perfil(modelos, prospect.get("perfil_investidor"))
            modelo_keys = list(modelos.keys())
            default_idx = modelo_keys.index(suggested) if suggested and suggested in modelo_keys else 0

            modelo_sel = st.selectbox(
                "Selecionar modelo",
                modelo_keys,
                index=default_idx,
                key="modelo_selector",
            )

            if suggested and modelo_sel == suggested:
                st.success(f"Modelo '{modelo_sel}' sugerido automaticamente para perfil {prospect.get('perfil_investidor', '')}")

            modelo_info = modelos[modelo_sel]
            modelo_nome = modelo_sel

            # Display the model with rich formatting
            if modelo_info["is_rich"]:
                _render_modelo_rico(modelo_info["df"])
            else:
                st.dataframe(
                    modelo_info["df"],
                    use_container_width=True,
                    height=min(400, 35 * len(modelo_info["df"]) + 40),
                    hide_index=True,
                )

            modelo_base = modelo_info["records"]
        else:
            st.info(f"Nenhum modelo encontrado em `modelos_carteira/`. Faca upload ou use modelo manual.")

    with tab_upload:
        uploaded_model = st.file_uploader(
            "Faca upload de um arquivo Excel com a carteira modelo",
            type=["xlsx", "xls"],
            key="model_upload",
        )
        if uploaded_model:
            try:
                model_df = parse_model_portfolio(uploaded_model)
                modelo_base = model_df.to_dict(orient="records")
                modelo_nome = uploaded_model.name
                if "Classe" in model_df.columns:
                    _render_modelo_rico(model_df)
                else:
                    st.dataframe(model_df, use_container_width=True, hide_index=True)
                st.success(f"Modelo importado: {len(modelo_base)} ativos")
            except Exception as e:
                st.error(f"Erro: {e}")

    with tab_manual:
        st.markdown("Defina o modelo manualmente:")
        default_model = pd.DataFrame([
            {"Classe": "", "Ativo": "", "% Alvo": 0.0},
        ])
        edited_model = st.data_editor(
            default_model,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "% Alvo": st.column_config.NumberColumn("% Alvo", format="%.1f%%"),
            },
            key="manual_model_editor",
        )
        if st.button("Usar este modelo", key="btn_use_manual"):
            valid = edited_model[edited_model["% Alvo"] > 0]
            if not valid.empty:
                modelo_base = valid.to_dict(orient="records")
                modelo_nome = "Manual"
                st.success(f"Modelo definido com {len(modelo_base)} ativos")

    if not modelo_base:
        st.info("Selecione ou defina um modelo para continuar.")
        return

    st.markdown("---")

    # ── STEP 3: AI generates proposal ──
    st.subheader("3. Gerar Proposta com IA")

    ai_available = is_ai_available()
    if not ai_available:
        st.warning("API Key nao configurada. A proposta sera gerada com diagnostico basico (sem IA).")

    if st.button("Gerar Proposta", type="primary", use_container_width=True):
        with st.spinner("Analisando carteira e gerando proposta personalizada..."):
            st.session_state["proposta_step"] = 2

            # Generate diagnostic
            from pages_proposta.p2_carteira_atual import _compute_diagnostico
            liquid_df = load_liquidation_data()
            carteira_df = pd.DataFrame(carteira_data)
            diag_metricas = _compute_diagnostico(carteira_df, liquid_df)

            diagnostico_texto = generate_diagnostico(prospect, carteira_data, diag_metricas)

            # Generate recommendation (pass rich model data)
            recomendacao = generate_recomendacao(prospect, carteira_data, modelo_base)

            # Generate recommendation text
            rec_texto = generate_texto_recomendacao(prospect, recomendacao, diagnostico_texto)

            carteira_proposta = recomendacao.get("carteira_proposta", [])

            # ── Enrich proposed portfolio with fund catalog + R$ values ──
            patrimonio = float(prospect.get("patrimonio_investivel", 0))
            try:
                from shared.fund_catalog import match_fund_catalog
                for item in carteira_proposta:
                    name = item.get("ativo", item.get("Ativo", ""))
                    catalog = match_fund_catalog(name)
                    if catalog:
                        item.setdefault("instituicao", catalog.get("gestor", ""))
                        item.setdefault("resgate", catalog.get("resgate", ""))
                        item.setdefault("retorno_alvo", catalog.get("retorno_alvo", ""))
                        item.setdefault("retorno_12m", catalog.get("retorno_12m", 0))
                        item.setdefault("volatilidade", catalog.get("volatilidade", 0))
                        item.setdefault("risco_principal", catalog.get("risco_principal", ""))
                        item.setdefault("horizonte_minimo", catalog.get("horizonte_minimo", ""))
                        item.setdefault("tipo_fundo", catalog.get("tipo", ""))
                        item.setdefault("subtipo_fundo", catalog.get("subtipo", ""))
                        item.setdefault("estrategia_descricao", catalog.get("estrategia", ""))

                    # Calculate R$ value
                    pct = float(item.get("pct_alvo", item.get("% Alvo", 0)))
                    if patrimonio > 0 and pct > 0:
                        item["proposta_rs"] = round(patrimonio * pct / 100, 2)
                    else:
                        item.setdefault("proposta_rs", 0)

                    # Default action
                    item.setdefault("acao_recomendada", "Aplicar")
            except Exception:
                pass

            # ── Build fund cards data from catalog ──
            fundos_sugeridos = []
            try:
                from shared.fund_catalog import match_fund_catalog as _mfc
                for item in carteira_proposta:
                    name = item.get("ativo", item.get("Ativo", ""))
                    catalog = _mfc(name)
                    card = {
                        "nome": name,
                        "pct_alvo": item.get("pct_alvo", item.get("% Alvo", 0)),
                        "proposta_rs": item.get("proposta_rs", 0),
                        "classe": item.get("classe", item.get("Classe", "")),
                    }
                    if catalog:
                        card.update({
                            "tipo": catalog.get("tipo", ""),
                            "subtipo": catalog.get("subtipo", ""),
                            "gestor": catalog.get("gestor", ""),
                            "estrategia": catalog.get("estrategia", ""),
                            "resgate": catalog.get("resgate", ""),
                            "retorno_alvo": catalog.get("retorno_alvo", ""),
                            "retorno_12m": catalog.get("retorno_12m", 0),
                            "volatilidade": catalog.get("volatilidade", 0),
                            "risco_principal": catalog.get("risco_principal", ""),
                            "horizonte_minimo": catalog.get("horizonte_minimo", ""),
                            "isento_ir": catalog.get("isento_ir", False),
                        })
                    fundos_sugeridos.append(card)
            except Exception:
                pass

            # ── Build proposta comercial from prospect fee data ──
            fee_data = prospect.get("fee_negociada", {})
            if not isinstance(fee_data, dict):
                fee_data = {}
            proposta_comercial = {
                "fee_table": [
                    {"faixa": "Ate R$ 500.000.000,00", "taxa_adm": fee_data.get("taxa_ate_500m", 0.25)},
                    {"faixa": "Acima de R$ 500.000.001,00", "taxa_adm": fee_data.get("taxa_acima_500m", 0.20)},
                ],
                "taxa_performance": fee_data.get("taxa_performance", 0),
                "servicos": fee_data.get("servicos", [
                    "Gestao de investimentos",
                    "Planejamento sucessorio",
                    "Consolidacao patrimonial",
                ]),
                "condicoes_especiais": fee_data.get("condicoes_especiais", ""),
            }

            # ── Enhanced analytics (15-section proposal) ──
            analytics = {}
            bottom_up = []
            section_texts = {}

            try:
                from shared.analytics import (
                    compute_allocation_comparison, compute_risk_analysis,
                    classify_assets_bottom_up, compute_efficiency_analysis,
                    compute_liquidity_comparison, compute_tax_analysis,
                    compute_concentration_by_institution, compute_maturity_ladder,
                )

                analytics["allocation"] = compute_allocation_comparison(
                    carteira_data, carteira_proposta, modelo_base)
                analytics["risk"] = compute_risk_analysis(carteira_data, liquid_df)
                analytics["liquidity"] = compute_liquidity_comparison(
                    carteira_data, carteira_proposta, liquid_df)
                analytics["tax"] = compute_tax_analysis(carteira_data, carteira_proposta)
                analytics["concentration"] = compute_concentration_by_institution(carteira_data)
                analytics["maturity"] = compute_maturity_ladder(carteira_data)
            except Exception as e:
                analytics["_error"] = str(e)

            try:
                bottom_up = classify_assets_bottom_up(carteira_data, carteira_proposta)
                analytics["bottom_up"] = bottom_up
            except Exception:
                pass

            # Generate AI section texts (now includes batches 4-6)
            try:
                from ai.sections import generate_all_section_texts
                section_texts = generate_all_section_texts(
                    prospect, carteira_data, carteira_proposta,
                    diagnostico_texto, rec_texto, analytics, modelo_base)
            except Exception:
                pass

            # ── Build politica_investimentos from section texts ──
            politica_investimentos = {
                "texto": section_texts.get("politica_investimentos_texto", ""),
                "governanca": section_texts.get("governanca_texto", ""),
                "perfil": prospect.get("perfil_investidor", "Moderado"),
            }
            try:
                from shared.tag_institucional import LIMITES_POLITICA_DEFAULT
                politica_investimentos["limites"] = LIMITES_POLITICA_DEFAULT.get(
                    prospect.get("perfil_investidor", "Moderado"),
                    LIMITES_POLITICA_DEFAULT.get("Moderado", {}),
                )
            except Exception:
                pass

            # Save proposta with all data (v3 with full PPTX coverage)
            proposta_id = create_proposta(prospect["id"], {
                "perfil_modelo": modelo_nome or prospect.get("perfil_investidor", ""),
                "modelo_dados": modelo_base,
                "restricoes_aplicadas": restricoes if isinstance(restricoes, list) else [],
                "diagnostico_texto": diagnostico_texto,
                "diagnostico_dados": diag_metricas,
                "recomendacao_texto": rec_texto,
                "carteira_proposta": carteira_proposta,
                "status": "Rascunho",
                "analytics_data": analytics,
                "section_texts": section_texts,
                "bottom_up_classification": bottom_up,
                "politica_investimentos": politica_investimentos,
                "fundos_sugeridos": fundos_sugeridos,
                "proposta_comercial": proposta_comercial,
            })

            st.session_state["current_proposta_id"] = proposta_id
            st.session_state["proposta_step"] = 3

        st.rerun()

    # ── STEP 4: Review and edit ──
    proposta_id = st.session_state.get("current_proposta_id")
    if not proposta_id:
        # Check for existing propostas
        existing = list_propostas(prospect["id"])
        if existing:
            st.markdown("---")
            st.subheader("Propostas Existentes")
            for prop in existing:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.markdown(f"**Versao {prop.get('versao', '?')}** - {prop.get('status', '')}")
                with col2:
                    st.caption(str(prop.get("created_at", ""))[:10])
                with col3:
                    if st.button("Carregar", key=f"load_prop_{prop['id']}"):
                        st.session_state["current_proposta_id"] = prop["id"]
                        st.session_state["proposta_step"] = 3
                        st.rerun()
        return

    proposta = get_proposta(proposta_id)
    if not proposta:
        return

    st.markdown("---")
    st.subheader("4. Revisao da Proposta")

    # Diagnostic
    with st.expander("Diagnostico da Carteira Atual", expanded=True):
        diag_text = proposta.get("diagnostico_texto", "Sem diagnostico")
        st.markdown(diag_text)

    # Recommendation text
    with st.expander("Recomendacao", expanded=True):
        rec_texto = st.text_area(
            "Texto da recomendacao (editavel pela gestao)",
            value=proposta.get("recomendacao_texto", ""),
            height=200,
            key="rec_text_edit",
        )

    # Proposed portfolio
    with st.expander("Carteira Proposta", expanded=True):
        cart_prop = proposta.get("carteira_proposta", [])
        if isinstance(cart_prop, str):
            try:
                cart_prop = json.loads(cart_prop)
            except Exception:
                cart_prop = []

        if cart_prop:
            prop_df = pd.DataFrame(cart_prop)

            # Show editable table
            col_config_prop = {}
            if "pct_alvo" in prop_df.columns:
                col_config_prop["pct_alvo"] = st.column_config.NumberColumn("% Alvo", format="%.1f%%")
            if "% Alvo" in prop_df.columns:
                col_config_prop["% Alvo"] = st.column_config.NumberColumn("% Alvo", format="%.1f%%")

            edited_prop = st.data_editor(
                prop_df,
                use_container_width=True,
                column_config=col_config_prop,
                hide_index=True,
                key="proposta_editor",
            )

            # Total check
            pct_col_name = "pct_alvo" if "pct_alvo" in edited_prop.columns else "% Alvo"
            if pct_col_name in edited_prop.columns:
                total_pct = edited_prop[pct_col_name].sum()
                if abs(total_pct - 100) > 0.5:
                    st.warning(f"Total da alocacao: {total_pct:.1f}% (deveria ser 100%)")
                else:
                    st.caption(f"Total: {total_pct:.1f}%")

            # Comparison chart: Atual vs Proposta
            st.markdown("### Comparativo: Atual vs Proposta")
            col1, col2 = st.columns(2)

            with col1:
                if carteira_data:
                    cart_df = pd.DataFrame(carteira_data)
                    if "Financeiro" in cart_df.columns:
                        total = cart_df["Financeiro"].sum()
                        if total > 0:
                            cart_df["pct"] = cart_df["Financeiro"] / total * 100
                            fig = _build_donut_chart(
                                cart_df["Ativo"].str[:25].tolist(),
                                cart_df["pct"].tolist(),
                                "Carteira Atual",
                            )
                            st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Build donut from proposed
                prop_labels = []
                prop_values = []
                for item in cart_prop:
                    name = item.get("ativo", item.get("Ativo", ""))[:25]
                    pct = item.get("pct_alvo", item.get("% Alvo", 0))
                    if pct > 0:
                        prop_labels.append(name)
                        prop_values.append(pct)

                if prop_labels:
                    fig = _build_donut_chart(prop_labels, prop_values, "Carteira Proposta TAG")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma carteira proposta disponivel.")

    # ── Actions ──
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Salvar Rascunho", use_container_width=True):
            update_data = {
                "recomendacao_texto": rec_texto,
                "status": "Rascunho",
            }
            if cart_prop and "edited_prop" in dir():
                update_data["carteira_proposta"] = edited_prop.to_dict(orient="records")
            update_proposta(proposta_id, update_data)
            st.success("Rascunho salvo!")

    with col2:
        if st.button("Enviar para Revisao", type="primary", use_container_width=True):
            update_proposta(proposta_id, {
                "recomendacao_texto": rec_texto,
                "status": "Revisao",
            })
            from database.models import update_prospect
            update_prospect(prospect["id"], {"status": "Proposta Enviada"})
            st.success("Proposta enviada para revisao!")
            st.session_state["proposta_step"] = 4

    with col3:
        if st.button("Aprovar Proposta", use_container_width=True):
            update_proposta(proposta_id, {"status": "Aprovada"})
            st.success("Proposta aprovada! Va para 'Visualizar Proposta' para gerar o HTML.")
            st.session_state["proposta_step"] = 4
