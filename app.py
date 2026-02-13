import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
import re
import os

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Simulador de Realocação",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DADOS_LIQUID_PATH = os.path.join(os.path.dirname(__file__), "Dados de liquid.xlsx")

# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def strip_html(val):
    """Remove HTML tags from cell values."""
    if isinstance(val, str):
        return re.sub(r"<[^>]+>", "", val).strip()
    return val


@st.cache_data(show_spinner="Carregando dados de liquidação...")
def load_liquidation_data():
    """Load and clean the liquidation master data."""
    df = pd.read_excel(DADOS_LIQUID_PATH, sheet_name="Sheet")
    # Strip HTML from all string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(strip_html)
    # Ensure numeric columns
    for col in ["Conversão Resgate", "Liquid. Resgate", "Conversão Aplic."]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def normalize_columns(df):
    """Normalize column names that may have encoding issues."""
    col_map = {}
    for c in df.columns:
        normalized = c.strip()
        # Fix common encoding issues with Portuguese characters
        replacements = {
            "C\u00c3\u201cD.": "CÓD.",
            "C�D.": "CÓD.",
            "ESTRAT\u00c3\u2030GIA": "ESTRATÉGIA",
            "ESTRAT�GIA": "ESTRATÉGIA",
            "PRE\u00c3\u2021O": "PREÇO",
            "PRE�O": "PREÇO",
            "POSI\u00c3\u2021\u00c3\u0192O": "POSIÇÃO",
            "POSI��O": "POSIÇÃO",
            "PROJE\u00c3\u2021\u00c3\u0192O": "PROJEÇÃO",
            "PROJE��O": "PROJEÇÃO",
            "DESCRI\u00c3\u2021\u00c3\u0192O": "DESCRIÇÃO",
            "DESCRI��O": "DESCRIÇÃO",
            "LIQUIDA\u00c3\u2021\u00c3\u0192O": "LIQUIDAÇÃO",
            "LIQUIDA��O": "LIQUIDAÇÃO",
            "OPERA\u00c3\u2021\u00c3\u0192O": "OPERAÇÃO",
            "OPERA��O": "OPERAÇÃO",
            "COTIZA\u00c3\u2021\u00c3\u0192O": "COTIZAÇÃO",
            "COTIZA��O": "COTIZAÇÃO",
            "VE\u00c3\u0178CULO": "VEÍCULO",
            "VE�CULO": "VEÍCULO",
        }
        for bad, good in replacements.items():
            normalized = normalized.replace(bad, good)
        col_map[c] = normalized
    return df.rename(columns=col_map)


def parse_portfolio_file(uploaded_file):
    """Parse the uploaded portfolio file (Posição Projetada format)."""
    xl = pd.ExcelFile(uploaded_file)
    sheets = {}

    # Find sheet names flexibly (encoding may affect sheet names too)
    sheet_map = {}
    for name in xl.sheet_names:
        name_upper = name.upper()
        if "CARTEIRA" in name_upper and "CAIXA" in name_upper:
            sheet_map["carteira"] = name
        elif "ATIVO" in name_upper and "BOLETA" not in name_upper:
            sheet_map["ativos"] = name
        elif "PROVIS" in name_upper:
            sheet_map["provisoes"] = name
        elif "BOLETA" in name_upper:
            sheet_map["boletas"] = name

    if "carteira" in sheet_map:
        df = pd.read_excel(xl, sheet_name=sheet_map["carteira"])
        sheets["carteira"] = normalize_columns(df)

    if "ativos" in sheet_map:
        df = pd.read_excel(xl, sheet_name=sheet_map["ativos"])
        sheets["ativos"] = normalize_columns(df)

    if "provisoes" in sheet_map:
        df = pd.read_excel(xl, sheet_name=sheet_map["provisoes"])
        sheets["provisoes"] = normalize_columns(df)

    if "boletas" in sheet_map:
        df = pd.read_excel(xl, sheet_name=sheet_map["boletas"])
        sheets["boletas"] = normalize_columns(df)

    return sheets


def find_col(df, *candidates):
    """Find the first matching column from candidates. Handles encoding issues."""
    for c in candidates:
        if c in df.columns:
            return c
    # Fallback: partial match
    for c in candidates:
        for col in df.columns:
            if c.upper()[:6] in col.upper():
                return col
    return None


