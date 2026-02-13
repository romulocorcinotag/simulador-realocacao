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
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(strip_html)
    for col in ["Conversão Resgate", "Liquid. Resgate", "Conversão Aplic."]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def find_col(df, *candidates):
    """Find the first matching column from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    for c in candidates:
        for col in df.columns:
            if c.upper()[:6] in col.upper():
                return col
    return None


def parse_portfolio_file(uploaded_file):
    """Parse the uploaded portfolio file (Posição Projetada format)."""
    xl = pd.ExcelFile(uploaded_file)
    sheets = {}
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

    for key in sheet_map:
        sheets[key] = pd.read_excel(xl, sheet_name=sheet_map[key])
    return sheets


def add_business_days(start_date, num_days, count_type="Úteis"):
    """Add business or calendar days to a date."""
    if num_days == 0:
        return start_date
    if count_type == "Úteis":
        current = start_date
        added = 0
        while added < num_days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current
    else:
        return start_date + timedelta(days=num_days)


def is_stock_ticker(name):
    """Check if the asset name looks like a B3 stock/ETF ticker."""
    if not name:
        return False
    return bool(re.match(r'^[A-Z]{4}\d{1,2}$', str(name).strip().upper()))


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
        for col in ["Apelido", "Nome"]:
            match = liquid_df[liquid_df[col].str.upper().str.strip() == name_clean]
            if not match.empty:
                return match.iloc[0]
        for col in ["Apelido", "Nome"]:
            for idx, row in liquid_df.iterrows():
                liq_name = str(row[col]).strip().upper()
                if len(name_clean) > 5 and (name_clean in liq_name or liq_name in name_clean):
                    return row

    check_name = fund_name if fund_name else fund_code
    if check_name and is_stock_ticker(str(check_name)):
        return pd.Series({
            "Apelido": str(check_name).upper(),
            "Conversão Resgate": 0, "Liquid. Resgate": 2,
            "Conversão Aplic.": 0, "Contagem Resgate": "Úteis",
            "Código Anbima": "", "Categoria": "Ação/ETF B3",
        })
    return None


def extract_provisions_as_movements(provisoes_df, ativos_df):
    """
    Extract provisions from the portfolio file and convert them to movements.
    Provisions with positive values = incoming cash (resgates liquidando)
    Provisions with negative values = outgoing cash (passivos/débitos)
    """
    movements = []
    if provisoes_df is None or provisoes_df.empty:
        return movements

    desc_col = find_col(provisoes_df, "DESCRIÇÃO", "DESCRICAO") or provisoes_df.columns[0]
    data_op_col = find_col(provisoes_df, "DATA OPERAÇÃO", "DATA OPERACAO") or provisoes_df.columns[1]
    data_liq_col = find_col(provisoes_df, "DATA LIQUIDAÇÃO", "DATA LIQUIDACAO") or provisoes_df.columns[2]
    valor_col = find_col(provisoes_df, "VALOR") or provisoes_df.columns[3]

    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO") if ativos_df is not None else None

    for _, row in provisoes_df.iterrows():
        desc = str(row[desc_col])
        valor = row[valor_col]
        data_liq = row[data_liq_col]
        data_op = row[data_op_col]

        # Parse dates
        if isinstance(data_liq, str):
            try:
                data_liq = pd.to_datetime(data_liq, dayfirst=True)
            except Exception:
                continue
        if isinstance(data_op, str):
            try:
                data_op = pd.to_datetime(data_op, dayfirst=True)
            except Exception:
                data_op = data_liq

        if pd.isna(data_liq) or pd.isna(valor):
            continue

        # Try to extract fund code from description like "(1103)" or "(394)"
        code_match = re.search(r'\((\d+)\)', desc)
        fund_code = code_match.group(1) if code_match else None
        fund_name = ""

        # Try to match fund code to an asset in the portfolio
        if fund_code and ativos_df is not None and cod_col:
            asset_match = ativos_df[ativos_df[cod_col].astype(str) == fund_code]
            if not asset_match.empty:
                fund_name = str(asset_match.iloc[0].get("ATIVO", ""))

        # Determine type
        if valor > 0:
            # Positive = incoming cash (resgate de fundo liquidando)
            op_type = "Resgate (Provisão)"
            source = "provisao_credito"
        else:
            # Negative = outgoing cash (débito/passivo)
            op_type = "Débito/Passivo"
            source = "provisao_debito"

        movements.append({
            "fund_name": fund_name if fund_name else desc[:60],
            "fund_code": fund_code,
            "operation": op_type,
            "value": abs(valor),
            "request_date": pd.Timestamp(data_op),
            "liquidation_date": pd.Timestamp(data_liq),
            "description": desc,
            "source": source,
        })

    return movements


def compute_liquidation_date_for_new_movement(mov, liquid_df):
    """Compute liquidation date for a manually-added movement."""
    fund_name = mov["fund_name"]
    fund_code = mov.get("fund_code", None)
    operation = mov["operation"]
    request_date = mov["request_date"]

    liq_info = match_fund_liquidation(fund_name, fund_code, liquid_df)

    if liq_info is not None:
        if "Resgate" in operation:
            conv_days = int(liq_info["Conversão Resgate"])
            liq_days = int(liq_info["Liquid. Resgate"])
            count_type = str(liq_info.get("Contagem Resgate", "Úteis"))
            if count_type not in ["Úteis", "Corridos"]:
                count_type = "Úteis"
        else:
            conv_days = int(liq_info["Conversão Aplic."])
            liq_days = 0
            count_type = "Úteis"

        cotizacao_date = add_business_days(request_date, conv_days, count_type)
        liquidacao_date = add_business_days(cotizacao_date, liq_days, count_type)
        return liquidacao_date, f"D+{conv_days}+{liq_days}", True
    else:
        return request_date, "N/A", False


def build_evolution_table(ativos_df, all_movements, caixa_initial):
    """
    Build the main evolution table: rows=assets, columns=dates.
    Each cell shows the financial position of that asset on that date.
    Includes Caixa row that receives/pays cash from movements.
    """
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    # Build asset list with initial positions
    assets = []
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        name = str(row.get("ATIVO", ""))
        fin = float(row.get("FINANCEIRO", 0))
        pct = float(row.get("% PL", 0))
        assets.append({
            "code": code,
            "name": name,
            "financeiro_atual": fin,
            "pct_pl_atual": pct,
        })

    # Collect all unique liquidation dates and sort them
    all_dates = sorted(set(
        pd.Timestamp(m["liquidation_date"]) for m in all_movements
        if pd.notna(m.get("liquidation_date"))
    ))

    if not all_dates:
        return None, None, None

    # Build the evolution: for each date, compute cumulative impact
    # Result: dict of {date: {code: adjustment}}
    date_adjustments = {}
    caixa_adjustments = {}

    for d in all_dates:
        date_adjustments[d] = {}
        caixa_adj = 0.0

        for mov in all_movements:
            liq_date = pd.Timestamp(mov["liquidation_date"])
            if liq_date > d:
                continue  # Not yet liquidated

            fund_code = str(mov.get("fund_code", ""))
            fund_name = mov["fund_name"]
            value = mov["value"]
            op = mov["operation"]

            # Find matching asset
            matched_code = None
            if fund_code:
                for a in assets:
                    if a["code"] == fund_code:
                        matched_code = a["code"]
                        break
            if not matched_code and fund_name:
                for a in assets:
                    if fund_name.upper()[:20] in a["name"].upper() or a["name"].upper()[:20] in fund_name.upper():
                        matched_code = a["code"]
                        break

            if "Resgate" in op or op == "Resgate (Provisão)":
                # Resgate: subtract from fund, add to caixa
                if matched_code:
                    date_adjustments[d][matched_code] = date_adjustments[d].get(matched_code, 0) - value
                caixa_adj += value
            elif "Aplicação" in op:
                # Aplicação: add to fund, subtract from caixa
                if matched_code:
                    date_adjustments[d][matched_code] = date_adjustments[d].get(matched_code, 0) + value
                caixa_adj -= value
            elif op == "Débito/Passivo":
                # Débito: subtract from caixa
                caixa_adj -= value

        caixa_adjustments[d] = caixa_adj

    # Build the table
    # Rows: assets + Caixa + Total
    rows_financeiro = []
    rows_pct = []

    for a in assets:
        row_fin = {"Ativo": a["name"][:45], "Código": a["code"], "Atual (R$)": a["financeiro_atual"]}
        row_pct = {"Ativo": a["name"][:45], "Código": a["code"], "Atual (%)": a["pct_pl_atual"]}

        for d in all_dates:
            adj = date_adjustments[d].get(a["code"], 0)
            row_fin[d.strftime("%d/%m/%Y")] = a["financeiro_atual"] + adj
            # % will be calculated after totals

        rows_financeiro.append(row_fin)

    # Caixa row
    caixa_row_fin = {"Ativo": "💰 CAIXA", "Código": "CAIXA", "Atual (R$)": caixa_initial}
    for d in all_dates:
        caixa_row_fin[d.strftime("%d/%m/%Y")] = caixa_initial + caixa_adjustments[d]
    rows_financeiro.append(caixa_row_fin)

    df_fin = pd.DataFrame(rows_financeiro)

    # Calculate totals
    date_cols = [d.strftime("%d/%m/%Y") for d in all_dates]
    total_row = {"Ativo": "📊 TOTAL PL", "Código": "", "Atual (R$)": df_fin["Atual (R$)"].sum()}
    for dc in date_cols:
        total_row[dc] = df_fin[dc].sum()
    rows_financeiro.append(total_row)
    df_fin = pd.DataFrame(rows_financeiro)

    # Now build % PL table
    rows_pct = []
    for _, r in df_fin.iterrows():
        if r["Ativo"] == "📊 TOTAL PL":
            continue
        row_pct = {
            "Ativo": r["Ativo"],
            "Código": r["Código"],
            "Atual (%)": (r["Atual (R$)"] / total_row["Atual (R$)"] * 100) if total_row["Atual (R$)"] != 0 else 0,
        }
        for dc in date_cols:
            total_on_date = total_row[dc]
            row_pct[dc] = (r[dc] / total_on_date * 100) if total_on_date != 0 else 0
        rows_pct.append(row_pct)

    # Total % row
    total_pct_row = {"Ativo": "📊 TOTAL PL", "Código": "", "Atual (%)": 100.0}
    for dc in date_cols:
        total_pct_row[dc] = 100.0
    rows_pct.append(total_pct_row)
    df_pct = pd.DataFrame(rows_pct)

    # Movements summary table
    mov_rows = []
    for m in all_movements:
        mov_rows.append({
            "Fundo": m["fund_name"][:45],
            "Código": m.get("fund_code", ""),
            "Operação": m["operation"],
            "Valor (R$)": m["value"],
            "Data Solicitação": m["request_date"].strftime("%d/%m/%Y") if pd.notna(m.get("request_date")) else "",
            "Data Liquidação": m["liquidation_date"].strftime("%d/%m/%Y") if pd.notna(m.get("liquidation_date")) else "",
            "Origem": m.get("source", "manual"),
        })
    df_mov = pd.DataFrame(mov_rows)

    return df_fin, df_pct, df_mov


def export_to_excel(df_fin, df_pct, df_mov, carteira_info):
    """Export simulation results to Excel."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if carteira_info is not None and not carteira_info.empty:
            carteira_info.to_excel(writer, sheet_name="Carteira Info", index=False)
        if df_fin is not None and not df_fin.empty:
            df_fin.to_excel(writer, sheet_name="Evolução R$", index=False)
        if df_pct is not None and not df_pct.empty:
            df_pct.to_excel(writer, sheet_name="Evolução % PL", index=False)
        if df_mov is not None and not df_mov.empty:
            df_mov.to_excel(writer, sheet_name="Movimentos", index=False)
    return output.getvalue()


