"""
Modulo unificado de dados de balancos + estimativas de consenso.

Combina:
  - brapi.dev (balancos patrimoniais, DRE, fluxo de caixa)
  - yfinance (estimativas de consenso - gratuito)

Uso:
    from shared.earnings_data import EarningsDataService

    service = EarningsDataService()

    # Apenas balancos (brapi)
    df = service.get_latest_earnings("PETR4")

    # Balancos + estimativas (brapi + yfinance)
    report = service.get_full_report("PETR4")

    # Comparar realizado vs estimado
    df = service.get_actual_vs_estimate("PETR4")
"""

import logging
from typing import Optional
from datetime import datetime

import pandas as pd

from shared.brapi_client import BrapiClient, BrapiError
from shared.estimates_client import EstimatesClient

logger = logging.getLogger(__name__)


class EarningsDataService:
    """
    Servico unificado que combina dados de balancos (brapi) com
    estimativas de consenso (yfinance - gratuito).
    """

    def __init__(self, brapi_token: Optional[str] = None):
        """
        Args:
            brapi_token: Token da brapi.dev (ou usa BRAPI_TOKEN do .env)
        """
        self.brapi = BrapiClient(token=brapi_token)
        self.estimates = EstimatesClient()

    # ------------------------------------------------------------------
    # Metodos de alto nivel
    # ------------------------------------------------------------------
    def get_latest_earnings(self, ticker: str, quarterly: bool = True) -> dict:
        """
        Retorna os dados mais recentes do balanco de uma empresa.

        Args:
            ticker: Codigo B3 (ex: "PETR4")
            quarterly: Se True, retorna trimestral; se False, anual

        Returns:
            Dict com:
              - 'income_statement': DataFrame da DRE
              - 'balance_sheet': DataFrame do BP
              - 'cashflow': DataFrame do FC
              - 'key_metrics': DataFrame com indicadores-chave
              - 'meta': dict com ticker, periodo, data
        """
        try:
            all_data = self.brapi.get_all_financials(ticker, quarterly=quarterly)

            # Pega apenas o periodo mais recente de cada demonstracao
            latest = {}
            for key in ["income_statement", "balance_sheet", "cashflow", "value_added"]:
                df = all_data.get(key, pd.DataFrame())
                if not df.empty:
                    latest[key] = df.head(1)
                else:
                    latest[key] = pd.DataFrame()

            latest["key_statistics"] = all_data.get("key_statistics", pd.DataFrame())
            latest["financial_data"] = all_data.get("financial_data", pd.DataFrame())
            latest["profile"] = all_data.get("profile", {})

            # Meta info
            dre = all_data.get("income_statement", pd.DataFrame())
            end_date = None
            if not dre.empty and "endDate" in dre.columns:
                end_date = dre["endDate"].iloc[0]

            latest["meta"] = {
                "ticker": ticker,
                "period_type": "quarterly" if quarterly else "annual",
                "latest_period": str(end_date) if end_date else "N/A",
                "fetched_at": datetime.now().isoformat(),
            }

            return latest

        except BrapiError as e:
            logger.error(f"Erro ao buscar balancos de {ticker}: {e}")
            raise

    def get_consensus_estimates(self, ticker: str) -> dict:
        """
        Retorna estimativas de consenso (yfinance - gratuito).

        Args:
            ticker: Codigo B3 (ex: "PETR4")

        Returns:
            Dict com todas as estimativas disponiveis.
        """
        return self.estimates.get_full_estimates(ticker)

    def get_full_report(self, ticker: str, quarterly: bool = True) -> dict:
        """
        Retorna relatorio completo: balancos + estimativas de consenso.

        Args:
            ticker: Codigo B3 (ex: "PETR4")
            quarterly: Se True, balancos trimestrais

        Returns:
            Dict com:
              - 'earnings': dados do balanco (brapi)
              - 'estimates': estimativas de consenso (yfinance)
              - 'analyst_info': target price e recomendacoes
              - 'meta': metadados
        """
        report = {
            "ticker": ticker,
            "fetched_at": datetime.now().isoformat(),
        }

        # 1. Balancos (brapi)
        try:
            report["earnings"] = self.get_latest_earnings(ticker, quarterly)
        except BrapiError as e:
            logger.error(f"Erro brapi para {ticker}: {e}")
            report["earnings"] = None

        # 2. Estimativas (yfinance - gratuito)
        try:
            report["estimates"] = self.estimates.get_full_estimates(ticker)
        except Exception as e:
            logger.warning(f"Erro ao buscar estimativas de {ticker}: {e}")
            report["estimates"] = None

        return report

    def get_actual_vs_estimate(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Retorna historico de resultados: EPS real vs estimado.
        Usa yfinance earnings_history (gratuito).
        """
        return self.estimates.get_earnings_history(ticker)

    # ------------------------------------------------------------------
    # Batch (multiplos tickers)
    # ------------------------------------------------------------------
    def get_batch_reports(self, tickers: list[str], quarterly: bool = True) -> dict[str, dict]:
        """Gera relatorios completos para multiplos tickers."""
        reports = {}
        for ticker in tickers:
            try:
                reports[ticker] = self.get_full_report(ticker, quarterly)
                logger.info(f"OK: {ticker}")
            except Exception as e:
                logger.warning(f"Erro no relatorio de {ticker}: {e}")
                reports[ticker] = {"error": str(e)}
        return reports

    def get_batch_income_statements(self, tickers: list[str], quarterly: bool = True) -> pd.DataFrame:
        """Retorna DREs concatenadas para multiplos tickers."""
        return self.brapi.get_batch_financials(tickers, quarterly=quarterly, statement="income_statement")

    # ------------------------------------------------------------------
    # Utilidades para Streamlit
    # ------------------------------------------------------------------
    def format_earnings_for_display(self, ticker: str, quarterly: bool = True) -> dict:
        """Formata dados de balanco para exibicao no Streamlit."""
        data = self.get_latest_earnings(ticker, quarterly)

        display = {
            "ticker": ticker,
            "period": data["meta"]["latest_period"],
            "metrics": {},
            "tables": {},
        }

        dre = data.get("income_statement", pd.DataFrame())
        if not dre.empty:
            row = dre.iloc[0]
            display["metrics"]["Receita Liquida"] = _fmt_brl(row.get("totalRevenue"))
            display["metrics"]["Lucro Bruto"] = _fmt_brl(row.get("grossProfit"))
            display["metrics"]["EBITDA"] = _fmt_brl(row.get("cleanEbitda"))
            display["metrics"]["Lucro Liquido"] = _fmt_brl(row.get("netIncome"))
            display["metrics"]["LPA"] = _fmt_number(row.get("earningsPerShare"))

        fin = data.get("financial_data", pd.DataFrame())
        if not fin.empty:
            row = fin.iloc[0]
            display["metrics"]["Margem Bruta"] = _fmt_pct(row.get("grossMargins"))
            display["metrics"]["Margem EBITDA"] = _fmt_pct(row.get("ebitdaMargins"))
            display["metrics"]["Margem Liquida"] = _fmt_pct(row.get("profitMargins"))
            display["metrics"]["ROE"] = _fmt_pct(row.get("returnOnEquity"))

        for key in ["income_statement", "balance_sheet", "cashflow"]:
            df = data.get(key, pd.DataFrame())
            if not df.empty:
                display["tables"][key] = df

        return display


# ---------------------------------------------------------------------------
# Funcoes auxiliares de formatacao
# ---------------------------------------------------------------------------
def _fmt_brl(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    try:
        v = float(value)
        if abs(v) >= 1e9:
            return f"R$ {v/1e9:,.1f}B"
        elif abs(v) >= 1e6:
            return f"R$ {v/1e6:,.1f}M"
        elif abs(v) >= 1e3:
            return f"R$ {v/1e3:,.1f}K"
        else:
            return f"R$ {v:,.2f}"
    except (ValueError, TypeError):
        return "N/D"

def _fmt_pct(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    try:
        return f"{float(value)*100:.1f}%"
    except (ValueError, TypeError):
        return "N/D"

def _fmt_number(value) -> str:
    if value is None or pd.isna(value):
        return "N/D"
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return "N/D"


# ---------------------------------------------------------------------------
# Shortcuts
# ---------------------------------------------------------------------------
def get_earnings(ticker: str, quarterly: bool = True) -> dict:
    """Shortcut: retorna balancos mais recentes via brapi."""
    return EarningsDataService().get_latest_earnings(ticker, quarterly)

def get_full_report(ticker: str) -> dict:
    """Shortcut: retorna relatorio completo (brapi + yfinance)."""
    return EarningsDataService().get_full_report(ticker)

def get_batch_dre(tickers: list[str], quarterly: bool = True) -> pd.DataFrame:
    """Shortcut: retorna DREs concatenadas para multiplos tickers."""
    return EarningsDataService().get_batch_income_statements(tickers, quarterly)
