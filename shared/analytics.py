"""
Analytics engine for TAG Investimentos proposal system.
Computes quantitative analysis for the 15 professional proposal sections:
  - Allocation comparison (Section 3)
  - Risk analysis & concentration (Section 4)
  - Bottom-up asset classification (Section 5)
  - Efficiency analysis (Section 6)
  - Liquidity comparison (Section 12)
  - Tax analysis (Section 13)
  - Concentration by institution (Section 4)
  - Maturity ladder (Section 12)

All functions accept lists of dicts (DB format) and return JSON-serializable dicts.
"""
from datetime import datetime

import numpy as np
import pandas as pd

from shared.backtest import _normalize_category, CATEGORY_PROXY


# ── Helpers ──

def _to_df(data):
    """Convert list-of-dicts to DataFrame, handling None/empty."""
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, list):
        return pd.DataFrame(data) if data else pd.DataFrame()
    return pd.DataFrame()


def _get_field(row, *candidates, default=""):
    """Get first non-empty field value from a row dict."""
    for c in candidates:
        v = row.get(c)
        if v is not None and str(v).strip() and str(v).strip().lower() != "nan":
            return v
    return default


def _get_category(row):
    """Extract normalized category from a row."""
    raw = _get_field(row, "Categoria", "categoria", "Estrategia", "Estratégia",
                     "classe", "Classe", "Subcategoria", default="Outros")
    return _normalize_category(str(raw))


def _get_financeiro(row):
    """Extract financial value from a row."""
    for k in ["Financeiro", "financeiro", "saldo_atual", "Saldo Bruto Atual"]:
        v = row.get(k)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return 0.0


def _get_pct(row, context="atual"):
    """Extract percentage from a row."""
    if context == "proposta":
        keys = ["pct_alvo", "Proposta %", "proposta_pct", "% Alvo", "Proposta"]
    else:
        keys = ["% Atual", "pct_atual", "% PL"]
    for k in keys:
        v = row.get(k)
        if v is not None:
            try:
                f = float(v)
                if f > 0:
                    return f
            except (ValueError, TypeError):
                pass
    return 0.0


# ── Section 3: Allocation Comparison ──

def compute_allocation_comparison(carteira_atual, carteira_proposta, modelo_base=None):
    """Compare allocation by asset class: current vs proposed vs model.

    Returns:
        dict with:
          - class_breakdown: list of {classe, pct_atual, pct_proposta, pct_modelo, delta}
          - exposure_summary: {rv, juros_reais, credito, alternativos, offshore, caixa}
    """
    df_atual = _to_df(carteira_atual)
    df_prop = _to_df(carteira_proposta)

    # Group by class
    actual_by_class = {}
    if not df_atual.empty:
        total_atual = sum(_get_financeiro(r) for r in (carteira_atual or []))
        if total_atual > 0:
            for item in (carteira_atual or []):
                cat = _get_category(item)
                fin = _get_financeiro(item)
                actual_by_class[cat] = actual_by_class.get(cat, 0) + fin / total_atual * 100

    proposed_by_class = {}
    if carteira_proposta:
        total_prop = sum(_get_pct(r, "proposta") for r in carteira_proposta)
        if total_prop > 0:
            for item in carteira_proposta:
                cat = _get_category(item)
                pct = _get_pct(item, "proposta")
                proposed_by_class[cat] = proposed_by_class.get(cat, 0) + pct / total_prop * 100

    model_by_class = {}
    if modelo_base:
        total_model = sum(_get_pct(r, "proposta") for r in modelo_base)
        if total_model > 0:
            for item in modelo_base:
                cat = _get_category(item)
                pct = _get_pct(item, "proposta")
                model_by_class[cat] = model_by_class.get(cat, 0) + pct / total_model * 100

    all_classes = sorted(set(list(actual_by_class.keys()) +
                             list(proposed_by_class.keys()) +
                             list(model_by_class.keys())))

    breakdown = []
    for cls in all_classes:
        pa = actual_by_class.get(cls, 0)
        pp = proposed_by_class.get(cls, 0)
        pm = model_by_class.get(cls, 0)
        breakdown.append({
            "classe": cls,
            "pct_atual": round(pa, 2),
            "pct_proposta": round(pp, 2),
            "pct_modelo": round(pm, 2),
            "delta": round(pp - pa, 2),
        })

    # Exposure summary
    exposure_map = {
        "rv": ["Renda Variavel"],
        "juros_reais": ["Renda Fixa Inflacao", "Renda Fixa Pre"],
        "credito": ["Renda Fixa CDI+", "Renda Fixa Pos"],
        "alternativos": ["Alternativos"],
        "caixa": ["Caixa"],
        "multimercado": ["Multimercados"],
        "listados": ["Fundos Listados Isentos"],
    }
    exposure = {}
    for key, classes in exposure_map.items():
        exposure[key] = {
            "atual": round(sum(actual_by_class.get(c, 0) for c in classes), 2),
            "proposta": round(sum(proposed_by_class.get(c, 0) for c in classes), 2),
        }

    return {
        "class_breakdown": breakdown,
        "exposure_summary": exposure,
    }


