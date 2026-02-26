"""
Tela 8: Balancos & Estimativas
Consulta dados de balancos patrimoniais, DRE, fluxo de caixa (brapi.dev)
e estimativas de consenso de analistas (yfinance - gratuito).
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from shared.brand import TAG, PLOTLY_LAYOUT, fmt_brl, fmt_pct, render_card
from shared.brapi_client import BrapiClient, BrapiError
from shared.estimates_client import EstimatesClient

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
TICKERS_POPULARES = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "B3SA3", "WEGE3", "ABEV3",
    "RENT3", "SUZB3", "GGBR4", "JBSS3", "BBAS3", "MGLU3", "LREN3",
    "RADL3", "HAPV3", "RAIL3", "EMBR3", "TOTS3", "CSAN3", "VIVT3",
    "PRIO3", "EQTL3", "BPAC11", "ENEV3", "KLBN11", "CCRO3", "ITSA4",
]


def render_balancos():
    """Render principal da pagina de Balancos & Estimativas."""
    st.title("Balancos & Estimativas")
    st.caption("Dados de demonstracoes financeiras (brapi.dev) e estimativas de consenso (yfinance)")

    # ── Barra de busca ──
    col_search, col_period, col_btn = st.columns([3, 1.5, 1])
    with col_search:
        ticker_input = st.text_input(
            "Ticker B3",
            placeholder="Ex: PETR4, VALE3, ITUB4",
            help="Digite o codigo da acao na B3 (sem .SA)",
        )
    with col_period:
        periodo = st.selectbox(
            "Periodo",
            ["Trimestral", "Anual"],
            index=0,
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        buscar = st.button("🔍 Buscar", type="primary", use_container_width=True)

    # ── Quick picks ──
    st.markdown(
        f'<p style="color:{TAG["text_muted"]};font-size:0.8rem;margin-top:4px">'
        f'Populares: {" · ".join(TICKERS_POPULARES[:12])}</p>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Logica de busca ──
    ticker = ticker_input.strip().upper().replace(".SA", "") if ticker_input else ""
    quarterly = periodo == "Trimestral"

    if not buscar or not ticker:
        _render_empty_state()
        return

    # Busca dados
    with st.spinner(f"Buscando dados de {ticker}..."):
        try:
            client = BrapiClient()
            all_data = client.get_all_financials(ticker, quarterly=quarterly)
        except BrapiError as e:
            st.error(f"Erro ao buscar dados de **{ticker}**: {e}")
            return

    # ── Perfil da empresa ──
    profile = all_data.get("profile", {})
    if profile:
        _render_company_header(ticker, profile)

    # ── Tabs de conteudo ──
    tab_dre, tab_bp, tab_fc, tab_indicadores, tab_estimativas = st.tabs([
        "📊 DRE",
        "🏦 Balanco Patrimonial",
        "💰 Fluxo de Caixa",
        "📈 Indicadores",
        "🎯 Estimativas de Analistas",
    ])

    with tab_dre:
        _render_income_statement(all_data, ticker, quarterly)

    with tab_bp:
        _render_balance_sheet(all_data, ticker, quarterly)

    with tab_fc:
        _render_cashflow(all_data, ticker, quarterly)

    with tab_indicadores:
        _render_indicators(all_data, ticker)

    with tab_estimativas:
        _render_estimates(ticker)


# ---------------------------------------------------------------------------
# Componentes auxiliares
# ---------------------------------------------------------------------------
def _render_empty_state():
    """Exibe estado vazio antes da busca."""
    st.markdown(
        f"""
        <div style="text-align:center;padding:60px 20px">
            <div style="font-size:3rem;margin-bottom:16px">📊</div>
            <h3 style="color:{TAG['offwhite']};margin-bottom:8px">Consulte Balancos & Estimativas</h3>
            <p style="color:{TAG['text_muted']};max-width:500px;margin:0 auto">
                Digite o ticker de uma empresa da B3 para visualizar suas demonstracoes
                financeiras e estimativas de consenso dos analistas.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_company_header(ticker: str, profile: dict):
    """Exibe cabecalho com informacoes da empresa."""
    nome = profile.get("longName", ticker)
    setor = profile.get("sector", "")
    industria = profile.get("industry", "")
    cnpj = profile.get("cnpj", "")
    descricao = profile.get("longBusinessSummary", "")

    st.markdown(
        f"""
        <div class="tag-card" style="margin-bottom:24px">
            <div style="display:flex;align-items:center;gap:16px">
                <div>
                    <h2 style="margin:0 !important;font-size:1.5rem !important">{nome}</h2>
                    <p style="color:{TAG['laranja']};font-size:1.1rem;margin:4px 0 0 0;font-weight:600">{ticker}</p>
                </div>
                <div style="margin-left:auto;text-align:right">
                    <p style="color:{TAG['text_muted']};font-size:0.85rem;margin:0">
                        {setor}{' · ' + industria if industria else ''}
                    </p>
                    {'<p style="color:' + TAG['text_muted'] + ';font-size:0.75rem;margin:4px 0 0 0">CNPJ: ' + cnpj + '</p>' if cnpj else ''}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tab: DRE
# ---------------------------------------------------------------------------
def _render_income_statement(all_data: dict, ticker: str, quarterly: bool):
    """Renderiza a aba de DRE."""
    dre = all_data.get("income_statement", pd.DataFrame())

    if dre.empty:
        st.warning(f"Nenhum dado de DRE encontrado para {ticker}.")
        return

    # Metricas do periodo mais recente
    latest = dre.iloc[0]
    periodo_label = _format_period(latest)

    st.markdown(f"### Resultado - {periodo_label}")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Receita Liquida", _fmt_val(latest.get("totalRevenue")))
    with col2:
        st.metric("Lucro Bruto", _fmt_val(latest.get("grossProfit")))
    with col3:
        st.metric("EBITDA", _fmt_val(latest.get("cleanEbitda")))
    with col4:
        st.metric("EBIT", _fmt_val(latest.get("ebit")))
    with col5:
        st.metric("Lucro Liquido", _fmt_val(latest.get("netIncome")))

    # Margens
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    revenue = latest.get("totalRevenue")
    with col1:
        st.metric("Margem Bruta", _calc_margin(latest.get("grossProfit"), revenue))
    with col2:
        st.metric("Margem EBITDA", _calc_margin(latest.get("cleanEbitda"), revenue))
    with col3:
        st.metric("Margem Operacional", _calc_margin(latest.get("operatingIncome"), revenue))
    with col4:
        st.metric("Margem Liquida", _calc_margin(latest.get("netIncome"), revenue))

    st.markdown("---")

    # Grafico de evolucao da receita e lucro
    if len(dre) > 1:
        st.markdown("### Evolucao Historica")
        _chart_revenue_profit(dre)

    # Waterfall DRE
    st.markdown("### Composicao do Resultado")
    _chart_dre_waterfall(latest)

    # Tabela completa
    with st.expander("📋 Tabela Completa da DRE", expanded=False):
        display_df = _prepare_display_df(dre)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def _chart_revenue_profit(dre: pd.DataFrame):
    """Grafico de barras: Receita vs Lucro ao longo do tempo."""
    df = dre.copy().sort_values("endDate")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["endDate"].dt.strftime("%Y-%m") if "endDate" in df.columns else df.index,
        y=df.get("totalRevenue", pd.Series(dtype=float)),
        name="Receita Liquida",
        marker_color=TAG["chart"][0],
        opacity=0.85,
    ))

    fig.add_trace(go.Bar(
        x=df["endDate"].dt.strftime("%Y-%m") if "endDate" in df.columns else df.index,
        y=df.get("cleanEbitda", pd.Series(dtype=float)),
        name="EBITDA",
        marker_color=TAG["chart"][1],
        opacity=0.85,
    ))

    fig.add_trace(go.Bar(
        x=df["endDate"].dt.strftime("%Y-%m") if "endDate" in df.columns else df.index,
        y=df.get("netIncome", pd.Series(dtype=float)),
        name="Lucro Liquido",
        marker_color=TAG["chart"][2],
        opacity=0.85,
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="group",
        height=380,
        yaxis_title="R$",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def _chart_dre_waterfall(latest: pd.Series):
    """Waterfall chart da DRE."""
    items = [
        ("Receita", latest.get("totalRevenue", 0)),
        ("(-) CPV", -(latest.get("costOfRevenue", 0) or 0)),
        ("Lucro Bruto", latest.get("grossProfit", 0)),
        ("(-) Desp. Operacionais", -(abs(latest.get("sellingGeneralAdministrative", 0) or 0))),
        ("Res. Financeiro", latest.get("financialResult", 0)),
        ("(-) IR/CS", -(abs(latest.get("incomeTaxExpense", 0) or 0))),
        ("Lucro Liquido", latest.get("netIncome", 0)),
    ]

    # Filtra itens com valor zero ou None
    items = [(name, val) for name, val in items if val is not None and val != 0]

    if not items:
        st.info("Dados insuficientes para o waterfall.")
        return

    measures = []
    for i, (name, val) in enumerate(items):
        if name in ("Receita",):
            measures.append("absolute")
        elif name in ("Lucro Bruto", "Lucro Liquido"):
            measures.append("total")
        else:
            measures.append("relative")

    fig = go.Figure(go.Waterfall(
        x=[item[0] for item in items],
        y=[item[1] for item in items],
        measure=measures,
        textposition="outside",
        text=[_fmt_val(item[1]) for item in items],
        connector=dict(line=dict(color=TAG["text_muted"], width=1, dash="dot")),
        increasing=dict(marker=dict(color=TAG["verde"])),
        decreasing=dict(marker=dict(color=TAG["rosa"])),
        totals=dict(marker=dict(color=TAG["laranja"])),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=400,
        showlegend=False,
        yaxis_title="R$",
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab: Balanco Patrimonial
# ---------------------------------------------------------------------------
def _render_balance_sheet(all_data: dict, ticker: str, quarterly: bool):
    """Renderiza a aba de Balanco Patrimonial."""
    bp = all_data.get("balance_sheet", pd.DataFrame())

    if bp.empty:
        st.warning(f"Nenhum dado de Balanco Patrimonial encontrado para {ticker}.")
        return

    latest = bp.iloc[0]
    periodo_label = _format_period(latest)

    st.markdown(f"### Balanco Patrimonial - {periodo_label}")

    # Metricas principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Ativo Total", _fmt_val(latest.get("totalAssets")))
    with col2:
        st.metric("Passivo Total", _fmt_val(latest.get("totalLiabilities")))
    with col3:
        st.metric("Patrimonio Liquido", _fmt_val(latest.get("shareholdersEquity")))
    with col4:
        divida_liq = _calc_net_debt(latest)
        st.metric("Divida Liquida", _fmt_val(divida_liq))

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Caixa", _fmt_val(latest.get("cash")))
    with col2:
        st.metric("Divida CP", _fmt_val(latest.get("shortTermDebt")))
    with col3:
        st.metric("Divida LP", _fmt_val(latest.get("longTermDebt")))
    with col4:
        st.metric("Ativo Circulante", _fmt_val(latest.get("totalCurrentAssets")))

    st.markdown("---")

    # Grafico de composicao do ativo
    if len(bp) > 1:
        st.markdown("### Evolucao Patrimonial")
        _chart_balance_evolution(bp)

    # Grafico pizza: composicao
    st.markdown("### Composicao do Ativo")
    _chart_asset_composition(latest)

    # Tabela
    with st.expander("📋 Tabela Completa do BP", expanded=False):
        display_df = _prepare_display_df(bp)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def _chart_balance_evolution(bp: pd.DataFrame):
    """Evolucao de Ativo, Passivo e PL ao longo do tempo."""
    df = bp.copy().sort_values("endDate")

    fig = go.Figure()

    for col, name, color in [
        ("totalAssets", "Ativo Total", TAG["chart"][1]),
        ("totalLiabilities", "Passivo Total", TAG["chart"][4]),
        ("shareholdersEquity", "Patrimonio Liquido", TAG["chart"][2]),
    ]:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["endDate"].dt.strftime("%Y-%m"),
                y=df[col],
                name=name,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=6),
            ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=380,
        yaxis_title="R$",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def _chart_asset_composition(latest: pd.Series):
    """Pizza/Donut da composicao do ativo."""
    items = {
        "Caixa e Equiv.": latest.get("cash", 0) or 0,
        "Investimentos CP": latest.get("shortTermInvestments", 0) or 0,
        "Contas a Receber": latest.get("netReceivables", 0) or 0,
        "Estoques": latest.get("inventory", 0) or 0,
        "Imobilizado": latest.get("propertyPlantEquipment", 0) or 0,
        "Intangiveis": latest.get("intangibleAssets", 0) or 0,
        "Goodwill": latest.get("goodwill", 0) or 0,
        "Outros": latest.get("otherAssets", 0) or 0,
    }

    # Remove zeros
    items = {k: v for k, v in items.items() if v > 0}

    if not items:
        st.info("Dados insuficientes para composicao do ativo.")
        return

    fig = go.Figure(go.Pie(
        labels=list(items.keys()),
        values=list(items.values()),
        hole=0.45,
        marker=dict(colors=TAG["chart"][:len(items)]),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11, color=TAG["offwhite"]),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=380,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab: Fluxo de Caixa
# ---------------------------------------------------------------------------
def _render_cashflow(all_data: dict, ticker: str, quarterly: bool):
    """Renderiza a aba de Fluxo de Caixa."""
    fc = all_data.get("cashflow", pd.DataFrame())

    if fc.empty:
        st.warning(f"Nenhum dado de Fluxo de Caixa encontrado para {ticker}.")
        return

    latest = fc.iloc[0]
    periodo_label = _format_period(latest)

    st.markdown(f"### Fluxo de Caixa - {periodo_label}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("FC Operacional", _fmt_val(latest.get("operatingCashFlow")))
    with col2:
        st.metric("FC Investimentos", _fmt_val(latest.get("investmentCashFlow")))
    with col3:
        st.metric("FC Financiamento", _fmt_val(latest.get("financingCashFlow")))
    with col4:
        st.metric("Free Cash Flow", _fmt_val(latest.get("freeCashFlow")))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Saldo Inicial", _fmt_val(latest.get("initialCashBalance")))
    with col2:
        st.metric("Saldo Final", _fmt_val(latest.get("finalCashBalance")))

    st.markdown("---")

    # Grafico de evolucao
    if len(fc) > 1:
        st.markdown("### Evolucao do Fluxo de Caixa")
        _chart_cashflow_evolution(fc)

    # Waterfall do fluxo de caixa
    st.markdown("### Composicao do Fluxo de Caixa")
    _chart_cashflow_waterfall(latest)

    # Tabela
    with st.expander("📋 Tabela Completa do FC", expanded=False):
        display_df = _prepare_display_df(fc)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def _chart_cashflow_evolution(fc: pd.DataFrame):
    """Evolucao dos 3 fluxos de caixa ao longo do tempo."""
    df = fc.copy().sort_values("endDate")

    fig = go.Figure()

    for col, name, color in [
        ("operatingCashFlow", "FC Operacional", TAG["chart"][2]),
        ("investmentCashFlow", "FC Investimentos", TAG["chart"][4]),
        ("financingCashFlow", "FC Financiamento", TAG["chart"][1]),
        ("freeCashFlow", "Free Cash Flow", TAG["chart"][0]),
    ]:
        if col in df.columns:
            fig.add_trace(go.Bar(
                x=df["endDate"].dt.strftime("%Y-%m"),
                y=df[col],
                name=name,
                marker_color=color,
                opacity=0.85,
            ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="group",
        height=380,
        yaxis_title="R$",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def _chart_cashflow_waterfall(latest: pd.Series):
    """Waterfall do fluxo de caixa."""
    items = [
        ("Saldo Inicial", latest.get("initialCashBalance", 0)),
        ("FC Operacional", latest.get("operatingCashFlow", 0)),
        ("FC Investimentos", latest.get("investmentCashFlow", 0)),
        ("FC Financiamento", latest.get("financingCashFlow", 0)),
        ("Saldo Final", latest.get("finalCashBalance", 0)),
    ]

    items = [(name, val or 0) for name, val in items]

    measures = ["absolute", "relative", "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(
        x=[i[0] for i in items],
        y=[i[1] for i in items],
        measure=measures,
        textposition="outside",
        text=[_fmt_val(i[1]) for i in items],
        connector=dict(line=dict(color=TAG["text_muted"], width=1, dash="dot")),
        increasing=dict(marker=dict(color=TAG["verde"])),
        decreasing=dict(marker=dict(color=TAG["rosa"])),
        totals=dict(marker=dict(color=TAG["laranja"])),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=380,
        showlegend=False,
        yaxis_title="R$",
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab: Indicadores
# ---------------------------------------------------------------------------
def _render_indicators(all_data: dict, ticker: str):
    """Renderiza a aba de indicadores-chave."""
    fin = all_data.get("financial_data", pd.DataFrame())
    stats = all_data.get("key_statistics", pd.DataFrame())

    if fin.empty and stats.empty:
        st.warning(f"Nenhum indicador encontrado para {ticker}.")
        return

    st.markdown("### Indicadores Financeiros (TTM)")

    # Financial Data metrics
    if not fin.empty:
        row = fin.iloc[0]

        # Valuation
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Valuation</h4>', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Preco Atual", _fmt_price(row.get("currentPrice")))
        with col2:
            st.metric("Target Medio", _fmt_price(row.get("targetMeanPrice")))
        with col3:
            st.metric("Target Alto", _fmt_price(row.get("targetHighPrice")))
        with col4:
            st.metric("Target Baixo", _fmt_price(row.get("targetLowPrice")))
        with col5:
            recom = row.get("recommendationKey", "N/A")
            n_analysts = row.get("numberOfAnalystOpinions", "N/A")
            st.metric(f"Recomendacao ({n_analysts} analistas)", str(recom).upper())

        st.markdown("---")

        # Rentabilidade
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Rentabilidade</h4>', unsafe_allow_html=True)
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Margem Bruta", _fmt_margin(row.get("grossMargins")))
        with col2:
            st.metric("Margem EBITDA", _fmt_margin(row.get("ebitdaMargins")))
        with col3:
            st.metric("Margem Operac.", _fmt_margin(row.get("operatingMargins")))
        with col4:
            st.metric("Margem Liquida", _fmt_margin(row.get("profitMargins")))
        with col5:
            st.metric("ROE", _fmt_margin(row.get("returnOnEquity")))
        with col6:
            st.metric("ROA", _fmt_margin(row.get("returnOnAssets")))

        st.markdown("---")

        # Endividamento
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Endividamento & Liquidez</h4>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Divida Total", _fmt_val(row.get("totalDebt")))
        with col2:
            st.metric("Caixa Total", _fmt_val(row.get("totalCash")))
        with col3:
            d2e = row.get("debtToEquity")
            st.metric("Divida/PL", f"{d2e:.2f}" if d2e is not None else "N/D")
        with col4:
            cr = row.get("currentRatio")
            st.metric("Liquidez Corrente", f"{cr:.2f}" if cr is not None else "N/D")

        st.markdown("---")

        # Crescimento
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Crescimento</h4>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Cresc. Receita", _fmt_margin(row.get("revenueGrowth")))
        with col2:
            st.metric("Cresc. Lucro", _fmt_margin(row.get("earningsGrowth")))
        with col3:
            st.metric("EBITDA", _fmt_val(row.get("ebitda")))
        with col4:
            st.metric("FCL", _fmt_val(row.get("freeCashflow")))

    # Key Statistics
    if not stats.empty:
        st.markdown("---")
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Multiplos</h4>', unsafe_allow_html=True)
        row = stats.iloc[0]

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            pe = row.get("trailingPE")
            st.metric("P/L (trailing)", f"{pe:.1f}" if pe is not None else "N/D")
        with col2:
            fpe = row.get("forwardPE")
            st.metric("P/L (forward)", f"{fpe:.1f}" if fpe is not None else "N/D")
        with col3:
            pb = row.get("priceToBook")
            st.metric("P/VP", f"{pb:.2f}" if pb is not None else "N/D")
        with col4:
            ev_ebitda = row.get("enterpriseToEbitda")
            st.metric("EV/EBITDA", f"{ev_ebitda:.1f}" if ev_ebitda is not None else "N/D")
        with col5:
            ev_rev = row.get("enterpriseToRevenue")
            st.metric("EV/Receita", f"{ev_rev:.2f}" if ev_rev is not None else "N/D")
        with col6:
            beta = row.get("beta")
            st.metric("Beta", f"{beta:.2f}" if beta is not None else "N/D")

        # Grafico radar de indicadores
        st.markdown("---")
        st.markdown("### Radar de Indicadores")
        _chart_radar_indicators(fin, stats)


def _chart_radar_indicators(fin: pd.DataFrame, stats: pd.DataFrame):
    """Radar chart com indicadores-chave."""
    categories = ["Margem Bruta", "Margem EBITDA", "Margem Liquida", "ROE", "ROA"]
    values = []

    if not fin.empty:
        row = fin.iloc[0]
        for field in ["grossMargins", "ebitdaMargins", "profitMargins", "returnOnEquity", "returnOnAssets"]:
            val = row.get(field)
            values.append((val or 0) * 100 if val is not None else 0)
    else:
        values = [0] * 5

    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],  # Fechar o radar
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor=f"{TAG['laranja']}30",
        line=dict(color=TAG["laranja"], width=2),
        marker=dict(size=6, color=TAG["laranja"]),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=400,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                gridcolor="rgba(230,228,219,0.10)",
                ticksuffix="%",
                tickfont=dict(size=10, color=TAG["text_muted"]),
            ),
            angularaxis=dict(
                gridcolor="rgba(230,228,219,0.10)",
                tickfont=dict(size=12, color=TAG["offwhite"]),
            ),
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab: Estimativas de Analistas (yfinance - 100% gratuito)
# ---------------------------------------------------------------------------
def _render_estimates(ticker: str):
    """Renderiza a aba de estimativas de consenso usando yfinance (gratuito)."""

    with st.spinner("Buscando estimativas de analistas..."):
        try:
            client = EstimatesClient()
            estimates = client.get_full_estimates(ticker)
        except Exception as e:
            st.error(f"Erro ao buscar estimativas de {ticker}: {e}")
            return

    # ── 1. Target Price & Recomendacao ──
    info = estimates.get("analyst_info", {})
    if info:
        _render_target_price(info)

    st.markdown("---")

    # ── 2. Estimativas de EPS ──
    st.markdown(f'<h4 style="color:{TAG["laranja"]}">Estimativas de LPA (EPS)</h4>', unsafe_allow_html=True)
    eps_df = estimates.get("eps_estimates", pd.DataFrame())
    if not eps_df.empty:
        # Remove coluna ticker para exibicao
        display = eps_df.drop(columns=["ticker"], errors="ignore")
        st.dataframe(display, use_container_width=True)
    else:
        st.info("Sem estimativas de EPS disponiveis para este ticker.")

    st.markdown("---")

    # ── 3. Estimativas de Receita ──
    st.markdown(f'<h4 style="color:{TAG["laranja"]}">Estimativas de Receita</h4>', unsafe_allow_html=True)
    rev_df = estimates.get("revenue_estimates", pd.DataFrame())
    if not rev_df.empty:
        display = rev_df.drop(columns=["ticker"], errors="ignore")
        st.dataframe(display, use_container_width=True)
    else:
        st.info("Sem estimativas de receita disponiveis para este ticker.")

    st.markdown("---")

    # ── 4. Historico de Surpresas (Actual vs Estimate) ──
    st.markdown(f'<h4 style="color:{TAG["laranja"]}">Historico de Surpresas de Resultados</h4>', unsafe_allow_html=True)
    hist_df = estimates.get("earnings_history", pd.DataFrame())
    if not hist_df.empty:
        _render_earnings_surprises(hist_df)
    else:
        st.info("Sem historico de surpresas disponiveis.")

    st.markdown("---")

    # ── 5. Tendencia de Revisoes ──
    col_trend, col_rev = st.columns(2)

    with col_trend:
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Tendencia de EPS</h4>', unsafe_allow_html=True)
        trend_df = estimates.get("eps_trend", pd.DataFrame())
        if not trend_df.empty:
            display = trend_df.drop(columns=["ticker"], errors="ignore")
            st.dataframe(display, use_container_width=True)
        else:
            st.info("Sem dados de tendencia.")

    with col_rev:
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Revisoes de Analistas</h4>', unsafe_allow_html=True)
        rev_eps_df = estimates.get("eps_revisions", pd.DataFrame())
        if not rev_eps_df.empty:
            display = rev_eps_df.drop(columns=["ticker"], errors="ignore")
            st.dataframe(display, use_container_width=True)
        else:
            st.info("Sem dados de revisoes.")

    st.markdown("---")

    # ── 6. Estimativas de Crescimento ──
    st.markdown(f'<h4 style="color:{TAG["laranja"]}">Estimativas de Crescimento</h4>', unsafe_allow_html=True)
    growth_df = estimates.get("growth_estimates", pd.DataFrame())
    if not growth_df.empty:
        display = growth_df.drop(columns=["ticker"], errors="ignore")
        st.dataframe(display, use_container_width=True)
    else:
        st.info("Sem estimativas de crescimento disponiveis.")

    st.markdown("---")

    # ── 7. Recomendacoes ──
    st.markdown(f'<h4 style="color:{TAG["laranja"]}">Historico de Recomendacoes</h4>', unsafe_allow_html=True)
    rec_df = estimates.get("recommendations", pd.DataFrame())
    if not rec_df.empty:
        _render_recommendations_chart(rec_df)
    else:
        st.info("Sem historico de recomendacoes disponivel.")

    st.markdown("---")

    # ── 8. Upgrades/Downgrades ──
    st.markdown(f'<h4 style="color:{TAG["laranja"]}">Upgrades & Downgrades Recentes</h4>', unsafe_allow_html=True)
    ud_df = estimates.get("upgrades_downgrades", pd.DataFrame())
    if not ud_df.empty:
        display = ud_df.drop(columns=["ticker"], errors="ignore")
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("Sem upgrades/downgrades recentes.")

    # ── 9. Proximas Datas de Resultados ──
    dates_df = estimates.get("earnings_dates", pd.DataFrame())
    if not dates_df.empty:
        st.markdown("---")
        st.markdown(f'<h4 style="color:{TAG["laranja"]}">Proximas Datas de Resultados</h4>', unsafe_allow_html=True)
        display = dates_df.drop(columns=["ticker"], errors="ignore")
        st.dataframe(display, use_container_width=True)


def _render_target_price(info: dict):
    """Exibe target price e recomendacao de analistas."""
    st.markdown("### Consenso de Analistas")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Preco Atual", _fmt_price(info.get("currentPrice")))
    with col2:
        st.metric("Target Medio", _fmt_price(info.get("targetMeanPrice")))
    with col3:
        st.metric("Target Mediano", _fmt_price(info.get("targetMedianPrice")))
    with col4:
        st.metric("Target Alto", _fmt_price(info.get("targetHighPrice")))
    with col5:
        st.metric("Target Baixo", _fmt_price(info.get("targetLowPrice")))

    # Upside/Downside
    preco = info.get("currentPrice")
    target = info.get("targetMeanPrice")
    if preco and target and preco > 0:
        upside = (target - preco) / preco * 100
        color = TAG["verde"] if upside > 0 else TAG["rosa"]
        st.markdown(
            f'<p style="text-align:center;font-size:1.3rem;font-weight:700;color:{color};margin:16px 0">'
            f'{"▲" if upside > 0 else "▼"} Upside: {upside:+.1f}%</p>',
            unsafe_allow_html=True,
        )

    # Recomendacao
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        recom = info.get("recommendationKey", "N/A")
        st.metric("Recomendacao", str(recom).upper() if recom else "N/D")
    with col2:
        mean = info.get("recommendationMean")
        st.metric("Media Recom.", f"{mean:.2f}" if mean is not None else "N/D")
        st.caption("1=Strong Buy, 5=Strong Sell")
    with col3:
        n = info.get("numberOfAnalystOpinions")
        st.metric("Num. Analistas", str(n) if n else "N/D")
    with col4:
        fpe = info.get("forwardPE")
        st.metric("P/L Forward", f"{fpe:.1f}" if fpe is not None else "N/D")


def _render_earnings_surprises(hist_df: pd.DataFrame):
    """Grafico de surpresas de resultados (actual vs estimate)."""
    df = hist_df.drop(columns=["ticker"], errors="ignore").copy()

    # Tenta encontrar as colunas corretas
    eps_est_col = None
    eps_act_col = None
    surprise_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "estimate" in col_lower and "eps" in col_lower:
            eps_est_col = col
        elif "actual" in col_lower and "eps" in col_lower:
            eps_act_col = col
        elif "surprise" in col_lower and "percent" in col_lower:
            surprise_col = col

    # Fallback por posicao de coluna
    if eps_est_col is None and len(df.columns) >= 2:
        eps_est_col = df.columns[0]
    if eps_act_col is None and len(df.columns) >= 3:
        eps_act_col = df.columns[1]
    if surprise_col is None and len(df.columns) >= 4:
        surprise_col = df.columns[3]

    if eps_est_col and eps_act_col:
        # Grafico de barras agrupadas
        x_labels = [str(i) for i in df.index]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=x_labels,
            y=pd.to_numeric(df[eps_est_col], errors="coerce"),
            name="Estimado",
            marker_color=TAG["chart"][1],
            opacity=0.85,
        ))

        fig.add_trace(go.Bar(
            x=x_labels,
            y=pd.to_numeric(df[eps_act_col], errors="coerce"),
            name="Realizado",
            marker_color=TAG["chart"][0],
            opacity=0.85,
        ))

        fig.update_layout(
            **PLOTLY_LAYOUT,
            barmode="group",
            height=350,
            yaxis_title="EPS (R$)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        st.plotly_chart(fig, use_container_width=True)

    # Tabela
    with st.expander("📋 Tabela de Surpresas", expanded=False):
        st.dataframe(df, use_container_width=True)


def _render_recommendations_chart(rec_df: pd.DataFrame):
    """Grafico de recomendacoes ao longo do tempo."""
    df = rec_df.drop(columns=["ticker"], errors="ignore").copy()

    # Colunas tipicas: period, strongBuy, buy, hold, sell, strongSell
    rec_cols = []
    colors = []
    labels = []

    for col, label, color in [
        ("strongBuy", "Strong Buy", TAG["verde"]),
        ("buy", "Buy", "#6BDE9780"),
        ("hold", "Hold", TAG["amarelo"]),
        ("sell", "Sell", "#ED5A6E80"),
        ("strongSell", "Strong Sell", TAG["rosa"]),
    ]:
        if col in df.columns:
            rec_cols.append(col)
            colors.append(color)
            labels.append(label)

    if not rec_cols:
        st.dataframe(df, use_container_width=True)
        return

    # Pega os ultimos 6 periodos
    df = df.head(6).iloc[::-1]  # Reverte para ordem cronologica

    x_labels = df.get("period", pd.Series(range(len(df)))).astype(str)

    fig = go.Figure()

    for col, label, color in zip(rec_cols, labels, colors):
        fig.add_trace(go.Bar(
            x=x_labels,
            y=pd.to_numeric(df[col], errors="coerce"),
            name=label,
            marker_color=color,
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="stack",
        height=380,
        yaxis_title="Numero de Analistas",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _fmt_val(value) -> str:
    """Formata valor monetario compacto."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/D"
    try:
        v = float(value)
        if abs(v) >= 1e9:
            return f"R$ {v/1e9:,.1f}B"
        elif abs(v) >= 1e6:
            return f"R$ {v/1e6:,.1f}M"
        elif abs(v) >= 1e3:
            return f"R$ {v/1e3:,.0f}K"
        else:
            return f"R$ {v:,.0f}"
    except (ValueError, TypeError):
        return "N/D"


def _fmt_price(value) -> str:
    """Formata preco de acao."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/D"
    try:
        return f"R$ {float(value):,.2f}"
    except (ValueError, TypeError):
        return "N/D"


def _fmt_margin(value) -> str:
    """Formata margem/percentual."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/D"
    try:
        return f"{float(value)*100:.1f}%"
    except (ValueError, TypeError):
        return "N/D"


def _calc_margin(numerator, denominator) -> str:
    """Calcula e formata uma margem."""
    if numerator is None or denominator is None:
        return "N/D"
    try:
        n = float(numerator)
        d = float(denominator)
        if d == 0:
            return "N/D"
        return f"{(n/d)*100:.1f}%"
    except (ValueError, TypeError):
        return "N/D"


def _calc_net_debt(row: pd.Series) -> float:
    """Calcula divida liquida = divida total - caixa."""
    short_debt = row.get("shortTermDebt", 0) or 0
    long_debt = row.get("longTermDebt", 0) or 0
    cash = row.get("cash", 0) or 0
    short_invest = row.get("shortTermInvestments", 0) or 0
    return (short_debt + long_debt) - (cash + short_invest)


def _format_period(row) -> str:
    """Formata o periodo para exibicao."""
    end_date = row.get("endDate")
    tipo = row.get("type", "")
    if end_date is not None:
        if isinstance(end_date, str):
            return end_date
        return end_date.strftime("%d/%m/%Y")
    return tipo or "Periodo N/D"


def _prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara DataFrame para exibicao (formata datas e valores)."""
    display = df.copy()

    # Formata endDate
    if "endDate" in display.columns:
        display["endDate"] = display["endDate"].apply(
            lambda x: x.strftime("%d/%m/%Y") if hasattr(x, "strftime") else str(x)
        )

    # Remove coluna ticker se existir (ja esta no titulo)
    if "ticker" in display.columns:
        display = display.drop(columns=["ticker"])

    # Remove coluna type se existir
    if "type" in display.columns:
        display = display.drop(columns=["type"])

    return display
