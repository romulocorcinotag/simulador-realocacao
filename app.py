import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
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
    font=dict(family="Tahoma, sans-serif", color=TAG["offwhite"], size=12),
    margin=dict(t=40, b=40, l=40, r=20),
    xaxis=dict(gridcolor="rgba(230,228,219,0.08)", zerolinecolor="rgba(230,228,219,0.08)"),
    yaxis=dict(gridcolor="rgba(230,228,219,0.08)", zerolinecolor="rgba(230,228,219,0.08)"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    colorway=TAG["chart"],
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
    """
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    # Compute initial effective cash (CAIXA + cash fund positions)
    cash_fund_total = 0.0
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        if code in cash_fund_codes:
            cash_fund_total += float(row.get("FINANCEIRO", 0))
    initial_effective_cash = caixa_initial + cash_fund_total

    if not all_movements:
        return pd.DataFrame(), initial_effective_cash

    # Filter movements with valid liquidation dates
    valid_movs = [m for m in all_movements if pd.notna(m.get("liquidation_date"))]
    if not valid_movs:
        return pd.DataFrame(), initial_effective_cash

    today = pd.Timestamp(datetime.today().date())
    last_date = max(pd.Timestamp(m["liquidation_date"]) for m in valid_movs)
    if last_date < today:
        last_date = today + timedelta(days=5)

    # Build daily event map: {date: [(description, amount_on_cash)]}
    events = {}
    for m in valid_movs:
        liq_date = pd.Timestamp(m["liquidation_date"])
        if liq_date < today:
            continue  # Past movements are already in initial balances
        fund_code = str(m.get("fund_code", ""))
        op = m["operation"]
        value = m["value"]
        fund_name = m.get("fund_name", "")[:40]
        is_cash_fund = fund_code in cash_fund_codes

        # Determine cash impact
        cash_impact = 0.0
        if op == "Resgate Passivo":
            cash_impact = -value  # Investors withdrawing
            desc = f"⬇️ Resgate Passivo: -R$ {value:,.0f}"
        elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
            if is_cash_fund:
                cash_impact = 0.0  # Cash-to-cash: net zero
                desc = f"↔️ Resgate caixa ({fund_name}): R$ {value:,.0f} (neutro)"
            else:
                cash_impact = +value  # Non-cash fund → caixa
                desc = f"⬆️ Resgate {fund_name}: +R$ {value:,.0f}"
        elif "Aplicação" in op:
            if is_cash_fund:
                cash_impact = 0.0  # Caixa-to-cash fund: net zero
                desc = f"↔️ Aplicação caixa ({fund_name}): R$ {value:,.0f} (neutro)"
            else:
                cash_impact = -value  # Caixa → non-cash fund
                desc = f"⬇️ Aplicação {fund_name}: -R$ {value:,.0f}"
        elif op == "Débito/Passivo":
            cash_impact = -value
            desc = f"⬇️ Débito: -R$ {value:,.0f}"
        elif op == "Crédito (Provisão)":
            cash_impact = +value
            desc = f"⬆️ Crédito: +R$ {value:,.0f}"
        else:
            desc = f"❓ {op}: R$ {value:,.0f}"

        if liq_date not in events:
            events[liq_date] = []
        events[liq_date].append((desc, cash_impact))

    # Generate timeline (business days only)
    rows = []
    running_balance = initial_effective_cash
    current = today
    while current <= last_date + timedelta(days=3):
        if current.weekday() < 5:  # Business days only
            day_events = events.get(current, [])
            inflows = sum(amt for _, amt in day_events if amt > 0)
            outflows = sum(abs(amt) for _, amt in day_events if amt < 0)
            net = inflows - outflows
            running_balance += net
            details = " | ".join(d for d, _ in day_events) if day_events else ""
            rows.append({
                "Data": current,
                "Entradas (R$)": inflows,
                "Saídas (R$)": outflows,
                "Líquido (R$)": net,
                "Saldo (R$)": running_balance,
                "Detalhes": details,
                "Negativo": running_balance < 0,
                "Tem Evento": len(day_events) > 0,
            })
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
    Generate a smart rebalancing plan that matches redemption settlement dates
    with passive (investor withdrawal) dates, while also rebalancing toward the model.

    Returns: (plan_df, plan_movements, warnings)
      - plan_df: DataFrame with columns including 'Data Solicitação', 'Data Liquidação', 'Motivo'
      - plan_movements: list of movement dicts compatible with build_cash_flow_timeline
      - warnings: list of {level: 'error'|'warning', message: str}
    """
    if today is None:
        today = pd.Timestamp(datetime.today().date())
    else:
        today = pd.Timestamp(today)

    warnings = []
    plan_rows = []
    plan_movements = []

    # ── FASE 0: Catálogo de Fundos ──
    catalog = {}  # code → fund info dict
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

        is_overweight = gap_rs < -100   # needs resgate to match model
        is_underweight = gap_rs > 100   # needs aplicação
        is_cash = code in cash_fund_codes
        max_resgate = abs(gap_rs) if is_overweight else 0  # max we WANT to redeem for model
        available_fin = max(0, financeiro)  # total available in fund

        catalog[code] = {
            "code": code, "name": name, "gap_rs": gap_rs,
            "financeiro": financeiro, "available_fin": available_fin,
            "d_conv": d_conv, "d_liq": d_liq, "contagem": contagem,
            "d_conv_aplic": d_conv_aplic,
            "d_total": d_conv + d_liq,
            "is_overweight": is_overweight, "is_underweight": is_underweight,
            "is_cash": is_cash, "max_model_resgate": max_resgate,
            "pct_atual": row["% Atual (Pós-Mov.)"],
            "pct_alvo": row["% Alvo (Modelo)"],
            "already_redeemed": 0.0,  # track cumulative resgates in this plan
        }

    # ── FASE 1: Extrair Passivos Pendentes ──
    passivos = {}  # {date: total_value}
    if all_movements:
        for m in all_movements:
            if m["operation"] != "Resgate Passivo":
                continue
            liq_date = pd.Timestamp(m["liquidation_date"]) if pd.notna(m.get("liquidation_date")) else None
            if liq_date is None or liq_date < today:
                continue
            passivos.setdefault(liq_date, 0.0)
            passivos[liq_date] += m["value"]

    passivos_sorted = sorted(passivos.items(), key=lambda x: x[0])

    # ── FASE 2: Cobrir Cada Passivo com Resgates ──
    # Build effective cash available today (caixa + cash fund positions)
    effective_cash = caixa_initial
    if ativos_df is not None and not ativos_df.empty:
        cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")
        if cod_col:
            for _, row in ativos_df.iterrows():
                code = str(row[cod_col])
                if code in cash_fund_codes:
                    effective_cash += float(row.get("FINANCEIRO", 0))

    # Pre-compute inflows from existing provisions (non-passive resgates already in progress)
    # These will add cash on their liquidation dates
    provision_inflows = {}  # {date: amount}
    if all_movements:
        for m in all_movements:
            op = m["operation"]
            if op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
                fund_code = str(m.get("fund_code", ""))
                if fund_code not in cash_fund_codes:  # non-cash fund resgates add to cash
                    liq_date = pd.Timestamp(m["liquidation_date"]) if pd.notna(m.get("liquidation_date")) else None
                    if liq_date and liq_date >= today:
                        provision_inflows.setdefault(liq_date, 0.0)
                        provision_inflows[liq_date] += m["value"]

    # Track plan-generated inflows: {date: amount}
    plan_inflows = {}

    for passivo_date, passivo_value in passivos_sorted:
        # Compute cash available at passivo_date considering:
        # 1) effective_cash today
        # 2) provision inflows settling <= passivo_date
        # 3) plan inflows from earlier phases settling <= passivo_date
        # 4) earlier passivos that drain cash
        cash_at_date = effective_cash

        # Add provision inflows settling by this date
        for d, v in provision_inflows.items():
            if d <= passivo_date:
                cash_at_date += v

        # Add plan inflows from earlier passivo coverage settling by this date
        for d, v in plan_inflows.items():
            if d <= passivo_date:
                cash_at_date += v

        # Subtract earlier passivos
        for pd_date, pd_val in passivos_sorted:
            if pd_date < passivo_date:
                cash_at_date -= pd_val
            else:
                break

        deficit = passivo_value - cash_at_date
        if deficit <= 0:
            continue  # Cash already covers this passivo

        # Need to find funds to redeem that settle by passivo_date
        candidates = []
        for code, fund in catalog.items():
            if fund["is_cash"]:
                continue  # Cash funds don't help (already counted)
            remaining = fund["available_fin"] - fund["already_redeemed"]
            if remaining < 100:
                continue

            # When must we request to settle by passivo_date?
            req_date = compute_latest_request_date(
                passivo_date, fund["d_conv"], fund["d_liq"], fund["contagem"]
            )
            if req_date < today:
                continue  # D+ too long — impossible to settle in time

            settle = compute_settle_date(req_date, fund["d_conv"], fund["d_liq"], fund["contagem"])

            candidates.append({
                "code": code,
                "fund": fund,
                "request_date": req_date,
                "settle_date": settle,
                "remaining": remaining,
                "is_overweight": fund["is_overweight"],
                "model_resgate": fund["max_model_resgate"] - fund["already_redeemed"],
            })

        # Sort: overweight funds first (kills two birds), then by D+ ascending (faster settlement)
        candidates.sort(key=lambda c: (0 if c["is_overweight"] else 1, c["fund"]["d_total"]))

        # Greedy allocation
        still_needed = deficit
        for cand in candidates:
            if still_needed <= 0:
                break

            # How much to redeem from this fund
            if cand["is_overweight"] and cand["model_resgate"] > 0:
                # Prefer up to model gap first
                amount = min(still_needed, cand["model_resgate"], cand["remaining"])
            else:
                amount = min(still_needed, cand["remaining"])

            if amount < 100:
                continue

            fund = cand["fund"]
            req_date = cand["request_date"]
            settle_date = cand["settle_date"]
            d_plus_str = f"D+{fund['d_conv']}+{fund['d_liq']} ({fund['contagem']})"

            plan_rows.append({
                "Prioridade": 0,
                "Ativo": fund["name"], "Código": fund["code"],
                "Operação": "Resgate",
                "Valor (R$)": round(amount, 2),
                "D+": d_plus_str,
                "Data Solicitação": req_date.strftime("%d/%m/%Y"),
                "Data Liquidação": settle_date.strftime("%d/%m/%Y"),
                "Motivo": f"Cobertura passivo {passivo_date.strftime('%d/%m')}",
                "De % Atual": fund["pct_atual"],
                "Para % Alvo": fund["pct_alvo"],
            })
            plan_movements.append({
                "fund_name": fund["name"], "fund_code": fund["code"],
                "operation": "Resgate", "value": round(amount, 2),
                "request_date": req_date,
                "liquidation_date": settle_date,
                "description": f"Plano: Resgate {fund['name'][:30]} (cob. passivo {passivo_date.strftime('%d/%m')})",
                "source": "plano_cobertura_passivo",
            })

            fund["already_redeemed"] += amount
            plan_inflows.setdefault(settle_date, 0.0)
            plan_inflows[settle_date] += amount
            still_needed -= amount

        if still_needed > 100:
            # Try any fund even below model (emergency)
            for cand in candidates:
                if still_needed <= 0:
                    break
                remaining_after = cand["remaining"] - (cand["fund"]["already_redeemed"] - catalog[cand["code"]]["already_redeemed"] + cand["fund"]["already_redeemed"])
                # re-check actual remaining
                actual_remaining = cand["fund"]["available_fin"] - cand["fund"]["already_redeemed"]
                extra = min(still_needed, actual_remaining)
                if extra < 100:
                    continue

                fund = cand["fund"]
                req_date = cand["request_date"]
                settle_date = cand["settle_date"]
                d_plus_str = f"D+{fund['d_conv']}+{fund['d_liq']} ({fund['contagem']})"

                plan_rows.append({
                    "Prioridade": 0,
                    "Ativo": fund["name"], "Código": fund["code"],
                    "Operação": "Resgate",
                    "Valor (R$)": round(extra, 2),
                    "D+": d_plus_str,
                    "Data Solicitação": req_date.strftime("%d/%m/%Y"),
                    "Data Liquidação": settle_date.strftime("%d/%m/%Y"),
                    "Motivo": f"Cobertura passivo {passivo_date.strftime('%d/%m')} (emergencial)",
                    "De % Atual": fund["pct_atual"],
                    "Para % Alvo": fund["pct_alvo"],
                })
                plan_movements.append({
                    "fund_name": fund["name"], "fund_code": fund["code"],
                    "operation": "Resgate", "value": round(extra, 2),
                    "request_date": req_date,
                    "liquidation_date": settle_date,
                    "description": f"Plano: Resgate {fund['name'][:30]} (emerg. passivo {passivo_date.strftime('%d/%m')})",
                    "source": "plano_cobertura_passivo",
                })

                fund["already_redeemed"] += extra
                plan_inflows.setdefault(settle_date, 0.0)
                plan_inflows[settle_date] += extra
                still_needed -= extra

        if still_needed > 100:
            warnings.append({
                "level": "error",
                "message": (
                    f"Impossivel cobrir passivo de R$ {passivo_value:,.0f} em "
                    f"{passivo_date.strftime('%d/%m/%Y')}: deficit de R$ {still_needed:,.0f}. "
                    f"Nenhum fundo consegue liquidar a tempo."
                ),
            })

    # ── FASE 3: Rebalancear Excedentes (overweight restante) ──
    for code, fund in catalog.items():
        if fund["is_cash"]:
            continue
        if not fund["is_overweight"]:
            continue
        remaining_model_gap = fund["max_model_resgate"] - fund["already_redeemed"]
        if remaining_model_gap < 100:
            continue

        req_date = today
        settle_date = compute_settle_date(req_date, fund["d_conv"], fund["d_liq"], fund["contagem"])
        d_plus_str = f"D+{fund['d_conv']}+{fund['d_liq']} ({fund['contagem']})"

        plan_rows.append({
            "Prioridade": 0,
            "Ativo": fund["name"], "Código": fund["code"],
            "Operação": "Resgate",
            "Valor (R$)": round(remaining_model_gap, 2),
            "D+": d_plus_str,
            "Data Solicitação": req_date.strftime("%d/%m/%Y"),
            "Data Liquidação": settle_date.strftime("%d/%m/%Y"),
            "Motivo": "Rebalanceamento (acima do modelo)",
            "De % Atual": fund["pct_atual"],
            "Para % Alvo": fund["pct_alvo"],
        })
        plan_movements.append({
            "fund_name": fund["name"], "fund_code": fund["code"],
            "operation": "Resgate", "value": round(remaining_model_gap, 2),
            "request_date": req_date,
            "liquidation_date": settle_date,
            "description": f"Plano: Resgate {fund['name'][:30]} (rebalanceamento)",
            "source": "plano_rebalanceamento",
        })

        fund["already_redeemed"] += remaining_model_gap
        plan_inflows.setdefault(settle_date, 0.0)
        plan_inflows[settle_date] += remaining_model_gap

    # ── FASE 4: Aplicações nos Fundos Abaixo do Modelo ──
    # Compute when cash will be available from ALL resgates (provisions + plan)
    all_inflow_dates = sorted(set(
        list(provision_inflows.keys()) + list(plan_inflows.keys())
    ))

    # Compute total cash available for applications:
    # = effective_cash + all resgate inflows - all passivos
    total_passivos = sum(passivos.values())
    total_provision_inflows = sum(provision_inflows.values())
    total_plan_inflows = sum(plan_inflows.values())
    cash_for_applications = effective_cash + total_provision_inflows + total_plan_inflows - total_passivos

    # Determine earliest application date = day after last resgate settles
    if all_inflow_dates:
        last_inflow_date = max(all_inflow_dates)
        # Applications go one business day after last inflow
        aplic_date = add_business_days(last_inflow_date, 1, "Úteis")
    else:
        aplic_date = add_business_days(today, 1, "Úteis")

    # Sort underweight funds by gap (largest gap first)
    underweight_funds = [
        (code, fund) for code, fund in catalog.items()
        if fund["is_underweight"] and not fund["is_cash"]
    ]
    underweight_funds.sort(key=lambda x: x[1]["gap_rs"], reverse=True)

    available_for_aplic = max(0, cash_for_applications)

    for code, fund in underweight_funds:
        if available_for_aplic < 100:
            break

        gap = fund["gap_rs"]  # positive = needs application
        amount = min(gap, available_for_aplic)
        if amount < 100:
            continue

        settle_date = add_business_days(aplic_date, fund["d_conv_aplic"], "Úteis")
        d_plus_str = f"D+{fund['d_conv_aplic']}"

        plan_rows.append({
            "Prioridade": 0,
            "Ativo": fund["name"], "Código": fund["code"],
            "Operação": "Aplicação",
            "Valor (R$)": round(amount, 2),
            "D+": d_plus_str,
            "Data Solicitação": aplic_date.strftime("%d/%m/%Y"),
            "Data Liquidação": settle_date.strftime("%d/%m/%Y"),
            "Motivo": "Rebalanceamento (abaixo do modelo)",
            "De % Atual": fund["pct_atual"],
            "Para % Alvo": fund["pct_alvo"],
        })
        plan_movements.append({
            "fund_name": fund["name"], "fund_code": fund["code"],
            "operation": "Aplicação", "value": round(amount, 2),
            "request_date": aplic_date,
            "liquidation_date": settle_date,
            "description": f"Plano: Aplicação {fund['name'][:30]} (rebalanceamento)",
            "source": "plano_rebalanceamento",
        })

        available_for_aplic -= amount

    if underweight_funds and available_for_aplic < 0:
        warnings.append({
            "level": "warning",
            "message": (
                f"Caixa insuficiente para todas as aplicações. "
                f"Faltam R$ {abs(available_for_aplic):,.0f}."
            ),
        })

    # ── FASE 5: Validação Final de Caixa ──
    # Quick check: simulate day-by-day cash with provisions + plan
    if plan_movements and ativos_df is not None and not ativos_df.empty:
        combined = (all_movements or []) + plan_movements
        df_check, _ = build_cash_flow_timeline(
            caixa_initial, ativos_df, combined, cash_fund_codes
        )
        if not df_check.empty:
            neg_days = df_check[df_check["Negativo"]]
            if not neg_days.empty:
                first_neg = neg_days.iloc[0]
                warnings.append({
                    "level": "warning",
                    "message": (
                        f"Caixa fica negativo em {first_neg['Data'].strftime('%d/%m/%Y')} "
                        f"(R$ {first_neg['Saldo (R$)']:,.0f}). Verifique o plano."
                    ),
                })

    # ── Build final DataFrame ──
    plan_df = pd.DataFrame(plan_rows)
    if not plan_df.empty:
        # Sort: cobertura passivo first, then resgates, then aplicações
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
    """Display R$ and % PL evolution tables."""
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

    df_pct_display = df_pct.drop(columns=["Código"]).copy()

    if model_map:
        df_pct_display["🎯 Modelo"] = df_pct_display["Ativo"].map(model_map).fillna(0)
        fmt_pct["🎯 Modelo"] = "{:.2f}%"

        pct_value_cols = ["Atual (%)"] + evo_date_cols

        def color_vs_model(row):
            styles = []
            ativo = row["Ativo"]
            target = model_map.get(ativo, None)
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
            "📋 Posição Atual",
            "📊 Projeção da Carteira",
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

                st.success(f"✅ Carteira carregada: **{uploaded.name}**")

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
                st.info(f"**{matched_count}/{len(df_match)}** ativos encontrados na base de liquidação.")
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
            model_df = st.session_state.model_df
            col1, col2 = st.columns([2, 1])
            with col1:
                st.dataframe(
                    model_df.style.format({"% Alvo": "{:.2f}%"}),
                    use_container_width=True, hide_index=True,
                )
            with col2:
                fig = px.pie(model_df, values="% Alvo", names="Ativo", hole=0.45,
                             color_discrete_sequence=TAG["chart"])
                fig.update_traces(textposition="inside", textinfo="percent+label",
                                  textfont_size=10, marker=dict(line=dict(color=TAG["bg_dark"], width=2)))
                fig.update_layout(**PLOTLY_LAYOUT, height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
# PAGE: POSIÇÃO ATUAL
# ═══════════════════════════════════════════════════════════

elif page == "📋 Posição Atual":
    st.header("Posição Atual da Carteira")

    ctx = get_portfolio_context()
    if not ctx:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Dados** primeiro.")
    else:
        ativos = ctx["ativos"]
        carteira = ctx["carteira"]

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

        # Table
        st.subheader("Ativos")
        estrategia_col = find_col(ativos, "ESTRATÉGIA", "ESTRATEGIA")
        preco_col = find_col(ativos, "PREÇO", "PRECO")
        display_col_candidates = [
            "ATIVO", "CLASSE", estrategia_col or "ESTRATÉGIA",
            "QUANTIDADE", preco_col or "PREÇO", "FINANCEIRO", "% PL",
        ]
        available_cols = [c for c in display_col_candidates if c and c in ativos.columns]
        df_display = ativos[available_cols].copy()
        fmt = {"FINANCEIRO": "R$ {:,.2f}", "QUANTIDADE": "{:,.2f}", "% PL": "{:.2f}%"}
        if preco_col and preco_col in df_display.columns:
            fmt[preco_col] = "R$ {:,.6f}"
        st.dataframe(df_display.style.format(fmt), use_container_width=True, hide_index=True, height=400)

        # Charts
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Alocação por Ativo")
            fig = px.pie(ativos, values="FINANCEIRO", names="ATIVO", hole=0.45,
                         color_discrete_sequence=TAG["chart"])
            fig.update_traces(textposition="inside", textinfo="percent+label",
                              textfont_size=11, marker=dict(line=dict(color=TAG["bg_dark"], width=2)))
            fig.update_layout(**PLOTLY_LAYOUT, height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            strat_col = find_col(ativos, "ESTRATÉGIA", "ESTRATEGIA")
            if strat_col and strat_col in ativos.columns:
                st.subheader("Alocação por Estratégia")
                strat = ativos.groupby(strat_col)["FINANCEIRO"].sum().reset_index()
                fig2 = px.bar(strat, x=strat_col, y="FINANCEIRO", text_auto=",.0f",
                              color_discrete_sequence=[TAG["laranja"]])
                fig2.update_layout(**PLOTLY_LAYOUT, xaxis_tickangle=-45, height=400)
                fig2.update_traces(marker_line_width=0, textfont_color=TAG["offwhite"])
                st.plotly_chart(fig2, use_container_width=True)

        # Provisões
        if ctx["provision_movs"]:
            st.divider()
            display_provisions_summary(ctx["provision_movs"], expanded=False)


# ═══════════════════════════════════════════════════════════
# PAGE: PROJEÇÃO DA CARTEIRA
# ═══════════════════════════════════════════════════════════

elif page == "📊 Projeção da Carteira":
    st.header("Projeção da Carteira")

    ctx = get_portfolio_context()
    if not ctx:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Dados** primeiro.")
    else:
        ativos = ctx["ativos"]
        carteira = ctx["carteira"]
        caixa_initial = ctx["caixa_initial"]
        all_movements = ctx["all_movements"]

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
                "📭 Nenhum movimento pendente. A carteira não possui provisões e não há movimentos manuais.\n\n"
                "Use o botão **➕ Adicionar Movimento Manual** acima para simular realocações."
            )
        else:
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
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name="Hoje", x=chart_df["Ativo"], y=chart_df["Atual (%)"],
                                         marker_color=TAG["chart"][1], marker_line_width=0))
                    fig.add_trace(go.Bar(name=last_date_col, x=chart_df["Ativo"], y=chart_df[last_date_col],
                                         marker_color=TAG["laranja"], marker_line_width=0))
                    fig.update_layout(**PLOTLY_LAYOUT, barmode="group", height=400,
                                      xaxis_tickangle=-30, yaxis_title="% PL")
                    st.plotly_chart(fig, use_container_width=True)

                # Timeline
                st.subheader("Timeline de Liquidação")
                timeline_data = df_mov[df_mov["Data Liquidação"] != ""].copy()
                if not timeline_data.empty:
                    timeline_data["Data Solicitação"] = pd.to_datetime(timeline_data["Data Solicitação"], dayfirst=True)
                    timeline_data["Data Liquidação"] = pd.to_datetime(timeline_data["Data Liquidação"], dayfirst=True)
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
                            "Resgate (Cotizando)": TAG["chart"][4],  # ED5A6E
                            "Resgate Passivo": TAG["laranja"],
                            "Débito/Passivo": TAG["chart"][6],  # A485F2
                            "Crédito (Provisão)": TAG["chart"][5],  # 58C6F5
                            "Resgate": TAG["vermelho_light"],
                            "Aplicação": TAG["chart"][2],  # 6BDE97
                        },
                    )
                    fig_tl.update_layout(**PLOTLY_LAYOUT, height=max(300, len(timeline_data) * 40), yaxis_title="")
                    st.plotly_chart(fig_tl, use_container_width=True)

                # ── CASH FLOW TIMELINE ──
                st.divider()
                st.subheader("📈 Fluxo de Caixa Diário")
                st.caption(
                    "Projeção dia-a-dia do caixa efetivo (CAIXA + fundos D+0/D+1). "
                    "O saldo nunca pode ficar negativo."
                )

                cash_fund_codes = ctx.get("cash_fund_codes", set())
                cash_details = ctx.get("cash_details", [])

                # A. Cash fund identification
                with st.expander("💰 Fundos Considerados como Caixa (D+0/D+1)", expanded=False):
                    if cash_details:
                        df_cash = pd.DataFrame(cash_details)
                        total_cash_funds = df_cash["Financeiro (R$)"].sum()
                        st.metric("Caixa Efetivo Inicial",
                                  f"R$ {caixa_initial + total_cash_funds:,.0f}",
                                  f"CAIXA R$ {caixa_initial:,.0f} + Fundos-Caixa R$ {total_cash_funds:,.0f}")
                        st.dataframe(
                            df_cash.style.format({"Financeiro (R$)": "R$ {:,.0f}"}),
                            use_container_width=True, hide_index=True,
                        )
                    else:
                        st.info("Nenhum fundo D+0/D+1 encontrado na carteira.")
                        st.metric("Caixa Efetivo Inicial", f"R$ {caixa_initial:,.0f}")

                # B. Run cash flow analysis
                suggestions, negative_dates, df_timeline, initial_cash = suggest_request_dates(
                    all_movements, liquid_df, cash_fund_codes, caixa_initial, ativos
                )

                # C. Alerts
                if negative_dates:
                    st.error(
                        f"🚨 **ATENÇÃO**: Caixa ficará negativo em "
                        f"**{len(negative_dates)} data(s)**! O fundo não pode operar assim."
                    )
                    for nd in negative_dates[:5]:  # Show first 5
                        st.warning(
                            f"📅 **{nd['date'].strftime('%d/%m/%Y')}** — "
                            f"Saldo: **R$ {nd['balance']:,.0f}** — "
                            f"Déficit: **R$ {nd['shortfall']:,.0f}**"
                        )
                    if len(negative_dates) > 5:
                        st.caption(f"... e mais {len(negative_dates) - 5} datas com saldo negativo.")
                else:
                    if not df_timeline.empty:
                        st.success("✅ **Fluxo de caixa positivo** em todas as datas. Nenhum risco de caixa negativo.")

                # D. Chart
                if not df_timeline.empty:
                    fig_cf = go.Figure()

                    # Running balance area
                    pos_mask = df_timeline["Saldo (R$)"] >= 0
                    neg_mask = df_timeline["Saldo (R$)"] < 0

                    fig_cf.add_trace(go.Scatter(
                        x=df_timeline["Data"], y=df_timeline["Saldo (R$)"],
                        fill="tozeroy", mode="lines+markers",
                        name="Saldo Caixa",
                        line=dict(color=TAG["chart"][2], width=2),
                        fillcolor="rgba(107,222,151,0.12)",
                        marker=dict(size=4),
                    ))

                    # Highlight negative areas
                    if neg_mask.any():
                        neg_data = df_timeline[neg_mask]
                        fig_cf.add_trace(go.Scatter(
                            x=neg_data["Data"], y=neg_data["Saldo (R$)"],
                            fill="tozeroy", mode="markers",
                            name="Déficit",
                            line=dict(color=TAG["chart"][4]),
                            fillcolor="rgba(237,90,110,0.25)",
                            marker=dict(size=8, color=TAG["chart"][4], symbol="x"),
                        ))

                    # Inflow/outflow bars (only on event days)
                    event_days = df_timeline[df_timeline["Tem Evento"]]
                    if not event_days.empty:
                        fig_cf.add_trace(go.Bar(
                            x=event_days["Data"], y=event_days["Entradas (R$)"],
                            name="Entradas", marker_color=TAG["chart"][2], opacity=0.5,
                        ))
                        fig_cf.add_trace(go.Bar(
                            x=event_days["Data"], y=-event_days["Saídas (R$)"],
                            name="Saídas", marker_color=TAG["chart"][4], opacity=0.5,
                        ))

                    # Zero line
                    fig_cf.add_hline(
                        y=0, line_dash="dash", line_color=TAG["chart"][4],
                        line_width=2,
                        annotation_text="Zero — Limite Mínimo",
                        annotation_position="top right",
                        annotation_font_color=TAG["chart"][4],
                    )

                    fig_cf.update_layout(
                        **PLOTLY_LAYOUT, height=450, barmode="overlay",
                        yaxis_title="R$", xaxis_title="Data",
                    )
                    fig_cf.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
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

                # Export
                st.divider()
                excel_data = export_to_excel(df_fin, df_pct, df_mov, carteira)
                st.download_button(
                    label="📥 Exportar para Excel",
                    data=excel_data,
                    file_name=f"projecao_carteira_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                )


# ═══════════════════════════════════════════════════════════
# PAGE: CARTEIRA MODELO
# ═══════════════════════════════════════════════════════════

elif page == "🎯 Carteira Modelo":
    st.header("Aderência à Carteira Modelo")

    ctx = get_portfolio_context()
    if not ctx:
        st.warning("Nenhuma carteira carregada. Vá em **📂 Importar Dados** primeiro.")
    elif not st.session_state.model_loaded:
        st.warning("Nenhuma carteira modelo carregada. Vá em **📂 Importar Dados** → aba **🎯 Carteira Modelo**.")
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

        # Gap chart
        chart_data = adherence_df[adherence_df["Código"] != "CAIXA"].copy()
        fig_gap = go.Figure()
        fig_gap.add_trace(go.Bar(name="% Atual", x=chart_data["Ativo"],
                                  y=chart_data["% Atual (Pós-Mov.)"],
                                  marker_color=TAG["chart"][1], marker_line_width=0))
        fig_gap.add_trace(go.Bar(name="% Modelo", x=chart_data["Ativo"],
                                  y=chart_data["% Alvo (Modelo)"],
                                  marker_color=TAG["laranja"], marker_line_width=0))
        fig_gap.update_layout(**PLOTLY_LAYOUT, barmode="group", height=400,
                              xaxis_tickangle=-30, yaxis_title="% PL")
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
            display_cols = ["Prioridade", "Ativo", "Operação", "Valor (R$)", "D+",
                            "Data Solicitação", "Data Liquidação", "Motivo"]
            fmt = {"Valor (R$)": "R$ {:,.0f}"}

            # ── Seção 1: Cobertura de Passivos ──
            cobertura = plan_df[plan_df["Motivo"].str.contains("passivo", case=False, na=False)]
            if not cobertura.empty:
                st.markdown("### 🎯 Cobertura de Passivos")
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
                st.markdown("### 📤 Resgates (Rebalanceamento)")
                st.caption("Resgates adicionais para ajustar a carteira ao modelo.")
                st.dataframe(
                    resgates_rebal[display_cols].style.format(fmt),
                    use_container_width=True, hide_index=True,
                )
                st.metric("Total Resgates (Rebalanceamento)", f"R$ {resgates_rebal['Valor (R$)'].sum():,.0f}")

            # ── Seção 3: Aplicações ──
            aplicacoes = plan_df[plan_df["Operação"] == "Aplicação"]
            if not aplicacoes.empty:
                st.markdown("### 📥 Aplicações")
                st.caption("Aplicações programadas para quando o caixa dos resgates estiver disponível.")
                st.dataframe(
                    aplicacoes[display_cols].style.format(fmt),
                    use_container_width=True, hide_index=True,
                )
                st.metric("Total Aplicações", f"R$ {aplicacoes['Valor (R$)'].sum():,.0f}")

            # ── Nenhum movimento ──
            if cobertura.empty and resgates_rebal.empty and aplicacoes.empty:
                st.info("Nenhum movimento necessário.")

            # ── Timeline Visual ──
            st.markdown("### 📅 Cronograma de Liquidações")
            st.caption("Cada linha mostra quando solicitar e quando o dinheiro liquida. Linhas vermelhas tracejadas = prazo dos passivos.")

            try:
                # Collect passivo dates
                passivo_dates = {}
                for m in all_movements:
                    if m["operation"] == "Resgate Passivo" and pd.notna(m.get("liquidation_date")):
                        ld = pd.Timestamp(m["liquidation_date"])
                        if ld >= pd.Timestamp(plan_date):
                            passivo_dates[ld] = passivo_dates.get(ld, 0) + m["value"]

                fig_tl = go.Figure()

                # One horizontal arrow per movement: solicitação → liquidação
                y_labels = []
                for idx, (_, row) in enumerate(plan_df.iterrows()):
                    req = pd.to_datetime(row["Data Solicitação"], dayfirst=True)
                    liq = pd.to_datetime(row["Data Liquidação"], dayfirst=True)
                    is_resgate = row["Operação"] == "Resgate"
                    color = TAG["vermelho"] if is_resgate else TAG["chart"][2]
                    y_val = len(plan_df) - idx  # top to bottom
                    short_name = row["Ativo"][:22]
                    y_labels.append((y_val, short_name))

                    # Connecting line (solicitação → liquidação)
                    fig_tl.add_trace(go.Scatter(
                        x=[req, liq], y=[y_val, y_val],
                        mode="lines",
                        line=dict(color=color, width=3),
                        showlegend=False, hoverinfo="skip",
                    ))

                    # Solicitação marker (circle)
                    fig_tl.add_trace(go.Scatter(
                        x=[req], y=[y_val],
                        mode="markers+text",
                        marker=dict(size=10, color=TAG["bg_dark"], line=dict(color=color, width=2)),
                        text=[f"Solic. {req.strftime('%d/%m')}"],
                        textposition="bottom center",
                        textfont=dict(size=9, color=TAG["offwhite"]),
                        showlegend=False,
                        hovertemplate=(
                            f"<b>Solicitação</b><br>{short_name}<br>"
                            f"{row['Operação']}: R$ {row['Valor (R$)']:,.0f}<br>"
                            f"Data: {row['Data Solicitação']}<extra></extra>"
                        ),
                    ))

                    # Liquidação marker (filled)
                    symbol = "triangle-right" if is_resgate else "diamond"
                    fig_tl.add_trace(go.Scatter(
                        x=[liq], y=[y_val],
                        mode="markers+text",
                        marker=dict(size=12, color=color, symbol=symbol),
                        text=[f"R$ {row['Valor (R$)']:,.0f}"],
                        textposition="top center",
                        textfont=dict(size=10, color=color, family="Inter"),
                        showlegend=False,
                        hovertemplate=(
                            f"<b>Liquidação</b><br>{short_name}<br>"
                            f"{row['Operação']}: R$ {row['Valor (R$)']:,.0f}<br>"
                            f"Data: {row['Data Liquidação']}<br>"
                            f"D+: {row['D+']}<br>"
                            f"Motivo: {row['Motivo']}<extra></extra>"
                        ),
                    ))

                # Vertical dashed lines for passivo deadlines
                for pd_date, pd_val in passivo_dates.items():
                    fig_tl.add_vline(
                        x=pd_date, line_dash="dash", line_color=TAG["vermelho"],
                        line_width=2, opacity=0.8,
                    )
                    fig_tl.add_annotation(
                        x=pd_date, y=len(plan_df) + 0.7,
                        text=f"Passivo {pd_date.strftime('%d/%m')}<br>R$ {pd_val:,.0f}",
                        showarrow=False, font=dict(size=10, color=TAG["vermelho"]),
                        bgcolor=TAG["bg_dark"], bordercolor=TAG["vermelho"], borderwidth=1,
                        borderpad=3,
                    )

                # Y-axis with fund names
                fig_tl.update_layout(**PLOTLY_LAYOUT, height=max(350, len(plan_df) * 55 + 120))
                fig_tl.update_layout(
                    xaxis=dict(title="Data", type="date", gridcolor=f"{TAG['offwhite']}15"),
                    yaxis=dict(
                        tickvals=[yl[0] for yl in y_labels],
                        ticktext=[yl[1] for yl in y_labels],
                        title="",
                    ),
                    margin=dict(l=160),
                )

                # Legend manual via annotations
                c_res = TAG["vermelho"]
                c_apl = TAG["chart"][2]
                legend_txt = (
                    f"<span style='color:{c_res}'>▶ Resgate</span>"
                    f"  &nbsp;  "
                    f"<span style='color:{c_apl}'>◆ Aplicação</span>"
                    f"  &nbsp;  "
                    f"<span style='color:{c_res}'>┆ Prazo Passivo</span>"
                    f"  &nbsp;  ○ Solicitação  →  Liquidação"
                )
                fig_tl.add_annotation(
                    x=0.01, y=-0.12, xref="paper", yref="paper",
                    text=legend_txt,
                    showarrow=False, font=dict(size=11, color=TAG["offwhite"]),
                )

                st.plotly_chart(fig_tl, use_container_width=True)
            except Exception:
                pass  # Non-critical visualization

            st.divider()

            # ── Evolução: Provisões + Plano ──
            st.subheader("📅 Projeção Completa (Provisões + Plano)")
            st.caption("Como a carteira ficará em cada data de liquidação, incluindo provisões em andamento e o plano sugerido.")

            combined_movements = all_movements + plan_movements
            df_evo_fin, df_evo_pct, df_evo_mov = build_evolution_table(ativos, combined_movements, caixa_initial)

            if df_evo_fin is not None:
                evo_date_cols = [c for c in df_evo_fin.columns if c not in ["Ativo", "Código", "Atual (R$)"]]

                # Build model map for color comparison
                model_map = dict(zip(adherence_df["Ativo"].str[:45], adherence_df["% Alvo (Modelo)"]))

                display_provisions_summary(combined_movements, expanded=False)
                display_evolution_tables(df_evo_fin, df_evo_pct, evo_date_cols, model_map=model_map)

                # Final comparison chart
                if evo_date_cols:
                    last_dc = evo_date_cols[-1]
                    st.subheader(f"Comparação Final: {last_dc} vs Modelo")
                    df_evo_pct_display = df_evo_pct.drop(columns=["Código"]).copy()
                    df_evo_pct_display["🎯 Modelo"] = df_evo_pct_display["Ativo"].map(model_map).fillna(0)
                    cmp = df_evo_pct_display[~df_evo_pct_display["Ativo"].isin(["📊 TOTAL PL"])].copy()
                    fig_cmp = go.Figure()
                    fig_cmp.add_trace(go.Bar(name=f"Projeção {last_dc}", x=cmp["Ativo"], y=cmp[last_dc],
                                              marker_color=TAG["chart"][1], marker_line_width=0))
                    fig_cmp.add_trace(go.Bar(name="🎯 Modelo", x=cmp["Ativo"], y=cmp["🎯 Modelo"],
                                              marker_color=TAG["laranja"], marker_line_width=0))
                    fig_cmp.update_layout(**PLOTLY_LAYOUT, barmode="group", height=400,
                                          xaxis_tickangle=-30, yaxis_title="% PL")
                    st.plotly_chart(fig_cmp, use_container_width=True)

            # ── CASH FLOW for combined movements ──
            st.divider()
            st.subheader("📈 Fluxo de Caixa (Provisões + Plano)")
            st.caption(
                "Verifica se o caixa efetivo ficará negativo ao longo do tempo, "
                "considerando todos os movimentos do plano."
            )

            cash_fund_codes = ctx.get("cash_fund_codes", set())
            sug_plan, neg_plan, tl_plan, init_plan = suggest_request_dates(
                combined_movements, liquid_df, cash_fund_codes, caixa_initial, ativos
            )

            if neg_plan:
                st.error(
                    f"🚨 **ATENÇÃO**: Com este plano, o caixa ficará negativo em "
                    f"**{len(neg_plan)} data(s)**!"
                )
                for nd in neg_plan[:5]:
                    st.warning(
                        f"📅 **{nd['date'].strftime('%d/%m/%Y')}** — "
                        f"Saldo: **R$ {nd['balance']:,.0f}** — "
                        f"Déficit: **R$ {nd['shortfall']:,.0f}**"
                    )
            else:
                if not tl_plan.empty:
                    st.success("✅ **Plano viável!** Caixa positivo em todas as datas.")

            if not tl_plan.empty:
                fig_plan = go.Figure()
                fig_plan.add_trace(go.Scatter(
                    x=tl_plan["Data"], y=tl_plan["Saldo (R$)"],
                    fill="tozeroy", mode="lines+markers",
                    name="Saldo Caixa",
                    line=dict(color=TAG["chart"][2], width=2),
                    fillcolor="rgba(107,222,151,0.12)",
                    marker=dict(size=4),
                ))
                neg_m = tl_plan["Saldo (R$)"] < 0
                if neg_m.any():
                    fig_plan.add_trace(go.Scatter(
                        x=tl_plan.loc[neg_m, "Data"], y=tl_plan.loc[neg_m, "Saldo (R$)"],
                        fill="tozeroy", mode="markers",
                        name="Déficit",
                        line=dict(color=TAG["chart"][4]),
                        fillcolor="rgba(237,90,110,0.25)",
                        marker=dict(size=8, color=TAG["chart"][4], symbol="x"),
                    ))
                event_d = tl_plan[tl_plan["Tem Evento"]]
                if not event_d.empty:
                    fig_plan.add_trace(go.Bar(
                        x=event_d["Data"], y=event_d["Entradas (R$)"],
                        name="Entradas", marker_color=TAG["chart"][2], opacity=0.5,
                    ))
                    fig_plan.add_trace(go.Bar(
                        x=event_d["Data"], y=-event_d["Saídas (R$)"],
                        name="Saídas", marker_color=TAG["chart"][4], opacity=0.5,
                    ))
                fig_plan.add_hline(y=0, line_dash="dash", line_color=TAG["chart"][4], line_width=2)
                fig_plan.update_layout(
                    **PLOTLY_LAYOUT, height=400, barmode="overlay",
                    yaxis_title="R$", xaxis_title="Data",
                )
                fig_plan.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_plan, use_container_width=True)

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
        fig = px.histogram(liquid_df, x="Conversão Resgate", nbins=30, title="D+ Conversão Resgate",
                           color_discrete_sequence=[TAG["laranja"]])
        fig.update_layout(**PLOTLY_LAYOUT, height=350)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.histogram(liquid_df, x="Liquid. Resgate", nbins=30, title="D+ Liquidação Resgate",
                            color_discrete_sequence=[TAG["chart"][1]])
        fig2.update_layout(**PLOTLY_LAYOUT, height=350)
        st.plotly_chart(fig2, use_container_width=True)
