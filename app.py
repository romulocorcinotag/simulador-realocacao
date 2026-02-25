import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
import re
import os
import base64

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Simulador de Realocação · TAG Investimentos",
    page_icon="https://taginvest.com.br/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

DADOS_LIQUID_PATH = os.path.join(os.path.dirname(__file__), "Dados de liquid.xlsx")

# ─────────────────────────────────────────────────────────
# TAG BRAND IDENTITY
# ─────────────────────────────────────────────────────────
# From TAG Investimentos Brand Guide 2021
TAG = {
    "vermelho": "#630D24",
    "vermelho_light": "#8B1A3A",
    "vermelho_dark": "#3D0816",
    "offwhite": "#E6E4DB",
    "laranja": "#FF8853",
    "laranja_dark": "#E06B35",
    "bg_dark": "#1A0A10",
    "bg_card": "#2A1520",
    "bg_card_alt": "#321A28",
    "text": "#E6E4DB",
    "text_muted": "#9A9590",
    # Paleta de gráficos (oficial do brand guide)
    "chart": ["#FF8853", "#5C85F7", "#6BDE97", "#FFBB00", "#ED5A6E",
              "#58C6F5", "#A485F2", "#477C88", "#002A6E", "#6A6864"],
}

# Plotly template
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, Tahoma, sans-serif", color=TAG["offwhite"], size=13),
    margin=dict(t=30, b=50, l=50, r=20),
    xaxis=dict(
        gridcolor="rgba(230,228,219,0.10)", zerolinecolor="rgba(230,228,219,0.10)",
        showline=True, linecolor="rgba(230,228,219,0.15)", linewidth=1,
    ),
    yaxis=dict(
        gridcolor="rgba(230,228,219,0.10)", zerolinecolor="rgba(230,228,219,0.10)",
        showline=True, linecolor="rgba(230,228,219,0.15)", linewidth=1,
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
    colorway=TAG["chart"],
    hoverlabel=dict(bgcolor=TAG["bg_card"], font_size=12, font_color=TAG["offwhite"]),
)

