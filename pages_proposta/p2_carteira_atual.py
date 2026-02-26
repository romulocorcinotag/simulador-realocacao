"""
Tela 2: Carteira Atual do Prospect
Upload, diagnostic and analysis of the prospect's current portfolio.
"""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from shared.brand import TAG, PLOTLY_LAYOUT, fmt_brl, fmt_pct
from shared.fund_utils import load_liquidation_data, find_col, match_fund_liquidation
from shared.portfolio_utils import parse_portfolio_file
from database.models import list_prospects, get_prospect, update_prospect


def _compute_diagnostico(carteira_df, liquid_df):
    """Compute portfolio diagnostic metrics."""
    if carteira_df is None or carteira_df.empty:
        return {}

    total = carteira_df["Financeiro"].sum()
    if total == 0:
        return {}

    carteira_df = carteira_df.copy()
    carteira_df["% PL"] = carteira_df["Financeiro"] / total * 100

    # Concentration (HHI)
    hhi = (carteira_df["% PL"] ** 2).sum()
    hhi_normalized = (hhi - 10000 / len(carteira_df)) / (10000 - 10000 / len(carteira_df)) if len(carteira_df) > 1 else 1

    # Top 3 concentration
    top3_pct = carteira_df.nlargest(3, "% PL")["% PL"].sum()

    # Liquidity analysis
    liq_buckets = {"D+0-1": 0, "D+2-5": 0, "D+6-30": 0, "D+30+": 0}
    total_cost = 0
    matched_count = 0

    for _, row in carteira_df.iterrows():
        code = str(row.get("Código", ""))
        name = str(row.get("Ativo", ""))
        fin = row["Financeiro"]

        liq_info = match_fund_liquidation(name, code, liquid_df)
        if liq_info is not None:
            d_total = int(liq_info.get("Conversão Resgate", 0)) + int(liq_info.get("Liquid. Resgate", 0))
            if d_total <= 1:
                liq_buckets["D+0-1"] += fin
            elif d_total <= 5:
                liq_buckets["D+2-5"] += fin
            elif d_total <= 30:
                liq_buckets["D+6-30"] += fin
            else:
                liq_buckets["D+30+"] += fin
            matched_count += 1
        else:
            liq_buckets["D+30+"] += fin

    # Convert to percentages
    for k in liq_buckets:
        liq_buckets[k] = liq_buckets[k] / total * 100 if total > 0 else 0

    # Categories
    categorias = {}
    for _, row in carteira_df.iterrows():
        cat = str(row.get("Categoria", row.get("Estratégia", "Outros")))
        if not cat or cat == "nan":
            cat = "Outros"
        categorias[cat] = categorias.get(cat, 0) + row["Financeiro"]

    return {
        "total_pl": total,
        "num_ativos": len(carteira_df),
        "hhi": hhi,
        "hhi_normalized": hhi_normalized,
        "top3_pct": top3_pct,
        "liq_buckets": liq_buckets,
        "categorias": {k: v / total * 100 for k, v in categorias.items()},
        "categorias_abs": categorias,
        "matched_funds": matched_count,
    }


