"""
Backtest engine for TAG Investimentos proposal system.
Calculates historical performance of portfolios across multiple time windows.
Uses CDI (BCB API), yfinance for ETFs/stocks, and proxy mappings for private assets.
"""
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

from shared.brand import TAG, PLOTLY_LAYOUT

warnings.filterwarnings("ignore", category=FutureWarning)


def _base_layout(*exclude_keys):
    """Return PLOTLY_LAYOUT without specified keys to avoid duplicate kwargs."""
    return {k: v for k, v in PLOTLY_LAYOUT.items() if k not in exclude_keys}

# ── Constants ──
WINDOWS_MONTHS = [6, 12, 24, 36, 60]
WINDOW_LABELS = {6: "6 Meses", 12: "1 Ano", 24: "2 Anos", 36: "3 Anos", 60: "5 Anos"}
BIZ_DAYS_YEAR = 252


# ── Data Fetching ──

def _cache_data(func):
    """Apply st.cache_data if streamlit is available."""
    if HAS_STREAMLIT:
        return st.cache_data(ttl=3600, show_spinner=False)(func)
    return func


@_cache_data
def fetch_cdi_daily(start_date_str, end_date_str):
    """Fetch daily CDI rates from BCB API (series 12 = CDI daily rate in %).
    Returns Series of daily CDI factors (1 + r_daily) indexed by date.
    """
    import requests

    # Series 12 = CDI daily rate (e.g., 0.0519 = 0.0519% per day)
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados"
        f"?formato=json&dataInicial={start_date_str}&dataFinal={end_date_str}"
    )
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return _synthetic_cdi(start_date_str, end_date_str)

    if not data:
        return _synthetic_cdi(start_date_str, end_date_str)

    df = pd.DataFrame(data)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce") / 100  # convert from % to decimal
    df = df.set_index("data").sort_index()
    df = df.dropna(subset=["valor"])

    # Sanity check: daily CDI should be small (< 0.1% per day = 0.001)
    # If values look like annualized rates (> 0.01), convert
    median_val = df["valor"].median()
    if median_val > 0.01:
        # Values are annualized rates, convert to daily
        df["factor"] = (1 + df["valor"]) ** (1 / 252)
    else:
        df["factor"] = 1 + df["valor"]

    return df["factor"]


def _synthetic_cdi(start_str, end_str):
    """Generate synthetic CDI series as fallback."""
    start = pd.to_datetime(start_str, dayfirst=True)
    end = pd.to_datetime(end_str, dayfirst=True)
    dates = pd.bdate_range(start, end)
    daily_rate = (1.1325) ** (1 / 252) - 1  # ~13.25% a.a.
    return pd.Series(1 + daily_rate, index=dates, name="factor")


@_cache_data
def fetch_benchmark_data(ticker, start_date_str, end_date_str):
    """Fetch price data from yfinance. Returns daily returns Series."""
    if not HAS_YFINANCE:
        return pd.Series(dtype=float)

    start = pd.to_datetime(start_date_str, dayfirst=True)
    end = pd.to_datetime(end_date_str, dayfirst=True)

    try:
        data = yf.download(
            ticker, start=start - timedelta(days=5), end=end + timedelta(days=1),
            progress=False, auto_adjust=True,
        )
        if data.empty:
            return pd.Series(dtype=float)

        # Handle MultiIndex columns from yfinance
        if isinstance(data.columns, pd.MultiIndex):
            close = data[("Close", ticker)] if ("Close", ticker) in data.columns else data["Close"].iloc[:, 0]
        else:
            close = data["Close"]

        returns = close.pct_change().dropna()
        returns.index = returns.index.tz_localize(None)
        return returns
    except Exception:
        return pd.Series(dtype=float)


# ── Proxy Mapping ──

