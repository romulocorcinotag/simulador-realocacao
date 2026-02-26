"""
Portfolio parsing, movement handling, and cash flow utilities.
"""
import re
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd

from shared.fund_utils import find_col, load_liquidation_data, match_fund_liquidation, identify_cash_funds
from shared.date_utils import add_business_days, subtract_business_days, compute_settle_date


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


def parse_model_portfolio(uploaded_file, sheet_name=None):
    """Parse model portfolio. Supports both rich format (Classe/Subcategoria/Min/Max)
    and simple format (Código/Ativo/% Alvo). Returns DataFrame with available columns.

    Rich format columns: Classe, Subcategoria, Ativo, % Alvo, Min %, Max %
    Simple format columns: Código, Ativo, % Alvo
    """
    kwargs = {}
    if sheet_name:
        kwargs["sheet_name"] = sheet_name

    df = pd.read_excel(uploaded_file, **kwargs)
    df.columns = [str(c).strip() for c in df.columns]

    # ── Detect rich format (Classe + Subcategoria + Ativo + % Alvo + Min/Max) ──
    classe_col = subcategoria_col = name_col = pct_col = min_col = max_col = None
    code_col = None

    col_upper_map = {c: c.upper() for c in df.columns}

    for c, cu in col_upper_map.items():
        if classe_col is None and any(k in cu for k in ["CLASSE", "CLASS"]):
            classe_col = c
        elif subcategoria_col is None and any(k in cu for k in ["SUBCATEGORIA", "SUBCATEG", "SUB"]):
            subcategoria_col = c
        elif min_col is None and "MIN" in cu and "%" in cu:
            min_col = c
        elif max_col is None and "MAX" in cu and "%" in cu:
            max_col = c

    # Detect ativo/name column
    for c, cu in col_upper_map.items():
        if name_col is None and any(k in cu for k in ["ATIVO", "NOME", "FUNDO", "NAME", "ASSET"]):
            name_col = c

    # Detect % target column
    for c, cu in col_upper_map.items():
        if pct_col is None and any(k in cu for k in ["% ALVO", "%ALVO", "PESO", "TARGET", "ALOC"]):
            if c != min_col and c != max_col:
                pct_col = c

    # Detect code column
    for c, cu in col_upper_map.items():
        if code_col is None and any(k in cu for k in ["COD", "CODE", "ID"]):
            code_col = c

    # Fallback: try to detect by dtype
    if pct_col is None:
        for c in df.columns:
            if c == min_col or c == max_col or c == classe_col or c == subcategoria_col or c == name_col:
                continue
            if df[c].dtype in ["float64", "int64"]:
                vals = df[c].dropna()
                if len(vals) > 0 and vals.max() <= 100 and vals.min() >= 0:
                    pct_col = c
                    break

    if name_col is None and code_col is None:
        # Last resort: first non-numeric column that isn't classe/subcategoria
        for c in df.columns:
            if c != classe_col and c != subcategoria_col and df[c].dtype == "object":
                name_col = c
                break

    # ── Build result ──
    is_rich = classe_col is not None and subcategoria_col is not None

    result = pd.DataFrame()

    if is_rich:
        result["Classe"] = df[classe_col].astype(str).str.strip()
        result["Subcategoria"] = df[subcategoria_col].astype(str).str.strip()

    if code_col:
        result["Codigo"] = df[code_col].astype(str)
    else:
        result["Codigo"] = ""

    result["Ativo"] = df[name_col].astype(str).str.strip() if name_col else result.get("Codigo", "")
    result["% Alvo"] = (
        pd.to_numeric(df[pct_col], errors="coerce").fillna(0) if pct_col else 0
    )

    if is_rich:
        if min_col:
            result["Min %"] = pd.to_numeric(df[min_col], errors="coerce").fillna(0)
        if max_col:
            result["Max %"] = pd.to_numeric(df[max_col], errors="coerce").fillna(0)

    # Filter out rows with 0 allocation (keep full model in sheet "Modelo" if rich)
    result = result[result["% Alvo"] > 0].reset_index(drop=True)
    return result