# ── Section 4: Risk Analysis ──

def compute_risk_analysis(carteira_atual, liquid_df=None):
    """Compute risk metrics: concentration by issuer, strategy, manager.

    Returns:
        dict with concentration_by_issuer, concentration_by_strategy,
        hhi_issuer, top5_issuer_pct
    """
    items = carteira_atual or []
    if not items:
        return {}

    total = sum(_get_financeiro(r) for r in items)
    if total == 0:
        return {}

    # Concentration by institution/issuer
    by_issuer = {}
    for item in items:
        issuer = _get_field(item, "instituicao", "Instituicao", "Instituição",
                            default="Outros")
        issuer = str(issuer).strip()
        if not issuer or issuer.lower() in ("", "nan", "none"):
            # Try to infer from asset name
            name = str(_get_field(item, "Ativo", "ativo", default=""))
            if name:
                parts = name.split()
                issuer = parts[0] if parts else "Outros"
            else:
                issuer = "Outros"
        fin = _get_financeiro(item)
        by_issuer[issuer] = by_issuer.get(issuer, 0) + fin

    issuer_list = []
    for issuer, fin in sorted(by_issuer.items(), key=lambda x: -x[1]):
        issuer_list.append({
            "instituicao": issuer,
            "financeiro": round(fin, 2),
            "pct": round(fin / total * 100, 2),
        })

    # HHI by issuer
    hhi_issuer = sum((item["pct"]) ** 2 for item in issuer_list)

    # Top 5 concentration
    top5_pct = sum(item["pct"] for item in issuer_list[:5])

    # Concentration by strategy/category
    by_strategy = {}
    for item in items:
        cat = _get_category(item)
        fin = _get_financeiro(item)
        by_strategy[cat] = by_strategy.get(cat, 0) + fin

    strategy_list = []
    for cat, fin in sorted(by_strategy.items(), key=lambda x: -x[1]):
        strategy_list.append({
            "estrategia": cat,
            "financeiro": round(fin, 2),
            "pct": round(fin / total * 100, 2),
            "num_ativos": sum(1 for r in items if _get_category(r) == cat),
        })

    return {
        "concentration_by_issuer": issuer_list,
        "concentration_by_strategy": strategy_list,
        "hhi_issuer": round(hhi_issuer, 2),
        "top5_issuer_pct": round(top5_pct, 2),
        "total_pl": round(total, 2),
    }


# ── Section 5: Bottom-Up Classification ──

