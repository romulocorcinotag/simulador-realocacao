"""
Parser for the TAG Investimentos proposal Excel format.
Handles multi-sheet files with multiple clients and banks.
"""
import re
import pandas as pd
import numpy as np


def detect_clients_and_sheets(filepath):
    """Auto-detect which clients and banks are in the file.
    Returns dict: {client_name: {bank_name: sheet_name, ...}, ...}
    Plus special keys for consolidated/total sheets.
    """
    xl = pd.ExcelFile(filepath)
    result = {"clients": {}, "totals": [], "graficos": [], "all_sheets": xl.sheet_names}

    for name in xl.sheet_names:
        name_lower = name.lower()

        if "grafico" in name_lower or "graficos" in name_lower:
            result["graficos"].append(name)
            continue

        # Detect client-bank pattern: "Bradesco-Lud", "Santander-Ana"
        parts = name.split("-")
        if len(parts) == 2:
            bank_or_type = parts[0].strip()
            client_suffix = parts[1].strip()

            # Check if it's a Total-Client pattern
            if bank_or_type.lower().startswith("total"):
                if client_suffix not in result["clients"]:
                    result["clients"][client_suffix] = {}
                result["clients"][client_suffix]["_consolidated"] = name
            else:
                if client_suffix not in result["clients"]:
                    result["clients"][client_suffix] = {}
                result["clients"][client_suffix][bank_or_type] = name
        elif name_lower in ("total", "total2"):
            result["totals"].append(name)

    return result


def parse_proposal_sheet(filepath, sheet_name):
    """Parse a single sheet from the proposal Excel.
    Returns DataFrame with clean, named columns.
    """
    df_raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    # Find the header row - look for "Instituicao" or "Saldo Bruto Atual"
    header_row = None
    for idx in range(min(5, len(df_raw))):
        row_str = " ".join(str(v) for v in df_raw.iloc[idx].values if pd.notna(v))
        if "Institui" in row_str or "Saldo Bruto" in row_str:
            header_row = idx
            break

    if header_row is None:
        header_row = 0  # fallback

    # Data starts after header row (row 1 is totals header, row 2+ is data)
    data_start = header_row + 2  # skip header + totals line
    if data_start >= len(df_raw):
        return pd.DataFrame()

    rows = []
    for idx in range(data_start, len(df_raw)):
        r = df_raw.iloc[idx]

        # Skip completely empty rows
        non_null = r.dropna()
        if len(non_null) < 2:
            continue

        # Extract values by position
        row = {
            "instituicao": _clean_str(r.iloc[1]) if len(r) > 1 else None,
            "ativo": _clean_str(r.iloc[2]) if len(r) > 2 else None,
            "taxa": _clean_str(r.iloc[3]) if len(r) > 3 else None,
            "vencimento": _parse_date(r.iloc[4]) if len(r) > 4 else None,
            "saldo_atual": _parse_num(r.iloc[5]) if len(r) > 5 else None,
            "pct_atual": _parse_num(r.iloc[6]) if len(r) > 6 else None,
            "proposta_valor": _parse_num(r.iloc[7]) if len(r) > 7 else None,
            "proposta_pct": _parse_num(r.iloc[8]) if len(r) > 8 else None,
            "categoria": _clean_str(r.iloc[9]) if len(r) > 9 else None,
            "isento": _clean_str(r.iloc[10]) if len(r) > 10 else None,
            "prazo_liquidez": _clean_str(r.iloc[11]) if len(r) > 11 else None,
            "dias_vencimento": _parse_num(r.iloc[12]) if len(r) > 12 else None,
            "observacao": _clean_str(r.iloc[13]) if len(r) > 13 else None,
            "retorno_1a": _parse_return(r.iloc[15]) if len(r) > 15 else None,
            "retorno_3a": _parse_return(r.iloc[16]) if len(r) > 16 else None,
            "retorno_5a": _parse_return(r.iloc[17]) if len(r) > 17 else None,
            "vol_12m": _parse_return(r.iloc[18]) if len(r) > 18 else None,
        }

        # Determine if this is an asset row or subtotal
        is_subtotal = pd.isna(r.iloc[1]) if len(r) > 1 else True
        row["is_subtotal"] = is_subtotal

        # Only include rows that have meaningful data
        # Skip rows where ativo looks like a number (spurious total rows)
        if row["ativo"]:
            try:
                float(row["ativo"])
                continue  # skip numeric "ativo" values
            except (ValueError, TypeError):
                pass

        if row["ativo"] or row["saldo_atual"]:
            rows.append(row)

    return pd.DataFrame(rows)