def load_all_model_profiles(filepath):
    """Load the master model file that contains all profiles.
    Expects columns: Classe Ativo, Subcategoria, Ativo, and HOJE columns per profile.
    Returns dict {perfil: list of dicts} with full model data.
    """
    df = pd.read_excel(filepath)
    df.columns = [str(c).strip() for c in df.columns]

    profiles = {}
    # Detect HOJE columns (e.g., "Renda Fixa HOJE", "Conservador HOJE")
    hoje_cols = [c for c in df.columns if "HOJE" in c.upper()]

    # Detect key columns
    classe_col = next((c for c in df.columns if "CLASSE" in c.upper()), None)
    sub_col = next((c for c in df.columns if "SUBCATEG" in c.upper() or "SUB" in c.upper()), None)
    ativo_col = next((c for c in df.columns if "ATIVO" in c.upper()), None)

    if not classe_col or not ativo_col:
        return profiles

    # Detect min/max columns per profile
    for hcol in hoje_cols:
        perfil_name = hcol.replace("HOJE", "").strip()
        prefix = perfil_name[:3].upper()  # "RF ", "Con", "Mod", "Agr"

        # Find matching min/max columns
        min_col = next((c for c in df.columns if prefix in c.upper() and "MIN" in c.upper()), None)
        max_col = next((c for c in df.columns if prefix in c.upper() and "MAX" in c.upper()), None)

        rows = []
        for _, r in df.iterrows():
            pct = pd.to_numeric(r[hcol], errors="coerce") or 0
            entry = {
                "classe": str(r[classe_col]).strip() if pd.notna(r[classe_col]) else "",
                "subcategoria": str(r[sub_col]).strip() if sub_col and pd.notna(r[sub_col]) else "",
                "ativo": str(r[ativo_col]).strip() if pd.notna(r[ativo_col]) else "",
                "pct_alvo": float(pct),
            }
            if min_col:
                entry["min_pct"] = float(pd.to_numeric(r[min_col], errors="coerce") or 0)
            if max_col:
                entry["max_pct"] = float(pd.to_numeric(r[max_col], errors="coerce") or 0)
            rows.append(entry)

        profiles[perfil_name] = rows

    return profiles


def extract_provisions_as_movements(provisoes_df, ativos_df):
    """Extract provisions from the portfolio file and convert to movements."""
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
        code_match = re.search(r"\((\d+)\)", desc)
        fund_code = code_match.group(1) if code_match else None
        fund_name = ""

        if fund_code and ativos_df is not None and cod_col:
            asset_match = ativos_df[ativos_df[cod_col].astype(str) == fund_code]
            if not asset_match.empty:
                fund_name = str(asset_match.iloc[0].get("ATIVO", ""))

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

        movements.append(
            {
                "fund_name": fund_name if fund_name else desc[:60],
                "fund_code": fund_code,
                "operation": op_type,
                "value": abs(valor),
                "request_date": pd.Timestamp(data_op),
                "liquidation_date": pd.Timestamp(data_liq),
                "description": desc,
                "source": source,
            }
        )

    return movements


def apply_movement(op, value, fund_code, positions, caixa):
    """Apply a single movement to positions dict and caixa. Returns updated caixa."""
    if op == "Resgate Passivo":
        caixa -= value
    elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
        if fund_code and fund_code in positions:
            positions[fund_code]["financeiro"] -= value
        caixa += value
    elif "Aplicação" in op:
        if fund_code and fund_code in positions:
            positions[fund_code]["financeiro"] += value
        caixa -= value
    elif op == "Débito/Passivo":
        caixa -= value
    elif op == "Crédito (Provisão)":
        caixa += value
    return caixa


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