def classify_assets_bottom_up(carteira_atual, carteira_proposta):
    """Classify each current asset into the quality matrix.

    Categories:
      - Convicto: exists in proposed with >= current %
      - Neutro: exists in proposed but reduced
      - Observação: borderline, may require attention
      - Saída Estrutural: not in proposed, liquid enough to sell
      - Ilíquido em Carregamento: not in proposed, but illiquid (D+30+)

    Returns:
        list of dicts [{ativo, classificacao, motivo, pct_atual, pct_proposta, liquidez}]
    """
    items_atual = carteira_atual or []
    items_prop = carteira_proposta or []

    if not items_atual:
        return []

    total_atual = sum(_get_financeiro(r) for r in items_atual)
    if total_atual == 0:
        return []

    # Build proposed assets lookup by name
    prop_lookup = {}
    for item in items_prop:
        name = str(_get_field(item, "ativo", "Ativo", default="")).strip().upper()
        pct = _get_pct(item, "proposta")
        if name:
            prop_lookup[name] = pct

    result = []
    for item in items_atual:
        name = str(_get_field(item, "Ativo", "ativo", default="")).strip()
        name_upper = name.upper()
        fin = _get_financeiro(item)
        pct_atual = fin / total_atual * 100

        # Check liquidity
        liq_str = str(_get_field(item, "Prazo Liquidez", "prazo_liquidez",
                                  "Vencimento", "vencimento", default=""))
        is_illiquid = False
        if liq_str:
            liq_upper = liq_str.upper()
            # D+60, D+90, D+180, etc.
            if "D+" in liq_upper:
                try:
                    d_plus = int(liq_upper.split("D+")[1].split()[0])
                    is_illiquid = d_plus >= 30
                except (ValueError, IndexError):
                    pass
            # Check for future dates (fixed maturity)
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(liq_str.strip(), fmt)
                    days_to_maturity = (dt - datetime.now()).days
                    is_illiquid = days_to_maturity > 30
                    break
                except ValueError:
                    pass

        # Classify
        pct_prop = prop_lookup.get(name_upper, 0)

        # Try partial match if exact match fails
        if pct_prop == 0 and name_upper:
            for pname, ppct in prop_lookup.items():
                if name_upper in pname or pname in name_upper:
                    pct_prop = ppct
                    break

        if pct_prop > 0 and pct_prop >= pct_atual * 0.9:
            classificacao = "Convicto"
            motivo = "Mantido ou aumentado na proposta"
        elif pct_prop > 0:
            classificacao = "Neutro"
            motivo = f"Reduzido de {pct_atual:.1f}% para {pct_prop:.1f}%"
        elif is_illiquid:
            classificacao = "Ilíquido em Carregamento"
            motivo = f"Sem liquidez imediata ({liq_str}). Carregamento até vencimento."
        elif pct_atual < 0.5:
            classificacao = "Observação"
            motivo = f"Posição residual ({pct_atual:.2f}%)"
        else:
            classificacao = "Saída Estrutural"
            motivo = "Não faz parte da proposta. Resgate quando possível."

        result.append({
            "ativo": name,
            "classificacao": classificacao,
            "motivo": motivo,
            "pct_atual": round(pct_atual, 2),
            "pct_proposta": round(pct_prop, 2),
            "liquidez": liq_str or "N/D",
            "financeiro": round(fin, 2),
        })

    # Sort by classification priority
    priority = {
        "Convicto": 0, "Neutro": 1, "Observação": 2,
        "Saída Estrutural": 3, "Ilíquido em Carregamento": 4,
    }
    result.sort(key=lambda x: (priority.get(x["classificacao"], 5), -x["financeiro"]))

    return result


# ── Section 6: Efficiency Analysis ──

def compute_efficiency_analysis(backtest_result):
    """Compute return/risk efficiency metrics from backtest data.

    Returns:
        dict with sharpe, sortino, return_per_vol, efficiency by window
    """
    windows = backtest_result.get("windows", {})
    if not windows:
        return {}

    efficiency_by_window = []
    for label, w in sorted(windows.items(), key=lambda x: x[1]["months"]):
        ret = w.get("total_return", 0)
        vol = w.get("volatility", 0)
        sharpe = w.get("sharpe", 0)
        cdi_ret = w.get("cdi_return", 0)

        # Sortino (downside deviation)
        cum = w.get("cumulative")
        sortino = 0
        if cum is not None and not cum.empty:
            daily_returns = cum.pct_change().dropna()
            daily_cdi = (1 + cdi_ret) ** (1 / len(daily_returns)) - 1 if len(daily_returns) > 0 else 0
            excess = daily_returns - daily_cdi
            downside = excess[excess < 0]
            downside_dev = float(downside.std() * np.sqrt(252)) if len(downside) > 2 else 0
            sortino = float(excess.mean() * 252 / downside_dev) if downside_dev > 0 else 0

        efficiency_by_window.append({
            "janela": label,
            "retorno": round(ret * 100, 2),
            "volatilidade": round(vol * 100, 2),
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "retorno_por_vol": round(ret / vol, 2) if vol > 0 else 0,
            "alpha_cdi": round(w.get("alpha_cdi", 0) * 100, 2),
        })

    return {
        "efficiency_by_window": efficiency_by_window,
    }


# ── Section 12: Liquidity Comparison ──