def add_business_days(start_date, num_days, count_type="Úteis"):
    """Add business or calendar days to a date."""
    if count_type == "Úteis":
        current = start_date
        added = 0
        while added < num_days:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Mon-Fri
                added += 1
        return current
    else:  # Corridos
        return start_date + timedelta(days=num_days)


def is_stock_ticker(name):
    """Check if the asset name looks like a B3 stock/ETF ticker (e.g., FRAS3, BOVA11)."""
    if not name:
        return False
    name = str(name).strip().upper()
    import re as _re
    return bool(_re.match(r'^[A-Z]{4}\d{1,2}$', name))


def make_stock_liquidation_info(ticker):
    """Create a synthetic liquidation info for B3 stocks (D+2 settlement)."""
    return pd.Series({
        "Apelido": ticker,
        "Nome": ticker,
        "Conversão Resgate": 0,
        "Liquid. Resgate": 2,
        "Conversão Aplic.": 0,
        "Contagem Resgate": "Úteis",
        "Código Anbima": "",
        "Categoria": "Ação/ETF B3",
    })


def match_fund_liquidation(fund_name, fund_code, liquid_df):
    """Try to match a fund from the portfolio with liquidation data."""
    if fund_code and not pd.isna(fund_code):
        code_str = str(int(fund_code)) if isinstance(fund_code, float) else str(fund_code)
        match = liquid_df[liquid_df["Código Anbima"].astype(str) == code_str]
        if not match.empty:
            return match.iloc[0]
        match = liquid_df[liquid_df["Id Carteira"].astype(str) == code_str]
        if not match.empty:
            return match.iloc[0]

    if fund_name:
        name_clean = str(fund_name).strip().upper()
        # Try exact match on Apelido or Nome
        for col in ["Apelido", "Nome"]:
            match = liquid_df[liquid_df[col].str.upper().str.strip() == name_clean]
            if not match.empty:
                return match.iloc[0]
        # Fuzzy: check if portfolio name is contained in liquidation name or vice versa
        for col in ["Apelido", "Nome"]:
            for idx, row in liquid_df.iterrows():
                liq_name = str(row[col]).strip().upper()
                if len(name_clean) > 5 and (name_clean in liq_name or liq_name in name_clean):
                    return row

    # If it looks like a B3 stock/ETF ticker, use standard D+2 settlement
    check_name = fund_name if fund_name else fund_code
    if check_name and is_stock_ticker(str(check_name)):
        return make_stock_liquidation_info(str(check_name).upper())

    return None


def compute_liquidation_dates(movements, liquid_df):
    """For each movement, compute cotização and liquidação dates."""
    results = []
    for mov in movements:
        fund_name = mov["fund_name"]
        fund_code = mov.get("fund_code", None)
        operation = mov["operation"]  # "Resgate" or "Aplicação"
        request_date = mov["request_date"]
        value = mov["value"]

        liq_info = match_fund_liquidation(fund_name, fund_code, liquid_df)

        if liq_info is not None:
            if operation == "Resgate":
                conv_days = int(liq_info["Conversão Resgate"])
                liq_days = int(liq_info["Liquid. Resgate"])
                count_type = str(liq_info["Contagem Resgate"])
                if count_type not in ["Úteis", "Corridos"]:
                    count_type = "Úteis"
            else:  # Aplicação
                conv_days = int(liq_info["Conversão Aplic."])
                liq_days = 0  # Aplicação usually immediate after cotização
                count_type = "Úteis"

            cotizacao_date = add_business_days(request_date, conv_days, count_type)
            liquidacao_date = add_business_days(cotizacao_date, liq_days, count_type)
            matched = True
            total_days = f"D+{conv_days + liq_days}"
        else:
            cotizacao_date = request_date
            liquidacao_date = request_date
            matched = False
            total_days = "N/A"

        results.append({
            "Fundo": fund_name,
            "Código": fund_code,
            "Operação": operation,
            "Valor (R$)": value,
            "Data Solicitação": request_date,
            "D+ Conversão": conv_days if liq_info is not None else "N/A",
            "D+ Liquidação": liq_days if liq_info is not None else "N/A",
            "Contagem": count_type if liq_info is not None else "N/A",
            "Data Cotização": cotizacao_date,
            "Data Liquidação": liquidacao_date,
            "Total D+": total_days,
            "Match Encontrado": matched,
        })

    return pd.DataFrame(results)