def build_cash_flow_timeline(caixa_initial, ativos_df, all_movements, cash_fund_codes):
    """Build day-by-day cash flow timeline. Returns (df_timeline, initial_effective_cash)."""
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    cash_components = {"CAIXA": caixa_initial}
    cash_fund_names = {"CAIXA": "Linha CAIXA"}
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        if code in cash_fund_codes:
            fin = float(row.get("FINANCEIRO", 0))
            name = str(row.get("ATIVO", ""))[:35]
            cash_components[code] = fin
            cash_fund_names[code] = name

    if all_movements:
        for m in all_movements:
            fc = str(m.get("fund_code", ""))
            if fc and fc in cash_fund_codes and fc not in cash_components:
                cash_components[fc] = 0.0
                cash_fund_names[fc] = m.get("fund_name", fc)[:35]

    initial_effective_cash = sum(cash_components.values())

    if not all_movements:
        today = pd.Timestamp(datetime.today().date())
        rows = []
        for i in range(5):
            d = today + timedelta(days=i)
            if d.weekday() < 5:
                row_data = {
                    "Data": d,
                    "Entradas (R$)": 0,
                    "Saídas (R$)": 0,
                    "Líquido (R$)": 0,
                    "Saldo (R$)": initial_effective_cash,
                    "Detalhes": "",
                    "Negativo": False,
                    "Tem Evento": False,
                }
                for comp_code in cash_components:
                    comp_name = cash_fund_names.get(comp_code, comp_code)
                    row_data[f"_{comp_name}"] = cash_components.get(comp_code, 0)
                rows.append(row_data)
        return pd.DataFrame(rows), initial_effective_cash

    valid_movs = [m for m in all_movements if pd.notna(m.get("liquidation_date"))]
    if not valid_movs:
        return pd.DataFrame(), initial_effective_cash

    today = pd.Timestamp(datetime.today().date())
    last_date = max(pd.Timestamp(m["liquidation_date"]) for m in valid_movs)
    if last_date < today:
        last_date = today + timedelta(days=5)

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
        comp_impacts = {}

        if op == "Resgate Passivo":
            cash_impact = -value
            comp_impacts["CAIXA"] = -value
            desc = f"Resgate Passivo: -R$ {value:,.0f}"
        elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
            if is_cash_fund:
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

    rows = []
    running_balance = initial_effective_cash
    running_components = dict(cash_components)
    current = today
    while current <= last_date + timedelta(days=3):
        if current.weekday() < 5:
            day_events = events.get(current, [])
            inflows = sum(ci for _, ci, _ in day_events if ci > 0)
            outflows = sum(abs(ci) for _, ci, _ in day_events if ci < 0)
            net = inflows - outflows
            running_balance += net

            for _, _, comp_imp in day_events:
                for comp_code, delta in comp_imp.items():
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
            for comp_code in cash_components:
                comp_name = cash_fund_names.get(comp_code, comp_code)
                row_data[f"_{comp_name}"] = running_components.get(comp_code, 0)
            rows.append(row_data)
        current += timedelta(days=1)

    df_timeline = pd.DataFrame(rows)
    return df_timeline, initial_effective_cash