def compute_liquidity_comparison(carteira_atual, carteira_proposta, liquid_df=None):
    """Compare liquidity profile: current vs proposed portfolio.

    Returns:
        dict with atual_buckets, proposta_buckets, pct_cash_quickly,
        maturity_ladder
    """
    from shared.fund_utils import match_fund_liquidation

    def _compute_buckets(items):
        if not items:
            return {"D+0-1": 0, "D+2-5": 0, "D+6-30": 0, "D+30+": 0}

        total = sum(_get_financeiro(r) for r in items)
        # If no Financeiro, use pct_alvo (proposed portfolio)
        use_pct = total == 0
        if use_pct:
            total = sum(_get_pct(r, "proposta") for r in items)
        if total == 0:
            return {"D+0-1": 0, "D+2-5": 0, "D+6-30": 0, "D+30+": 0}

        buckets = {"D+0-1": 0, "D+2-5": 0, "D+6-30": 0, "D+30+": 0}

        for item in items:
            fin = _get_pct(item, "proposta") if use_pct else _get_financeiro(item)
            name = str(_get_field(item, "Ativo", "ativo", default=""))
            code = str(_get_field(item, "Codigo", "Código", default=""))
            liq_str = str(_get_field(item, "Prazo Liquidez", "prazo_liquidez", default=""))

            d_total = None

            # Try parsed D+ string
            if liq_str and "D+" in liq_str.upper():
                try:
                    d_total = int(liq_str.upper().split("D+")[1].split()[0])
                except (ValueError, IndexError):
                    pass

            # Try liquidation database
            if d_total is None and liquid_df is not None and not liquid_df.empty:
                liq_info = match_fund_liquidation(name, code, liquid_df)
                if liq_info is not None:
                    try:
                        d_total = int(liq_info.get("Conversão Resgate", 0)) + \
                                  int(liq_info.get("Liquid. Resgate", 0))
                    except (ValueError, TypeError):
                        pass

            if d_total is None:
                d_total = 60  # default conservative

            if d_total <= 1:
                buckets["D+0-1"] += fin
            elif d_total <= 5:
                buckets["D+2-5"] += fin
            elif d_total <= 30:
                buckets["D+6-30"] += fin
            else:
                buckets["D+30+"] += fin

        # Convert to pct
        for k in buckets:
            buckets[k] = round(buckets[k] / total * 100, 2)

        return buckets

    atual_buckets = _compute_buckets(carteira_atual)
    proposta_buckets = _compute_buckets(carteira_proposta)

    # % that can become cash quickly (D+5 or less)
    pct_cash_quickly_atual = atual_buckets.get("D+0-1", 0) + atual_buckets.get("D+2-5", 0)
    pct_cash_quickly_proposta = proposta_buckets.get("D+0-1", 0) + proposta_buckets.get("D+2-5", 0)

    return {
        "atual_buckets": atual_buckets,
        "proposta_buckets": proposta_buckets,
        "pct_cash_quickly_atual": round(pct_cash_quickly_atual, 2),
        "pct_cash_quickly_proposta": round(pct_cash_quickly_proposta, 2),
    }


# ── Section 13: Tax Analysis ──

def compute_tax_analysis(carteira_atual, carteira_proposta):
    """Compare tax efficiency: current vs proposed.

    Returns:
        dict with isentos percentages, turnover impact notes
    """
    TAX_EXEMPT_CATEGORIES = {
        "Fundos Listados Isentos", "FII", "FI-Infra", "FIAGRO",
    }
    TAX_EXEMPT_KEYWORDS = [
        "LCI", "LCA", "CRI", "CRA", "FII", "FIAGRO", "INFRA",
        "ISENTOS", "ISENTO", "KNIP", "KNRI", "KDIF", "RURA",
        "AZIN", "XPML", "HGLG", "MXRF",
    ]

    def _pct_isento(items, use_pct=False):
        if not items:
            return 0

        # For proposed portfolios, use pct_alvo instead of Financeiro
        if use_pct:
            total = sum(_get_pct(r, "proposta") for r in items)
            if total == 0:
                return 0
            isento = 0
            for item in items:
                cat = _get_category(item)
                name = str(_get_field(item, "Ativo", "ativo", default="")).upper()
                is_exempt = cat in TAX_EXEMPT_CATEGORIES

                if not is_exempt:
                    isento_field = str(_get_field(item, "Isento", "isento", default="")).upper()
                    if isento_field in ("SIM", "S", "TRUE", "1", "ISENTO"):
                        is_exempt = True

                if not is_exempt:
                    for kw in TAX_EXEMPT_KEYWORDS:
                        if kw in name:
                            is_exempt = True
                            break

                if is_exempt:
                    isento += _get_pct(item, "proposta")
            return round(isento / total * 100, 2)

        # For current portfolios, use Financeiro
        total = sum(_get_financeiro(r) for r in items)
        if total == 0:
            return 0

        isento = 0
        for item in items:
            cat = _get_category(item)
            name = str(_get_field(item, "Ativo", "ativo", default="")).upper()
            is_exempt = cat in TAX_EXEMPT_CATEGORIES

            if not is_exempt:
                isento_field = str(_get_field(item, "Isento", "isento", default="")).upper()
                if isento_field in ("SIM", "S", "TRUE", "1", "ISENTO"):
                    is_exempt = True

            if not is_exempt:
                for kw in TAX_EXEMPT_KEYWORDS:
                    if kw in name:
                        is_exempt = True
                        break

            if is_exempt:
                isento += _get_financeiro(item)

        return round(isento / total * 100, 2)

    atual_isentos = _pct_isento(carteira_atual, use_pct=False)
    # Proposed portfolio uses pct_alvo, not Financeiro
    has_financeiro = any(_get_financeiro(r) > 0 for r in (carteira_proposta or []))
    proposta_isentos = _pct_isento(carteira_proposta, use_pct=not has_financeiro)

    # Turnover analysis: how many assets are being sold/added
    nomes_atual = set()
    for item in (carteira_atual or []):
        n = str(_get_field(item, "Ativo", "ativo", default="")).strip().upper()
        if n:
            nomes_atual.add(n)

    nomes_proposta = set()
    for item in (carteira_proposta or []):
        n = str(_get_field(item, "ativo", "Ativo", default="")).strip().upper()
        if n:
            nomes_proposta.add(n)

    saindo = nomes_atual - nomes_proposta
    entrando = nomes_proposta - nomes_atual
    mantidos = nomes_atual & nomes_proposta

    return {
        "atual_isentos_pct": atual_isentos,
        "proposta_isentos_pct": proposta_isentos,
        "delta_isentos": round(proposta_isentos - atual_isentos, 2),
        "turnover": {
            "saindo": len(saindo),
            "entrando": len(entrando),
            "mantidos": len(mantidos),
            "total_atual": len(nomes_atual),
            "total_proposta": len(nomes_proposta),
        },
        "notas": [],
    }