# ─────────────────────────────────────────────────────────
# LOAD LIQUIDATION DATA
# ─────────────────────────────────────────────────────────
liquid_df = load_liquidation_data()

# ─────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────
if "new_movements" not in st.session_state:
    st.session_state.new_movements = []
if "portfolio_loaded" not in st.session_state:
    st.session_state.portfolio_loaded = False

# ─────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Simulador de Realocação")
    st.caption("TAG Investimentos")
    st.divider()

    page = st.radio(
        "Navegação",
        [
            "📂 Importar Carteira",
            "📋 Posição Atual",
            "📊 Projeção da Carteira",
            "🔄 Nova Realocação",
            "📅 Dados de Liquidação",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"Base de liquidação: {len(liquid_df)} fundos")
    if st.session_state.portfolio_loaded:
        st.caption(f"✅ Carteira: {st.session_state.get('uploaded_filename', '')}")

# ═════════════════════════════════════════════════════════
# PAGE: IMPORTAR CARTEIRA
# ═════════════════════════════════════════════════════════
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

            # Extract provisions as pending movements
            ativos = sheets["ativos"]
            provisoes = sheets.get("provisoes")
            prov_movements = extract_provisions_as_movements(provisoes, ativos)
            st.session_state.provision_movements = prov_movements

            st.success(f"✅ Carteira carregada com sucesso! ({uploaded.name})")

            # Show summary
            carteira = sheets.get("carteira")
            if carteira is not None and not carteira.empty:
                row = carteira.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Carteira", str(row.get("CARTEIRA", "N/A")))
                with col2:
                    pl = row.get("PL PROJETADO", row.get("PL FECHAMENTO", 0))
                    st.metric("PL Projetado", f"R$ {pl:,.2f}")
                with col3:
                    st.metric("Qtde Ativos", len(ativos))
                with col4:
                    st.metric("Provisões", len(prov_movements))

            # Show provisions extracted
            if prov_movements:
                st.subheader("📌 Movimentos Pendentes Extraídos das Provisões")
                prov_df = pd.DataFrame([{
                    "Fundo": m["fund_name"][:45],
                    "Operação": m["operation"],
                    "Valor (R$)": m["value"],
                    "Data Liquidação": m["liquidation_date"].strftime("%d/%m/%Y"),
                    "Descrição": m["description"][:60],
                } for m in prov_movements])
                st.dataframe(prov_df, use_container_width=True, hide_index=True)

            # Show match with liquidation data
            st.subheader("Correspondência com dados de liquidação")
            cod_col = find_col(ativos, "CÓD. ATIVO", "COD. ATIVO", "CODIGO")
            match_results = []
            for _, ativo in ativos.iterrows():
                fund_name = str(ativo.get("ATIVO", ""))
                fund_code = ativo.get(cod_col, None) if cod_col else None
                liq = match_fund_liquidation(fund_name, fund_code, liquid_df)
                match_results.append({
                    "Ativo": fund_name[:45],
                    "Código": fund_code,
                    "Match": "✅" if liq is not None else "❌",
                    "D+ Conv. Resgate": int(liq["Conversão Resgate"]) if liq is not None else "-",
                    "D+ Liq. Resgate": int(liq["Liquid. Resgate"]) if liq is not None else "-",
                    "Contagem": str(liq.get("Contagem Resgate", "")) if liq is not None else "-",
                })
            df_match = pd.DataFrame(match_results)
            matched_count = (df_match["Match"] == "✅").sum()
            st.info(f"**{matched_count}** de **{len(df_match)}** ativos encontrados na base de liquidação.")
            st.dataframe(df_match, use_container_width=True, hide_index=True)
        else:
            st.error("Arquivo não contém a aba 'Ativos'. Verifique o formato.")


# ═════════════════════════════════════════════════════════
# PAGE: POSIÇÃO ATUAL
# ═════════════════════════════════════════════════════════
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
        estrategia_col = find_col(ativos, "ESTRATÉGIA", "ESTRATEGIA")
        preco_col = find_col(ativos, "PREÇO", "PRECO")
        display_col_candidates = [
            "ATIVO", "CLASSE",
            estrategia_col or "ESTRATÉGIA",
            "QUANTIDADE", preco_col or "PREÇO",
            "FINANCEIRO", "% PL",
        ]
        available_cols = [c for c in display_col_candidates if c and c in ativos.columns]
        df_display = ativos[available_cols].copy()
        fmt = {"FINANCEIRO": "R$ {:,.2f}", "QUANTIDADE": "{:,.2f}", "% PL": "{:.2f}%"}
        if preco_col and preco_col in df_display.columns:
            fmt[preco_col] = "R$ {:,.6f}"

        st.dataframe(df_display.style.format(fmt), use_container_width=True, hide_index=True, height=400)

        # Charts side by side
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Alocação por Ativo")
            fig = px.pie(ativos, values="FINANCEIRO", names="ATIVO", hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=450, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            strat_col = find_col(ativos, "ESTRATÉGIA", "ESTRATEGIA")
            if strat_col and strat_col in ativos.columns:
                st.subheader("Alocação por Estratégia")
                strat = ativos.groupby(strat_col)["FINANCEIRO"].sum().reset_index()
                fig2 = px.bar(strat, x=strat_col, y="FINANCEIRO", text_auto=",.0f")
                fig2.update_layout(xaxis_tickangle=-45, height=450)
                st.plotly_chart(fig2, use_container_width=True)

        # Provisões
        provisoes = sheets.get("provisoes")
        if provisoes is not None and not provisoes.empty:
            st.subheader("Provisões Pendentes")
            st.dataframe(provisoes, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════
# PAGE: PROJEÇÃO DA CARTEIRA (MAIN VIEW)
# ═════════════════════════════════════════════════════════
elif page == "📊 Projeção da Carteira":
    st.header("📊 Projeção da Carteira por Data de Liquidação")

    if not st.session_state.portfolio_loaded:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Carteira** primeiro.")
    else:
        sheets = st.session_state.portfolio_sheets
        ativos = sheets["ativos"]
        carteira = sheets.get("carteira")

        # Get initial caixa
        caixa_initial = 0.0
        if carteira is not None and not carteira.empty:
            caixa_initial = float(carteira.iloc[0].get("CAIXA", 0))

        # Combine provision movements + new manual movements
        provision_movs = st.session_state.get("provision_movements", [])
        new_movs = st.session_state.get("new_movements", [])
        all_movements = provision_movs + new_movs

        if not all_movements:
            st.info("Nenhum movimento pendente encontrado nas provisões e nenhuma realocação cadastrada.")
        else:
            # Build the evolution tables
            df_fin, df_pct, df_mov = build_evolution_table(ativos, all_movements, caixa_initial)

            if df_fin is not None:
                # ── Summary metrics ──
                date_cols = [c for c in df_fin.columns if c not in ["Ativo", "Código", "Atual (R$)"]]
                total_row = df_fin[df_fin["Ativo"] == "📊 TOTAL PL"].iloc[0]

                if date_cols:
                    st.subheader("Resumo por Data")
                    metric_cols = st.columns(min(len(date_cols) + 1, 6))
                    with metric_cols[0]:
                        st.metric("Hoje", f"R$ {total_row['Atual (R$)']:,.0f}")
                    for i, dc in enumerate(date_cols[:5]):
                        with metric_cols[min(i + 1, 5)]:
                            val = total_row[dc]
                            delta = val - total_row["Atual (R$)"]
                            st.metric(dc, f"R$ {val:,.0f}", f"R$ {delta:,.0f}")

                st.divider()

                # ── Movimentos pendentes ──
                st.subheader("📌 Movimentos Considerados")
                with st.expander(f"Ver {len(all_movements)} movimentos", expanded=False):
                    st.dataframe(df_mov, use_container_width=True, hide_index=True)

                st.divider()

                # ── Main evolution table (R$) ──
                st.subheader("Evolução da Carteira (R$)")

                # Format the financial table
                format_dict_fin = {"Atual (R$)": "R$ {:,.2f}"}
                for dc in date_cols:
                    format_dict_fin[dc] = "R$ {:,.2f}"

                # Color rows: highlight total and caixa
                def highlight_special_rows(row):
                    if row["Ativo"] == "📊 TOTAL PL":
                        return ["background-color: #1a3a5c; font-weight: bold"] * len(row)
                    elif row["Ativo"] == "💰 CAIXA":
                        return ["background-color: #2d4a1a"] * len(row)
                    return [""] * len(row)

                styled_fin = (
                    df_fin.drop(columns=["Código"])
                    .style
                    .format(format_dict_fin)
                    .apply(highlight_special_rows, axis=1)
                )
                st.dataframe(styled_fin, use_container_width=True, hide_index=True, height=450)

                # ── Evolution table (% PL) ──
                st.subheader("Evolução da Carteira (% PL)")
                format_dict_pct = {"Atual (%)": "{:.2f}%"}
                for dc in date_cols:
                    format_dict_pct[dc] = "{:.2f}%"

                def highlight_special_rows_pct(row):
                    if row["Ativo"] == "📊 TOTAL PL":
                        return ["background-color: #1a3a5c; font-weight: bold"] * len(row)
                    elif row["Ativo"] == "💰 CAIXA":
                        return ["background-color: #2d4a1a"] * len(row)
                    return [""] * len(row)

                styled_pct = (
                    df_pct.drop(columns=["Código"])
                    .style
                    .format(format_dict_pct)
                    .apply(highlight_special_rows_pct, axis=1)
                )
                st.dataframe(styled_pct, use_container_width=True, hide_index=True, height=450)

                # ── Variation chart ──
                st.subheader("Variação % PL: Hoje vs Última Data")
                last_date_col = date_cols[-1] if date_cols else None
                if last_date_col:
                    chart_df = df_pct[~df_pct["Ativo"].isin(["📊 TOTAL PL"])].copy()
                    chart_df["Δ % PL"] = chart_df[last_date_col] - chart_df["Atual (%)"]

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name="Hoje",
                        x=chart_df["Ativo"],
                        y=chart_df["Atual (%)"],
                        marker_color="#3498db",
                    ))
                    fig.add_trace(go.Bar(
                        name=last_date_col,
                        x=chart_df["Ativo"],
                        y=chart_df[last_date_col],
                        marker_color="#e67e22",
                    ))
                    fig.update_layout(barmode="group", height=450, xaxis_tickangle=-30, yaxis_title="% PL")
                    st.plotly_chart(fig, use_container_width=True)

                # ── Timeline chart ──
                st.subheader("Timeline de Liquidação")
                timeline_data = df_mov[df_mov["Data Liquidação"] != ""].copy()
                if not timeline_data.empty:
                    timeline_data["Data Solicitação"] = pd.to_datetime(timeline_data["Data Solicitação"], dayfirst=True)
                    timeline_data["Data Liquidação"] = pd.to_datetime(timeline_data["Data Liquidação"], dayfirst=True)
                    # Ensure start < end for timeline
                    timeline_data.loc[
                        timeline_data["Data Solicitação"] == timeline_data["Data Liquidação"],
                        "Data Liquidação"
                    ] += timedelta(days=1)
                    timeline_data["Label"] = (
                        timeline_data["Operação"].str[:10] + " | " +
                        timeline_data["Fundo"].str[:25] +
                        " (R$ " + timeline_data["Valor (R$)"].apply(lambda x: f"{x:,.0f}") + ")"
                    )
                    fig_tl = px.timeline(
                        timeline_data, x_start="Data Solicitação", x_end="Data Liquidação",
                        y="Label", color="Operação",
                        color_discrete_map={
                            "Resgate (Provisão)": "#e74c3c",
                            "Débito/Passivo": "#9b59b6",
                            "Resgate": "#e74c3c",
                            "Aplicação": "#2ecc71",
                        },
                    )
                    fig_tl.update_layout(height=max(300, len(timeline_data) * 45), yaxis_title="")
                    st.plotly_chart(fig_tl, use_container_width=True)

                # ── Export ──
                st.divider()
                excel_data = export_to_excel(df_fin, df_pct, df_mov, carteira)
                st.download_button(
                    label="📥 Exportar para Excel",
                    data=excel_data,
                    file_name=f"projecao_carteira_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                )


# ═════════════════════════════════════════════════════════
# PAGE: NOVA REALOCAÇÃO
# ═════════════════════════════════════════════════════════
elif page == "🔄 Nova Realocação":
    st.header("🔄 Cadastrar Nova Realocação / Movimento")

    if not st.session_state.portfolio_loaded:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Carteira** primeiro.")
    else:
        ativos = st.session_state.portfolio_sheets["ativos"]
        fund_names = ativos["ATIVO"].tolist()
        cod_col = find_col(ativos, "CÓD. ATIVO", "COD. ATIVO")

        # ── Novo Movimento Individual ──
        st.subheader("Novo Movimento")
        with st.form("movement_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                operation = st.selectbox("Operação", ["Resgate", "Aplicação"])
                fund = st.selectbox("Fundo/Ativo", fund_names)
            with col2:
                value = st.number_input("Valor (R$)", min_value=0.01, step=10000.0, format="%.2f")
                request_date = st.date_input("Data de Solicitação", value=datetime.today())

            submitted = st.form_submit_button("➕ Adicionar Movimento", type="primary")

            if submitted:
                fund_row = ativos[ativos["ATIVO"] == fund].iloc[0]
                fund_code = str(fund_row[cod_col]) if cod_col else None
                mov = {
                    "fund_name": fund,
                    "fund_code": fund_code,
                    "operation": operation,
                    "value": value,
                    "request_date": pd.Timestamp(request_date),
                    "source": "manual",
                }
                # Compute liquidation date
                liq_date, d_plus, matched = compute_liquidation_date_for_new_movement(mov, liquid_df)
                mov["liquidation_date"] = liq_date
                mov["description"] = f"{operation} manual - {fund[:40]}"

                st.session_state.new_movements.append(mov)
                st.success(
                    f"✅ {operation} de R$ {value:,.2f} em **{fund[:40]}**\n\n"
                    f"📅 Liquidação: **{liq_date.strftime('%d/%m/%Y')}** ({d_plus})"
                )

        # ── Realocação Rápida ──
        st.divider()
        st.subheader("Realocação Rápida (Vender X → Comprar Y)")

        with st.form("realloc_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                sell_fund = st.selectbox("Resgatar de", fund_names, key="sell")
            with col2:
                buy_fund = st.selectbox("Aplicar em", fund_names, key="buy")
            with col3:
                realloc_value = st.number_input("Valor (R$)", min_value=0.01, step=10000.0, format="%.2f", key="rv")
            realloc_date = st.date_input("Data de Solicitação", value=datetime.today(), key="rd")
            realloc_submitted = st.form_submit_button("🔄 Realizar Realocação", type="primary")

            if realloc_submitted:
                sell_row = ativos[ativos["ATIVO"] == sell_fund].iloc[0]
                buy_row = ativos[ativos["ATIVO"] == buy_fund].iloc[0]
                sell_code = str(sell_row[cod_col]) if cod_col else None
                buy_code = str(buy_row[cod_col]) if cod_col else None

                # Resgate
                mov_sell = {
                    "fund_name": sell_fund, "fund_code": sell_code,
                    "operation": "Resgate", "value": realloc_value,
                    "request_date": pd.Timestamp(realloc_date), "source": "manual",
                    "description": f"Realocação: Resgate de {sell_fund[:30]}",
                }
                liq_sell, dp_sell, _ = compute_liquidation_date_for_new_movement(mov_sell, liquid_df)
                mov_sell["liquidation_date"] = liq_sell

                # Aplicação
                mov_buy = {
                    "fund_name": buy_fund, "fund_code": buy_code,
                    "operation": "Aplicação", "value": realloc_value,
                    "request_date": pd.Timestamp(realloc_date), "source": "manual",
                    "description": f"Realocação: Aplicação em {buy_fund[:30]}",
                }
                liq_buy, dp_buy, _ = compute_liquidation_date_for_new_movement(mov_buy, liquid_df)
                mov_buy["liquidation_date"] = liq_buy

                st.session_state.new_movements.append(mov_sell)
                st.session_state.new_movements.append(mov_buy)

                st.success(
                    f"✅ Realocação cadastrada!\n\n"
                    f"📤 Resgate de R$ {realloc_value:,.2f} de {sell_fund[:30]} → Liq: {liq_sell.strftime('%d/%m/%Y')} ({dp_sell})\n\n"
                    f"📥 Aplicação de R$ {realloc_value:,.2f} em {buy_fund[:30]} → Liq: {liq_buy.strftime('%d/%m/%Y')} ({dp_buy})"
                )

        # ── Movimentos manuais cadastrados ──
        st.divider()
        new_movs = st.session_state.new_movements
        st.subheader(f"Movimentos Manuais Cadastrados ({len(new_movs)})")

        if new_movs:
            mov_display = pd.DataFrame([{
                "Fundo": m["fund_name"][:40],
                "Operação": m["operation"],
                "Valor (R$)": m["value"],
                "Data Solicitação": m["request_date"].strftime("%d/%m/%Y"),
                "Data Liquidação": m["liquidation_date"].strftime("%d/%m/%Y"),
            } for m in new_movs])
            st.dataframe(mov_display, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Limpar Todos", type="secondary"):
                    st.session_state.new_movements = []
                    st.rerun()
            with col2:
                if st.button("↩️ Remover Último", type="secondary"):
                    st.session_state.new_movements.pop()
                    st.rerun()
        else:
            st.info("Nenhum movimento manual cadastrado. Os movimentos das provisões já aparecem automaticamente na projeção.")

        st.divider()
        st.markdown("💡 **Dica:** Após cadastrar, vá em **📊 Projeção da Carteira** para ver como fica a carteira em cada data de liquidação.")


# ═════════════════════════════════════════════════════════
# PAGE: DADOS DE LIQUIDAÇÃO
# ═════════════════════════════════════════════════════════
elif page == "📅 Dados de Liquidação":
    st.header("📅 Base de Dados de Liquidação")
    st.markdown(f"**{len(liquid_df)} fundos** carregados na base.")

    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Buscar fundo", placeholder="Nome ou código...")
    with col2:
        cat_filter = st.multiselect("Categoria", options=sorted(liquid_df["Categoria"].dropna().unique()))
    with col3:
        gestor_col = "Gestor" if "Gestor" in liquid_df.columns else None
        if gestor_col:
            gestor_filter = st.multiselect("Gestor", options=sorted(liquid_df[gestor_col].dropna().unique()))
        else:
            gestor_filter = []

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
    if gestor_filter and gestor_col:
        filtered = filtered[filtered[gestor_col].isin(gestor_filter)]

    display_cols = [
        "Apelido", "Código Anbima", "Conversão Resgate", "Liquid. Resgate",
        "Contagem Resgate", "Conversão Aplic.", "Categoria",
    ]
    if gestor_col:
        display_cols.append(gestor_col)
    if "Administrador" in filtered.columns:
        display_cols.append("Administrador")
    available = [c for c in display_cols if c in filtered.columns]

    st.dataframe(filtered[available], use_container_width=True, hide_index=True, height=600)

    st.subheader("Estatísticas de Liquidação")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(liquid_df, x="Conversão Resgate", nbins=30, title="D+ Conversão Resgate")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.histogram(liquid_df, x="Liquid. Resgate", nbins=30, title="D+ Liquidação Resgate")
        st.plotly_chart(fig2, use_container_width=True)