# ─────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    /* ── Typography ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', 'Tahoma', sans-serif;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {TAG["vermelho_dark"]} 0%, {TAG["bg_dark"]} 100%);
        border-right: 1px solid {TAG["vermelho"]}33;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        font-size: 0.9rem;
        padding: 6px 0;
    }}

    /* ── Headers ── */
    h1 {{
        color: {TAG["offwhite"]} !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        border-bottom: 2px solid {TAG["laranja"]}40;
        padding-bottom: 12px !important;
    }}
    h2, h3 {{
        color: {TAG["offwhite"]} !important;
        font-weight: 500 !important;
    }}

    /* ── Metrics ── */
    [data-testid="stMetric"] {{
        background: linear-gradient(135deg, {TAG["bg_card"]} 0%, {TAG["bg_card_alt"]} 100%);
        border: 1px solid {TAG["vermelho"]}30;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 16px rgba(99,13,36,0.15);
    }}
    [data-testid="stMetric"] label {{
        color: {TAG["text_muted"]} !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    [data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {TAG["offwhite"]} !important;
        font-weight: 600 !important;
    }}

    /* ── Expanders ── */
    .streamlit-expanderHeader {{
        background: {TAG["bg_card"]} !important;
        border: 1px solid {TAG["vermelho"]}25 !important;
        border-radius: 8px !important;
        color: {TAG["offwhite"]} !important;
    }}

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {TAG["vermelho"]}20;
        border-radius: 8px;
        overflow: hidden;
    }}

    /* ── Buttons ── */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {TAG["laranja"]} 0%, {TAG["laranja_dark"]} 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(255,136,83,0.3) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        box-shadow: 0 6px 20px rgba(255,136,83,0.5) !important;
        transform: translateY(-1px);
    }}
    .stDownloadButton > button {{
        background: linear-gradient(135deg, {TAG["vermelho"]} 0%, {TAG["vermelho_dark"]} 100%) !important;
        color: {TAG["offwhite"]} !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 2px solid {TAG["vermelho"]}30;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        padding: 8px 24px;
        font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{
        background: {TAG["vermelho"]}20 !important;
        border-bottom: 3px solid {TAG["laranja"]} !important;
    }}

    /* ── Dividers ── */
    hr {{
        border-color: {TAG["vermelho"]}25 !important;
    }}

    /* ── Info/Warning boxes ── */
    [data-testid="stAlert"] {{
        border-radius: 8px;
    }}

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {{
        border: 2px dashed {TAG["vermelho"]}40 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }}

    /* ── Captions in sidebar ── */
    [data-testid="stSidebar"] .stCaption {{
        color: {TAG["text_muted"]} !important;
    }}

    /* ── Legend bar ── */
    .tag-legend {{
        display: flex;
        gap: 20px;
        font-size: 0.82rem;
        margin-top: 8px;
        padding: 8px 12px;
        background: {TAG["bg_card"]};
        border-radius: 8px;
        border: 1px solid {TAG["vermelho"]}20;
    }}

    /* ── Hide default decoration ── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

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
    """Find the first matching column from candidates (exact → partial)."""
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


def subtract_business_days(end_date, num_days, count_type="Úteis"):
    """Subtract business or calendar days from a date (inverse of add_business_days)."""
    if num_days == 0:
        return end_date
    if count_type == "Úteis":
        current = end_date
        subtracted = 0
        while subtracted < num_days:
            current -= timedelta(days=1)
            if current.weekday() < 5:
                subtracted += 1
        return current
    else:
        return end_date - timedelta(days=num_days)


def compute_settle_date(request_date, conv_days, liq_days, count_type):
    """Compute liquidation date from a request date: request → cotização → liquidação."""
    cot = add_business_days(request_date, conv_days, count_type)
    return add_business_days(cot, liq_days, count_type)


def compute_latest_request_date(target_date, conv_days, liq_days, count_type):
    """Latest possible request date so that money settles by target_date."""
    pre_liq = subtract_business_days(target_date, liq_days, count_type)
    return subtract_business_days(pre_liq, conv_days, count_type)


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


def identify_cash_funds(ativos_df, liquid_df):
    """
    Identify funds in the portfolio that are cash-equivalent.
    A fund is cash if its ESTRATÉGIA column contains the word 'CAIXA'.
    Returns set of fund codes (str) and a list of dicts with details.
    """
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")
    strat_col = find_col(ativos_df, "ESTRATÉGIA", "ESTRATEGIA")
    cash_codes = set()
    cash_details = []
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        name = str(row.get("ATIVO", ""))
        fin = float(row.get("FINANCEIRO", 0))
        estrategia = str(row.get(strat_col, "")).upper() if strat_col else ""

        if "CAIXA" in estrategia:
            cash_codes.add(code)
            # Try to get D+ info for display
            liq_info = match_fund_liquidation(name, code, liquid_df)
            if liq_info is not None:
                conv = int(liq_info.get("Conversão Resgate", 0))
                liq = int(liq_info.get("Liquid. Resgate", 0))
            else:
                conv, liq = 0, 0
            cash_details.append({
                "Ativo": name[:50], "Código": code,
                "Estratégia": estrategia, "D+ Conv.": conv, "D+ Liq.": liq,
                "Financeiro (R$)": fin,
            })
    return cash_codes, cash_details


def get_portfolio_context():
    """
    Centralized helper to get portfolio data from session state.
    Returns dict with keys: ativos, carteira, caixa_initial, pl_total,
    provision_movs, new_movs, all_movements, cod_col, cash_fund_codes, cash_details.
    Returns None if no portfolio loaded.
    """
    if not st.session_state.get("portfolio_loaded"):
        return None
    sheets = st.session_state.portfolio_sheets
    ativos = sheets["ativos"]
    carteira = sheets.get("carteira")
    caixa_initial = 0.0
    pl_total = 0.0
    if carteira is not None and not carteira.empty:
        caixa_initial = float(carteira.iloc[0].get("CAIXA", 0))
        pl_total = float(carteira.iloc[0].get("PL PROJETADO", carteira.iloc[0].get("PL FECHAMENTO", 0)))
    provision_movs = st.session_state.get("provision_movements", [])
    new_movs = st.session_state.get("new_movements", [])
    all_movements = provision_movs + new_movs
    cod_col = find_col(ativos, "CÓD. ATIVO", "COD. ATIVO")
    cash_fund_codes, cash_details = identify_cash_funds(ativos, load_liquidation_data())
    return {
        "ativos": ativos,
        "carteira": carteira,
        "caixa_initial": caixa_initial,
        "pl_total": pl_total,
        "provision_movs": provision_movs,
        "new_movs": new_movs,
        "all_movements": all_movements,
        "cod_col": cod_col,
        "cash_fund_codes": cash_fund_codes,
        "cash_details": cash_details,
    }


# ─────────────────────────────────────────────────────────
# PROVISION EXTRACTION
# ─────────────────────────────────────────────────────────

def extract_provisions_as_movements(provisoes_df, ativos_df):
    """
    Extract provisions from the portfolio file and convert them to movements.

    Three main types:
    1. "Provisão de Crédito por movimentação de Cotas (XXXX)"
       → Resgate de ativo já cotizando. Valor positivo.
       → Subtrai do ativo (XXXX = id do ativo), entra no caixa.
       → Operação: "Resgate (Cotizando)"

    2. "Débito referente a Movimento Carteira"
       → Resgate de passivo = investidores do fundo resgatando.
       → Valor negativo. Dinheiro sai do PL (caixa diminui, PL diminui).
       → Operação: "Resgate Passivo"

    3. Outros débitos/créditos (taxas, IR, etc.)
       → Operação: "Débito/Passivo" ou "Crédito (Provisão)"
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

        desc_upper = desc.upper()

        # Extract fund code from description like "(1103)" or "(394)"
        code_match = re.search(r'\((\d+)\)', desc)
        fund_code = code_match.group(1) if code_match else None
        fund_name = ""

        # Match fund code to an asset in the portfolio
        if fund_code and ativos_df is not None and cod_col:
            asset_match = ativos_df[ativos_df[cod_col].astype(str) == fund_code]
            if not asset_match.empty:
                fund_name = str(asset_match.iloc[0].get("ATIVO", ""))

        # ── Classify provision type ──
        if "MOVIMENTAÇÃO DE COTAS" in desc_upper or "MOVIMENTACAO DE COTAS" in desc_upper:
            op_type = "Resgate (Cotizando)"
            source = "provisao_resgate_ativo"
        elif "MOVIMENTO CARTEIRA" in desc_upper or "MOV. CARTEIRA" in desc_upper or "MOV CARTEIRA" in desc_upper:
            op_type = "Resgate Passivo"
            source = "provisao_resgate_passivo"
        elif valor > 0:
            op_type = "Crédito (Provisão)"
            source = "provisao_credito"
        else:
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


# ─────────────────────────────────────────────────────────
# LIQUIDATION DATE COMPUTATION
# ─────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────
# APPLY MOVEMENTS (single source of truth)
# ─────────────────────────────────────────────────────────

def apply_movement(op, value, fund_code, positions, caixa):
    """
    Apply a single movement to positions dict and caixa.
    Returns updated caixa. Mutates positions in place.
    Single source of truth for movement logic.
    """
    if op == "Resgate Passivo":
        # Investidores resgatando: sai do PL inteiro (caixa diminui)
        caixa -= value
    elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
        # Resgate de ativo: subtrai do fundo, entra no caixa
        if fund_code and fund_code in positions:
            positions[fund_code]["financeiro"] -= value
        caixa += value
    elif "Aplicação" in op:
        # Aplicação: entra no fundo, sai do caixa
        if fund_code and fund_code in positions:
            positions[fund_code]["financeiro"] += value
        caixa -= value
    elif op == "Débito/Passivo":
        caixa -= value
    elif op == "Crédito (Provisão)":
        caixa += value
    return caixa


# ─────────────────────────────────────────────────────────
# CASH FLOW TIMELINE & REQUEST DATE SUGGESTIONS
# ─────────────────────────────────────────────────────────

def build_cash_flow_timeline(caixa_initial, ativos_df, all_movements, cash_fund_codes):
    """
    Build day-by-day cash flow timeline.
    Cash efetivo = caixa_initial + sum of cash-equivalent fund positions.
    Returns (df_timeline, initial_effective_cash).
    df_timeline includes per-component columns for each cash fund.
    """
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    # Compute initial effective cash (CAIXA + cash fund positions)
    # Track each cash fund individually
    cash_components = {"CAIXA": caixa_initial}  # code → initial balance
    cash_fund_names = {"CAIXA": "Linha CAIXA"}  # code → display name
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        if code in cash_fund_codes:
            fin = float(row.get("FINANCEIRO", 0))
            name = str(row.get("ATIVO", ""))[:35]
            cash_components[code] = fin
            cash_fund_names[code] = name

    # Also scan movements for cash funds not yet in cash_components
    # (e.g., plan movements that reference cash funds not in original portfolio)
    if all_movements:
        for m in all_movements:
            fc = str(m.get("fund_code", ""))
            if fc and fc in cash_fund_codes and fc not in cash_components:
                cash_components[fc] = 0.0
                cash_fund_names[fc] = m.get("fund_name", fc)[:35]

    initial_effective_cash = sum(cash_components.values())

    if not all_movements:
        # Even without movements, return a minimal timeline so chart can render
        today = pd.Timestamp(datetime.today().date())
        rows = []
        for i in range(5):
            d = today + timedelta(days=i)
            if d.weekday() < 5:
                row_data = {
                    "Data": d, "Entradas (R$)": 0, "Saídas (R$)": 0,
                    "Líquido (R$)": 0, "Saldo (R$)": initial_effective_cash,
                    "Detalhes": "", "Negativo": False, "Tem Evento": False,
                }
                for comp_code in cash_components:
                    comp_name = cash_fund_names.get(comp_code, comp_code)
                    row_data[f"_{comp_name}"] = cash_components.get(comp_code, 0)
                rows.append(row_data)
        return pd.DataFrame(rows), initial_effective_cash

    # Filter movements with valid liquidation dates
    valid_movs = [m for m in all_movements if pd.notna(m.get("liquidation_date"))]
    if not valid_movs:
        return pd.DataFrame(), initial_effective_cash

    today = pd.Timestamp(datetime.today().date())
    last_date = max(pd.Timestamp(m["liquidation_date"]) for m in valid_movs)
    if last_date < today:
        last_date = today + timedelta(days=5)

    # Build daily event map: {date: [(description, cash_impact_total, component_impacts)]}
    # component_impacts: {code: delta} for per-fund tracking
    events = {}
    for m in valid_movs:
        liq_date = pd.Timestamp(m["liquidation_date"])
        if liq_date < today:
            continue
        fund_code = str(m.get("fund_code", ""))
        op = m["operation"]
        value = m["value"]
        fund_name = m.get("fund_name", "")[:40]
        is_cash_fund = fund_code in cash_fund_codes

        cash_impact = 0.0
        comp_impacts = {}  # per-component impact

        if op == "Resgate Passivo":
            cash_impact = -value
            comp_impacts["CAIXA"] = -value
            desc = f"Resgate Passivo: -R$ {value:,.0f}"
        elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
            if is_cash_fund:
                # Cash fund → CAIXA: fund goes down, CAIXA goes up, total unchanged
                cash_impact = 0.0
                comp_impacts[fund_code] = -value
                comp_impacts["CAIXA"] = comp_impacts.get("CAIXA", 0) + value
                desc = f"Resgate caixa ({fund_name}): R$ {value:,.0f} (neutro)"
            else:
                cash_impact = +value
                comp_impacts["CAIXA"] = +value
                desc = f"Resgate {fund_name}: +R$ {value:,.0f}"
        elif "Aplicação" in op:
            if is_cash_fund:
                # CAIXA → cash fund: CAIXA goes down, fund goes up, total unchanged
                cash_impact = 0.0
                comp_impacts["CAIXA"] = comp_impacts.get("CAIXA", 0) - value
                comp_impacts[fund_code] = +value
                desc = f"Aplicacao caixa ({fund_name}): R$ {value:,.0f} (neutro)"
            else:
                cash_impact = -value
                comp_impacts["CAIXA"] = -value
                desc = f"Aplicacao {fund_name}: -R$ {value:,.0f}"
        elif op == "Débito/Passivo":
            cash_impact = -value
            comp_impacts["CAIXA"] = -value
            desc = f"Debito: -R$ {value:,.0f}"
        elif op == "Crédito (Provisão)":
            cash_impact = +value
            comp_impacts["CAIXA"] = +value
            desc = f"Credito: +R$ {value:,.0f}"
        else:
            desc = f"{op}: R$ {value:,.0f}"

        if liq_date not in events:
            events[liq_date] = []
        events[liq_date].append((desc, cash_impact, comp_impacts))

    # Generate timeline (business days only)
    rows = []
    running_balance = initial_effective_cash
    running_components = dict(cash_components)  # copy
    current = today
    while current <= last_date + timedelta(days=3):
        if current.weekday() < 5:
            day_events = events.get(current, [])
            inflows = sum(ci for _, ci, _ in day_events if ci > 0)
            outflows = sum(abs(ci) for _, ci, _ in day_events if ci < 0)
            net = inflows - outflows
            running_balance += net

            # Update per-component balances
            for _, _, comp_imp in day_events:
                for comp_code, delta in comp_imp.items():
                    # Initialize component if not yet tracked (new fund from plan)
                    if comp_code not in running_components:
                        running_components[comp_code] = 0.0
                        cash_components[comp_code] = 0.0
                        cash_fund_names[comp_code] = comp_code
                    running_components[comp_code] += delta

            details = " | ".join(d for d, _, _ in day_events) if day_events else ""
            row_data = {
                "Data": current,
                "Entradas (R$)": inflows,
                "Saídas (R$)": outflows,
                "Líquido (R$)": net,
                "Saldo (R$)": running_balance,
                "Detalhes": details,
                "Negativo": running_balance < 0,
                "Tem Evento": len(day_events) > 0,
            }
            # Add per-component columns (prefixed with _ for identification)
            for comp_code in cash_components:
                comp_name = cash_fund_names.get(comp_code, comp_code)
                row_data[f"_{comp_name}"] = running_components.get(comp_code, 0)
            rows.append(row_data)
        current += timedelta(days=1)

    df_timeline = pd.DataFrame(rows)
    return df_timeline, initial_effective_cash


def suggest_request_dates(all_movements, liquid_df, cash_fund_codes, caixa_initial, ativos_df):
    """
    Analyze movements and suggest optimal request dates so effective cash never goes negative.
    Returns (suggestions, negative_dates, df_timeline, initial_cash).
    """
    df_timeline, initial_cash = build_cash_flow_timeline(
        caixa_initial, ativos_df, all_movements, cash_fund_codes
    )

    if df_timeline.empty:
        return [], [], df_timeline, initial_cash

    # Identify negative dates
    neg_rows = df_timeline[df_timeline["Negativo"]].copy()
    negative_dates = []
    for _, row in neg_rows.iterrows():
        negative_dates.append({
            "date": row["Data"],
            "balance": row["Saldo (R$)"],
            "shortfall": abs(row["Saldo (R$)"]),
        })

    if not negative_dates:
        return [], [], df_timeline, initial_cash

    today = pd.Timestamp(datetime.today().date())

    # Separate outflows and inflows
    outflows = []  # Movements that decrease cash
    inflows = []   # Movements that could be adjusted (non-cash resgates)
    for m in all_movements:
        if pd.isna(m.get("liquidation_date")):
            continue
        liq_date = pd.Timestamp(m["liquidation_date"])
        if liq_date < today:
            continue
        fund_code = str(m.get("fund_code", ""))
        op = m["operation"]
        is_cash_fund = fund_code in cash_fund_codes

        if op == "Resgate Passivo" or (op == "Débito/Passivo"):
            outflows.append(m)
        elif "Aplicação" in op and not is_cash_fund:
            outflows.append(m)
        elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate") and not is_cash_fund:
            inflows.append(m)

    # Sort outflows by liquidation_date
    outflows.sort(key=lambda x: pd.Timestamp(x["liquidation_date"]))

    suggestions = []
    for outflow in outflows:
        out_date = pd.Timestamp(outflow["liquidation_date"])
        out_value = outflow["value"]

        # Check if cash is negative around this outflow date
        is_problem_date = any(
            nd["date"] == out_date or
            (nd["date"] >= out_date - timedelta(days=3) and nd["date"] <= out_date + timedelta(days=3))
            for nd in negative_dates
        )
        if not is_problem_date:
            continue

        # Find inflow movements that could cover this outflow
        for inflow in inflows:
            in_date = pd.Timestamp(inflow["liquidation_date"])
            fund_name = inflow.get("fund_name", "")
            fund_code = str(inflow.get("fund_code", ""))

            # If inflow settles AFTER the outflow, we need to suggest earlier request
            if in_date > out_date:
                liq_info = match_fund_liquidation(fund_name, fund_code, liquid_df)
                if liq_info is not None:
                    conv = int(liq_info.get("Conversão Resgate", 0))
                    liq = int(liq_info.get("Liquid. Resgate", 0))
                    count_type = str(liq_info.get("Contagem Resgate", "Úteis"))
                    if count_type not in ["Úteis", "Corridos"]:
                        count_type = "Úteis"
                    total_d = conv + liq

                    # Suggested request date = outflow_date - total_d business days
                    suggested_req = subtract_business_days(out_date, total_d, count_type)
                    current_req = pd.Timestamp(inflow.get("request_date", today))

                    if suggested_req < today:
                        reason = (
                            f"⚠️ IMPOSSÍVEL: precisaria solicitar em "
                            f"{suggested_req.strftime('%d/%m/%Y')} (passado). "
                            f"Aumente o caixa ou atrase a saída."
                        )
                    elif suggested_req < current_req:
                        reason = (
                            f"Antecipar para {suggested_req.strftime('%d/%m/%Y')} "
                            f"(D+{total_d} {count_type}) para liquidar até "
                            f"{out_date.strftime('%d/%m/%Y')}"
                        )
                    else:
                        continue  # Already good

                    suggestions.append({
                        "Fundo": fund_name[:45],
                        "Código": fund_code,
                        "Operação": inflow["operation"],
                        "Valor (R$)": inflow["value"],
                        "Data Atual": current_req.strftime("%d/%m/%Y"),
                        "Data Sugerida": suggested_req.strftime("%d/%m/%Y") if suggested_req >= today else f"{suggested_req.strftime('%d/%m/%Y')} ⚠️",
                        "D+": f"D+{total_d} ({count_type})",
                        "Cobre Saída Em": out_date.strftime("%d/%m/%Y"),
                        "Motivo": reason,
                        "is_impossible": suggested_req < today,
                    })

    # Also suggest: for each outflow without a matching inflow, flag it
    for outflow in outflows:
        out_date = pd.Timestamp(outflow["liquidation_date"])
        is_problem = any(
            nd["date"] == out_date or
            (nd["date"] >= out_date - timedelta(days=1) and nd["date"] <= out_date)
            for nd in negative_dates
        )
        if is_problem:
            # Check if any suggestion already covers this date
            already_covered = any(s["Cobre Saída Em"] == out_date.strftime("%d/%m/%Y") for s in suggestions)
            if not already_covered:
                suggestions.append({
                    "Fundo": outflow.get("fund_name", "")[:45],
                    "Código": str(outflow.get("fund_code", "")),
                    "Operação": outflow["operation"],
                    "Valor (R$)": outflow["value"],
                    "Data Atual": pd.Timestamp(outflow.get("request_date", today)).strftime("%d/%m/%Y"),
                    "Data Sugerida": "—",
                    "D+": "—",
                    "Cobre Saída Em": out_date.strftime("%d/%m/%Y"),
                    "Motivo": "⚠️ Saída sem entrada correspondente — garanta caixa suficiente",
                    "is_impossible": True,
                })

    return suggestions, negative_dates, df_timeline, initial_cash


# ─────────────────────────────────────────────────────────
# EVOLUTION TABLE
# ─────────────────────────────────────────────────────────

def build_evolution_table(ativos_df, all_movements, caixa_initial):
    """
    Build evolution table: rows=assets, columns=dates.
    Shows how portfolio changes at each liquidation date.
    """
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    assets = []
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        name = str(row.get("ATIVO", ""))
        fin = float(row.get("FINANCEIRO", 0))
        assets.append({"code": code, "name": name, "financeiro_atual": fin})

    # Unique sorted liquidation dates
    all_dates = sorted(set(
        pd.Timestamp(m["liquidation_date"]) for m in all_movements
        if pd.notna(m.get("liquidation_date"))
    ))
    if not all_dates:
        return None, None, None

    # For each date: cumulative adjustments
    date_adjustments = {}
    caixa_adjustments = {}

    for d in all_dates:
        date_adjustments[d] = {}
        caixa_adj = 0.0

        for mov in all_movements:
            liq_date = pd.Timestamp(mov["liquidation_date"])
            if liq_date > d:
                continue

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

            if op == "Resgate Passivo":
                caixa_adj -= value
            elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
                if matched_code:
                    date_adjustments[d][matched_code] = date_adjustments[d].get(matched_code, 0) - value
                caixa_adj += value
            elif "Aplicação" in op:
                if matched_code:
                    date_adjustments[d][matched_code] = date_adjustments[d].get(matched_code, 0) + value
                caixa_adj -= value
            elif op == "Débito/Passivo":
                caixa_adj -= value
            elif op == "Crédito (Provisão)":
                caixa_adj += value

        caixa_adjustments[d] = caixa_adj

    # Build R$ table
    rows_financeiro = []
    for a in assets:
        row_fin = {"Ativo": a["name"][:45], "Código": a["code"], "Atual (R$)": a["financeiro_atual"]}
        for d in all_dates:
            adj = date_adjustments[d].get(a["code"], 0)
            row_fin[d.strftime("%d/%m/%Y")] = a["financeiro_atual"] + adj
        rows_financeiro.append(row_fin)

    # Caixa row
    caixa_row_fin = {"Ativo": "💰 CAIXA", "Código": "CAIXA", "Atual (R$)": caixa_initial}
    for d in all_dates:
        caixa_row_fin[d.strftime("%d/%m/%Y")] = caixa_initial + caixa_adjustments[d]
    rows_financeiro.append(caixa_row_fin)

    df_fin = pd.DataFrame(rows_financeiro)

    # Total row
    date_cols = [d.strftime("%d/%m/%Y") for d in all_dates]
    total_row = {"Ativo": "📊 TOTAL PL", "Código": "", "Atual (R$)": df_fin["Atual (R$)"].sum()}
    for dc in date_cols:
        total_row[dc] = df_fin[dc].sum()
    rows_financeiro.append(total_row)
    df_fin = pd.DataFrame(rows_financeiro)

    # Build % PL table
    rows_pct = []
    for _, r in df_fin.iterrows():
        if r["Ativo"] == "📊 TOTAL PL":
            continue
        row_pct = {
            "Ativo": r["Ativo"], "Código": r["Código"],
            "Atual (%)": (r["Atual (R$)"] / total_row["Atual (R$)"] * 100) if total_row["Atual (R$)"] != 0 else 0,
        }
        for dc in date_cols:
            total_on_date = total_row[dc]
            row_pct[dc] = (r[dc] / total_on_date * 100) if total_on_date != 0 else 0
        rows_pct.append(row_pct)

    total_pct_row = {"Ativo": "📊 TOTAL PL", "Código": "", "Atual (%)": 100.0}
    for dc in date_cols:
        total_pct_row[dc] = 100.0
    rows_pct.append(total_pct_row)
    df_pct = pd.DataFrame(rows_pct)

    # Movements summary
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


# ─────────────────────────────────────────────────────────
# MODEL PORTFOLIO
# ─────────────────────────────────────────────────────────

def parse_model_portfolio(uploaded_file):
    """Parse model portfolio. Auto-detects columns for code/name/% target."""
    df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]

    code_col = name_col = pct_col = None

    for c in df.columns:
        col_upper = c.upper()
        if pct_col is None and any(k in col_upper for k in ["%", "PESO", "ALVO", "TARGET", "ALOC"]):
            pct_col = c
        elif code_col is None and any(k in col_upper for k in ["CÓD", "COD", "CODIGO", "CODE", "ID"]):
            code_col = c
        elif name_col is None and any(k in col_upper for k in ["ATIVO", "NOME", "FUNDO", "NAME", "ASSET"]):
            name_col = c

    # Fallback
    if code_col is None and name_col is None and pct_col is None:
        for c in df.columns:
            if df[c].dtype in ['float64', 'int64'] and pct_col is None:
                pct_col = c
            elif code_col is None:
                code_col = c

    if pct_col is None:
        for c in df.columns:
            if df[c].dtype in ['float64', 'int64']:
                vals = df[c].dropna()
                if len(vals) > 0 and vals.max() <= 100 and vals.min() >= 0:
                    pct_col = c
                    break

    result = pd.DataFrame()
    result["Código"] = df[code_col].astype(str) if code_col else ""
    result["Ativo"] = df[name_col].astype(str) if name_col else result["Código"]
    result["% Alvo"] = pd.to_numeric(df[pct_col], errors="coerce").fillna(0) if pct_col else 0
    result = result[result["% Alvo"] > 0].reset_index(drop=True)
    return result


def build_adherence_analysis(ativos_df, model_df, all_movements, caixa_initial, pl_total):
    """
    Compare portfolio (after all pending movements) with model.
    Returns adherence DataFrame + summary info dict.
    """
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    # Build positions
    positions = {}
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        name = str(row.get("ATIVO", ""))
        fin = float(row.get("FINANCEIRO", 0))
        positions[code] = {"name": name, "financeiro": fin, "code": code}

    # Apply movements
    caixa = caixa_initial
    for mov in all_movements:
        fund_code = str(mov.get("fund_code", ""))
        caixa = apply_movement(mov["operation"], mov["value"], fund_code, positions, caixa)

    total_after = sum(p["financeiro"] for p in positions.values()) + caixa

    # Match model to positions
    rows = []
    model_codes = set()

    for _, model_row in model_df.iterrows():
        m_code = str(model_row["Código"]).strip()
        m_name = str(model_row["Ativo"]).strip()
        m_pct_alvo = float(model_row["% Alvo"])
        model_codes.add(m_code)

        matched_pos = None
        if m_code in positions:
            matched_pos = positions[m_code]
        else:
            for code, pos in positions.items():
                if (m_name.upper()[:15] in pos["name"].upper() or
                        pos["name"].upper()[:15] in m_name.upper()):
                    matched_pos = pos
                    model_codes.add(code)
                    break

        fin_atual = matched_pos["financeiro"] if matched_pos else 0
        pct_atual = (fin_atual / total_after * 100) if total_after > 0 else 0
        gap_pct = m_pct_alvo - pct_atual
        gap_rs = gap_pct / 100 * total_after

        if abs(gap_pct) < 0.1:
            acao = "✅ OK"
        elif gap_pct > 0:
            acao = f"📥 Aplicar R$ {abs(gap_rs):,.0f}"
        else:
            acao = f"📤 Resgatar R$ {abs(gap_rs):,.0f}"

        rows.append({
            "Ativo": m_name[:45], "Código": m_code,
            "Financeiro Projetado": fin_atual,
            "% Atual (Pós-Mov.)": round(pct_atual, 2),
            "% Alvo (Modelo)": round(m_pct_alvo, 2),
            "Gap (p.p.)": round(gap_pct, 2),
            "Gap (R$)": round(gap_rs, 2),
            "Ação Sugerida": acao,
        })

    # Positions NOT in model
    for code, pos in positions.items():
        if code not in model_codes and pos["financeiro"] > 100:
            pct_atual = (pos["financeiro"] / total_after * 100) if total_after > 0 else 0
            if pct_atual > 0.05:
                rows.append({
                    "Ativo": pos["name"][:45], "Código": code,
                    "Financeiro Projetado": pos["financeiro"],
                    "% Atual (Pós-Mov.)": round(pct_atual, 2),
                    "% Alvo (Modelo)": 0.0,
                    "Gap (p.p.)": round(-pct_atual, 2),
                    "Gap (R$)": round(-pos["financeiro"], 2),
                    "Ação Sugerida": f"📤 Resgatar R$ {pos['financeiro']:,.0f} (fora do modelo)",
                })

    # Caixa
    caixa_pct = (caixa / total_after * 100) if total_after > 0 else 0
    caixa_target = 100 - model_df["% Alvo"].sum()
    caixa_gap = caixa_target - caixa_pct
    rows.append({
        "Ativo": "💰 CAIXA", "Código": "CAIXA",
        "Financeiro Projetado": caixa,
        "% Atual (Pós-Mov.)": round(caixa_pct, 2),
        "% Alvo (Modelo)": round(max(0, caixa_target), 2),
        "Gap (p.p.)": round(caixa_gap, 2),
        "Gap (R$)": round(caixa_gap / 100 * total_after, 2),
        "Ação Sugerida": "Residual" if abs(caixa_gap) < 1 else ("Excesso" if caixa_gap < -1 else "Déficit"),
    })

    df = pd.DataFrame(rows)
    info = {
        "pl_projetado": total_after,
        "caixa_projetado": caixa,
        "total_aplicar": sum(r["Gap (R$)"] for r in rows if r["Gap (R$)"] > 0 and r["Código"] != "CAIXA"),
        "total_resgatar": sum(abs(r["Gap (R$)"]) for r in rows if r["Gap (R$)"] < 0 and r["Código"] != "CAIXA"),
    }
    return df, info


def generate_rebalancing_plan(adherence_df, liquid_df, request_date=None):
    """Legacy wrapper — calls smart version with minimal args for backward compat."""
    plan_df, plan_movements, _warnings = generate_smart_rebalancing_plan(
        adherence_df, liquid_df, [], 0, None, set(), today=request_date
    )
    return plan_df, plan_movements


def generate_smart_rebalancing_plan(
    adherence_df, liquid_df, all_movements, caixa_initial,
    ativos_df, cash_fund_codes, today=None
):
    """
    Generate a rebalancing plan that GUARANTEES cash never goes negative.
    Uses day-by-day cash simulation to schedule all movements safely.

    Core principle: at every business day, effective_cash >= 0.
    Effective cash = CAIXA line + funds with strategy "Caixa".

    Returns: (plan_df, plan_movements, warnings)
    """
    if today is None:
        today = pd.Timestamp(datetime.today().date())
    else:
        today = pd.Timestamp(today)

    warnings = []

    def _add_plan_entry(plan_rows, plan_movs, fund, op, amount, req_date, settle_date, motivo, source):
        """Helper to append both plan row and movement."""
        d_str = (f"D+{fund['d_conv']}+{fund['d_liq']} ({fund['contagem']})"
                 if op == "Resgate" else f"D+{fund['d_conv_aplic']}")
        plan_rows.append({
            "Prioridade": 0,
            "Ativo": fund["name"], "Código": fund["code"],
            "Operação": op, "Valor (R$)": round(amount, 2), "D+": d_str,
            "Data Solicitação": req_date.strftime("%d/%m/%Y"),
            "Data Liquidação": settle_date.strftime("%d/%m/%Y"),
            "Motivo": motivo,
            "De % Atual": fund["pct_atual"], "Para % Alvo": fund["pct_alvo"],
        })
        plan_movs.append({
            "fund_name": fund["name"], "fund_code": fund["code"],
            "operation": op, "value": round(amount, 2),
            "request_date": req_date, "liquidation_date": settle_date,
            "description": f"Plano: {op} {fund['name'][:30]} ({motivo[:30]})",
            "source": source,
        })

    plan_rows = []
    plan_movements = []

    # ── FASE 0: Catálogo de Fundos ──
    catalog = {}
    for _, row in adherence_df.iterrows():
        code = str(row["Código"])
        if code == "CAIXA":
            continue
        name = row["Ativo"]
        gap_rs = row["Gap (R$)"]
        financeiro = row.get("Financeiro Projetado", 0)
        liq_info = match_fund_liquidation(name, code, liquid_df)
        if liq_info is not None:
            d_conv = int(liq_info["Conversão Resgate"])
            d_liq = int(liq_info["Liquid. Resgate"])
            contagem = str(liq_info.get("Contagem Resgate", "Úteis"))
            if contagem not in ["Úteis", "Corridos"]:
                contagem = "Úteis"
            d_conv_aplic = int(liq_info["Conversão Aplic."])
        else:
            d_conv, d_liq, contagem = 0, 0, "Úteis"
            d_conv_aplic = 0

        catalog[code] = {
            "code": code, "name": name, "gap_rs": gap_rs,
            "financeiro": financeiro, "available_fin": max(0, financeiro),
            "d_conv": d_conv, "d_liq": d_liq, "contagem": contagem,
            "d_conv_aplic": d_conv_aplic, "d_total": d_conv + d_liq,
            "is_overweight": gap_rs < -100, "is_underweight": gap_rs > 100,
            "is_cash": code in cash_fund_codes,
            "max_model_resgate": abs(gap_rs) if gap_rs < -100 else 0,
            "pct_atual": row["% Atual (Pós-Mov.)"],
            "pct_alvo": row["% Alvo (Modelo)"],
            "already_redeemed": 0.0,
            "already_applied": 0.0,
        }

    # ── FASE 1: Build day-by-day cash map from existing movements ──
    # cash_events[date] = net cash impact (positive = money in, negative = money out)
    cash_events = {}  # date → float

    # Effective cash today = CAIXA + cash fund positions
    effective_cash = caixa_initial
    if ativos_df is not None and not ativos_df.empty:
        cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")
        if cod_col:
            for _, row in ativos_df.iterrows():
                code = str(row[cod_col])
                if code in cash_fund_codes:
                    effective_cash += float(row.get("FINANCEIRO", 0))

    # Add all existing provision impacts
    passivo_dates = {}  # date → total passivo value
    if all_movements:
        for m in all_movements:
            liq_date = pd.Timestamp(m["liquidation_date"]) if pd.notna(m.get("liquidation_date")) else None
            if liq_date is None or liq_date < today:
                continue
            op = m["operation"]
            val = m["value"]
            fund_code = str(m.get("fund_code", ""))
            is_cash_fund = fund_code in cash_fund_codes

            impact = 0.0
            if op == "Resgate Passivo":
                impact = -val
                passivo_dates.setdefault(liq_date, 0.0)
                passivo_dates[liq_date] += val
            elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
                impact = 0.0 if is_cash_fund else +val
            elif "Aplicação" in op:
                impact = 0.0 if is_cash_fund else -val
            elif op == "Débito/Passivo":
                impact = -val
            elif op == "Crédito (Provisão)":
                impact = +val

            if impact != 0:
                cash_events.setdefault(liq_date, 0.0)
                cash_events[liq_date] += impact

    # ── FASE 2: Cobrir Passivos (resgates que liquidam antes do passivo) ──
    passivos_sorted = sorted(passivo_dates.items(), key=lambda x: x[0])

    # Helper: compute running cash at a given date given current cash_events
    def cash_at_date(target_date):
        running = effective_cash
        for d in sorted(cash_events.keys()):
            if d <= target_date:
                running += cash_events[d]
        return running

    for passivo_date, passivo_value in passivos_sorted:
        # Check if cash is already sufficient at this date
        cash_before = cash_at_date(passivo_date)
        if cash_before >= 0:
            continue  # No problem at this date

        deficit = abs(cash_before)

        # Find funds to redeem that settle by passivo_date
        candidates = []
        for code, fund in catalog.items():
            if fund["is_cash"]:
                continue
            remaining = fund["available_fin"] - fund["already_redeemed"]
            if remaining < 100:
                continue
            req_date = compute_latest_request_date(
                passivo_date, fund["d_conv"], fund["d_liq"], fund["contagem"]
            )
            if req_date < today:
                continue
            settle = compute_settle_date(req_date, fund["d_conv"], fund["d_liq"], fund["contagem"])
            candidates.append({
                "code": code, "fund": fund, "request_date": req_date,
                "settle_date": settle, "remaining": remaining,
                "is_overweight": fund["is_overweight"],
                "model_resgate": max(0, fund["max_model_resgate"] - fund["already_redeemed"]),
            })

        # Prefer overweight first, then fastest D+
        candidates.sort(key=lambda c: (0 if c["is_overweight"] else 1, c["fund"]["d_total"]))

        still_needed = deficit
        for cand in candidates:
            if still_needed <= 0:
                break
            fund = cand["fund"]
            actual_remaining = fund["available_fin"] - fund["already_redeemed"]
            if cand["is_overweight"] and cand["model_resgate"] > 0:
                amount = min(still_needed, cand["model_resgate"], actual_remaining)
            else:
                amount = min(still_needed, actual_remaining)
            if amount < 100:
                continue

            _add_plan_entry(plan_rows, plan_movements, fund, "Resgate", amount,
                            cand["request_date"], cand["settle_date"],
                            f"Cobertura passivo {passivo_date.strftime('%d/%m')}",
                            "plano_cobertura_passivo")
            fund["already_redeemed"] += amount
            cash_events.setdefault(cand["settle_date"], 0.0)
            cash_events[cand["settle_date"]] += amount
            still_needed -= amount

        if still_needed > 100:
            warnings.append({
                "level": "error",
                "message": (
                    f"Impossivel cobrir passivo de R$ {passivo_value:,.0f} em "
                    f"{passivo_date.strftime('%d/%m/%Y')}: deficit de R$ {still_needed:,.0f}. "
                    f"Nenhum fundo consegue liquidar a tempo."
                ),
            })

    # ── FASE 3: Resgates de Rebalanceamento (overweight restante) ──
    for code, fund in catalog.items():
        if not fund["is_overweight"]:
            continue
        remaining_gap = fund["max_model_resgate"] - fund["already_redeemed"]
        if remaining_gap < 100:
            continue

        req_date = today
        settle_date = compute_settle_date(req_date, fund["d_conv"], fund["d_liq"], fund["contagem"])
        _add_plan_entry(plan_rows, plan_movements, fund, "Resgate", remaining_gap,
                        req_date, settle_date, "Rebalanceamento (acima do modelo)",
                        "plano_rebalanceamento")
        fund["already_redeemed"] += remaining_gap
        # Cash funds: resgate is neutral for effective cash
        if not fund["is_cash"]:
            cash_events.setdefault(settle_date, 0.0)
            cash_events[settle_date] += remaining_gap

    # ── FASE 4: Aplicações com verificação dia-a-dia de caixa ──
    # Build a sorted timeline of ALL future business days with events
    all_event_dates = sorted(cash_events.keys())
    if not all_event_dates:
        last_event = today + timedelta(days=5)
    else:
        last_event = max(all_event_dates) + timedelta(days=5)

    # Compute running cash balance at each business day
    daily_cash = {}
    running = effective_cash
    current = today
    while current <= last_event:
        if current.weekday() < 5:
            running += cash_events.get(current, 0)
            daily_cash[current] = running
        current += timedelta(days=1)

    # Find earliest date when cash is stable and positive for applications
    # Cash funds are included but don't affect effective cash
    underweight_funds = [
        (code, fund) for code, fund in catalog.items()
        if fund["is_underweight"]
    ]
    underweight_funds.sort(key=lambda x: (0 if x[1]["is_cash"] else 1, -x[1]["gap_rs"]))

    # Find the first business day where cash stays positive from there on
    sorted_days = sorted(daily_cash.keys())
    if sorted_days:
        # Compute min future cash at each day (from that day forward)
        min_future = {}
        running_min = float('inf')
        for d in reversed(sorted_days):
            running_min = min(running_min, daily_cash[d])
            min_future[d] = running_min

    plan_outflows = {}  # track planned application outflows by date (non-cash only)

    for code, fund in underweight_funds:
        gap = fund["gap_rs"] - fund["already_applied"]
        if gap < 100:
            continue

        # Cash funds: application is neutral (CAIXA → cash fund = zero impact on effective cash)
        # So we can schedule immediately without cash constraints
        if fund["is_cash"]:
            best_date = today
            settle_date = add_business_days(best_date, fund["d_conv_aplic"], "Úteis")
            _add_plan_entry(plan_rows, plan_movements, fund, "Aplicação", gap,
                            best_date, settle_date, "Rebalanceamento (abaixo do modelo)",
                            "plano_rebalanceamento")
            fund["already_applied"] += gap
            continue

        # Non-cash funds: find earliest date we can request this application
        # On that date, cash must stay >= 0 after this withdrawal
        best_date = None
        for d in sorted_days:
            if d < today:
                continue
            # Cash available = daily_cash at d, minus any already planned outflows on/before d
            planned_out = sum(v for dd, v in plan_outflows.items() if dd <= d)
            available = daily_cash[d] - planned_out
            # Also check all future days remain >= 0 after this outflow
            future_ok = True
            for fd in sorted_days:
                if fd >= d:
                    future_planned = sum(v for dd, v in plan_outflows.items() if dd <= fd)
                    if daily_cash[fd] - future_planned - gap < -1:
                        future_ok = False
                        break
            if available >= gap and future_ok:
                best_date = d
                break

        if best_date is None:
            # Try with reduced amount — find max we can apply
            for d in sorted_days:
                if d < today:
                    continue
                planned_out = sum(v for dd, v in plan_outflows.items() if dd <= d)
                available = daily_cash[d] - planned_out
                # Check minimum future cash after this outflow
                min_fut = float('inf')
                for fd in sorted_days:
                    if fd >= d:
                        future_planned = sum(v for dd, v in plan_outflows.items() if dd <= fd)
                        min_fut = min(min_fut, daily_cash[fd] - future_planned)
                max_amount = min(gap, available, min_fut)
                if max_amount >= 100:
                    gap = max_amount
                    best_date = d
                    break

        if best_date is None or gap < 100:
            continue

        settle_date = add_business_days(best_date, fund["d_conv_aplic"], "Úteis")
        _add_plan_entry(plan_rows, plan_movements, fund, "Aplicação", gap,
                        best_date, settle_date, "Rebalanceamento (abaixo do modelo)",
                        "plano_rebalanceamento")
        fund["already_applied"] += gap
        plan_outflows.setdefault(best_date, 0.0)
        plan_outflows[best_date] += gap

    # ── FASE 5: Validação final — simular dia a dia ──
    if plan_movements and ativos_df is not None and not ativos_df.empty:
        combined = (all_movements or []) + plan_movements
        df_check, _ = build_cash_flow_timeline(
            caixa_initial, ativos_df, combined, cash_fund_codes
        )
        if not df_check.empty:
            neg_days = df_check[df_check["Negativo"]]
            if not neg_days.empty:
                for _, neg_row in neg_days.iterrows():
                    warnings.append({
                        "level": "error",
                        "message": (
                            f"Caixa negativo em {neg_row['Data'].strftime('%d/%m/%Y')}: "
                            f"R$ {neg_row['Saldo (R$)']:,.0f}"
                        ),
                    })

    # ── Build final DataFrame ──
    plan_df = pd.DataFrame(plan_rows)
    if not plan_df.empty:
        motivo_order = plan_df["Motivo"].apply(
            lambda m: 0 if "passivo" in m.lower() else (1 if "acima" in m.lower() else 2)
        )
        plan_df["_sort"] = motivo_order * 10 + plan_df["Operação"].map({"Resgate": 0, "Aplicação": 5}).fillna(3)
        plan_df = plan_df.sort_values(["_sort", "Data Liquidação", "Valor (R$)"],
                                       ascending=[True, True, False])
        plan_df["Prioridade"] = range(1, len(plan_df) + 1)
        plan_df = plan_df.drop(columns=["_sort"])

    return plan_df, plan_movements, warnings


# ─────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────

def build_cashflow_chart(df_timeline):
    """Build a cash flow chart: bars for daily inflows/outflows + line for running balance.
    Shows only event days (days with actual movements).
    Left Y-axis: movement bars (entradas/saídas).
    Right Y-axis: running balance line.
    """
    if df_timeline.empty:
        fig = go.Figure()
        fig.update_layout(**PLOTLY_LAYOUT, height=300)
        fig.add_annotation(text="Sem dados para exibir", showarrow=False,
                           font=dict(size=16, color=TAG["text_muted"]), xref="paper", yref="paper", x=0.5, y=0.5)
        return fig

    # Only show event days (days with actual movements)
    if "Tem Evento" in df_timeline.columns:
        df_events = df_timeline[df_timeline["Tem Evento"]].copy()
    else:
        df_events = df_timeline[
            (df_timeline["Entradas (R$)"] > 0) | (df_timeline["Saídas (R$)"] > 0)
        ].copy()

    if df_events.empty:
        fig = go.Figure()
        fig.update_layout(**PLOTLY_LAYOUT, height=300)
        fig.add_annotation(text="Nenhum movimento no período", showarrow=False,
                           font=dict(size=16, color=TAG["text_muted"]), xref="paper", yref="paper", x=0.5, y=0.5)
        return fig

    from plotly.subplots import make_subplots
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Format dates as strings for categorical x-axis (cleaner bars)
    date_labels = df_events["Data"].dt.strftime("%d/%m/%Y").tolist()

    # ── Bars: Entradas (green, positive) ──
    fig.add_trace(go.Bar(
        x=date_labels, y=df_events["Entradas (R$)"],
        name="Entradas",
        marker_color=TAG["chart"][2],
        marker_line_width=0,
        text=df_events["Entradas (R$)"].apply(lambda v: f"R$ {v:,.0f}" if v > 0 else ""),
        textposition="outside", textfont=dict(size=9, color=TAG["chart"][2]),
        hovertemplate="<b>%{x}</b><br>Entrada: R$ %{y:,.0f}<extra></extra>",
    ), secondary_y=False)

    # ── Bars: Saídas (red, negative for visual) ──
    fig.add_trace(go.Bar(
        x=date_labels, y=-df_events["Saídas (R$)"],
        name="Saídas",
        marker_color=TAG["chart"][4],
        marker_line_width=0,
        text=df_events["Saídas (R$)"].apply(lambda v: f"-R$ {v:,.0f}" if v > 0 else ""),
        textposition="outside", textfont=dict(size=9, color=TAG["chart"][4]),
        hovertemplate="<b>%{x}</b><br>Saída: R$ %{customdata:,.0f}<extra></extra>",
        customdata=df_events["Saídas (R$)"],
    ), secondary_y=False)

    # ── Line: Saldo acumulado (right Y-axis) ──
    fig.add_trace(go.Scatter(
        x=date_labels, y=df_events["Saldo (R$)"],
        name="Saldo Caixa",
        mode="lines+markers",
        line=dict(color=TAG["offwhite"], width=2.5),
        marker=dict(size=6, color=TAG["offwhite"]),
        hovertemplate="<b>%{x}</b><br>Saldo: R$ %{y:,.0f}<extra></extra>",
    ), secondary_y=True)

    # ── Deficit markers ──
    neg_events = df_events[df_events["Saldo (R$)"] < 0]
    if not neg_events.empty:
        neg_labels = neg_events["Data"].dt.strftime("%d/%m/%Y").tolist()
        fig.add_trace(go.Scatter(
            x=neg_labels, y=neg_events["Saldo (R$)"],
            name="Deficit",
            mode="markers",
            marker=dict(size=12, color=TAG["chart"][4], symbol="x", line=dict(width=2)),
            hovertemplate="<b>DEFICIT</b><br>%{x}<br>R$ %{y:,.0f}<extra></extra>",
        ), secondary_y=True)

    # Zero line on right axis
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(230,228,219,0.25)", line_width=1,
                  secondary_y=True)

    fig.update_layout(**PLOTLY_LAYOUT, height=420)
    fig.update_layout(
        barmode="relative",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        hovermode="x unified",
        margin=dict(b=80),
    )
    fig.update_xaxes(
        tickangle=-45, tickfont=dict(size=9),
        categoryorder="array", categoryarray=date_labels,
    )
    fig.update_yaxes(
        title_text="Movimentos (R$)", tickformat=",.0f", tickprefix="R$ ",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Saldo Acumulado (R$)", tickformat=",.0f", tickprefix="R$ ",
        secondary_y=True,
    )
    return fig


def display_provisions_summary(movements, expanded=False):
    """Display a categorized view of provisions/movements."""
    if not movements:
        return

    cotizando = [m for m in movements if m["operation"] == "Resgate (Cotizando)"]
    passivo = [m for m in movements if m["operation"] == "Resgate Passivo"]
    outros = [m for m in movements if m["operation"] in ("Débito/Passivo", "Crédito (Provisão)")]
    manuais = [m for m in movements if m.get("source") == "manual"]
    plano = [m for m in movements if m.get("source") == "plano_modelo"]

    with st.expander(f"📌 {len(movements)} movimentos considerados", expanded=expanded):
        if cotizando:
            st.markdown(f"**🔄 Resgates Cotizando ({len(cotizando)})** — já solicitados, aguardando liquidação")
            cotiz_df = pd.DataFrame([{
                "Ativo": m["fund_name"][:40], "Código": m.get("fund_code", ""),
                "Valor (R$)": m["value"],
                "Liquidação": m["liquidation_date"].strftime("%d/%m/%Y"),
            } for m in cotizando])
            st.dataframe(cotiz_df.style.format({"Valor (R$)": "R$ {:,.2f}"}),
                         use_container_width=True, hide_index=True)

        if passivo:
            st.markdown(f"**📤 Resgates Passivo ({len(passivo)})** — investidores resgatando (reduz PL)")
            pass_df = pd.DataFrame([{
                "Descrição": m["description"][:55],
                "Valor (R$)": m["value"],
                "Liquidação": m["liquidation_date"].strftime("%d/%m/%Y"),
            } for m in passivo])
            st.dataframe(pass_df.style.format({"Valor (R$)": "R$ {:,.2f}"}),
                         use_container_width=True, hide_index=True)

        if outros:
            st.markdown(f"**💳 Débitos/Créditos ({len(outros)})** — taxas, IR, etc.")
            outros_df = pd.DataFrame([{
                "Descrição": m["description"][:55], "Tipo": m["operation"],
                "Valor (R$)": m["value"],
                "Liquidação": m["liquidation_date"].strftime("%d/%m/%Y"),
            } for m in outros])
            st.dataframe(outros_df.style.format({"Valor (R$)": "R$ {:,.2f}"}),
                         use_container_width=True, hide_index=True)

        if manuais:
            st.markdown(f"**✏️ Movimentos Manuais ({len(manuais)})**")
            man_df = pd.DataFrame([{
                "Ativo": m["fund_name"][:40], "Operação": m["operation"],
                "Valor (R$)": m["value"],
                "Liquidação": m["liquidation_date"].strftime("%d/%m/%Y"),
            } for m in manuais])
            st.dataframe(man_df.style.format({"Valor (R$)": "R$ {:,.2f}"}),
                         use_container_width=True, hide_index=True)

        if plano:
            st.markdown(f"**🎯 Plano Modelo ({len(plano)})**")
            plan_df = pd.DataFrame([{
                "Ativo": m["fund_name"][:40], "Operação": m["operation"],
                "Valor (R$)": m["value"],
                "Liquidação": m["liquidation_date"].strftime("%d/%m/%Y"),
            } for m in plano])
            st.dataframe(plan_df.style.format({"Valor (R$)": "R$ {:,.2f}"}),
                         use_container_width=True, hide_index=True)

        # Totals
        total_val = sum(m["value"] for m in movements)
        cols_summary = st.columns(5)
        with cols_summary[0]:
            st.metric("Total Movimentos", len(movements))
        with cols_summary[1]:
            st.metric("Resgates Cotizando", f"R$ {sum(m['value'] for m in cotizando):,.0f}")
        with cols_summary[2]:
            st.metric("Resgates Passivo", f"R$ {sum(m['value'] for m in passivo):,.0f}")
        with cols_summary[3]:
            st.metric("Débitos/Créditos", f"R$ {sum(m['value'] for m in outros):,.0f}")
        with cols_summary[4]:
            st.metric("Manuais", f"R$ {sum(m['value'] for m in manuais):,.0f}")


def style_evolution_table_rows(row):
    """Style function for evolution table rows (TAG brand)."""
    if row["Ativo"] == "📊 TOTAL PL":
        return [f"background-color: {TAG['vermelho']}40; font-weight: bold; color: {TAG['offwhite']}"] * len(row)
    elif row["Ativo"] == "💰 CAIXA":
        return [f"background-color: {TAG['bg_card_alt']}; color: {TAG['offwhite']}"] * len(row)
    return [""] * len(row)


def display_evolution_tables(df_fin, df_pct, evo_date_cols, model_map=None):
    """Display R$ and % PL evolution tables.
    model_map: dict {código: % alvo} — uses fund code as key for reliable matching.
    """
    evo_total_row = df_fin[df_fin["Ativo"] == "📊 TOTAL PL"].iloc[0]

    # PL metrics
    if evo_date_cols:
        mcols = st.columns(min(len(evo_date_cols) + 1, 7))
        with mcols[0]:
            st.metric("PL Hoje", f"R$ {evo_total_row['Atual (R$)']:,.0f}")
        for i, dc in enumerate(evo_date_cols[:6]):
            with mcols[min(i + 1, 6)]:
                val = evo_total_row[dc]
                delta = val - evo_total_row["Atual (R$)"]
                st.metric(dc, f"R$ {val:,.0f}", f"R$ {delta:,.0f}")

    # R$ table
    st.markdown("##### Evolução R$")
    fmt_fin = {"Atual (R$)": "R$ {:,.2f}"}
    for dc in evo_date_cols:
        fmt_fin[dc] = "R$ {:,.2f}"
    st.dataframe(
        df_fin.drop(columns=["Código"]).style.format(fmt_fin).apply(style_evolution_table_rows, axis=1),
        use_container_width=True, hide_index=True, height=420,
    )

    # % PL table
    st.markdown("##### Evolução % PL")
    fmt_pct = {"Atual (%)": "{:.2f}%"}
    for dc in evo_date_cols:
        fmt_pct[dc] = "{:.2f}%"

    df_pct_display = df_pct.copy()

    if model_map:
        # Map using Código (reliable) — model_map is {code: % alvo}
        df_pct_display["🎯 Modelo"] = df_pct_display["Código"].map(model_map).fillna(0)
        # Build a code→target lookup for color_vs_model
        code_to_target = model_map
        # Build ativo→code lookup for the color function
        ativo_to_code = dict(zip(df_pct_display["Ativo"], df_pct_display["Código"]))
        fmt_pct["🎯 Modelo"] = "{:.2f}%"

        # Now drop Código for display
        df_pct_display = df_pct_display.drop(columns=["Código"])

        pct_value_cols = ["Atual (%)"] + evo_date_cols

        def color_vs_model(row):
            styles = []
            ativo = row["Ativo"]
            code = ativo_to_code.get(ativo, "")
            target = code_to_target.get(code, None)
            for col in row.index:
                if ativo == "📊 TOTAL PL":
                    styles.append(f"background-color: {TAG['vermelho']}40; font-weight: bold; color: {TAG['offwhite']}")
                elif ativo == "💰 CAIXA":
                    styles.append(f"background-color: {TAG['bg_card_alt']}; color: {TAG['offwhite']}")
                elif col in pct_value_cols and target is not None:
                    val = row[col]
                    diff = val - target
                    if abs(diff) < 0.5:
                        # On target → green
                        styles.append("background-color: rgba(107,222,151,0.15); color: #6BDE97")
                    elif diff > 0:
                        # Overweight → blue (TAG chart blue)
                        intensity = min(abs(diff) / 5.0, 1.0)
                        alpha = 0.12 + 0.18 * intensity
                        styles.append(f"background-color: rgba(92,133,247,{alpha:.2f}); color: #5C85F7")
                    else:
                        # Underweight → TAG vermelho
                        intensity = min(abs(diff) / 5.0, 1.0)
                        alpha = 0.12 + 0.18 * intensity
                        styles.append(f"background-color: rgba(237,90,110,{alpha:.2f}); color: #ED5A6E")
                elif col == "🎯 Modelo":
                    styles.append(f"background-color: rgba(255,136,83,0.12); color: {TAG['laranja']}; font-weight: 600")
                else:
                    styles.append("")
            return styles

        st.dataframe(
            df_pct_display.style.format(fmt_pct).apply(color_vs_model, axis=1),
            use_container_width=True, hide_index=True, height=420,
        )
        st.markdown(
            f"<div class='tag-legend'>"
            f"<span style='color:#6BDE97'>● <b>Aderente</b> (±0.5 p.p.)</span>"
            f"<span style='color:#5C85F7'>● <b>Acima</b> do modelo</span>"
            f"<span style='color:#ED5A6E'>● <b>Abaixo</b> do modelo</span>"
            f"<span style='color:{TAG['laranja']}'>● <b>Modelo</b> = % alvo</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        df_pct_display = df_pct_display.drop(columns=["Código"])
        st.dataframe(
            df_pct_display.style.format(fmt_pct).apply(style_evolution_table_rows, axis=1),
            use_container_width=True, hide_index=True, height=420,
        )


def export_to_excel(df_fin, df_pct, df_mov, carteira_info, adherence_df=None, plan_df=None):
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
        if adherence_df is not None and not adherence_df.empty:
            adherence_df.to_excel(writer, sheet_name="Aderência ao Modelo", index=False)
        if plan_df is not None and not plan_df.empty:
            plan_df.to_excel(writer, sheet_name="Plano de Realocação", index=False)
    return output.getvalue()


# ═══════════════════════════════════════════════════════════
# LOAD DATA & SESSION STATE
# ═══════════════════════════════════════════════════════════

liquid_df = load_liquidation_data()

if "new_movements" not in st.session_state:
    st.session_state.new_movements = []
if "portfolio_loaded" not in st.session_state:
    st.session_state.portfolio_loaded = False
if "model_loaded" not in st.session_state:
    st.session_state.model_loaded = False


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    # Logo TAG from brand guide (loaded from PNG file)
    _logo_path = os.path.join(os.path.dirname(__file__), "logo_sidebar.png")
    if os.path.exists(_logo_path):
        with open(_logo_path, "rb") as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode()
        st.markdown(
            f"""<div style='text-align:center; padding: 12px 0 8px 0;'>
            <img src='data:image/png;base64,{_logo_b64}'
                 alt='TAG Investimentos'
                 style='width:160px; height:auto; margin-bottom:6px;'/>
            <div style='width:40px; height:2px; background:{TAG["laranja"]}; margin:6px auto 0;'></div>
            <div style='font-size:0.75rem; color:{TAG["laranja"]}; margin-top:8px; font-weight:500;'>
            Simulador de Realocação</div>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""<div style='text-align:center; padding: 8px 0 16px 0;'>
            <div style='font-size:1.5rem; font-weight:700; color:{TAG["offwhite"]}; letter-spacing:-0.03em;'>
            TAG</div>
            <div style='font-size:0.7rem; text-transform:uppercase; letter-spacing:0.15em; color:{TAG["text_muted"]}; margin-top:-4px;'>
            Investimentos</div>
            <div style='width:40px; height:2px; background:{TAG["laranja"]}; margin:10px auto 0;'></div>
            <div style='font-size:0.75rem; color:{TAG["laranja"]}; margin-top:8px; font-weight:500;'>
            Simulador de Realocação</div>
            </div>""",
            unsafe_allow_html=True,
        )
    st.divider()

    page = st.radio(
        "Navegação",
        [
            "📂 Importar Dados",
            "📊 Carteira",
            "🎯 Carteira Modelo",
            "📅 Dados de Liquidação",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # Context info
    st.caption(f"Base de liquidação: {len(liquid_df)} fundos")
    if st.session_state.portfolio_loaded:
        ctx = get_portfolio_context()
        if ctx:
            st.caption(f"✅ {st.session_state.get('uploaded_filename', '')}")
            st.caption(f"PL: R$ {ctx['pl_total']:,.0f}")
            n_prov = len(ctx["provision_movs"])
            n_man = len(ctx["new_movs"])
            if n_prov:
                cotiz = len([m for m in ctx["provision_movs"] if m["operation"] == "Resgate (Cotizando)"])
                passv = len([m for m in ctx["provision_movs"] if m["operation"] == "Resgate Passivo"])
                st.caption(f"Provisões: {cotiz} resgates + {passv} passivo + {n_prov - cotiz - passv} outros")
            if n_man:
                st.caption(f"Movimentos manuais: {n_man}")
            if st.session_state.model_loaded:
                st.caption(f"🎯 Modelo: {len(st.session_state.model_df)} ativos")
    else:
        st.caption("⚠️ Nenhuma carteira carregada")


# ═══════════════════════════════════════════════════════════
# PAGE: IMPORTAR DADOS
# ═══════════════════════════════════════════════════════════

if page == "📂 Importar Dados":
    st.header("Importar Dados")

    tab_carteira, tab_modelo = st.tabs(["📁 Carteira (Posição Projetada)", "🎯 Carteira Modelo"])

    with tab_carteira:
        st.markdown(
            "Faça upload do arquivo de **Posição Projetada** "
            "(`.xlsx` com abas: *Carteira e Caixa*, *Ativos*, *Provisões*, *Boletas*)."
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

                ativos = sheets["ativos"]
                provisoes = sheets.get("provisoes")
                prov_movements = extract_provisions_as_movements(provisoes, ativos)
                st.session_state.provision_movements = prov_movements

                st.success(f"Carteira carregada: {uploaded.name}")

                # Summary
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
                        st.metric("Ativos", len(ativos))
                    with col4:
                        st.metric("Provisões", len(prov_movements))

                # Provisions
                if prov_movements:
                    display_provisions_summary(prov_movements, expanded=True)

                # Liquidation match
                st.subheader("Correspondência com Dados de Liquidação")
                cod_col = find_col(ativos, "CÓD. ATIVO", "COD. ATIVO", "CODIGO")
                match_results = []
                for _, ativo in ativos.iterrows():
                    fund_name = str(ativo.get("ATIVO", ""))
                    fund_code = ativo.get(cod_col, None) if cod_col else None
                    liq = match_fund_liquidation(fund_name, fund_code, liquid_df)
                    match_results.append({
                        "Ativo": fund_name[:45], "Código": fund_code,
                        "Match": "✅" if liq is not None else "❌",
                        "D+ Conv.": int(liq["Conversão Resgate"]) if liq is not None else "-",
                        "D+ Liq.": int(liq["Liquid. Resgate"]) if liq is not None else "-",
                        "Contagem": str(liq.get("Contagem Resgate", "")) if liq is not None else "-",
                    })
                df_match = pd.DataFrame(match_results)
                matched_count = (df_match["Match"] == "✅").sum()
                st.info(f"{matched_count}/{len(df_match)} ativos encontrados na base de liquidação.")
                st.dataframe(df_match, use_container_width=True, hide_index=True)
            else:
                st.error("Arquivo não contém a aba 'Ativos'. Verifique o formato.")

    with tab_modelo:
        st.markdown("Faça upload da **Carteira Modelo** (planilha com colunas: Código/Ativo e % Alvo).")

        model_file = st.file_uploader(
            "Selecione o arquivo da Carteira Modelo",
            type=["xlsx", "xls"],
            help="Planilha com % alvo por ativo",
            key="model_upload",
        )

        if model_file:
            with st.spinner("Processando modelo..."):
                model_df = parse_model_portfolio(model_file)
                st.session_state.model_df = model_df
                st.session_state.model_loaded = True

            st.success(f"✅ Modelo carregado: {len(model_df)} ativos, total {model_df['% Alvo'].sum():.1f}%")

        if st.session_state.model_loaded:
            model_df = st.session_state.model_df.copy()

            st.markdown("#### Editar % Alvo")
            st.caption("Altere os valores diretamente na tabela. Para remover um ativo, coloque 0%.")

            edited_df = st.data_editor(
                model_df,
                column_config={
                    "Código": st.column_config.TextColumn("Código", disabled=True),
                    "Ativo": st.column_config.TextColumn("Ativo", disabled=True),
                    "% Alvo": st.column_config.NumberColumn(
                        "% Alvo", min_value=0, max_value=100, step=0.1, format="%.2f%%",
                    ),
                },
                use_container_width=True, hide_index=True,
                key="model_editor",
            )

            # Detect changes and apply
            if not edited_df.equals(st.session_state.model_df):
                # Remove rows with 0% and save
                edited_df = edited_df[edited_df["% Alvo"] > 0].reset_index(drop=True)
                st.session_state.model_df = edited_df
                model_df = edited_df
                st.rerun()

            total_pct = model_df["% Alvo"].sum()
            remaining = 100 - total_pct
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Alocado", f"{total_pct:.1f}%")
            c2.metric("Caixa (residual)", f"{max(0, remaining):.1f}%")
            c3.metric("Ativos no Modelo", len(model_df))

            if total_pct > 100:
                st.error(f"Total ultrapassa 100%! Excesso de {total_pct - 100:.1f} p.p.")

            # ── Adicionar Novo Ativo ──
            st.divider()
            st.markdown("#### Adicionar Ativo ao Modelo")

            # Load available funds from liquidation database
            liquid_df = load_liquidation_data()
            existing_codes = set(model_df["Código"].astype(str))

            # Build options: "Apelido (Código Anbima) — Categoria"
            fund_options = []
            fund_lookup = {}  # display_name → {code, name}
            for _, frow in liquid_df.iterrows():
                code = str(frow.get("Código Anbima", "")).strip()
                name = str(frow.get("Apelido", "")).strip()
                categoria = str(frow.get("Categoria", "")).strip()
                if not name or code in existing_codes:
                    continue
                d_conv = int(frow.get("Conversão Resgate", 0))
                d_liq = int(frow.get("Liquid. Resgate", 0))
                display = f"{name}  |  Cód: {code}  |  {categoria}  |  D+{d_conv}+{d_liq}"
                fund_options.append(display)
                fund_lookup[display] = {"code": code, "name": name}

            ac1, ac2 = st.columns([3, 1])
            with ac1:
                selected_fund = st.selectbox(
                    "Buscar ativo disponível",
                    options=[""] + fund_options,
                    placeholder="Digite para buscar...",
                    key="model_fund_search",
                )
            with ac2:
                new_pct = st.number_input("% Alvo", min_value=0.01, max_value=100.0, step=0.5, value=1.0, key="add_model_pct")

            # Salvar seleção no session_state para persistir entre reruns
            if selected_fund and selected_fund in fund_lookup:
                st.session_state["_model_add_code"] = fund_lookup[selected_fund]["code"]
                st.session_state["_model_add_name"] = fund_lookup[selected_fund]["name"]
            elif not selected_fund:
                st.session_state.pop("_model_add_code", None)
                st.session_state.pop("_model_add_name", None)

            sel_code = st.session_state.get("_model_add_code", "")
            sel_name = st.session_state.get("_model_add_name", "")

            if sel_code:
                st.caption(f"Selecionado: **{sel_name}** (Código: {sel_code})")

            if st.button("Adicionar ao Modelo", type="primary"):
                if not sel_code:
                    st.warning("Selecione um ativo na lista acima.")
                elif sel_code in existing_codes:
                    st.warning(f"Código {sel_code} já existe no modelo. Altere o % Alvo na tabela acima.")
                else:
                    new_row = pd.DataFrame([{
                        "Código": sel_code,
                        "Ativo": sel_name,
                        "% Alvo": new_pct,
                    }])
                    st.session_state.model_df = pd.concat(
                        [st.session_state.model_df, new_row], ignore_index=True
                    )
                    # Limpar seleção após adicionar
                    st.session_state.pop("_model_add_code", None)
                    st.session_state.pop("_model_add_name", None)
                    st.rerun()

            # ── Gráfico ──
            if not model_df.empty:
                fig = go.Figure(go.Pie(
                    labels=model_df["Ativo"], values=model_df["% Alvo"],
                    hole=0.5, textinfo="label+percent", textposition="outside",
                    textfont=dict(size=11, color=TAG["offwhite"]),
                    marker=dict(colors=TAG["chart"], line=dict(color=TAG["bg_dark"], width=1.5)),
                    hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
                ))
                fig.update_layout(**PLOTLY_LAYOUT, height=350, showlegend=False)
                fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
# PAGE: POSIÇÃO ATUAL
# ═══════════════════════════════════════════════════════════

elif page == "📊 Carteira":
    st.header("Carteira")

    ctx = get_portfolio_context()
    if not ctx:
        st.warning("Nenhuma carteira carregada. Vá em Importar Dados primeiro.")
    else:
        ativos = ctx["ativos"]
        carteira = ctx["carteira"]
        caixa_initial = ctx["caixa_initial"]
        pl_total = ctx["pl_total"]
        all_movements = ctx["all_movements"]

        tab_pos, tab_proj, tab_cf = st.tabs([
            "📈 Posição Atual",
            "📊 Projeção",
            "💰 Fluxo de Caixa",
        ])

        # ── TAB 1: Posição Atual ──
        with tab_pos:
            if carteira is not None and not carteira.empty:
                row = carteira.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    pl = row.get("PL PROJETADO", row.get("PL FECHAMENTO", 0))
                    st.metric("PL Total", f"R$ {pl:,.2f}")
                with col2:
                    caixa = row.get("CAIXA", 0)
                    st.metric("Caixa", f"R$ {caixa:,.2f}")
                with col3:
                    liq_d0 = row.get("LIQUIDEZ D0", 0)
                    st.metric("Liquidez D0", f"R$ {liq_d0:,.2f}")
                with col4:
                    st.metric("Ativos", len(ativos))

            # Table — include CAIXA as a row
            st.subheader("Ativos")
            caixa_val = ctx["caixa_initial"]
            pl_val = ctx["pl_total"]
            estrategia_col = find_col(ativos, "ESTRATÉGIA", "ESTRATEGIA")
            preco_col = find_col(ativos, "PREÇO", "PRECO")

            # Build CAIXA row to prepend
            caixa_row_data = {"ATIVO": "CAIXA", "FINANCEIRO": caixa_val}
            if "% PL" in ativos.columns:
                caixa_row_data["% PL"] = (caixa_val / pl_val * 100) if pl_val > 0 else 0
            if estrategia_col and estrategia_col in ativos.columns:
                caixa_row_data[estrategia_col] = "CAIXA"
            if "CLASSE" in ativos.columns:
                caixa_row_data["CLASSE"] = "Caixa"
            caixa_row = pd.DataFrame([caixa_row_data])
            ativos_com_caixa = pd.concat([caixa_row, ativos], ignore_index=True)

            display_col_candidates = [
                "ATIVO", "CLASSE", estrategia_col or "ESTRATÉGIA",
                "QUANTIDADE", preco_col or "PREÇO", "FINANCEIRO", "% PL",
            ]
            available_cols = [c for c in display_col_candidates if c and c in ativos_com_caixa.columns]
            df_display = ativos_com_caixa[available_cols].copy()
            fmt = {"FINANCEIRO": "R$ {:,.2f}", "QUANTIDADE": "{:,.2f}", "% PL": "{:.2f}%"}
            if preco_col and preco_col in df_display.columns:
                fmt[preco_col] = "R$ {:,.6f}"
            st.dataframe(df_display.style.format(fmt, na_rep="—"), use_container_width=True, hide_index=True, height=400)

            # Charts — include CAIXA
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Alocação por Ativo")
                pie_source = ativos_com_caixa[["ATIVO", "FINANCEIRO"]].copy()
                top_n = pie_source.nlargest(10, "FINANCEIRO")
                others = pie_source[~pie_source.index.isin(top_n.index)]
                if not others.empty:
                    others_row = pd.DataFrame([{"ATIVO": "Outros", "FINANCEIRO": others["FINANCEIRO"].sum()}])
                    pie_data = pd.concat([top_n[["ATIVO", "FINANCEIRO"]], others_row], ignore_index=True)
                else:
                    pie_data = top_n[["ATIVO", "FINANCEIRO"]].copy()
                fig = go.Figure(go.Pie(
                    labels=pie_data["ATIVO"], values=pie_data["FINANCEIRO"],
                    hole=0.5, textinfo="label+percent", textposition="outside",
                    textfont=dict(size=11, color=TAG["offwhite"]),
                    marker=dict(colors=TAG["chart"], line=dict(color=TAG["bg_dark"], width=1.5)),
                    hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
                    pull=[0.02] * len(pie_data),
                ))
                fig.update_layout(**PLOTLY_LAYOUT, height=420, showlegend=False)
                fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                strat_col = find_col(ativos_com_caixa, "ESTRATÉGIA", "ESTRATEGIA")
                if strat_col and strat_col in ativos_com_caixa.columns:
                    st.subheader("Alocação por Estratégia")
                    strat = ativos_com_caixa.groupby(strat_col)["FINANCEIRO"].sum().reset_index().sort_values("FINANCEIRO", ascending=True)
                    fig2 = go.Figure(go.Bar(
                        y=strat[strat_col], x=strat["FINANCEIRO"],
                        orientation="h",
                        marker_color=TAG["laranja"], marker_line_width=0,
                        text=strat["FINANCEIRO"].apply(lambda v: f"R$ {v:,.0f}"),
                        textposition="auto", textfont=dict(color=TAG["offwhite"], size=11),
                        hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>",
                    ))
                    fig2.update_layout(**PLOTLY_LAYOUT, height=420)
                    fig2.update_layout(xaxis_title="Financeiro (R$)", yaxis_title="", margin=dict(l=140))
                    st.plotly_chart(fig2, use_container_width=True)

            # Provisões
            if ctx["provision_movs"]:
                st.divider()
                display_provisions_summary(ctx["provision_movs"], expanded=False)

        # ── TAB 2: Projeção ──
        with tab_proj:
            # ── Add manual movement inline ──
            with st.expander("➕ Adicionar Movimento Manual", expanded=False):
                fund_names = ativos["ATIVO"].tolist()
                cod_col = ctx["cod_col"]

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    operation = st.selectbox("Operação", ["Resgate", "Aplicação"])
                with col2:
                    fund = st.selectbox("Fundo/Ativo", fund_names)
                with col3:
                    value = st.number_input("Valor (R$)", min_value=0.01, step=10000.0, format="%.2f")
                with col4:
                    request_date = st.date_input("Data Solicitação", value=datetime.today())

                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                with col_btn1:
                    if st.button("➕ Adicionar", type="primary", use_container_width=True):
                        fund_row = ativos[ativos["ATIVO"] == fund].iloc[0]
                        fund_code = str(fund_row[cod_col]) if cod_col else None

                        # Validation
                        if operation == "Resgate":
                            fin_atual = float(fund_row.get("FINANCEIRO", 0))
                            if value > fin_atual * 1.05:
                                st.error(f"⚠️ Valor R$ {value:,.2f} > financeiro do ativo R$ {fin_atual:,.2f}")
                                st.stop()

                        mov = {
                            "fund_name": fund, "fund_code": fund_code,
                            "operation": operation, "value": value,
                            "request_date": pd.Timestamp(request_date), "source": "manual",
                        }
                        liq_date, d_plus, matched = compute_liquidation_date_for_new_movement(mov, liquid_df)
                        mov["liquidation_date"] = liq_date
                        mov["description"] = f"{operation} manual - {fund[:40]}"
                        st.session_state.new_movements.append(mov)
                        st.success(f"✅ {operation} R$ {value:,.0f} em {fund[:30]} → Liq: {liq_date.strftime('%d/%m/%Y')} ({d_plus})")
                        st.rerun()

                with col_btn2:
                    if st.session_state.new_movements:
                        if st.button("🗑️ Limpar Manuais", type="secondary", use_container_width=True):
                            st.session_state.new_movements = []
                            st.rerun()

            # Refresh after possible new movement
            ctx = get_portfolio_context()
            all_movements = ctx["all_movements"]

            if not all_movements:
                st.info(
                    "📭 Nenhum movimento pendente (provisões). "
                    "Use o botão **➕ Adicionar Movimento Manual** acima para simular realocações."
                )

            if all_movements:
                # Show categorized movements
                display_provisions_summary(all_movements, expanded=False)

                st.divider()

                # Build evolution
                df_fin, df_pct, df_mov = build_evolution_table(ativos, all_movements, caixa_initial)

                if df_fin is not None:
                    date_cols = [c for c in df_fin.columns if c not in ["Ativo", "Código", "Atual (R$)"]]
                    display_evolution_tables(df_fin, df_pct, date_cols)

                    # Variation chart
                    st.divider()
                    st.subheader("Variação % PL: Hoje vs Última Data")
                    last_date_col = date_cols[-1] if date_cols else None
                    if last_date_col:
                        chart_df = df_pct[~df_pct["Ativo"].isin(["📊 TOTAL PL"])].copy()
                        chart_df = chart_df.sort_values("Atual (%)", ascending=True)
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            name="Hoje", y=chart_df["Ativo"], x=chart_df["Atual (%)"],
                            orientation="h", marker_color=TAG["chart"][1], marker_line_width=0,
                            text=chart_df["Atual (%)"].apply(lambda v: f"{v:.1f}%"),
                            textposition="auto", textfont=dict(size=11, color=TAG["offwhite"]),
                        ))
                        fig.add_trace(go.Bar(
                            name=last_date_col, y=chart_df["Ativo"], x=chart_df[last_date_col],
                            orientation="h", marker_color=TAG["laranja"], marker_line_width=0,
                            text=chart_df[last_date_col].apply(lambda v: f"{v:.1f}%"),
                            textposition="auto", textfont=dict(size=11, color=TAG["offwhite"]),
                        ))
                        fig.update_layout(**PLOTLY_LAYOUT, barmode="group",
                                          height=max(350, len(chart_df) * 40 + 80))
                        fig.update_layout(
                            xaxis_title="% PL", yaxis_title="",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                        bgcolor="rgba(0,0,0,0)"),
                            margin=dict(l=160),
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    # Timeline
                    st.subheader("Timeline de Liquidação")
                    timeline_data = df_mov[df_mov["Data Liquidação"] != ""].copy()
                    if not timeline_data.empty:
                        timeline_data["Data Liquidação DT"] = pd.to_datetime(timeline_data["Data Liquidação"], dayfirst=True)

                        op_colors = {
                            "Resgate (Cotizando)": TAG["chart"][4],
                            "Resgate Passivo": TAG["laranja"],
                            "Débito/Passivo": TAG["chart"][6],
                            "Crédito (Provisão)": TAG["chart"][5],
                            "Resgate": TAG["vermelho_light"],
                            "Aplicação": TAG["chart"][2],
                        }

                        # Group by liquidation date and show as vertical markers
                        tl_grouped = timeline_data.groupby("Data Liquidação DT").agg(
                            total=("Valor (R$)", "sum"),
                            count=("Fundo", "count"),
                            ops=("Operação", lambda x: ", ".join(x.unique())),
                            details=("Fundo", lambda x: "<br>".join(
                                f"• {f[:30]}" for f in x
                            )),
                        ).reset_index().sort_values("Data Liquidação DT")

                        fig_tl = go.Figure()

                        # Lollipop chart: stem + circle for each date
                        for _, grp in tl_grouped.iterrows():
                            main_op = grp["ops"].split(",")[0].strip()
                            color = op_colors.get(main_op, TAG["chart"][0])
                            fig_tl.add_trace(go.Scatter(
                                x=[grp["Data Liquidação DT"], grp["Data Liquidação DT"]],
                                y=[0, grp["total"]],
                                mode="lines", line=dict(color=color, width=2),
                                showlegend=False, hoverinfo="skip",
                            ))
                            fig_tl.add_trace(go.Scatter(
                                x=[grp["Data Liquidação DT"]],
                                y=[grp["total"]],
                                mode="markers+text",
                                marker=dict(size=14, color=color, line=dict(color=TAG["bg_dark"], width=1.5)),
                                text=[f"R$ {grp['total']:,.0f}"],
                                textposition="top center",
                                textfont=dict(size=10, color=TAG["offwhite"]),
                                showlegend=False,
                                hovertemplate=(
                                    f"<b>{grp['Data Liquidação DT'].strftime('%d/%m/%Y')}</b><br>"
                                    f"{grp['count']} movimento(s)<br>"
                                    f"Total: R$ {grp['total']:,.0f}<br>"
                                    f"{grp['details']}<extra></extra>"
                                ),
                            ))

                        fig_tl.update_layout(**PLOTLY_LAYOUT, height=350)
                        fig_tl.update_layout(
                            xaxis_title="Data de Liquidação", yaxis_title="Valor (R$)",
                            showlegend=False,
                        )
                        st.plotly_chart(fig_tl, use_container_width=True)

                    # Export evolution
                    st.divider()
                    excel_data = export_to_excel(df_fin, df_pct, df_mov, carteira)
                    st.download_button(
                        label="📥 Exportar para Excel",
                        data=excel_data,
                        file_name=f"projecao_carteira_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                    )

        # ── TAB 3: Fluxo de Caixa ──
        with tab_cf:
            st.subheader("📈 Fluxo de Caixa Diário")
            st.caption(
                "Barras verdes = entradas no caixa (resgates). Barras vermelhas = saídas (aplicações/passivos). "
                "Linha branca = saldo acumulado do caixa (eixo direito)."
            )

            cash_fund_codes = ctx.get("cash_fund_codes", set())
            cash_details = ctx.get("cash_details", [])

            # A. Cash fund identification
            with st.expander("Fundos Considerados como Caixa (estratégia = Caixa)", expanded=False):
                if cash_details:
                    df_cash = pd.DataFrame(cash_details)
                    total_cash_funds = df_cash["Financeiro (R$)"].sum()
                    st.metric("Caixa Efetivo Inicial",
                              f"R$ {caixa_initial + total_cash_funds:,.0f}",
                              f"CAIXA R$ {caixa_initial:,.0f} + Fundos Caixa R$ {total_cash_funds:,.0f}")
                    st.dataframe(
                        df_cash.style.format({"Financeiro (R$)": "R$ {:,.0f}"}),
                        use_container_width=True, hide_index=True,
                    )
                else:
                    st.info("Nenhum fundo com estratégia Caixa encontrado na carteira.")
                    st.metric("Caixa Efetivo Inicial", f"R$ {caixa_initial:,.0f}")

            # B. Run cash flow analysis
            # If model is loaded, include plan movements in the timeline
            cf_movements = list(all_movements)  # copy
            plan_included = False
            if st.session_state.get("model_loaded") and not st.session_state.model_df.empty:
                model_df_cf = st.session_state.model_df
                adh_cf, _ = build_adherence_analysis(ativos, model_df_cf, all_movements, caixa_initial, pl_total)
                _, plan_movs_cf, _ = generate_smart_rebalancing_plan(
                    adh_cf, liquid_df, all_movements, caixa_initial,
                    ativos, cash_fund_codes, today=pd.Timestamp(datetime.today().date())
                )
                if plan_movs_cf:
                    cf_movements = all_movements + plan_movs_cf
                    plan_included = True

            if cf_movements:
                suggestions, negative_dates, df_timeline, initial_cash = suggest_request_dates(
                    cf_movements, liquid_df, cash_fund_codes, caixa_initial, ativos
                )
            else:
                # No movements at all — build minimal timeline to show initial state
                df_timeline, initial_cash = build_cash_flow_timeline(
                    caixa_initial, ativos, [], cash_fund_codes
                )
                suggestions, negative_dates = [], []

            if plan_included:
                st.info(
                    f"Fluxo de caixa inclui {len(plan_movs_cf)} movimentos do plano de realocacao "
                    f"(baseado na carteira modelo). Para detalhes, va em Carteira Modelo."
                )
            else:
                if st.session_state.get("model_loaded"):
                    st.caption("Modelo carregado mas sem movimentos gerados. Ajuste os % alvos para gerar movimentos.")
                else:
                    st.caption("Carregue uma carteira modelo para ver o impacto do rebalanceamento no caixa.")

            # C. Alerts
            if negative_dates:
                st.error(
                    f"ATENCAO: Caixa ficara negativo em "
                    f"{len(negative_dates)} data(s)! O fundo nao pode operar assim."
                )
                for nd in negative_dates[:5]:
                    st.warning(
                        f"{nd['date'].strftime('%d/%m/%Y')} — "
                        f"Saldo: R$ {nd['balance']:,.0f} — "
                        f"Deficit: R$ {nd['shortfall']:,.0f}"
                    )
                if len(negative_dates) > 5:
                    st.caption(f"... e mais {len(negative_dates) - 5} datas com saldo negativo.")
            else:
                if not df_timeline.empty:
                    st.success("Fluxo de caixa positivo em todas as datas. Nenhum risco de caixa negativo.")

            # D. Chart
            if not df_timeline.empty:
                fig_cf = build_cashflow_chart(df_timeline)
                st.plotly_chart(fig_cf, use_container_width=True)

            # E. Suggestions table
            if suggestions:
                st.divider()
                st.subheader("📋 Sugestão de Datas de Solicitação")
                st.caption(
                    "Para evitar saldo negativo, solicite os resgates nas datas abaixo. "
                    "O sistema calcula retroativamente com base no D+ de cada fundo."
                )
                df_sug = pd.DataFrame(suggestions)
                display_cols = [
                    "Fundo", "Código", "Operação", "Valor (R$)",
                    "Data Atual", "Data Sugerida", "D+",
                    "Cobre Saída Em", "Motivo",
                ]
                available_cols = [c for c in display_cols if c in df_sug.columns]
                st.dataframe(
                    df_sug[available_cols].style.format({"Valor (R$)": "R$ {:,.0f}"}).apply(
                        lambda row: [
                            "background-color: rgba(237,90,110,0.15)"
                            if row.get("is_impossible", False) else ""
                        ] * len(row), axis=1
                    ) if "is_impossible" in df_sug.columns else df_sug[available_cols].style.format({"Valor (R$)": "R$ {:,.0f}"}),
                    use_container_width=True, hide_index=True,
                )

            # F. Detailed timeline table
            if not df_timeline.empty:
                with st.expander("📊 Detalhes do Fluxo de Caixa Diário", expanded=False):
                    display_tl = df_timeline[df_timeline["Tem Evento"] | (df_timeline.index == 0)].copy()
                    if display_tl.empty:
                        display_tl = df_timeline.head(20)
                    display_tl["Data"] = display_tl["Data"].dt.strftime("%d/%m/%Y")
                    st.dataframe(
                        display_tl[["Data", "Entradas (R$)", "Saídas (R$)", "Líquido (R$)", "Saldo (R$)", "Detalhes"]].style.format({
                            "Entradas (R$)": "R$ {:,.0f}",
                            "Saídas (R$)": "R$ {:,.0f}",
                            "Líquido (R$)": "R$ {:,.0f}",
                            "Saldo (R$)": "R$ {:,.0f}",
                        }).apply(
                            lambda row: [
                                "background-color: rgba(237,90,110,0.15)" if row["Saldo (R$)"] < 0 else ""
                            ] * len(row), axis=1
                        ),
                        use_container_width=True, hide_index=True, height=400,
                    )


# ═══════════════════════════════════════════════════════════
# PAGE: CARTEIRA MODELO
# ═══════════════════════════════════════════════════════════

elif page == "🎯 Carteira Modelo":
    st.header("Aderência à Carteira Modelo")

    ctx = get_portfolio_context()
    if not ctx:
        st.warning("Nenhuma carteira carregada. Vá em Importar Dados primeiro.")
    elif not st.session_state.model_loaded:
        st.warning("Nenhuma carteira modelo carregada. Vá em Importar Dados, aba Carteira Modelo.")
    else:
        model_df = st.session_state.model_df
        ativos = ctx["ativos"]
        carteira = ctx["carteira"]
        caixa_initial = ctx["caixa_initial"]
        pl_total = ctx["pl_total"]
        all_movements = ctx["all_movements"]

        # ── Movimentos em andamento ──
        if all_movements:
            display_provisions_summary(all_movements, expanded=False)
            st.divider()

        # ── Análise de Aderência ──
        st.subheader("📊 Análise de Aderência")
        if all_movements:
            cotiz = len([m for m in all_movements if m["operation"] == "Resgate (Cotizando)"])
            passv = len([m for m in all_movements if m["operation"] == "Resgate Passivo"])
            st.caption(f"Posição projetada considerando {len(all_movements)} movimentos pendentes ({cotiz} resgates cotizando, {passv} resgates passivo)")

        adherence_df, info = build_adherence_analysis(ativos, model_df, all_movements, caixa_initial, pl_total)

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PL Projetado", f"R$ {info['pl_projetado']:,.0f}")
        with col2:
            st.metric("Caixa Projetado", f"R$ {info['caixa_projetado']:,.0f}")
        with col3:
            st.metric("Total a Aplicar", f"R$ {info['total_aplicar']:,.0f}")
        with col4:
            st.metric("Total a Resgatar", f"R$ {info['total_resgatar']:,.0f}")

        # Adherence table with colors
        def color_gap(row):
            gap = row["Gap (p.p.)"]
            if row["Ativo"] == "💰 CAIXA":
                return [f"background-color: {TAG['bg_card_alt']}"] * len(row)
            if abs(gap) < 0.5:
                return ["background-color: rgba(107,222,151,0.10)"] * len(row)
            elif gap > 0:
                # Need to apply (underweight - modelo wants more)
                return ["background-color: rgba(92,133,247,0.12)"] * len(row)
            else:
                # Need to redeem (overweight)
                return ["background-color: rgba(237,90,110,0.12)"] * len(row)

        st.dataframe(
            adherence_df.style
            .format({
                "Financeiro Projetado": "R$ {:,.2f}",
                "% Atual (Pós-Mov.)": "{:.2f}%",
                "% Alvo (Modelo)": "{:.2f}%",
                "Gap (p.p.)": "{:+.2f}",
                "Gap (R$)": "R$ {:,.0f}",
            })
            .apply(color_gap, axis=1),
            use_container_width=True, hide_index=True, height=450,
        )

        # Gap chart — horizontal bars side by side
        chart_data = adherence_df[adherence_df["Código"] != "CAIXA"].copy()
        chart_data = chart_data.sort_values("% Atual (Pós-Mov.)", ascending=True)

        fig_gap = go.Figure()
        fig_gap.add_trace(go.Bar(
            name="% Atual", y=chart_data["Ativo"], x=chart_data["% Atual (Pós-Mov.)"],
            orientation="h", marker_color=TAG["chart"][1], marker_line_width=0,
            text=chart_data["% Atual (Pós-Mov.)"].apply(lambda v: f"{v:.1f}%"),
            textposition="auto", textfont=dict(size=11, color=TAG["offwhite"]),
            hovertemplate="<b>%{y}</b><br>Atual: %{x:.2f}%<extra></extra>",
        ))
        fig_gap.add_trace(go.Bar(
            name="% Modelo", y=chart_data["Ativo"], x=chart_data["% Alvo (Modelo)"],
            orientation="h", marker_color=TAG["laranja"], marker_line_width=0,
            text=chart_data["% Alvo (Modelo)"].apply(lambda v: f"{v:.1f}%"),
            textposition="auto", textfont=dict(size=11, color=TAG["offwhite"]),
            hovertemplate="<b>%{y}</b><br>Modelo: %{x:.2f}%<extra></extra>",
        ))
        fig_gap.update_layout(**PLOTLY_LAYOUT, barmode="group", height=max(350, len(chart_data) * 40 + 80))
        fig_gap.update_layout(
            xaxis_title="% PL", yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=160),
        )
        st.plotly_chart(fig_gap, use_container_width=True)

        st.divider()

        # ── Plano de Realocação ──
        st.subheader("📋 Plano de Realocação Sugerido")

        plan_date = st.date_input(
            "Data mais cedo para submeter solicitações",
            value=datetime.today(),
            help="Data mínima para solicitar movimentos. O algoritmo calculará a data ideal de cada solicitação para casar com passivos.",
        )

        plan_df, plan_movements, plan_warnings = generate_smart_rebalancing_plan(
            adherence_df, liquid_df, all_movements, caixa_initial,
            ativos, ctx.get("cash_fund_codes", set()), today=pd.Timestamp(plan_date)
        )

        # ── Warnings ──
        for w in plan_warnings:
            if w["level"] == "error":
                st.error(f"🚨 {w['message']}")
            else:
                st.warning(f"⚠️ {w['message']}")

        if not plan_df.empty:

            # ══════════════════════════════════════════════════════
            # ── TURNOVER DA CARTEIRA: Legenda de Entradas e Saídas ──
            # ══════════════════════════════════════════════════════
            st.markdown("### 🔄 Turnover da Carteira")

            # Compute turnover data per asset
            resgates_plan = plan_df[plan_df["Operação"] == "Resgate"].copy()
            aplicacoes_plan = plan_df[plan_df["Operação"] == "Aplicação"].copy()

            total_resgates = resgates_plan["Valor (R$)"].sum() if not resgates_plan.empty else 0
            total_aplicacoes = aplicacoes_plan["Valor (R$)"].sum() if not aplicacoes_plan.empty else 0
            turnover_total = total_resgates + total_aplicacoes
            pl_proj = info["pl_projetado"]
            turnover_pct = (turnover_total / pl_proj * 100) if pl_proj > 0 else 0

            # Provisão passivos
            passivo_movs = [m for m in all_movements if m["operation"] == "Resgate Passivo"]
            total_passivo = sum(m["value"] for m in passivo_movs)
            cotiz_movs = [m for m in all_movements if m["operation"] in ("Resgate (Cotizando)", "Resgate (Provisão)")]
            total_cotiz = sum(m["value"] for m in cotiz_movs)

            # Metrics row
            tc1, tc2, tc3, tc4, tc5 = st.columns(5)
            tc1.metric("Turnover Total", f"R$ {turnover_total:,.0f}", f"{turnover_pct:.1f}% do PL")
            tc2.metric("Saídas (Resgates)", f"R$ {total_resgates:,.0f}", f"{len(resgates_plan)} operações")
            tc3.metric("Entradas (Aplicações)", f"R$ {total_aplicacoes:,.0f}", f"{len(aplicacoes_plan)} operações")
            tc4.metric("Passivos (Investidores)", f"R$ {total_passivo:,.0f}", f"{len(passivo_movs)} saídas")
            tc5.metric("Cotizando (em trânsito)", f"R$ {total_cotiz:,.0f}", f"{len(cotiz_movs)} resgates")

            # ── Build turnover chart per asset ──
            # Aggregate resgates and aplicações by ativo
            resg_by_ativo = resgates_plan.groupby("Ativo")["Valor (R$)"].sum().reset_index()
            resg_by_ativo.columns = ["Ativo", "Resgate"]
            aplic_by_ativo = aplicacoes_plan.groupby("Ativo")["Valor (R$)"].sum().reset_index()
            aplic_by_ativo.columns = ["Ativo", "Aplicação"]

            # Merge
            turnover_df = pd.merge(resg_by_ativo, aplic_by_ativo, on="Ativo", how="outer").fillna(0)
            turnover_df = turnover_df.sort_values("Resgate", ascending=True)

            if not turnover_df.empty:
                fig_turnover = go.Figure()

                # Resgates (saídas) — negative bars (left side)
                fig_turnover.add_trace(go.Bar(
                    y=turnover_df["Ativo"], x=-turnover_df["Resgate"],
                    name="Saída (Resgate)",
                    orientation="h",
                    marker_color=TAG["chart"][4],  # vermelho/rosa
                    marker_line_width=0,
                    text=turnover_df["Resgate"].apply(lambda v: f"R$ {v:,.0f}" if v > 0 else ""),
                    textposition="auto",
                    textfont=dict(size=10, color=TAG["offwhite"]),
                    hovertemplate="<b>%{y}</b><br>Resgate: R$ %{customdata:,.0f}<extra></extra>",
                    customdata=turnover_df["Resgate"],
                ))

                # Aplicações (entradas) — positive bars (right side)
                fig_turnover.add_trace(go.Bar(
                    y=turnover_df["Ativo"], x=turnover_df["Aplicação"],
                    name="Entrada (Aplicação)",
                    orientation="h",
                    marker_color=TAG["chart"][2],  # verde
                    marker_line_width=0,
                    text=turnover_df["Aplicação"].apply(lambda v: f"R$ {v:,.0f}" if v > 0 else ""),
                    textposition="auto",
                    textfont=dict(size=10, color=TAG["offwhite"]),
                    hovertemplate="<b>%{y}</b><br>Aplicação: R$ %{customdata:,.0f}<extra></extra>",
                    customdata=turnover_df["Aplicação"],
                ))

                # Also add passivo outflows if any
                if passivo_movs:
                    pas_data = pd.DataFrame([{
                        "Ativo": "PASSIVO (Investidores)",
                        "Valor": total_passivo,
                    }])
                    fig_turnover.add_trace(go.Bar(
                        y=pas_data["Ativo"], x=-pas_data["Valor"],
                        name="Passivo (obrigação)",
                        orientation="h",
                        marker_color=TAG["vermelho"],
                        marker_line_width=0,
                        text=[f"R$ {total_passivo:,.0f}"],
                        textposition="auto",
                        textfont=dict(size=10, color=TAG["offwhite"]),
                        hovertemplate="<b>Passivo</b><br>R$ %{customdata:,.0f}<extra></extra>",
                        customdata=pas_data["Valor"],
                    ))

                fig_turnover.add_vline(x=0, line_color="rgba(230,228,219,0.4)", line_width=1.5)
                fig_turnover.update_layout(**PLOTLY_LAYOUT, barmode="relative",
                                           height=max(300, len(turnover_df) * 45 + 100))
                fig_turnover.update_layout(
                    xaxis_title="← Saídas (R$)          Entradas (R$) →",
                    yaxis_title="",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=180),
                    xaxis=dict(tickformat=",.0f", tickprefix="R$ "),
                )
                st.plotly_chart(fig_turnover, use_container_width=True)

            # Legend box
            st.markdown(
                f"""
<div style="background: {TAG['bg_card']}; border: 1px solid {TAG['vermelho']}33; border-radius: 8px; padding: 16px; margin: 8px 0 16px 0;">
<b style="color:{TAG['offwhite']}; font-size: 14px;">Legenda do Turnover</b><br><br>
<span style="color:{TAG['chart'][4]};">&#9632;</span> <b>Saida (Resgate)</b> — Dinheiro sendo retirado do fundo e voltando para o caixa da carteira. O ativo perde posicao.<br>
<span style="color:{TAG['chart'][2]};">&#9632;</span> <b>Entrada (Aplicacao)</b> — Dinheiro do caixa sendo aplicado no fundo. O ativo ganha posicao.<br>
<span style="color:{TAG['vermelho']};">&#9632;</span> <b>Passivo (Investidores)</b> — Resgates de cotistas do fundo. E uma obrigacao: o dinheiro sai do PL total.<br>
<span style="color:{TAG['chart'][5]};">&#9632;</span> <b>Cotizando</b> — Resgates ja solicitados que estao em periodo de conversao aguardando liquidacao.<br><br>
<b>Turnover = {turnover_pct:.1f}% do PL</b> — Soma de todos os resgates + aplicacoes do plano dividida pelo PL projetado.
</div>
""",
                unsafe_allow_html=True,
            )

            st.divider()

            # ══════════════════════════════════════════════════════
            # ── METODOLOGIA DE CALCULO ──
            # ══════════════════════════════════════════════════════
            with st.expander("📐 Como os calculos sao feitos?", expanded=False):
                cash_fund_codes_info = ctx.get("cash_fund_codes", set())
                n_cash_funds = len(cash_fund_codes_info)

                st.markdown(f"""
**1. Posicao Projetada (base do calculo)**

Partimos da posicao atual de cada ativo e aplicamos todos os movimentos pendentes
(provisoes, cotizando, passivos) para chegar na **posicao projetada**:

- **PL Projetado** = soma de todos os ativos + caixa apos movimentos = **R$ {info['pl_projetado']:,.0f}**
- **Caixa Projetado** = caixa atual apos provisoes = **R$ {info['caixa_projetado']:,.0f}**

---

**2. Gap vs Modelo (aderencia)**

Para cada ativo, calculamos:

- **% Atual** = Financeiro do ativo / PL Projetado x 100
- **% Alvo** = % definido na carteira modelo
- **Gap (p.p.)** = % Alvo - % Atual
- **Gap (R$)** = Gap (p.p.) / 100 x PL Projetado

Se Gap > 0 → o ativo esta **abaixo** do modelo (precisa de aplicacao).
Se Gap < 0 → o ativo esta **acima** do modelo (precisa de resgate).

A **linha CAIXA** recebe o residual: % Alvo do Caixa = 100% - soma dos % Alvo de todos os ativos.

---

**3. Plano de Realocacao (5 fases)**

O algoritmo gera o plano em 5 fases sequenciais:

**Fase 1 — Mapa de Caixa:** Simula o caixa efetivo (linha CAIXA {"+ " + str(n_cash_funds) + " fundos classificados como caixa" if n_cash_funds > 0 else ""})
dia a dia, registrando o impacto de cada provisao no caixa.

**Fase 2 — Cobertura de Passivos:** Se algum resgate de investidor (passivo) vai gerar caixa negativo,
o algoritmo agenda resgates de fundos overweight que liquidem **antes** do passivo. Prioriza fundos acima
do modelo e com D+ mais curto.

**Fase 3 — Resgates de Rebalanceamento:** Para cada fundo acima do modelo (Gap < 0), agenda um resgate
pelo valor do gap. O D+ de cada fundo e respeitado: Data Liquidacao = Hoje + D+ Conversao + D+ Liquidacao.

**Fase 4 — Aplicacoes com controle de caixa:** Para cada fundo abaixo do modelo (Gap > 0), encontra a
primeira data em que o caixa comporta a aplicacao **sem ficar negativo em nenhum dia futuro**.
{"Fundos classificados como caixa sao agendados imediatamente (a aplicacao e neutra para o caixa efetivo)." if n_cash_funds > 0 else ""}

**Fase 5 — Validacao Final:** Simula todo o fluxo (provisoes + plano) dia a dia para confirmar que o
caixa nunca fica negativo.

---

**4. D+ (Prazo de Liquidacao)**

Cada fundo tem seus prazos obtidos da base de liquidacao:

- **Conversao Resgate (D+X)** — dias apos a solicitacao para o fundo converter as cotas
- **Liquidacao Resgate (D+Y)** — dias apos a conversao para o dinheiro cair na conta
- **Contagem** — Dias uteis ou corridos
- **Data Liquidacao** = Data Solicitacao + D+ Conversao + D+ Liquidacao (respeitando a contagem)

Para aplicacoes: **Conversao Aplicacao (D+Z)** = dias para as cotas serem convertidas.

---

**5. Turnover**

- **Turnover Total (R$)** = Soma de todos os resgates + aplicacoes do plano = **R$ {turnover_total:,.0f}**
- **Turnover (% PL)** = Turnover Total / PL Projetado x 100 = **{turnover_pct:.1f}%**
- Quanto maior o turnover, mais movimentacoes sao necessarias para atingir o modelo
- Passivos NAO contam no turnover (sao obrigacoes, nao decisoes de realocacao)

---

**6. Caixa Efetivo**

O caixa efetivo e a soma de:
- **Linha CAIXA** (saldo disponivel imediato)
{"- **Fundos com estrategia CAIXA** (" + str(n_cash_funds) + " fundos) — posicoes em fundos de liquidez imediata" if n_cash_funds > 0 else ""}

Quando voce aplica em um fundo caixa, o dinheiro sai da linha CAIXA e entra no fundo — o caixa efetivo
total nao muda (a operacao e **neutra**). Por isso o grafico mostra cada componente separado.
""")

            st.divider()

            # ── Detalhamento do Plano ──
            st.markdown("### 📋 Detalhamento do Plano")

            display_cols = ["Prioridade", "Ativo", "Operação", "Valor (R$)", "D+",
                            "Data Solicitação", "Data Liquidação", "Motivo"]
            fmt = {"Valor (R$)": "R$ {:,.0f}"}

            # ── Seção 1: Cobertura de Passivos ──
            cobertura = plan_df[plan_df["Motivo"].str.contains("passivo", case=False, na=False)]
            if not cobertura.empty:
                st.markdown("#### 🎯 Cobertura de Passivos")
                st.caption("Resgates programados para que o dinheiro chegue a tempo de pagar os resgates de investidores.")
                st.dataframe(
                    cobertura[display_cols].style.format(fmt),
                    use_container_width=True, hide_index=True,
                )
                st.metric("Total Resgates (Cobertura)", f"R$ {cobertura['Valor (R$)'].sum():,.0f}")

            # ── Seção 2: Resgates de Rebalanceamento ──
            resgates_rebal = plan_df[
                (plan_df["Operação"] == "Resgate") &
                (~plan_df["Motivo"].str.contains("passivo", case=False, na=False))
            ]
            if not resgates_rebal.empty:
                st.markdown("#### 📤 Resgates (Rebalanceamento)")
                st.caption("Resgates adicionais para ajustar a carteira ao modelo.")
                st.dataframe(
                    resgates_rebal[display_cols].style.format(fmt),
                    use_container_width=True, hide_index=True,
                )
                st.metric("Total Resgates (Rebalanceamento)", f"R$ {resgates_rebal['Valor (R$)'].sum():,.0f}")

            # ── Seção 3: Aplicações ──
            aplicacoes = plan_df[plan_df["Operação"] == "Aplicação"]
            if not aplicacoes.empty:
                st.markdown("#### 📥 Aplicações")
                st.caption("Aplicações programadas para quando o caixa dos resgates estiver disponível.")
                st.dataframe(
                    aplicacoes[display_cols].style.format(fmt),
                    use_container_width=True, hide_index=True,
                )
                st.metric("Total Aplicações", f"R$ {aplicacoes['Valor (R$)'].sum():,.0f}")

            # ── Nenhum movimento ──
            if cobertura.empty and resgates_rebal.empty and aplicacoes.empty:
                st.info("Nenhum movimento necessário.")

            # ── Cronograma Visual por Ativo (Gantt) ──
            st.markdown("### 📅 Cronograma de Liquidações por Ativo")
            st.caption(
                "Cada barra mostra o periodo entre a data de solicitacao e a data de liquidacao de cada operacao. "
                "Passe o mouse para ver os detalhes."
            )

            try:
                today_ts = pd.Timestamp(plan_date)

                # Build per-asset timeline rows
                gantt_rows = []

                # 1. Passivos (obrigações de investidores)
                for m in all_movements:
                    if m["operation"] == "Resgate Passivo" and pd.notna(m.get("liquidation_date")):
                        ld = pd.Timestamp(m["liquidation_date"])
                        if ld >= today_ts:
                            gantt_rows.append({
                                "Ativo": "PASSIVO (Investidores)",
                                "Operação": "Passivo",
                                "Início": today_ts,
                                "Fim": ld,
                                "Valor": m["value"],
                                "D+": "",
                                "color": TAG["vermelho"],
                            })

                # 2. Cotizando (resgates em trânsito)
                for m in all_movements:
                    if m["operation"] in ("Resgate (Cotizando)", "Resgate (Provisão)") and pd.notna(m.get("liquidation_date")):
                        ld = pd.Timestamp(m["liquidation_date"])
                        rd = pd.Timestamp(m.get("request_date", today_ts))
                        fund_name = m.get("fund_name", "")[:30]
                        if ld >= today_ts:
                            gantt_rows.append({
                                "Ativo": fund_name,
                                "Operação": "Cotizando",
                                "Início": rd if rd >= today_ts else today_ts,
                                "Fim": ld,
                                "Valor": m["value"],
                                "D+": "",
                                "color": TAG["chart"][5],
                            })

                # 3. Plan movements (resgates e aplicações)
                for _, row in plan_df.iterrows():
                    sol = pd.to_datetime(row["Data Solicitação"], dayfirst=True)
                    liq = pd.to_datetime(row["Data Liquidação"], dayfirst=True)
                    op = row["Operação"]
                    ativo = str(row["Ativo"])[:30]
                    if op == "Resgate":
                        color = TAG["chart"][4]  # rosa/vermelho
                    else:
                        color = TAG["chart"][2]  # verde
                    gantt_rows.append({
                        "Ativo": ativo,
                        "Operação": op,
                        "Início": sol,
                        "Fim": liq,
                        "Valor": row["Valor (R$)"],
                        "D+": row.get("D+", ""),
                        "color": color,
                    })

                if gantt_rows:
                    df_gantt = pd.DataFrame(gantt_rows)

                    # Sort: Passivo first, then by liquidation date, then alphabetically
                    op_order = {"Passivo": 0, "Cotizando": 1, "Resgate": 2, "Aplicação": 3}
                    df_gantt["_sort"] = df_gantt["Operação"].map(op_order).fillna(5)
                    df_gantt = df_gantt.sort_values(["_sort", "Fim", "Ativo"], ascending=[True, True, True])

                    # Build Y labels: "Ativo (Operação)"
                    df_gantt["Label"] = df_gantt.apply(
                        lambda r: f"{r['Ativo']} ({r['Operação']})", axis=1
                    )

                    fig_gantt = go.Figure()
                    _epoch = pd.Timestamp("1970-01-01")

                    # Add one bar per row (horizontal Gantt)
                    # Use epoch-ms for base+x to avoid pandas Timestamp+int error
                    for idx, row in df_gantt.iterrows():
                        inicio = pd.Timestamp(row["Início"])
                        fim = pd.Timestamp(row["Fim"])
                        # Ensure bar has at least 1 day width for visibility
                        if fim <= inicio:
                            fim = inicio + timedelta(days=1)

                        duracao_dias = (fim - inicio).days
                        inicio_ms = int((inicio - _epoch).total_seconds() * 1000)
                        duracao_ms = int((fim - inicio).total_seconds() * 1000)

                        fig_gantt.add_trace(go.Bar(
                            y=[row["Label"]],
                            x=[duracao_ms],
                            base=[inicio_ms],
                            orientation="h",
                            marker_color=row["color"],
                            marker_line=dict(width=0.5, color=TAG["bg_dark"]),
                            text=f"R$ {row['Valor']:,.0f}",
                            textposition="inside",
                            textfont=dict(size=10, color=TAG["offwhite"]),
                            insidetextanchor="middle",
                            showlegend=False,
                            hovertemplate=(
                                f"<b>{row['Ativo']}</b><br>"
                                f"Operacao: {row['Operação']}<br>"
                                f"Solicitacao: {inicio.strftime('%d/%m/%Y')}<br>"
                                f"Liquidacao: {fim.strftime('%d/%m/%Y')}<br>"
                                f"Prazo: {duracao_dias} dias<br>"
                                f"Valor: R$ {row['Valor']:,.0f}<br>"
                                f"{row['D+']}"
                                "<extra></extra>"
                            ),
                        ))

                    # Add today line (epoch-ms)
                    today_ms = int((today_ts - _epoch).total_seconds() * 1000)
                    fig_gantt.add_vline(
                        x=today_ms, line_dash="dash",
                        line_color=TAG["offwhite"], line_width=1.5,
                        annotation_text="Hoje",
                        annotation_font=dict(size=10, color=TAG["offwhite"]),
                    )

                    # Legend traces (invisible, just for legend)
                    legend_items = [
                        ("Resgate (saída)", TAG["chart"][4]),
                        ("Aplicação (entrada)", TAG["chart"][2]),
                    ]
                    # Add passivo and cotizando to legend only if they exist
                    if any(r["Operação"] == "Passivo" for r in gantt_rows):
                        legend_items.append(("Passivo (obrigação)", TAG["vermelho"]))
                    if any(r["Operação"] == "Cotizando" for r in gantt_rows):
                        legend_items.append(("Cotizando (em trânsito)", TAG["chart"][5]))

                    for lname, lcolor in legend_items:
                        fig_gantt.add_trace(go.Bar(
                            y=[None], x=[None], name=lname,
                            marker_color=lcolor, showlegend=True,
                        ))

                    n_rows = len(df_gantt)
                    fig_gantt.update_layout(**PLOTLY_LAYOUT, height=max(350, n_rows * 38 + 100))
                    fig_gantt.update_layout(
                        xaxis=dict(
                            type="date", tickformat="%d/%m/%Y",
                            title="",
                            dtick=7 * 24 * 60 * 60 * 1000,  # 7 days in ms
                            tickangle=-45,
                            tickfont=dict(size=10),
                        ),
                        yaxis=dict(title="", autorange="reversed"),
                        barmode="overlay",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                        margin=dict(l=220),
                    )
                    st.plotly_chart(fig_gantt, use_container_width=True)

            except Exception as e:
                st.warning(f"Erro ao gerar cronograma: {e}")

            st.divider()

            # ── Evolução: Provisões + Plano ──
            st.subheader("📅 Projeção Completa (Provisões + Plano)")
            st.caption("Como a carteira ficará em cada data de liquidação, incluindo provisões em andamento e o plano sugerido.")

            combined_movements = all_movements + plan_movements
            df_evo_fin, df_evo_pct, df_evo_mov = build_evolution_table(ativos, combined_movements, caixa_initial)

            if df_evo_fin is not None:
                evo_date_cols = [c for c in df_evo_fin.columns if c not in ["Ativo", "Código", "Atual (R$)"]]

                # Build model map for color comparison — keyed by Código for reliable matching
                model_map = dict(zip(adherence_df["Código"], adherence_df["% Alvo (Modelo)"]))

                display_provisions_summary(combined_movements, expanded=False)
                display_evolution_tables(df_evo_fin, df_evo_pct, evo_date_cols, model_map=model_map)

                # ── Composition evolution chart ──
                if evo_date_cols:
                    st.subheader("Evolucao da Composicao da Carteira")
                    st.caption("Como o % de cada fundo muda ao longo das datas de liquidacao. As linhas tracejadas mostram o % alvo do modelo.")

                    # Build data: each fund's % at each date
                    fund_rows = df_evo_pct[~df_evo_pct["Ativo"].isin(["📊 TOTAL PL", "💰 CAIXA"])].copy()
                    time_points = ["Atual (%)"] + evo_date_cols
                    time_labels = ["Hoje"] + evo_date_cols

                    fig_evo_comp = go.Figure()
                    for idx, (_, fund_row) in enumerate(fund_rows.iterrows()):
                        ativo = fund_row["Ativo"]
                        code = fund_row["Código"]
                        color = TAG["chart"][idx % len(TAG["chart"])]
                        y_vals = [fund_row[tp] for tp in time_points]
                        fig_evo_comp.add_trace(go.Scatter(
                            x=time_labels, y=y_vals,
                            mode="lines+markers", name=ativo[:25],
                            line=dict(color=color, width=2.5),
                            marker=dict(size=7, color=color),
                            hovertemplate=(
                                f"<b>{ativo[:30]}</b><br>"
                                "%{x}<br>%{y:.2f}%<extra></extra>"
                            ),
                        ))
                        # Model target line (dashed horizontal)
                        target = model_map.get(code, None)
                        if target and target > 0:
                            fig_evo_comp.add_trace(go.Scatter(
                                x=[time_labels[0], time_labels[-1]], y=[target, target],
                                mode="lines", name=f"Alvo {ativo[:15]}",
                                line=dict(color=color, width=1.5, dash="dot"),
                                showlegend=False,
                                hovertemplate=f"<b>Alvo {ativo[:25]}</b>: {target:.1f}%<extra></extra>",
                            ))

                    fig_evo_comp.update_layout(**PLOTLY_LAYOUT, height=450)
                    fig_evo_comp.update_layout(
                        xaxis_title="", yaxis_title="% PL",
                        yaxis=dict(ticksuffix="%"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig_evo_comp, use_container_width=True)

                # Final comparison chart: Atual → Projeção → Modelo
                if evo_date_cols:
                    last_dc = evo_date_cols[-1]
                    st.subheader(f"Convergencia ao Modelo: Atual → {last_dc}")
                    st.caption("Compare a posicao atual, a projecao apos executar o plano e o % alvo do modelo.")
                    df_evo_pct_display = df_evo_pct.copy()
                    df_evo_pct_display["Modelo"] = df_evo_pct_display["Código"].map(model_map).fillna(0)
                    cmp = df_evo_pct_display[~df_evo_pct_display["Ativo"].isin(["📊 TOTAL PL"])].copy()
                    cmp = cmp.sort_values("Modelo", ascending=True)
                    fig_cmp = go.Figure()
                    # Bar 1: Current position
                    fig_cmp.add_trace(go.Bar(
                        name="% Atual (Hoje)", y=cmp["Ativo"], x=cmp["Atual (%)"],
                        orientation="h", marker_color=TAG["chart"][9], marker_line_width=0,
                        text=cmp["Atual (%)"].apply(lambda v: f"{v:.1f}%"),
                        textposition="auto", textfont=dict(size=10, color=TAG["offwhite"]),
                        hovertemplate="<b>%{y}</b><br>Atual: %{x:.2f}%<extra></extra>",
                    ))
                    # Bar 2: Projected after plan
                    fig_cmp.add_trace(go.Bar(
                        name=f"% Projetado ({last_dc})", y=cmp["Ativo"], x=cmp[last_dc],
                        orientation="h", marker_color=TAG["chart"][1], marker_line_width=0,
                        text=cmp[last_dc].apply(lambda v: f"{v:.1f}%"),
                        textposition="auto", textfont=dict(size=10, color=TAG["offwhite"]),
                        hovertemplate="<b>%{y}</b><br>Projetado: %{x:.2f}%<extra></extra>",
                    ))
                    # Bar 3: Model target
                    fig_cmp.add_trace(go.Bar(
                        name="% Modelo (Alvo)", y=cmp["Ativo"], x=cmp["Modelo"],
                        orientation="h", marker_color=TAG["laranja"], marker_line_width=0,
                        text=cmp["Modelo"].apply(lambda v: f"{v:.1f}%"),
                        textposition="auto", textfont=dict(size=10, color=TAG["offwhite"]),
                        hovertemplate="<b>%{y}</b><br>Modelo: %{x:.2f}%<extra></extra>",
                    ))
                    fig_cmp.update_layout(**PLOTLY_LAYOUT, barmode="group",
                                          height=max(400, len(cmp) * 50 + 100))
                    fig_cmp.update_layout(
                        xaxis_title="% PL", yaxis_title="",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                    bgcolor="rgba(0,0,0,0)"),
                        margin=dict(l=180),
                    )
                    st.plotly_chart(fig_cmp, use_container_width=True)

                    # Delta chart: show gap remaining after plan
                    cmp["Gap Restante"] = cmp[last_dc] - cmp["Modelo"]
                    cmp_sorted = cmp.sort_values("Gap Restante")
                    fig_delta = go.Figure()
                    colors = [TAG["chart"][2] if g >= -0.5 and g <= 0.5
                              else TAG["chart"][1] if g > 0.5
                              else TAG["chart"][4]
                              for g in cmp_sorted["Gap Restante"]]
                    fig_delta.add_trace(go.Bar(
                        y=cmp_sorted["Ativo"], x=cmp_sorted["Gap Restante"],
                        orientation="h", marker_color=colors, marker_line_width=0,
                        text=cmp_sorted["Gap Restante"].apply(lambda v: f"{v:+.1f} p.p."),
                        textposition="outside", textfont=dict(size=11, color=TAG["offwhite"]),
                        hovertemplate="<b>%{y}</b><br>Gap: %{x:+.2f} p.p.<extra></extra>",
                    ))
                    fig_delta.add_vline(x=0, line_color="rgba(230,228,219,0.3)", line_width=1)
                    fig_delta.update_layout(**PLOTLY_LAYOUT,
                                            height=max(300, len(cmp_sorted) * 35 + 80))
                    fig_delta.update_layout(
                        xaxis_title="Gap vs Modelo (p.p.)", yaxis_title="",
                        margin=dict(l=180),
                    )
                    st.caption("Gap restante apos execucao do plano: verde = aderente, azul = acima, vermelho = abaixo.")
                    st.plotly_chart(fig_delta, use_container_width=True)

            # ── CASH FLOW validation ──
            st.divider()
            st.subheader("📈 Validacao do Caixa")

            # Show plan summary metrics
            n_resg_plan = sum(1 for m in plan_movements if m["operation"] == "Resgate")
            n_aplic_plan = sum(1 for m in plan_movements if "Aplicação" in m["operation"])
            val_resg_plan = sum(m["value"] for m in plan_movements if m["operation"] == "Resgate")
            val_aplic_plan = sum(m["value"] for m in plan_movements if "Aplicação" in m["operation"])
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Provisoes", f"{len(all_movements)}")
            mc2.metric("Resgates (Plano)", f"{n_resg_plan}", f"R$ {val_resg_plan:,.0f}")
            mc3.metric("Aplicacoes (Plano)", f"{n_aplic_plan}", f"R$ {val_aplic_plan:,.0f}")
            mc4.metric("Liquido no Caixa", f"R$ {val_resg_plan - val_aplic_plan:,.0f}")

            cash_fund_codes = ctx.get("cash_fund_codes", set())
            sug_plan, neg_plan, tl_plan, init_plan = suggest_request_dates(
                combined_movements, liquid_df, cash_fund_codes, caixa_initial, ativos
            )

            if neg_plan:
                st.error(
                    f"ATENCAO: Com este plano, o caixa ficara negativo em "
                    f"{len(neg_plan)} data(s)!"
                )
                for nd in neg_plan[:5]:
                    st.warning(
                        f"{nd['date'].strftime('%d/%m/%Y')} — "
                        f"Saldo: R$ {nd['balance']:,.0f} — "
                        f"Deficit: R$ {nd['shortfall']:,.0f}"
                    )
            else:
                if not tl_plan.empty:
                    st.success("Plano viavel! Caixa positivo em todas as datas.")

            st.caption(
                "Barras verdes = entradas no caixa (resgates). Barras vermelhas = saídas (aplicações/passivos). "
                "Linha branca = saldo acumulado do caixa (eixo direito)."
            )

            if not tl_plan.empty:
                # Key cash metrics
                _saldo_vals = tl_plan["Saldo (R$)"]
                _cx_ini = _saldo_vals.iloc[0]
                _cx_min = _saldo_vals.min()
                _cx_fin = _saldo_vals.iloc[-1]
                _cx1, _cx2, _cx3 = st.columns(3)
                _cx1.metric("Caixa Inicial", f"R$ {_cx_ini:,.0f}")
                _cx2.metric("Caixa Mínimo", f"R$ {_cx_min:,.0f}",
                            delta=f"R$ {_cx_min - _cx_ini:,.0f}", delta_color="inverse")
                _cx3.metric("Caixa Final", f"R$ {_cx_fin:,.0f}",
                            delta=f"R$ {_cx_fin - _cx_ini:,.0f}", delta_color="inverse")

                fig_plan = build_cashflow_chart(tl_plan)
                st.plotly_chart(fig_plan, use_container_width=True)

                # Show event-day summary table
                event_tl = tl_plan[tl_plan["Tem Evento"]].copy()
                if not event_tl.empty:
                    with st.expander("Ver detalhes dia a dia (apenas datas com movimentação)", expanded=False):
                        event_display = event_tl[["Data", "Entradas (R$)", "Saídas (R$)", "Líquido (R$)", "Saldo (R$)", "Detalhes"]].copy()
                        event_display["Data"] = event_display["Data"].dt.strftime("%d/%m/%Y")

                        def _color_saldo(val):
                            if val < 0:
                                return f"color: {TAG['chart'][4]}; font-weight: bold"
                            return f"color: {TAG['chart'][2]}"

                        st.dataframe(
                            event_display.style.format({
                                "Entradas (R$)": "R$ {:,.0f}",
                                "Saídas (R$)": "R$ {:,.0f}",
                                "Líquido (R$)": "R$ {:,.0f}",
                                "Saldo (R$)": "R$ {:,.0f}",
                            }).map(_color_saldo, subset=["Saldo (R$)"]),
                            use_container_width=True, hide_index=True,
                        )

            if sug_plan:
                st.subheader("📋 Sugestão de Datas de Solicitação")
                df_sug_p = pd.DataFrame(sug_plan)
                disp_cols = ["Fundo", "Código", "Operação", "Valor (R$)",
                             "Data Atual", "Data Sugerida", "D+", "Cobre Saída Em", "Motivo"]
                avail_cols = [c for c in disp_cols if c in df_sug_p.columns]
                st.dataframe(
                    df_sug_p[avail_cols].style.format({"Valor (R$)": "R$ {:,.0f}"}),
                    use_container_width=True, hide_index=True,
                )

            # Export
            st.divider()
            excel_data = export_to_excel(df_evo_fin, df_evo_pct, df_evo_mov, carteira,
                                          adherence_df=adherence_df, plan_df=plan_df)
            st.download_button(
                label="📥 Exportar Tudo para Excel",
                data=excel_data,
                file_name=f"plano_modelo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )
        else:
            st.success("🎯 Carteira já está aderente ao modelo! Nenhuma movimentação necessária.")


# ═══════════════════════════════════════════════════════════
# PAGE: DADOS DE LIQUIDAÇÃO
# ═══════════════════════════════════════════════════════════

elif page == "📅 Dados de Liquidação":
    st.header("Base de Dados de Liquidação")
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
        fig = go.Figure(go.Histogram(
            x=liquid_df["Conversão Resgate"], nbinsx=30,
            marker_color=TAG["laranja"], marker_line_width=0,
            hovertemplate="D+%{x}<br>%{y} fundos<extra></extra>",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, height=350)
        fig.update_layout(xaxis_title="D+ Conversão Resgate", yaxis_title="Qtd Fundos")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = go.Figure(go.Histogram(
            x=liquid_df["Liquid. Resgate"], nbinsx=30,
            marker_color=TAG["chart"][1], marker_line_width=0,
            hovertemplate="D+%{x}<br>%{y} fundos<extra></extra>",
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=350)
        fig2.update_layout(xaxis_title="D+ Liquidação Resgate", yaxis_title="Qtd Fundos")
        st.plotly_chart(fig2, use_container_width=True)