# ── Section 4 (extra): Concentration by Institution ──

def compute_concentration_by_institution(carteira_atual):
    """Group assets by bank/institution for concentration chart.

    Returns:
        list of dicts [{instituicao, total_financeiro, pct, num_ativos}]
    """
    items = carteira_atual or []
    if not items:
        return []

    total = sum(_get_financeiro(r) for r in items)
    if total == 0:
        return []

    by_inst = {}
    for item in items:
        inst = str(_get_field(item, "instituicao", "Instituicao", "Instituição",
                              default="")).strip()
        if not inst or inst.lower() in ("", "nan", "none", "outros"):
            # Try extracting from asset name prefix
            name = str(_get_field(item, "Ativo", "ativo", default=""))
            cat = str(_get_field(item, "Categoria", "categoria", default=""))
            # Use category or first word of name
            inst = cat if cat and cat.lower() not in ("", "nan") else (
                name.split()[0] if name.split() else "Outros"
            )

        fin = _get_financeiro(item)
        if inst not in by_inst:
            by_inst[inst] = {"total": 0, "count": 0}
        by_inst[inst]["total"] += fin
        by_inst[inst]["count"] += 1

    result = []
    for inst, data in sorted(by_inst.items(), key=lambda x: -x[1]["total"]):
        result.append({
            "instituicao": inst,
            "total_financeiro": round(data["total"], 2),
            "pct": round(data["total"] / total * 100, 2),
            "num_ativos": data["count"],
        })

    return result


# ── Section 12 (extra): Maturity Ladder ──

def compute_maturity_ladder(carteira_atual):
    """Build maturity schedule grouped by quarter.

    Returns:
        list of dicts [{periodo, label, total_financeiro, pct}]
    """
    items = carteira_atual or []
    if not items:
        return []

    total = sum(_get_financeiro(r) for r in items)
    if total == 0:
        return []

    by_period = {}  # "YYYY-QN" -> total
    no_maturity = 0

    for item in items:
        venc_str = str(_get_field(item, "Vencimento", "vencimento", default="")).strip()
        fin = _get_financeiro(item)

        if not venc_str or venc_str.lower() in ("", "nan", "none", "-"):
            no_maturity += fin
            continue

        # Try parsing date
        dt = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                dt = datetime.strptime(venc_str, fmt)
                break
            except ValueError:
                pass

        if dt is None:
            no_maturity += fin
            continue

        # Group by quarter
        quarter = (dt.month - 1) // 3 + 1
        period_key = f"{dt.year}-Q{quarter}"
        by_period[period_key] = by_period.get(period_key, 0) + fin

    result = []
    for period in sorted(by_period.keys()):
        val = by_period[period]
        year, q = period.split("-")
        labels = {"Q1": "Jan-Mar", "Q2": "Abr-Jun", "Q3": "Jul-Set", "Q4": "Out-Dez"}
        result.append({
            "periodo": period,
            "label": f"{labels.get(q, q)} {year}",
            "total_financeiro": round(val, 2),
            "pct": round(val / total * 100, 2),
        })

    if no_maturity > 0:
        result.append({
            "periodo": "SEM_VENC",
            "label": "Sem Vencimento (Fundos)",
            "total_financeiro": round(no_maturity, 2),
            "pct": round(no_maturity / total * 100, 2),
        })

    return result