# Category -> proxy type mapping
CATEGORY_PROXY = {
    "Caixa": {"type": "cdi", "factor": 1.0},
    "Renda Fixa Pos": {"type": "cdi", "factor": 1.02},
    "Renda Fixa CDI+": {"type": "cdi", "factor": 1.05},
    "Multimercados": {"type": "cdi", "factor": 1.20},
    "Alternativos": {"type": "cdi", "factor": 1.50},
    "Previdencia": {"type": "cdi", "factor": 1.02},
    "Renda Fixa Pre": {"type": "ticker", "ticker": "IRFM11.SA", "fallback_cdi": 1.10},
    "Renda Fixa Inflacao": {"type": "ticker", "ticker": "B5P211.SA", "fallback_cdi": 1.08},
    "Fundos Listados Isentos": {"type": "ticker", "ticker": "XFIX11.SA", "fallback_cdi": 1.05},
    "Renda Variavel": {"type": "ticker", "ticker": "BOVA11.SA", "fallback_cdi": 0.90},
    "Cambial": {"type": "ticker", "ticker": "USDBRL=X", "fallback_cdi": 1.0},
}

# Normalize category names (handle accented chars)
_CATEGORY_NORMALIZE = {
    "caixa": "Caixa",
    "renda fixa pos": "Renda Fixa Pos",
    "renda fixa p\u00f3s": "Renda Fixa Pos",
    "renda fixa cdi+": "Renda Fixa CDI+",
    "renda fixa pre": "Renda Fixa Pre",
    "renda fixa pr\u00e9": "Renda Fixa Pre",
    "renda fixa inflacao": "Renda Fixa Inflacao",
    "renda fixa infla\u00e7\u00e3o": "Renda Fixa Inflacao",
    "multimercados": "Multimercados",
    "multimercado": "Multimercados",
    "renda variavel": "Renda Variavel",
    "renda vari\u00e1vel": "Renda Variavel",
    "alternativos": "Alternativos",
    "fundos listados isentos": "Fundos Listados Isentos",
    "previdencia": "Previdencia",
    "previd\u00eancia": "Previdencia",
    "cambial": "Cambial",
    "rf cambial": "Cambial",
    "local caixa": "Caixa",
    "local renda fixa pos": "Renda Fixa Pos",
    "local renda fixa p\u00f3s": "Renda Fixa Pos",
    "local renda fixa cdi+": "Renda Fixa CDI+",
    "local renda fixa pre": "Renda Fixa Pre",
    "local renda fixa pr\u00e9": "Renda Fixa Pre",
    "local renda fixa inflacao": "Renda Fixa Inflacao",
    "local renda fixa infla\u00e7\u00e3o": "Renda Fixa Inflacao",
    "local renda variavel": "Renda Variavel",
    "local renda vari\u00e1vel": "Renda Variavel",
    "local multimercado": "Multimercados",
    "local alternativos": "Alternativos",
    "local hedges": "Alternativos",
    "rf fundos listados isentos": "Fundos Listados Isentos",
}


def _normalize_category(cat):
    """Normalize category name for proxy lookup."""
    if not cat:
        return "Caixa"
    key = str(cat).strip().lower()
    return _CATEGORY_NORMALIZE.get(key, "Caixa")


def map_asset_to_proxy(asset_name, categoria, taxa=None):
    """Map an asset to its return proxy."""
    cat = _normalize_category(categoria)
    proxy = CATEGORY_PROXY.get(cat, {"type": "cdi", "factor": 1.0})

    # Check if asset is a known ticker (ETF/stock)
    known_tickers = {
        "B5P211": "B5P211.SA", "IRFM11": "IRFM11.SA", "BOVA11": "BOVA11.SA",
        "SPXR11": "SPXR11.SA", "RURA11": "RURA11.SA", "KNIP11": "KNIP11.SA",
        "XFIX11": "XFIX11.SA", "KDIF11": "KDIF11.SA", "ALZC11": "ALZC11.SA",
        "BIT11": "BIT11.SA", "IDKA11": "IDKA11.SA",
    }
    if asset_name:
        name_upper = str(asset_name).upper()
        for code, ticker in known_tickers.items():
            if code in name_upper:
                return {"type": "ticker", "ticker": ticker, "fallback_cdi": 1.0}

    # Parse taxa for CDI+spread or IPCA+spread
    if taxa:
        taxa_str = str(taxa).upper()
        if "CDI" in taxa_str:
            # Extract CDI factor (e.g., "100,50% CDI" -> 1.005, "CDI + 1,50%" -> CDI * 1.015)
            if "+" in taxa_str:
                try:
                    spread = float(taxa_str.split("+")[1].replace("%", "").replace(",", ".").strip()) / 100
                    return {"type": "cdi", "factor": 1.0 + spread * 8}  # rough annual spread proxy
                except (ValueError, IndexError):
                    pass
            else:
                try:
                    pct = float(taxa_str.replace("CDI", "").replace("%", "").replace(",", ".").strip()) / 100
                    if pct > 0:
                        return {"type": "cdi", "factor": pct}
                except ValueError:
                    pass

        if "IPCA" in taxa_str:
            return {"type": "ticker", "ticker": "B5P211.SA", "fallback_cdi": 1.08}

    return proxy