def extract_assets_from_sheet(df):
    """Extract individual asset rows (skip subtotals)."""
    if df.empty or "is_subtotal" not in df.columns:
        return df
    assets = df[~df["is_subtotal"]].copy()
    # Also filter out CAIXA entries that are just the header
    assets = assets[assets["ativo"].notna()].reset_index(drop=True)
    return assets


def extract_summary_from_sheet(df):
    """Extract category-level subtotals."""
    if df.empty or "is_subtotal" not in df.columns:
        return df
    subtotals = df[df["is_subtotal"] & df["ativo"].notna()].copy()
    # These are category lines like "RENDA FIXA POS", "RENDA FIXA INFLACAO"
    subtotals = subtotals[~subtotals["ativo"].str.upper().str.contains("CAIXA", na=False) |
                          (subtotals["saldo_atual"].abs() > 1000)].reset_index(drop=True)
    return subtotals


def parse_proposal_excel(filepath):
    """Parse the entire proposal file.
    Returns dict with parsed data for each sheet plus metadata.
    """
    structure = detect_clients_and_sheets(filepath)
    result = {
        "structure": structure,
        "sheets": {},
        "clients": {},
    }

    # Parse each sheet
    for name in structure["all_sheets"]:
        if any(g in name.lower() for g in ["grafico", "total2"]):
            continue
        try:
            df = parse_proposal_sheet(filepath, name)
            if not df.empty:
                result["sheets"][name] = {
                    "all": df,
                    "assets": extract_assets_from_sheet(df),
                    "summary": extract_summary_from_sheet(df),
                }
        except Exception:
            pass

    # Build client portfolios
    for client, sheets in structure["clients"].items():
        client_data = {"banks": {}, "consolidated": None}

        for bank, sheet_name in sheets.items():
            if sheet_name in result["sheets"]:
                if bank == "_consolidated":
                    client_data["consolidated"] = result["sheets"][sheet_name]
                else:
                    client_data["banks"][bank] = result["sheets"][sheet_name]

        result["clients"][client] = client_data

    return result


def get_client_portfolio(parsed, client_name):
    """Get a clean portfolio DataFrame for a specific client.
    Uses consolidated sheet if available, otherwise merges bank sheets.
    Returns DataFrame with asset-level data.
    """
    client = parsed["clients"].get(client_name)
    if not client:
        # Try partial match
        for key in parsed["clients"]:
            if client_name.lower() in key.lower():
                client = parsed["clients"][key]
                break

    if not client:
        return pd.DataFrame()

    if client["consolidated"]:
        return client["consolidated"]["assets"]

    # Merge bank sheets
    dfs = []
    for bank_name, bank_data in client["banks"].items():
        df = bank_data["assets"].copy()
        if "instituicao" not in df.columns or df["instituicao"].isna().all():
            df["instituicao"] = bank_name
        dfs.append(df)

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


def get_all_assets(parsed):
    """Get all assets from the main total/consolidated sheet."""
    # Try TOTAL sheet first
    for name in ["TOTAL", "Total"]:
        if name in parsed["sheets"]:
            return parsed["sheets"][name]["assets"]

    # Try any Total- sheet
    for name in parsed["sheets"]:
        if name.lower().startswith("total"):
            return parsed["sheets"][name]["assets"]

    return pd.DataFrame()