def simulate_portfolio_evolution(portfolio_df, movements_df, pl_total):
    """Simulate portfolio at each relevant liquidation date."""
    if movements_df.empty:
        return pd.DataFrame()

    # Collect all unique liquidation dates
    all_dates = sorted(movements_df["Data Liquidação"].unique())

    snapshots = []
    for target_date in all_dates:
        snapshot = portfolio_df.copy()
        snapshot["Financeiro Ajustado"] = snapshot["FINANCEIRO"].copy()

        # Apply movements that have liquidated by target_date
        for _, mov in movements_df.iterrows():
            if mov["Data Liquidação"] <= target_date:
                fund_mask = snapshot["ATIVO"].str.upper().str.contains(
                    str(mov["Fundo"]).upper()[:20], na=False, regex=False
                )
                if mov["Operação"] == "Resgate":
                    snapshot.loc[fund_mask, "Financeiro Ajustado"] -= mov["Valor (R$)"]
                else:
                    snapshot.loc[fund_mask, "Financeiro Ajustado"] += mov["Valor (R$)"]

        # Recalculate total and percentages
        total_adjusted = snapshot["Financeiro Ajustado"].sum()
        snapshot["% PL Ajustado"] = (
            snapshot["Financeiro Ajustado"] / total_adjusted * 100
        ).round(2)
        snapshot["Data Referência"] = target_date

        snapshots.append(snapshot)

    if snapshots:
        return pd.concat(snapshots, ignore_index=True)
    return pd.DataFrame()