# ── Backtest Calculation ──

def _build_return_series(proxy, cdi_factors, start_date, end_date):
    """Build a daily return series for a given proxy."""
    start_str = start_date.strftime("%d/%m/%Y")
    end_str = end_date.strftime("%d/%m/%Y")

    if proxy["type"] == "cdi":
        factor = proxy.get("factor", 1.0)
        if cdi_factors is not None and not cdi_factors.empty:
            # CDI factor adjusted: daily_cdi * factor
            adjusted = (cdi_factors - 1) * factor + 1
            return adjusted
        # Fallback
        daily = (1.1325 ** (factor / 252)) - 1
        dates = pd.bdate_range(start_date, end_date)
        return pd.Series(1 + daily, index=dates)

    elif proxy["type"] == "ticker":
        returns = fetch_benchmark_data(proxy["ticker"], start_str, end_str)
        if returns is not None and not returns.empty:
            return 1 + returns  # convert to factor

        # Fallback to CDI with adjustment
        fallback = proxy.get("fallback_cdi", 1.0)
        if cdi_factors is not None and not cdi_factors.empty:
            adjusted = (cdi_factors - 1) * fallback + 1
            return adjusted
        daily = (1.1325 ** (fallback / 252)) - 1
        dates = pd.bdate_range(start_date, end_date)
        return pd.Series(1 + daily, index=dates)

    return pd.Series(dtype=float)