def portfolio_to_standard_format(df):
    """Convert parsed proposal data to the standard format used by the system.
    Returns list of dicts compatible with the existing carteira_dados format.
    """
    records = []
    for _, row in df.iterrows():
        if row.get("is_subtotal"):
            continue

        # Validate and clean categoria (skip if it looks like a number)
        cat_raw = row.get("categoria", "") or ""
        try:
            float(str(cat_raw))
            cat_raw = ""  # numeric value, not a real category
        except (ValueError, TypeError):
            pass

        record = {
            "Ativo": str(row.get("ativo", ""))[:60],
            "Financeiro": float(row.get("saldo_atual") or 0),
            "Categoria": str(cat_raw),
            "Isento": str(row.get("isento", "") or ""),
        }

        # Add optional fields
        if row.get("taxa"):
            record["Taxa"] = str(row["taxa"])
        if row.get("vencimento"):
            record["Vencimento"] = str(row["vencimento"])
        if row.get("pct_atual"):
            record["% Atual"] = float(row["pct_atual"])
        if row.get("proposta_valor"):
            record["Proposta R$"] = float(row["proposta_valor"])
        if row.get("proposta_pct"):
            record["Proposta %"] = float(row["proposta_pct"])
        if row.get("observacao"):
            record["Observacao"] = str(row["observacao"])
        if row.get("prazo_liquidez"):
            record["Prazo Liquidez"] = str(row["prazo_liquidez"])
        if row.get("retorno_1a") is not None:
            record["Retorno 1a"] = float(row["retorno_1a"])
        if row.get("retorno_3a") is not None:
            record["Retorno 3a"] = float(row["retorno_3a"])
        if row.get("retorno_5a") is not None:
            record["Retorno 5a"] = float(row["retorno_5a"])
        if row.get("vol_12m") is not None:
            record["Vol 12m"] = float(row["vol_12m"])

        if record["Financeiro"] != 0 or record.get("Proposta R$", 0) != 0:
            records.append(record)

    return records


def build_category_summary(df):
    """Build a category-level summary from asset data.
    Returns DataFrame with columns: categoria, saldo_atual, pct_atual, proposta_valor, proposta_pct
    """
    if df.empty:
        return pd.DataFrame()

    assets = df[~df.get("is_subtotal", False)].copy() if "is_subtotal" in df.columns else df.copy()

    if "categoria" not in assets.columns:
        return pd.DataFrame()

    # Filter out rows without valid category
    assets = assets[assets["categoria"].notna() & (assets["categoria"] != "")].copy()

    # Group by category
    summary = assets.groupby("categoria", dropna=True).agg(
        saldo_atual=("saldo_atual", "sum"),
        proposta_valor=("proposta_valor", "sum"),
        num_ativos=("ativo", "count"),
    ).reset_index()

    total_atual = summary["saldo_atual"].sum()
    total_proposta = summary["proposta_valor"].sum()

    if total_atual > 0:
        summary["pct_atual"] = summary["saldo_atual"] / total_atual
    else:
        summary["pct_atual"] = 0

    if total_proposta > 0:
        summary["proposta_pct"] = summary["proposta_valor"] / total_proposta
    else:
        summary["proposta_pct"] = 0

    summary["delta_pct"] = summary["proposta_pct"] - summary["pct_atual"]

    return summary.sort_values("saldo_atual", ascending=False).reset_index(drop=True)


# ── Helper functions ──

def _clean_str(val):
    """Clean a string value."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _parse_num(val):
    """Parse a numeric value, handling Brazilian formatting."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    s = str(val).strip()
    if s in ("-", "", "nan", "None"):
        return None
    # Handle Brazilian format: 1.234,56
    s = s.replace("R$", "").replace(" ", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_return(val):
    """Parse return/percentage values. Handles '-' as None."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    s = str(val).strip()
    if s in ("-", "", "nan", "None", "* feito pelo indexador"):
        return None
    s = s.replace("%", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(val):
    """Parse date value."""
    if pd.isna(val):
        return None
    if isinstance(val, pd.Timestamp):
        return val
    s = str(val).strip()
    if not s or s in ("-", "nan", "None"):
        return None
    try:
        return pd.to_datetime(s, format="mixed", dayfirst=True)
    except Exception:
        try:
            return pd.to_datetime(s)
        except Exception:
            return None