def export_to_excel(portfolio_df, movements_df, evolution_df, carteira_info):
    """Export simulation results to Excel."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if carteira_info is not None and not carteira_info.empty:
            carteira_info.to_excel(writer, sheet_name="Carteira Info", index=False)
        if portfolio_df is not None and not portfolio_df.empty:
            portfolio_df.to_excel(writer, sheet_name="Posição Atual", index=False)
        if movements_df is not None and not movements_df.empty:
            # Convert dates to string for Excel compatibility
            mov_export = movements_df.copy()
            for col in mov_export.columns:
                if pd.api.types.is_datetime64_any_dtype(mov_export[col]):
                    mov_export[col] = mov_export[col].dt.strftime("%d/%m/%Y")
            mov_export.to_excel(writer, sheet_name="Movimentos", index=False)
        if evolution_df is not None and not evolution_df.empty:
            evo_export = evolution_df.copy()
            for col in evo_export.columns:
                if pd.api.types.is_datetime64_any_dtype(evo_export[col]):
                    evo_export[col] = evo_export[col].dt.strftime("%d/%m/%Y")
            evo_export.to_excel(writer, sheet_name="Evolução Carteira", index=False)
    return output.getvalue()


# ─────────────────────────────────────────────────────────
# LOAD LIQUIDATION DATA
# ─────────────────────────────────────────────────────────
liquid_df = load_liquidation_data()

# ─────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────
if "movements" not in st.session_state:
    st.session_state.movements = []
if "portfolio_loaded" not in st.session_state:
    st.session_state.portfolio_loaded = False

# ─────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("Simulador de Realocação")
    st.caption("TAG Investimentos")
    st.divider()

    page = st.radio(
        "Navegação",
        [
            "📂 Importar Carteira",
            "📋 Posição Atual",
            "🔄 Cadastrar Movimentos",
            "📊 Simulação",
            "📅 Dados de Liquidação",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"Base de liquidação: {len(liquid_df)} fundos carregados")

# ─────────────────────────────────────────────────────────
# PAGE: IMPORTAR CARTEIRA
# ─────────────────────────────────────────────────────────
if page == "📂 Importar Carteira":
    st.header("📂 Importar Carteira")
    st.markdown(
        "Faça upload do arquivo de **Posição Projetada** no formato padrão "
        "(`.xlsx` com abas: *Carteira e Caixa*, *Ativos*, *Provisões*, *Boletas Em Andamento*)."
    )

    uploaded = st.file_uploader(
        "Selecione o arquivo da carteira",
        type=["xlsx", "xls"],
        help="Arquivo Posição_Projetada_Carteira_XXX.xlsx",
    )

    if uploaded:
        with st.spinner("Processando arquivo..."):
            sheets = parse_portfolio_file(uploaded)

        if "ativos" in sheets:
            st.session_state.portfolio_sheets = sheets
            st.session_state.portfolio_loaded = True
            st.session_state.uploaded_filename = uploaded.name

            st.success(f"Carteira carregada com sucesso! ({uploaded.name})")

            # Show summary
            carteira = sheets.get("carteira")
            ativos = sheets["ativos"]

            if carteira is not None and not carteira.empty:
                col1, col2, col3, col4 = st.columns(4)
                row = carteira.iloc[0]
                with col1:
                    nome_carteira = str(row.get("CARTEIRA", "N/A"))
                    st.metric("Carteira", nome_carteira)
                with col2:
                    pl = row.get("PL PROJETADO", row.get("PL FECHAMENTO", 0))
                    st.metric("PL Projetado", f"R$ {pl:,.2f}")
                with col3:
                    st.metric("Qtde Ativos", len(ativos))
                with col4:
                    caixa_pct = row.get("% PL (CAIXA)", 0)
                    st.metric("Caixa (% PL)", f"{caixa_pct:.2f}%")

            # Match with liquidation data
            st.subheader("Correspondência com dados de liquidação")
            cod_col = find_col(ativos, "CÓD. ATIVO", "COD. ATIVO", "CODIGO")
            match_results = []
            for _, ativo in ativos.iterrows():
                fund_name = str(ativo.get("ATIVO", ""))
                fund_code = ativo.get(cod_col, None) if cod_col else None
                liq = match_fund_liquidation(fund_name, fund_code, liquid_df)
                match_results.append({
                    "Ativo": fund_name,
                    "Código": fund_code,
                    "Match": "✅" if liq is not None else "❌",
                    "D+ Conv. Resgate": int(liq["Conversão Resgate"]) if liq is not None else "-",
                    "D+ Liq. Resgate": int(liq["Liquid. Resgate"]) if liq is not None else "-",
                    "Contagem": str(liq["Contagem Resgate"]) if liq is not None else "-",
                })

            df_match = pd.DataFrame(match_results)
            matched_count = df_match["Match"].value_counts().get("✅", 0)
            st.info(
                f"**{matched_count}** de **{len(df_match)}** ativos encontrados "
                f"na base de liquidação."
            )
            st.dataframe(df_match, use_container_width=True, hide_index=True)
        else:
            st.error("Arquivo não contém a aba 'Ativos'. Verifique o formato.")

# ─────────────────────────────────────────────────────────
# PAGE: POSIÇÃO ATUAL
# ─────────────────────────────────────────────────────────
elif page == "📋 Posição Atual":
    st.header("📋 Posição Atual da Carteira")

    if not st.session_state.portfolio_loaded:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Carteira** primeiro.")
    else:
        sheets = st.session_state.portfolio_sheets
        ativos = sheets["ativos"]
        carteira = sheets.get("carteira")

        if carteira is not None and not carteira.empty:
            row = carteira.iloc[0]
            col1, col2, col3 = st.columns(3)
            with col1:
                pl = row.get("PL PROJETADO", row.get("PL FECHAMENTO", 0))
                st.metric("PL Total", f"R$ {pl:,.2f}")
            with col2:
                caixa = row.get("CAIXA", 0)
                st.metric("Caixa", f"R$ {caixa:,.2f}")
            with col3:
                liq_d0 = row.get("LIQUIDEZ D0", 0)
                st.metric("Liquidez D0", f"R$ {liq_d0:,.2f}")

        # Table
        st.subheader("Ativos")
        # Use find_col for columns that may have encoding issues
        estrategia_col = find_col(ativos, "ESTRATÉGIA", "ESTRATEGIA")
        preco_col = find_col(ativos, "PREÇO", "PRECO")
        display_col_candidates = [
            "ATIVO", "CLASSE",
            estrategia_col or "ESTRATÉGIA",
            "QUANTIDADE",
            preco_col or "PREÇO",
            "FINANCEIRO", "% PL",
        ]
        available_cols = [c for c in display_col_candidates if c and c in ativos.columns]
        df_display = ativos[available_cols].copy()

        # Build format dict dynamically
        fmt = {"FINANCEIRO": "R$ {:,.2f}", "QUANTIDADE": "{:,.2f}", "% PL": "{:.2f}%"}
        if preco_col and preco_col in df_display.columns:
            fmt[preco_col] = "R$ {:,.6f}"

        st.dataframe(
            df_display.style.format(fmt),
            use_container_width=True,
            hide_index=True,
            height=500,
        )

        # Chart
        st.subheader("Alocação por Ativo")
        fig = px.pie(
            ativos,
            values="FINANCEIRO",
            names="ATIVO",
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # By strategy
        st.subheader("Alocação por Estratégia")
        strat_col = find_col(ativos, "ESTRATÉGIA", "ESTRATEGIA")
        if strat_col and strat_col in ativos.columns:
            strat = ativos.groupby(strat_col)["FINANCEIRO"].sum().reset_index()
            fig2 = px.bar(
                strat,
                x=strat_col,
                y="FINANCEIRO",
                text_auto=",.0f",
            )
            fig2.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig2, use_container_width=True)

        # Provisões
        provisoes = sheets.get("provisoes")
        if provisoes is not None and not provisoes.empty:
            st.subheader("Provisões")
            st.dataframe(provisoes, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────
# PAGE: CADASTRAR MOVIMENTOS
# ─────────────────────────────────────────────────────────
elif page == "🔄 Cadastrar Movimentos":
    st.header("🔄 Cadastrar Movimentos")

    if not st.session_state.portfolio_loaded:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Carteira** primeiro.")
    else:
        ativos = st.session_state.portfolio_sheets["ativos"]
        fund_names = ativos["ATIVO"].tolist()

        st.subheader("Novo Movimento")

        with st.form("movement_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                operation = st.selectbox("Operação", ["Resgate", "Aplicação"])
                fund = st.selectbox("Fundo/Ativo", fund_names)
            with col2:
                value = st.number_input(
                    "Valor (R$)",
                    min_value=0.01,
                    step=1000.0,
                    format="%.2f",
                )
                request_date = st.date_input(
                    "Data de Solicitação",
                    value=datetime.today(),
                )

            submitted = st.form_submit_button("Adicionar Movimento", type="primary")

            if submitted:
                fund_row = ativos[ativos["ATIVO"] == fund].iloc[0]
                mov = {
                    "fund_name": fund,
                    "fund_code": fund_row.get(find_col(ativos, "CÓD. ATIVO", "COD. ATIVO") or "CÓD. ATIVO", None),
                    "operation": operation,
                    "value": value,
                    "request_date": pd.Timestamp(request_date),
                }
                st.session_state.movements.append(mov)
                st.success(f"Movimento adicionado: {operation} de R$ {value:,.2f} em {fund}")

        # --- Realocação rápida ---
        st.divider()
        st.subheader("Realocação Rápida (Vender X → Comprar Y)")

        with st.form("realloc_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                sell_fund = st.selectbox("Resgatar de", fund_names, key="sell")
            with col2:
                buy_fund = st.selectbox("Aplicar em", fund_names, key="buy")
            with col3:
                realloc_value = st.number_input(
                    "Valor (R$)", min_value=0.01, step=1000.0, format="%.2f", key="realloc_val"
                )
            realloc_date = st.date_input("Data de Solicitação", value=datetime.today(), key="realloc_date")
            realloc_submitted = st.form_submit_button("Realizar Realocação", type="primary")

            if realloc_submitted:
                sell_row = ativos[ativos["ATIVO"] == sell_fund].iloc[0]
                buy_row = ativos[ativos["ATIVO"] == buy_fund].iloc[0]
                st.session_state.movements.append({
                    "fund_name": sell_fund,
                    "fund_code": sell_row.get("CÓD. ATIVO", None),
                    "operation": "Resgate",
                    "value": realloc_value,
                    "request_date": pd.Timestamp(realloc_date),
                })
                st.session_state.movements.append({
                    "fund_name": buy_fund,
                    "fund_code": buy_row.get("CÓD. ATIVO", None),
                    "operation": "Aplicação",
                    "value": realloc_value,
                    "request_date": pd.Timestamp(realloc_date),
                })
                st.success(
                    f"Realocação adicionada: Resgate R$ {realloc_value:,.2f} de {sell_fund} "
                    f"→ Aplicação em {buy_fund}"
                )

        # Show current movements
        st.divider()
        st.subheader(f"Movimentos Cadastrados ({len(st.session_state.movements)})")

        if st.session_state.movements:
            mov_display = pd.DataFrame([
                {
                    "Fundo": m["fund_name"],
                    "Operação": m["operation"],
                    "Valor (R$)": m["value"],
                    "Data Solicitação": m["request_date"].strftime("%d/%m/%Y"),
                }
                for m in st.session_state.movements
            ])
            st.dataframe(mov_display, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Limpar Todos os Movimentos", type="secondary"):
                    st.session_state.movements = []
                    st.rerun()
            with col2:
                if st.button("↩️ Remover Último Movimento", type="secondary"):
                    st.session_state.movements.pop()
                    st.rerun()
        else:
            st.info("Nenhum movimento cadastrado ainda.")

# ─────────────────────────────────────────────────────────
# PAGE: SIMULAÇÃO
# ─────────────────────────────────────────────────────────
elif page == "📊 Simulação":
    st.header("📊 Simulação de Realocação")

    if not st.session_state.portfolio_loaded:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Carteira** primeiro.")
    elif not st.session_state.movements:
        st.warning("Nenhum movimento cadastrado. Vá em **🔄 Cadastrar Movimentos** primeiro.")
    else:
        sheets = st.session_state.portfolio_sheets
        ativos = sheets["ativos"]
        carteira = sheets.get("carteira")

        pl_total = 0
        if carteira is not None and not carteira.empty:
            pl_total = carteira.iloc[0].get("PL PROJETADO", carteira.iloc[0].get("PL FECHAMENTO", 0))

        # Compute liquidation dates
        movements_result = compute_liquidation_dates(st.session_state.movements, liquid_df)

        # ---- Plano de Movimentos ----
        st.subheader("Plano de Movimentos")
        st.dataframe(
            movements_result.style.format({
                "Valor (R$)": "R$ {:,.2f}",
            }).apply(
                lambda row: [
                    "background-color: #1a472a" if row["Match Encontrado"] else "background-color: #4a1a1a"
                ] * len(row),
                axis=1,
            ),
            use_container_width=True,
            hide_index=True,
        )

        # ---- Timeline ----
        st.subheader("Timeline de Liquidação")
        timeline_data = movements_result.copy()
        timeline_data["Label"] = (
            timeline_data["Operação"] + " - " +
            timeline_data["Fundo"].str[:30] + " (R$ " +
            timeline_data["Valor (R$)"].apply(lambda x: f"{x:,.0f}") + ")"
        )

        fig_timeline = px.timeline(
            timeline_data,
            x_start="Data Solicitação",
            x_end="Data Liquidação",
            y="Label",
            color="Operação",
            color_discrete_map={"Resgate": "#e74c3c", "Aplicação": "#2ecc71"},
        )
        fig_timeline.update_layout(
            height=max(300, len(timeline_data) * 50),
            yaxis_title="",
            xaxis_title="Data",
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # ---- Evolução da Carteira ----
        st.subheader("Evolução da Carteira por Data de Liquidação")

        evolution = simulate_portfolio_evolution(ativos, movements_result, pl_total)

        if not evolution.empty:
            # Summary by date
            dates = sorted(evolution["Data Referência"].unique())

            tabs = st.tabs([d.strftime("%d/%m/%Y") for d in dates])
            for i, (tab, date) in enumerate(zip(tabs, dates)):
                with tab:
                    snap = evolution[evolution["Data Referência"] == date]
                    total_adj = snap["Financeiro Ajustado"].sum()

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("PL Ajustado", f"R$ {total_adj:,.2f}")
                    with col2:
                        delta = total_adj - ativos["FINANCEIRO"].sum()
                        st.metric("Variação", f"R$ {delta:,.2f}")
                    with col3:
                        delta_pct = (delta / ativos["FINANCEIRO"].sum()) * 100 if ativos["FINANCEIRO"].sum() > 0 else 0
                        st.metric("Variação %", f"{delta_pct:+.2f}%")

                    display = snap[["ATIVO", "FINANCEIRO", "Financeiro Ajustado", "% PL", "% PL Ajustado"]].copy()
                    display.columns = ["Ativo", "Financeiro Atual", "Financeiro Ajustado", "% PL Atual", "% PL Ajustado"]
                    display["Δ Financeiro"] = display["Financeiro Ajustado"] - display["Financeiro Atual"]
                    display["Δ % PL"] = display["% PL Ajustado"] - display["% PL Atual"]

                    st.dataframe(
                        display.style.format({
                            "Financeiro Atual": "R$ {:,.2f}",
                            "Financeiro Ajustado": "R$ {:,.2f}",
                            "% PL Atual": "{:.2f}%",
                            "% PL Ajustado": "{:.2f}%",
                            "Δ Financeiro": "R$ {:,.2f}",
                            "Δ % PL": "{:+.2f} p.p.",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Comparison chart
                    fig_comp = go.Figure()
                    fig_comp.add_trace(go.Bar(
                        name="Antes",
                        x=display["Ativo"],
                        y=display["% PL Atual"],
                        marker_color="#3498db",
                    ))
                    fig_comp.add_trace(go.Bar(
                        name="Depois",
                        x=display["Ativo"],
                        y=display["% PL Ajustado"],
                        marker_color="#e67e22",
                    ))
                    fig_comp.update_layout(
                        barmode="group",
                        height=400,
                        xaxis_tickangle=-45,
                        yaxis_title="% PL",
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)

        # ---- Exportar ----
        st.divider()
        st.subheader("Exportar Resultado")

        col1, col2 = st.columns(2)
        with col1:
            excel_data = export_to_excel(
                ativos,
                movements_result,
                evolution,
                carteira,
            )
            st.download_button(
                label="📥 Baixar Excel",
                data=excel_data,
                file_name=f"simulacao_realocacao_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

# ─────────────────────────────────────────────────────────
# PAGE: DADOS DE LIQUIDAÇÃO
# ─────────────────────────────────────────────────────────
elif page == "📅 Dados de Liquidação":
    st.header("📅 Base de Dados de Liquidação")
    st.markdown(f"**{len(liquid_df)} fundos** carregados na base.")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Buscar fundo", placeholder="Nome ou código...")
    with col2:
        cat_filter = st.multiselect(
            "Categoria",
            options=sorted(liquid_df["Categoria"].dropna().unique()),
        )
    with col3:
        gestor_filter = st.multiselect(
            "Gestor",
            options=sorted(liquid_df["Gestor"].dropna().unique()),
        )

    filtered = liquid_df.copy()
    if search:
        mask = (
            filtered["Apelido"].str.contains(search, case=False, na=False) |
            filtered["Nome"].str.contains(search, case=False, na=False) |
            filtered["Código Anbima"].astype(str).str.contains(search, na=False)
        )
        filtered = filtered[mask]
    if cat_filter:
        filtered = filtered[filtered["Categoria"].isin(cat_filter)]
    if gestor_filter:
        filtered = filtered[filtered["Gestor"].isin(gestor_filter)]

    display_cols = [
        "Apelido", "Código Anbima", "Conversão Resgate", "Liquid. Resgate",
        "Contagem Resgate", "Conversão Aplic.", "Categoria", "Gestor",
        "Administrador",
    ]
    available = [c for c in display_cols if c in filtered.columns]

    st.dataframe(
        filtered[available],
        use_container_width=True,
        hide_index=True,
        height=600,
    )

    # Stats
    st.subheader("Estatísticas de Liquidação")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            liquid_df,
            x="Conversão Resgate",
            nbins=30,
            title="Distribuição D+ Conversão Resgate",
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.histogram(
            liquid_df,
            x="Liquid. Resgate",
            nbins=30,
            title="Distribuição D+ Liquidação Resgate",
        )
        st.plotly_chart(fig2, use_container_width=True)