def build_evolution_table(ativos_df, all_movements, caixa_initial):
    """Build evolution table: rows=assets, columns=dates."""
    cod_col = find_col(ativos_df, "CÓD. ATIVO", "COD. ATIVO")

    assets = []
    for _, row in ativos_df.iterrows():
        code = str(row[cod_col]) if cod_col else ""
        name = str(row.get("ATIVO", ""))
        fin = float(row.get("FINANCEIRO", 0))
        assets.append({"code": code, "name": name, "financeiro_atual": fin})

    all_dates = sorted(
        set(
            pd.Timestamp(m["liquidation_date"])
            for m in all_movements
            if pd.notna(m.get("liquidation_date"))
        )
    )
    if not all_dates:
        return None, None, None

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

            matched_code = None
            if fund_code:
                for a in assets:
                    if a["code"] == fund_code:
                        matched_code = a["code"]
                        break
            if not matched_code and fund_name:
                for a in assets:
                    if (
                        fund_name.upper()[:20] in a["name"].upper()
                        or a["name"].upper()[:20] in fund_name.upper()
                    ):
                        matched_code = a["code"]
                        break

            if op == "Resgate Passivo":
                caixa_adj -= value
            elif op in ("Resgate (Cotizando)", "Resgate (Provisão)", "Resgate"):
                if matched_code:
                    date_adjustments[d][matched_code] = (
                        date_adjustments[d].get(matched_code, 0) - value
                    )
                caixa_adj += value
            elif "Aplicação" in op:
                if matched_code:
                    date_adjustments[d][matched_code] = (
                        date_adjustments[d].get(matched_code, 0) + value
                    )
                caixa_adj -= value
            elif op == "Débito/Passivo":
                caixa_adj -= value
            elif op == "Crédito (Provisão)":
                caixa_adj += value

        caixa_adjustments[d] = caixa_adj

    rows_financeiro = []
    for a in assets:
        row_fin = {
            "Ativo": a["name"][:45],
            "Código": a["code"],
            "Atual (R$)": a["financeiro_atual"],
        }
        for d in all_dates:
            adj = date_adjustments[d].get(a["code"], 0)
            row_fin[d.strftime("%d/%m/%Y")] = a["financeiro_atual"] + adj
        rows_financeiro.append(row_fin)

    caixa_row_fin = {
        "Ativo": "CAIXA",
        "Código": "CAIXA",
        "Atual (R$)": caixa_initial,
    }
    for d in all_dates:
        caixa_row_fin[d.strftime("%d/%m/%Y")] = caixa_initial + caixa_adjustments[d]
    rows_financeiro.append(caixa_row_fin)

    df_fin = pd.DataFrame(rows_financeiro)

    date_cols = [d.strftime("%d/%m/%Y") for d in all_dates]
    total_row = {
        "Ativo": "TOTAL PL",
        "Código": "",
        "Atual (R$)": df_fin["Atual (R$)"].sum(),
    }
    for dc in date_cols:
        total_row[dc] = df_fin[dc].sum()
    rows_financeiro.append(total_row)
    df_fin = pd.DataFrame(rows_financeiro)

    rows_pct = []
    for _, r in df_fin.iterrows():
        if r["Ativo"] == "TOTAL PL":
            continue
        row_pct = {
            "Ativo": r["Ativo"],
            "Código": r["Código"],
            "Atual (%)": (
                (r["Atual (R$)"] / total_row["Atual (R$)"] * 100)
                if total_row["Atual (R$)"] != 0
                else 0
            ),
        }
        for dc in date_cols:
            total_on_date = total_row[dc]
            row_pct[dc] = (r[dc] / total_on_date * 100) if total_on_date != 0 else 0
        rows_pct.append(row_pct)

    total_pct_row = {"Ativo": "TOTAL PL", "Código": "", "Atual (%)": 100.0}
    for dc in date_cols:
        total_pct_row[dc] = 100.0
    rows_pct.append(total_pct_row)
    df_pct = pd.DataFrame(rows_pct)

    mov_rows = []
    for m in all_movements:
        mov_rows.append(
            {
                "Fundo": m["fund_name"][:45],
                "Código": m.get("fund_code", ""),
                "Operação": m["operation"],
                "Valor (R$)": m["value"],
                "Data Solicitação": (
                    m["request_date"].strftime("%d/%m/%Y")
                    if pd.notna(m.get("request_date"))
                    else ""
                ),
                "Data Liquidação": (
                    m["liquidation_date"].strftime("%d/%m/%Y")
                    if pd.notna(m.get("liquidation_date"))
                    else ""
                ),
                "Origem": m.get("source", "manual"),
            }
        )
    df_mov = pd.DataFrame(mov_rows)

    return df_fin, df_pct, df_mov