def render_carteira_atual():
    st.title("Carteira Atual do Prospect")

    # ── Select prospect ──
    prospects = list_prospects()
    if not prospects:
        st.warning("Nenhum prospect cadastrado. Vá para 'Cadastro de Prospect' primeiro.")
        return

    prospect_names = [f"{p['nome']} - {p['perfil_investidor']} ({fmt_brl(p['patrimonio_investivel'])})" for p in prospects]
    selected_idx = st.selectbox("Selecionar prospect", range(len(prospect_names)), format_func=lambda i: prospect_names[i])
    prospect = get_prospect(prospects[selected_idx]["id"])

    st.markdown("---")

    # ── Upload or manual entry ──
    tab_upload, tab_proposta, tab_manual = st.tabs([
        "Upload Posicao Projetada", "Upload Proposta TAG", "Preenchimento Manual",
    ])

    carteira_df = None

    with tab_upload:
        uploaded = st.file_uploader(
            "Upload da posicao atual do prospect (formato Posicao Projetada)",
            type=["xlsx", "xls"],
            key="carteira_upload",
        )

        if uploaded:
            try:
                sheets = parse_portfolio_file(uploaded)
                if "ativos" in sheets:
                    ativos_df = sheets["ativos"]
                    cod_col = find_col(ativos_df, "COD. ATIVO", "COD. ATIVO")
                    name_col = find_col(ativos_df, "ATIVO", "NOME")
                    fin_col = find_col(ativos_df, "FINANCEIRO", "VALOR")
                    strat_col = find_col(ativos_df, "ESTRATEGIA", "ESTRATEGIA", "CATEGORIA")

                    rows = []
                    for _, row in ativos_df.iterrows():
                        fin = float(row.get(fin_col, 0)) if fin_col else 0
                        if fin > 0:
                            rows.append({
                                "Codigo": str(row[cod_col]) if cod_col else "",
                                "Ativo": str(row[name_col]) if name_col else "",
                                "Financeiro": fin,
                                "Estrategia": str(row[strat_col]) if strat_col else "",
                            })
                    carteira_df = pd.DataFrame(rows)
                    st.success(f"Carteira importada: {len(carteira_df)} ativos")
                else:
                    df = pd.read_excel(uploaded)
                    st.dataframe(df, use_container_width=True)
                    st.info("Formato nao reconhecido automaticamente. Use outra aba.")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

    with tab_proposta:
        st.markdown("Upload no formato de proposta TAG (multi-sheet, multi-banco)")
        uploaded_prop = st.file_uploader(
            "Upload da proposta TAG (Excel)",
            type=["xlsx", "xls"],
            key="proposta_upload",
        )

        if uploaded_prop:
            try:
                from shared.proposal_parser import (
                    parse_proposal_excel, portfolio_to_standard_format,
                    build_category_summary,
                )
                import tempfile, os

                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(uploaded_prop.read())
                    tmp_path = tmp.name

                parsed = parse_proposal_excel(tmp_path)
                os.unlink(tmp_path)

                # Show detected structure
                structure = parsed["structure"]
                clients = structure["clients"]

                if clients:
                    st.success(f"Detectados {len(clients)} cliente(s): {', '.join(clients.keys())}")

                    # Let user select client
                    client_names = list(clients.keys())
                    if len(client_names) > 1:
                        client_sel = st.selectbox("Selecionar cliente", client_names, key="prop_client_sel")
                    else:
                        client_sel = client_names[0]

                    # Get client portfolio
                    client_data = parsed["clients"].get(client_sel, {})
                    source = client_data.get("consolidated") or next(iter(client_data.get("banks", {}).values()), None)

                    if source:
                        assets_df = source["assets"]
                        if not assets_df.empty:
                            # Show category summary
                            cat_summary = build_category_summary(assets_df)
                            if not cat_summary.empty:
                                st.markdown("**Resumo por Categoria:**")
                                st.dataframe(
                                    cat_summary[["categoria", "saldo_atual", "proposta_valor", "pct_atual", "proposta_pct", "delta_pct", "num_ativos"]].rename(columns={
                                        "categoria": "Categoria", "saldo_atual": "Atual R$",
                                        "proposta_valor": "Proposta R$", "pct_atual": "% Atual",
                                        "proposta_pct": "% Proposta", "delta_pct": "Delta %",
                                        "num_ativos": "# Ativos",
                                    }).style.format({
                                        "Atual R$": "R$ {:,.0f}", "Proposta R$": "R$ {:,.0f}",
                                        "% Atual": "{:.1%}", "% Proposta": "{:.1%}", "Delta %": "{:+.1%}",
                                    }),
                                    use_container_width=True,
                                    hide_index=True,
                                )

                            # Convert to standard format
                            records = portfolio_to_standard_format(assets_df)
                            carteira_df = pd.DataFrame([{
                                "Codigo": "",
                                "Ativo": r["Ativo"],
                                "Financeiro": r["Financeiro"],
                                "Categoria": r.get("Categoria", ""),
                            } for r in records if r["Financeiro"] > 0])

                            st.success(f"Importados {len(carteira_df)} ativos de {client_sel}")
                        else:
                            st.warning("Nenhum ativo encontrado para este cliente.")
                else:
                    st.warning("Dados nao encontrados para este cliente.")

            except Exception as e:
                st.error(f"Erro ao processar proposta: {e}")
                import traceback
                st.code(traceback.format_exc())

    with tab_manual:
        st.markdown("Preencha a carteira atual do prospect:")

        # Init or load existing data
        if prospect.get("carteira_dados"):
            try:
                existing = json.loads(prospect["carteira_dados"]) if isinstance(prospect["carteira_dados"], str) else prospect["carteira_dados"]
                default_df = pd.DataFrame(existing)
            except Exception:
                default_df = pd.DataFrame(columns=["Código", "Ativo", "Financeiro", "Estratégia"])
        else:
            default_df = pd.DataFrame(columns=["Código", "Ativo", "Financeiro", "Estratégia"])

        if default_df.empty:
            default_df = pd.DataFrame([
                {"Código": "", "Ativo": "", "Financeiro": 0.0, "Estratégia": ""},
            ])

        edited = st.data_editor(
            default_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Código": st.column_config.TextColumn("Código"),
                "Ativo": st.column_config.TextColumn("Ativo"),
                "Financeiro": st.column_config.NumberColumn("Financeiro (R$)", format="R$ %.2f"),
                "Estratégia": st.column_config.TextColumn("Estratégia/Categoria"),
            },
        )

        if st.button("Usar esta carteira", type="primary"):
            carteira_df = edited[edited["Financeiro"] > 0].reset_index(drop=True)
            if not carteira_df.empty:
                st.success(f"Carteira definida: {len(carteira_df)} ativos")

    # ── Save & Analyze ──
    if carteira_df is not None and not carteira_df.empty:
        # Save to database
        update_prospect(prospect["id"], {
            "carteira_dados": json.dumps(carteira_df.to_dict(orient="records"), ensure_ascii=False, default=str),
        })

        # Store in session for other pages
        st.session_state["current_prospect_carteira"] = carteira_df
        st.session_state["current_prospect_id"] = prospect["id"]

        st.markdown("---")
        st.subheader("Diagnóstico da Carteira")

        liquid_df = load_liquidation_data()
        diag = _compute_diagnostico(carteira_df, liquid_df)

        if diag:
            # ── Metrics ──
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Patrimônio Total", fmt_brl(diag["total_pl"]))
            with col2:
                st.metric("Ativos", diag["num_ativos"])
            with col3:
                conc_label = "Alta" if diag["top3_pct"] > 60 else ("Média" if diag["top3_pct"] > 40 else "Baixa")
                st.metric("Concentração Top 3", f"{diag['top3_pct']:.1f}%", delta=conc_label, delta_color="inverse" if diag["top3_pct"] > 60 else "normal")
            with col4:
                d01 = diag["liq_buckets"]["D+0-1"]
                st.metric("Liquidez Imediata", f"{d01:.1f}%")

            st.markdown("---")

            # ── Charts ──
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown(f"**Alocação por Estratégia**")
                cats = diag["categorias"]
                if cats:
                    fig = go.Figure(
                        go.Pie(
                            labels=list(cats.keys()),
                            values=list(cats.values()),
                            hole=0.55,
                            textinfo="label+percent",
                            textposition="outside",
                            textfont=dict(size=11, color=TAG["offwhite"]),
                            marker=dict(
                                colors=TAG["chart"],
                                line=dict(color=TAG["bg_dark"], width=1.5),
                            ),
                            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
                        )
                    )
                    fig.update_layout(**PLOTLY_LAYOUT, height=380, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

            with col_chart2:
                st.markdown(f"**Perfil de Liquidez**")
                buckets = diag["liq_buckets"]
                bucket_names = list(buckets.keys())
                bucket_vals = list(buckets.values())
                colors = [TAG["verde"], TAG["azul"], TAG["amarelo"], TAG["rosa"]]

                fig = go.Figure(
                    go.Bar(
                        x=bucket_vals,
                        y=bucket_names,
                        orientation="h",
                        marker_color=colors[:len(bucket_names)],
                        text=[f"{v:.1f}%" for v in bucket_vals],
                        textposition="auto",
                        textfont=dict(color=TAG["offwhite"]),
                    )
                )
                fig.update_layout(**PLOTLY_LAYOUT, height=380, showlegend=False)
                fig.update_xaxes(title_text="% do PL")
                st.plotly_chart(fig, use_container_width=True)

            # ── Table ──
            st.markdown("---")
            st.markdown("**Detalhamento da Carteira**")
            display_df = carteira_df.copy()
            total = display_df["Financeiro"].sum()
            display_df["% PL"] = display_df["Financeiro"] / total * 100
            display_df = display_df.sort_values("Financeiro", ascending=False).reset_index(drop=True)

            st.dataframe(
                display_df.style.format({
                    "Financeiro": "R$ {:,.2f}",
                    "% PL": "{:.2f}%",
                }),
                use_container_width=True,
                height=400,
            )

            # Save diagnostic data
            update_prospect(prospect["id"], {
                "carteira_dados": json.dumps(
                    carteira_df.to_dict(orient="records"),
                    ensure_ascii=False,
                    default=str,
                ),
            })

    elif prospect.get("carteira_dados"):
        # Load existing carteira from DB
        try:
            existing = json.loads(prospect["carteira_dados"]) if isinstance(prospect["carteira_dados"], str) else prospect["carteira_dados"]
            carteira_df = pd.DataFrame(existing)
            if not carteira_df.empty:
                st.session_state["current_prospect_carteira"] = carteira_df
                st.session_state["current_prospect_id"] = prospect["id"]

                st.info("Usando carteira salva anteriormente. Faça upload de um novo arquivo para atualizar.")

                liquid_df = load_liquidation_data()
                diag = _compute_diagnostico(carteira_df, liquid_df)

                if diag:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Patrimônio", fmt_brl(diag["total_pl"]))
                    with col2:
                        st.metric("Ativos", diag["num_ativos"])
                    with col3:
                        st.metric("Concentração Top 3", f"{diag['top3_pct']:.1f}%")
                    with col4:
                        st.metric("Liquidez D+0-1", f"{diag['liq_buckets']['D+0-1']:.1f}%")

                    st.dataframe(
                        carteira_df.style.format({"Financeiro": "R$ {:,.2f}"} if "Financeiro" in carteira_df.columns else {}),
                        use_container_width=True,
                    )
        except Exception:
            pass
