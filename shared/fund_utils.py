"""
Fund matching, identification and liquidation data utilities.
"""
import os
import re

import pandas as pd
import streamlit as st


DADOS_LIQUID_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "Dados de liquid.xlsx"
)


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
    """Find the first matching column from candidates (exact -> partial)."""
    for c in candidates:
        if c in df.columns:
            return c
    for c in candidates:
        for col in df.columns:
            if c.upper()[:6] in col.upper():
                return col
    return None


def is_stock_ticker(name):
    """Check if the asset name looks like a B3 stock/ETF ticker."""
    if not name:
        return False
    return bool(re.match(r"^[A-Z]{4}\d{1,2}$", str(name).strip().upper()))


def match_fund_liquidation(fund_name, fund_code, liquid_df):
    """Try to match a fund from the portfolio with liquidation data."""
    if fund_code and not pd.isna(fund_code):
        code_str = (
            str(int(fund_code)) if isinstance(fund_code, float) else str(fund_code)
        )
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
                if len(name_clean) > 5 and (
                    name_clean in liq_name or liq_name in name_clean
                ):
                    return row

    check_name = fund_name if fund_name else fund_code
    if check_name and is_stock_ticker(str(check_name)):
        return pd.Series(
            {
                "Apelido": str(check_name).upper(),
                "Conversão Resgate": 0,
                "Liquid. Resgate": 2,
                "Conversão Aplic.": 0,
                "Contagem Resgate": "Úteis",
                "Código Anbima": "",
                "Categoria": "Ação/ETF B3",
            }
        )
    return None


def identify_cash_funds(ativos_df, liquid_df):
    """Identify funds with ESTRATÉGIA containing 'CAIXA'."""
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
            liq_info = match_fund_liquidation(name, code, liquid_df)
            if liq_info is not None:
                conv = int(liq_info.get("Conversão Resgate", 0))
                liq = int(liq_info.get("Liquid. Resgate", 0))
            else:
                conv, liq = 0, 0
            cash_details.append(
                {
                    "Ativo": name[:50],
                    "Código": code,
                    "Estratégia": estrategia,
                    "D+ Conv.": conv,
                    "D+ Liq.": liq,
                    "Financeiro (R$)": fin,
                }
            )
    return cash_codes, cash_details