def calculate_portfolio_backtest(portfolio, windows=None):
    """Main backtest function.

    portfolio: list of dicts with keys like:
        - ativo (name), pct_alvo or pct_atual or % Alvo (weight as %)
        - categoria (asset class), taxa (rate)
    windows: list of months, default [6, 12, 24, 36, 60]

    Returns dict with metrics per window.
    """
    if windows is None:
        windows = WINDOWS_MONTHS

    if not portfolio:
        return {"error": "Empty portfolio", "windows": {}}

    end_date = datetime.now()
    max_months = max(windows)
    start_date = end_date - timedelta(days=max_months * 31)

    # Fetch CDI for full period
    start_str = start_date.strftime("%d/%m/%Y")
    end_str = end_date.strftime("%d/%m/%Y")
    cdi_factors = fetch_cdi_daily(start_str, end_str)

    # Build return series for each asset
    asset_series = {}
    weights = {}

    for item in portfolio:
        name = item.get("ativo", item.get("Ativo", "Unknown"))
        cat = item.get("categoria", item.get("Categoria", item.get("classe", "")))
        taxa = item.get("taxa", item.get("Taxa", ""))
        weight = float(
            item.get("pct_alvo", item.get("pct_atual", item.get("% Alvo",
            item.get("proposta_pct", item.get("Proposta %", 0))))) or 0
        )

        if weight <= 0:
            continue

        proxy = map_asset_to_proxy(name, cat, taxa)
        series = _build_return_series(proxy, cdi_factors, start_date, end_date)

        if series is not None and not series.empty:
            asset_series[name] = series
            weights[name] = weight / 100.0  # convert from % to decimal

    if not asset_series:
        return {"error": "No return data available", "windows": {}}

    # Normalize weights
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: v / total_w for k, v in weights.items()}

    # Align all series to common dates
    all_dates = None
    for s in asset_series.values():
        if all_dates is None:
            all_dates = s.index
        else:
            all_dates = all_dates.intersection(s.index)

    if all_dates is None or len(all_dates) < 10:
        return {"error": "Insufficient data for backtest", "windows": {}}

    all_dates = all_dates.sort_values()

    # Build portfolio daily factors
    portfolio_factors = pd.Series(0.0, index=all_dates)
    for name, series in asset_series.items():
        w = weights.get(name, 0)
        aligned = series.reindex(all_dates).fillna(1.0)
        portfolio_factors += aligned * w

    # CDI benchmark
    cdi_aligned = cdi_factors.reindex(all_dates).fillna(1.0) if cdi_factors is not None else pd.Series(1.0, index=all_dates)

    # IBOV benchmark
    ibov_returns = fetch_benchmark_data("^BVSP", start_str, end_str)
    if ibov_returns is not None and not ibov_returns.empty:
        ibov_factors = (1 + ibov_returns).reindex(all_dates).fillna(1.0)
    else:
        ibov_factors = pd.Series(1.0, index=all_dates)

    # IHFA benchmark (ANBIMA Hedge Fund Index) - proxy as CDI * 1.20
    # IHFA historically delivers ~CDI + 2-3% p.a., so daily factor ≈ CDI_daily * 1.20
    ihfa_factors = ((cdi_aligned - 1) * 1.20 + 1) if cdi_aligned is not None else pd.Series(1.0, index=all_dates)

    # Calculate metrics per window
    result = {"windows": {}, "portfolio_cumulative": None, "cdi_cumulative": None}

    for w_months in windows:
        w_days = int(w_months * 21)  # approx business days per month
        label = WINDOW_LABELS.get(w_months, f"{w_months}m")

        if len(all_dates) < w_days:
            w_days = len(all_dates)

        window_dates = all_dates[-w_days:]
        pf = portfolio_factors.loc[window_dates]
        cdi_w = cdi_aligned.loc[window_dates]
        ibov_w = ibov_factors.loc[window_dates]
        ihfa_w = ihfa_factors.loc[window_dates]

        # Cumulative returns
        cum_portfolio = pf.cumprod()
        cum_cdi = cdi_w.cumprod()
        cum_ibov = ibov_w.cumprod()
        cum_ihfa = ihfa_w.cumprod()

        total_ret = float(cum_portfolio.iloc[-1] - 1)
        cdi_ret = float(cum_cdi.iloc[-1] - 1)
        ibov_ret = float(cum_ibov.iloc[-1] - 1)
        ihfa_ret = float(cum_ihfa.iloc[-1] - 1)

        # Annualize
        years = w_days / BIZ_DAYS_YEAR
        ann_ret = (1 + total_ret) ** (1 / max(years, 0.1)) - 1 if total_ret > -1 else 0
        ann_cdi = (1 + cdi_ret) ** (1 / max(years, 0.1)) - 1 if cdi_ret > -1 else 0

        # Daily log returns for vol/sharpe
        daily_returns = pf - 1  # daily returns
        vol = float(daily_returns.std() * np.sqrt(BIZ_DAYS_YEAR))

        # Sharpe vs CDI
        daily_cdi_ret = cdi_w - 1
        excess = daily_returns - daily_cdi_ret
        sharpe = float(excess.mean() / excess.std() * np.sqrt(BIZ_DAYS_YEAR)) if excess.std() > 0 else 0

        # Max drawdown
        cum_max = cum_portfolio.cummax()
        drawdown = (cum_portfolio - cum_max) / cum_max
        max_dd = float(drawdown.min())

        # Alpha vs CDI
        alpha = total_ret - cdi_ret

        result["windows"][label] = {
            "months": w_months,
            "total_return": total_ret,
            "annualized_return": ann_ret,
            "volatility": vol,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "cdi_return": cdi_ret,
            "ibov_return": ibov_ret,
            "ihfa_return": ihfa_ret,
            "alpha_cdi": alpha,
            "alpha_ibov": total_ret - ibov_ret,
            "alpha_ihfa": total_ret - ihfa_ret,
            "cumulative": cum_portfolio,
            "cumulative_cdi": cum_cdi,
            "cumulative_ibov": cum_ibov,
            "cumulative_ihfa": cum_ihfa,
        }

    # Store longest window cumulative for charts
    longest = max(windows)
    longest_label = WINDOW_LABELS.get(longest, f"{longest}m")
    if longest_label in result["windows"]:
        result["portfolio_cumulative"] = result["windows"][longest_label]["cumulative"]
        result["cdi_cumulative"] = result["windows"][longest_label]["cumulative_cdi"]

    return result


def compare_portfolios_backtest(current_portfolio, proposed_portfolio, windows=None):
    """Compare two portfolios (current vs proposed).
    Returns dict with metrics for both + difference.
    """
    bt_current = calculate_portfolio_backtest(current_portfolio, windows)
    bt_proposed = calculate_portfolio_backtest(proposed_portfolio, windows)

    comparison = {
        "current": bt_current,
        "proposed": bt_proposed,
        "diff": {},
    }

    # Calculate differences per window
    for label in bt_proposed.get("windows", {}):
        if label in bt_current.get("windows", {}):
            curr = bt_current["windows"][label]
            prop = bt_proposed["windows"][label]
            comparison["diff"][label] = {
                "return_diff": prop["total_return"] - curr["total_return"],
                "vol_diff": prop["volatility"] - curr["volatility"],
                "sharpe_diff": prop["sharpe"] - curr["sharpe"],
                "dd_diff": prop["max_drawdown"] - curr["max_drawdown"],
            }

    return comparison


# ── Chart Generation ──

def chart_backtest_cumulative(backtest_result, title="Performance Acumulada"):
    """Create cumulative return chart for multiple windows."""
    fig = go.Figure()

    # Use the longest window
    windows = backtest_result.get("windows", {})
    if not windows:
        return _empty_chart("Sem dados de backtest")

    # Get longest window
    longest_label = max(windows.keys(), key=lambda k: windows[k]["months"])
    w = windows[longest_label]

    cum = w.get("cumulative")
    cum_cdi = w.get("cumulative_cdi")
    cum_ibov = w.get("cumulative_ibov")

    if cum is not None and not cum.empty:
        fig.add_trace(go.Scatter(
            x=cum.index, y=(cum - 1) * 100,
            mode="lines", name="Carteira",
            line=dict(color=TAG["laranja"], width=3),
        ))

    if cum_cdi is not None and not cum_cdi.empty:
        fig.add_trace(go.Scatter(
            x=cum_cdi.index, y=(cum_cdi - 1) * 100,
            mode="lines", name="CDI",
            line=dict(color=TAG["offwhite"], width=2, dash="dot"),
        ))

    if cum_ibov is not None and not cum_ibov.empty:
        ibov_vals = (cum_ibov - 1) * 100
        if ibov_vals.abs().sum() > 0:
            fig.add_trace(go.Scatter(
                x=cum_ibov.index, y=ibov_vals,
                mode="lines", name="IBOV",
                line=dict(color=TAG["chart"][2], width=2, dash="dash"),
            ))

    cum_ihfa = w.get("cumulative_ihfa")
    if cum_ihfa is not None and not cum_ihfa.empty:
        ihfa_vals = (cum_ihfa - 1) * 100
        if ihfa_vals.abs().sum() > 0:
            fig.add_trace(go.Scatter(
                x=cum_ihfa.index, y=ihfa_vals,
                mode="lines", name="IHFA",
                line=dict(color=TAG["verde"], width=2, dash="dashdot"),
            ))

    fig.update_layout(
        **_base_layout("legend"),
        height=400,
        title=dict(text=title, font=dict(color=TAG["offwhite"], size=14)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="Retorno (%)",
    )
    fig.add_hline(y=0, line_dash="dash", line_color=TAG["text_muted"], line_width=0.5)
    return fig


def chart_backtest_comparison(comparison, title="Comparativo: Atual vs Proposta"):
    """Create comparison chart for current vs proposed portfolio."""
    fig = go.Figure()

    curr = comparison.get("current", {}).get("windows", {})
    prop = comparison.get("proposed", {}).get("windows", {})

    if not curr and not prop:
        return _empty_chart("Sem dados para comparacao")

    # Use longest window
    all_labels = set(list(curr.keys()) + list(prop.keys()))
    longest = max(all_labels, key=lambda k: curr.get(k, prop.get(k, {})).get("months", 0))

    # Get benchmark data from whichever portfolio has it (prefer proposed)
    ref_data = prop.get(longest, {}) or curr.get(longest, {})
    curr_cum = curr.get(longest, {}).get("cumulative")
    prop_cum = prop.get(longest, {}).get("cumulative")
    cdi_cum = ref_data.get("cumulative_cdi")
    ibov_cum = ref_data.get("cumulative_ibov")
    ihfa_cum = ref_data.get("cumulative_ihfa")

    if curr_cum is not None and not curr_cum.empty:
        fig.add_trace(go.Scatter(
            x=curr_cum.index, y=(curr_cum - 1) * 100,
            mode="lines", name="Carteira Atual",
            line=dict(color=TAG["chart"][4], width=2),
            fill="tozeroy", fillcolor="rgba(160,82,45,0.1)",
        ))

    if prop_cum is not None and not prop_cum.empty:
        fig.add_trace(go.Scatter(
            x=prop_cum.index, y=(prop_cum - 1) * 100,
            mode="lines", name="Proposta TAG",
            line=dict(color=TAG["laranja"], width=3),
        ))

    if cdi_cum is not None and not cdi_cum.empty:
        fig.add_trace(go.Scatter(
            x=cdi_cum.index, y=(cdi_cum - 1) * 100,
            mode="lines", name="CDI",
            line=dict(color=TAG["offwhite"], width=1.5, dash="dot"),
        ))

    if ibov_cum is not None and not ibov_cum.empty:
        ibov_vals = (ibov_cum - 1) * 100
        if ibov_vals.abs().sum() > 0:
            fig.add_trace(go.Scatter(
                x=ibov_cum.index, y=ibov_vals,
                mode="lines", name="IBOV",
                line=dict(color=TAG["chart"][2], width=1.5, dash="dash"),
            ))

    if ihfa_cum is not None and not ihfa_cum.empty:
        ihfa_vals = (ihfa_cum - 1) * 100
        if ihfa_vals.abs().sum() > 0:
            fig.add_trace(go.Scatter(
                x=ihfa_cum.index, y=ihfa_vals,
                mode="lines", name="IHFA",
                line=dict(color=TAG["verde"], width=1.5, dash="dashdot"),
            ))

    fig.update_layout(
        **_base_layout("legend"),
        height=400,
        title=dict(text=title, font=dict(color=TAG["offwhite"], size=14)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="Retorno (%)",
    )
    fig.add_hline(y=0, line_dash="dash", line_color=TAG["text_muted"], line_width=0.5)
    return fig


def chart_backtest_metrics_table(backtest_result, title="Metricas por Janela"):
    """Create a metrics comparison table as a Plotly table figure."""
    windows = backtest_result.get("windows", {})
    if not windows:
        return _empty_chart("Sem dados")

    # Sort windows by months
    sorted_windows = sorted(windows.items(), key=lambda x: x[1]["months"])

    headers = ["Janela", "Retorno", "CDI", "IBOV", "IHFA", "Vol", "Sharpe", "Max DD", "vs CDI", "vs IBOV", "vs IHFA"]
    cells = [[] for _ in headers]

    for label, w in sorted_windows:
        cells[0].append(label)
        cells[1].append(f"{w['total_return']*100:.1f}%")
        cells[2].append(f"{w.get('cdi_return', 0)*100:.1f}%")
        cells[3].append(f"{w.get('ibov_return', 0)*100:.1f}%")
        cells[4].append(f"{w.get('ihfa_return', 0)*100:.1f}%")
        cells[5].append(f"{w['volatility']*100:.1f}%")
        cells[6].append(f"{w['sharpe']:.2f}")
        cells[7].append(f"{w['max_drawdown']*100:.1f}%")
        cells[8].append(f"{w['alpha_cdi']*100:+.1f}%")
        cells[9].append(f"{w.get('alpha_ibov', 0)*100:+.1f}%")
        cells[10].append(f"{w.get('alpha_ihfa', 0)*100:+.1f}%")

    fig = go.Figure(go.Table(
        header=dict(
            values=headers,
            fill_color=TAG["vermelho_dark"],
            font=dict(color=TAG["laranja"], size=12),
            align="center",
            height=35,
        ),
        cells=dict(
            values=cells,
            fill_color=TAG["bg_card"],
            font=dict(color=TAG["offwhite"], size=11),
            align="center",
            height=30,
        ),
    ))

    fig.update_layout(
        **_base_layout("margin"),
        height=35 + 30 * len(sorted_windows) + 50,
        title=dict(text=title, font=dict(color=TAG["offwhite"], size=14)),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def chart_risk_return_scatter(comparison, title="Risco x Retorno"):
    """Create risk/return scatter plot comparing current vs proposed + benchmarks."""
    fig = go.Figure()

    # Get reference data for benchmark metrics
    ref_bt = comparison.get("proposed", comparison.get("current", {}))
    ref_windows = ref_bt.get("windows", {})

    for key, name, color, symbol in [
        ("current", "Carteira Atual", TAG["chart"][4], "circle"),
        ("proposed", "Proposta TAG", TAG["laranja"], "star"),
    ]:
        bt = comparison.get(key, {})
        windows = bt.get("windows", {})
        if not windows:
            continue

        longest = max(windows.keys(), key=lambda k: windows[k]["months"])
        w = windows[longest]

        fig.add_trace(go.Scatter(
            x=[w["volatility"] * 100],
            y=[w["annualized_return"] * 100],
            mode="markers+text",
            name=name,
            marker=dict(color=color, size=18, symbol=symbol, line=dict(width=2, color=TAG["offwhite"])),
            text=[name],
            textposition="top center",
            textfont=dict(color=color, size=11),
        ))

    # Add benchmark points (CDI, IHFA) - positioned by their return
    if ref_windows:
        longest = max(ref_windows.keys(), key=lambda k: ref_windows[k]["months"])
        w = ref_windows[longest]
        years = w["months"] / 12

        # CDI point (near-zero vol)
        cdi_ann = (1 + w.get("cdi_return", 0)) ** (1 / max(years, 0.1)) - 1 if w.get("cdi_return", 0) > -1 else 0
        fig.add_trace(go.Scatter(
            x=[0.3], y=[cdi_ann * 100],
            mode="markers+text", name="CDI",
            marker=dict(color=TAG["offwhite"], size=12, symbol="diamond",
                       line=dict(width=1, color=TAG["text_muted"])),
            text=["CDI"], textposition="middle right",
            textfont=dict(color=TAG["offwhite"], size=10),
        ))

        # IHFA point (low vol, ~CDI+2-3%)
        ihfa_ann = (1 + w.get("ihfa_return", 0)) ** (1 / max(years, 0.1)) - 1 if w.get("ihfa_return", 0) > -1 else 0
        fig.add_trace(go.Scatter(
            x=[2.5], y=[ihfa_ann * 100],
            mode="markers+text", name="IHFA",
            marker=dict(color=TAG["verde"], size=12, symbol="diamond",
                       line=dict(width=1, color=TAG["text_muted"])),
            text=["IHFA"], textposition="middle right",
            textfont=dict(color=TAG["verde"], size=10),
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=380,
        title=dict(text=title, font=dict(color=TAG["offwhite"], size=14)),
        xaxis_title="Volatilidade Anual (%)",
        yaxis_title="Retorno Anualizado (%)",
    )
    return fig


def chart_drawdown(backtest_result, title="Max Drawdown"):
    """Create drawdown chart."""
    windows = backtest_result.get("windows", {})
    if not windows:
        return _empty_chart("Sem dados")

    longest = max(windows.keys(), key=lambda k: windows[k]["months"])
    w = windows[longest]
    cum = w.get("cumulative")

    if cum is None or cum.empty:
        return _empty_chart("Sem dados de drawdown")

    cum_max = cum.cummax()
    dd = ((cum - cum_max) / cum_max) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        mode="lines",
        fill="tozeroy",
        fillcolor=f"rgba(99,13,36,0.3)",
        line=dict(color=TAG["vermelho"], width=1.5),
        name="Drawdown",
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=250,
        title=dict(text=title, font=dict(color=TAG["offwhite"], size=14)),
        yaxis_title="Drawdown (%)",
        showlegend=False,
    )
    return fig


def _empty_chart(message):
    """Return an empty chart with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(color=TAG["text_muted"], size=14),
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=200)
    return fig


# ── HTML Export Helpers ──

def backtest_metrics_to_html(backtest_result):
    """Generate HTML table for backtest metrics (for proposal export)."""
    windows = backtest_result.get("windows", {})
    if not windows:
        return "<p>Sem dados de backtest disponiveis.</p>"

    sorted_windows = sorted(windows.items(), key=lambda x: x[1]["months"])

    th_style = f"padding:10px; color:{TAG['laranja']}; text-align:center;"
    html = f"""
    <table style="width:100%; border-collapse:collapse; margin:16px 0;">
        <thead>
            <tr style="background:{TAG['vermelho_dark']};">
                <th style="{th_style}">Janela</th>
                <th style="{th_style}">Retorno</th>
                <th style="{th_style}">CDI</th>
                <th style="{th_style}">IBOV</th>
                <th style="{th_style}">IHFA</th>
                <th style="{th_style}">Vol</th>
                <th style="{th_style}">Sharpe</th>
                <th style="{th_style}">Max DD</th>
                <th style="{th_style}">vs CDI</th>
                <th style="{th_style}">vs IBOV</th>
                <th style="{th_style}">vs IHFA</th>
            </tr>
        </thead>
        <tbody>
    """

    td_style = "padding:8px; text-align:center;"
    for label, w in sorted_windows:
        alpha_cdi_color = TAG["verde"] if w["alpha_cdi"] >= 0 else TAG["rosa"]
        alpha_ibov_color = TAG["verde"] if w.get("alpha_ibov", 0) >= 0 else TAG["rosa"]
        alpha_ihfa_color = TAG["verde"] if w.get("alpha_ihfa", 0) >= 0 else TAG["rosa"]
        html += f"""
            <tr style="border-bottom:1px solid {TAG['vermelho']}15;">
                <td style="{td_style} font-weight:500;">{label}</td>
                <td style="{td_style} font-weight:600;">{w['total_return']*100:.1f}%</td>
                <td style="{td_style} color:{TAG['text_muted']};">{w.get('cdi_return', 0)*100:.1f}%</td>
                <td style="{td_style} color:{TAG['text_muted']};">{w.get('ibov_return', 0)*100:.1f}%</td>
                <td style="{td_style} color:{TAG['text_muted']};">{w.get('ihfa_return', 0)*100:.1f}%</td>
                <td style="{td_style}">{w['volatility']*100:.1f}%</td>
                <td style="{td_style}">{w['sharpe']:.2f}</td>
                <td style="{td_style} color:{TAG['rosa']};">{w['max_drawdown']*100:.1f}%</td>
                <td style="{td_style} color:{alpha_cdi_color};">{w['alpha_cdi']*100:+.1f}%</td>
                <td style="{td_style} color:{alpha_ibov_color};">{w.get('alpha_ibov', 0)*100:+.1f}%</td>
                <td style="{td_style} color:{alpha_ihfa_color};">{w.get('alpha_ihfa', 0)*100:+.1f}%</td>
            </tr>
        """

    html += "</tbody></table>"
    return html
