"""
Cliente GRATUITO para estimativas de consenso de analistas.

Usa yfinance (ja instalado) para obter:
  - EPS estimates (atual e proximo trimestre/ano)
  - Revenue estimates
  - Earnings history (actual vs estimate, surpresas)
  - Target prices e recomendacoes
  - Upgrades/downgrades recentes

Opcionalmente usa Finnhub (free tier, 60 calls/min) para dados adicionais.

Nenhuma licenca paga necessaria.
"""

import os
import logging
from typing import Optional

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Finnhub (opcional - free tier: 60 calls/min)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


# ---------------------------------------------------------------------------
# Classe principal - yfinance (100% gratuito)
# ---------------------------------------------------------------------------
class EstimatesClient:
    """
    Cliente de estimativas de consenso usando yfinance (gratuito).

    Uso:
        client = EstimatesClient()
        df_eps = client.get_eps_estimates("PETR4")
        df_rev = client.get_revenue_estimates("PETR4")
        df_hist = client.get_earnings_history("PETR4")
        info = client.get_analyst_info("PETR4")
    """

    @staticmethod
    def _to_yf_ticker(ticker: str) -> str:
        """Converte ticker B3 para formato Yahoo Finance (ex: PETR4 -> PETR4.SA)."""
        ticker = ticker.upper().strip()
        if not ticker.endswith(".SA"):
            return f"{ticker}.SA"
        return ticker

    @staticmethod
    def _safe_get_df(yf_ticker, attr: str) -> pd.DataFrame:
        """Tenta obter um atributo do yfinance que retorna DataFrame."""
        try:
            data = getattr(yf_ticker, attr, None)
            if data is not None and isinstance(data, pd.DataFrame) and not data.empty:
                return data
        except Exception as e:
            logger.warning(f"Erro ao obter {attr}: {e}")
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # EPS Estimates
    # ------------------------------------------------------------------
    def get_eps_estimates(self, ticker: str) -> pd.DataFrame:
        """
        Retorna estimativas de EPS (Lucro por Acao).

        Colunas tipicas:
          - numberofAnalysts, avg, low, high, yearAgoEps, growth
        Indices: Current Qtr, Next Qtr, Current Year, Next Year

        Returns:
            DataFrame com estimativas de EPS por periodo.
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "eps_trend")

        # Fallback: tenta earnings_estimate
        if df.empty:
            df = self._safe_get_df(yf_ticker, "earnings_estimate")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())

        return df

    # ------------------------------------------------------------------
    # Revenue Estimates
    # ------------------------------------------------------------------
    def get_revenue_estimates(self, ticker: str) -> pd.DataFrame:
        """
        Retorna estimativas de Receita.

        Colunas tipicas:
          - numberOfAnalysts, avg, low, high, yearAgoRevenue, growth

        Returns:
            DataFrame com estimativas de receita por periodo.
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "revenue_estimate")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())

        return df

    # ------------------------------------------------------------------
    # Earnings History (Actual vs Estimate - Surpresas)
    # ------------------------------------------------------------------
    def get_earnings_history(self, ticker: str) -> pd.DataFrame:
        """
        Retorna historico de resultados: EPS real vs estimado.
        Ideal para calcular surpresas de earnings.

        Colunas tipicas:
          - epsEstimate, epsActual, epsDifference, surprisePercent

        Returns:
            DataFrame com historico de surpresas.
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "earnings_history")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())

        return df

    # ------------------------------------------------------------------
    # EPS Trend & Revisions
    # ------------------------------------------------------------------
    def get_eps_trend(self, ticker: str) -> pd.DataFrame:
        """
        Retorna tendencia de revisoes de EPS.

        Mostra como o consenso evoluiu nos ultimos 7/30/90 dias.
        Colunas: current, 7daysAgo, 30daysAgo, 60daysAgo, 90daysAgo

        Returns:
            DataFrame com evolucao do consenso de EPS.
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "eps_trend")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())

        return df

    def get_eps_revisions(self, ticker: str) -> pd.DataFrame:
        """
        Retorna revisoes de estimativas de EPS.

        Mostra quantos analistas revisaram para cima/baixo.
        Colunas: upLast7days, upLast30days, downLast7days, downLast30days
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "eps_revisions")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())

        return df

    # ------------------------------------------------------------------
    # Growth Estimates
    # ------------------------------------------------------------------
    def get_growth_estimates(self, ticker: str) -> pd.DataFrame:
        """
        Retorna estimativas de crescimento.

        Linhas: Stock, Industry, Sector, S&P 500
        Colunas: Current Qtr, Next Qtr, Current Year, Next Year, Next 5Y, Past 5Y
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "growth_estimates")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())

        return df

    # ------------------------------------------------------------------
    # Analyst Info (Target Price + Recomendacoes)
    # ------------------------------------------------------------------
    def get_analyst_info(self, ticker: str) -> dict:
        """
        Retorna informacoes consolidadas de analistas:
          - Target prices (high, low, mean, median)
          - Recomendacao (buy, hold, sell, etc)
          - Numero de analistas

        Returns:
            Dict com dados de analistas.
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))

        try:
            info = yf_ticker.info or {}
        except Exception:
            info = {}

        return {
            "ticker": ticker.upper(),
            "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
            "targetHighPrice": info.get("targetHighPrice"),
            "targetLowPrice": info.get("targetLowPrice"),
            "targetMeanPrice": info.get("targetMeanPrice"),
            "targetMedianPrice": info.get("targetMedianPrice"),
            "recommendationKey": info.get("recommendationKey"),
            "recommendationMean": info.get("recommendationMean"),
            "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
            # Dados adicionais uteis
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "trailingEps": info.get("trailingEps"),
            "forwardEps": info.get("forwardEps"),
            "pegRatio": info.get("pegRatio"),
            "dividendYield": info.get("dividendYield"),
            "marketCap": info.get("marketCap"),
            "enterpriseValue": info.get("enterpriseValue"),
        }

    # ------------------------------------------------------------------
    # Recommendations History
    # ------------------------------------------------------------------
    def get_recommendations(self, ticker: str) -> pd.DataFrame:
        """
        Retorna historico de recomendacoes de analistas.

        Colunas: period, strongBuy, buy, hold, sell, strongSell
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "recommendations")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())

        return df

    # ------------------------------------------------------------------
    # Upgrades/Downgrades recentes
    # ------------------------------------------------------------------
    def get_upgrades_downgrades(self, ticker: str) -> pd.DataFrame:
        """
        Retorna upgrades/downgrades recentes de analistas.

        Colunas: Firm, ToGrade, FromGrade, Action
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        df = self._safe_get_df(yf_ticker, "upgrades_downgrades")

        if not df.empty:
            df.insert(0, "ticker", ticker.upper())
            # Limita aos ultimos 20
            df = df.head(20)

        return df

    # ------------------------------------------------------------------
    # Earnings Calendar (proximas datas de resultados)
    # ------------------------------------------------------------------
    def get_earnings_dates(self, ticker: str) -> pd.DataFrame:
        """
        Retorna proximas datas de divulgacao de resultados.
        """
        yf_ticker = yf.Ticker(self._to_yf_ticker(ticker))
        try:
            df = yf_ticker.get_earnings_dates(limit=8)
            if df is not None and not df.empty:
                df.insert(0, "ticker", ticker.upper())
                return df
        except Exception as e:
            logger.warning(f"Erro ao obter earnings dates de {ticker}: {e}")

        return pd.DataFrame()

    # ------------------------------------------------------------------
    # Relatorio completo de estimativas
    # ------------------------------------------------------------------
    def get_full_estimates(self, ticker: str) -> dict:
        """
        Retorna TODAS as estimativas disponiveis para um ticker.

        Returns:
            Dict com todas as tabelas de estimativas:
              - eps_estimates, revenue_estimates, earnings_history,
              - eps_trend, eps_revisions, growth_estimates,
              - analyst_info, recommendations, upgrades_downgrades,
              - earnings_dates
        """
        result = {
            "ticker": ticker.upper(),
            "eps_estimates": self.get_eps_estimates(ticker),
            "revenue_estimates": self.get_revenue_estimates(ticker),
            "earnings_history": self.get_earnings_history(ticker),
            "eps_trend": self.get_eps_trend(ticker),
            "eps_revisions": self.get_eps_revisions(ticker),
            "growth_estimates": self.get_growth_estimates(ticker),
            "analyst_info": self.get_analyst_info(ticker),
            "recommendations": self.get_recommendations(ticker),
            "upgrades_downgrades": self.get_upgrades_downgrades(ticker),
            "earnings_dates": self.get_earnings_dates(ticker),
        }

        return result

    # ------------------------------------------------------------------
    # Batch (multiplos tickers)
    # ------------------------------------------------------------------
    def get_batch_analyst_info(self, tickers: list[str]) -> pd.DataFrame:
        """
        Retorna info de analistas para multiplos tickers.

        Returns:
            DataFrame com uma linha por ticker.
        """
        rows = []
        for ticker in tickers:
            try:
                info = self.get_analyst_info(ticker)
                rows.append(info)
            except Exception as e:
                logger.warning(f"Erro ao buscar info de {ticker}: {e}")
                continue

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Cliente Finnhub (opcional - requer API key gratuita)
# ---------------------------------------------------------------------------
class FinnhubEstimates:
    """
    Cliente opcional para Finnhub (free tier: 60 calls/min).
    Requer cadastro em https://finnhub.io (gratuito).

    Fornece dados adicionais como:
      - EPS surprises detalhados
      - Estimativas por analista individual
      - Earnings calendar

    Uso:
        client = FinnhubEstimates(api_key="seu_key")
        df = client.get_eps_surprises("PETR4")
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or FINNHUB_API_KEY
        self.base_url = "https://finnhub.io/api/v1"

        if not self.api_key:
            logger.info(
                "Finnhub API key nao configurada. "
                "Cadastre-se gratis em https://finnhub.io e configure FINNHUB_API_KEY no .env"
            )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _to_finnhub_symbol(self, ticker: str) -> str:
        """Converte ticker B3 para Finnhub (ex: PETR4 -> PETR4.SA)."""
        ticker = ticker.upper().strip()
        if not ticker.endswith(".SA"):
            return f"{ticker}.SA"
        return ticker

    def _request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Faz request para Finnhub API."""
        import requests

        if not self.api_key:
            raise FinnhubError("Finnhub API key nao configurada.")

        params = params or {}
        params["token"] = self.api_key

        resp = requests.get(
            f"{self.base_url}{endpoint}",
            params=params,
            timeout=15,
        )

        if resp.status_code == 401:
            raise FinnhubError("Finnhub API key invalida.")
        elif resp.status_code == 429:
            raise FinnhubError("Rate limit Finnhub excedido (max 60/min no plano gratuito).")

        resp.raise_for_status()
        return resp.json()

    def get_eps_surprises(self, ticker: str) -> pd.DataFrame:
        """
        Retorna historico de surpresas de EPS.

        Returns:
            DataFrame com colunas: actual, estimate, surprise, surprisePercent, period, symbol
        """
        symbol = self._to_finnhub_symbol(ticker)
        data = self._request("/stock/earnings", params={"symbol": symbol})

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df.insert(0, "ticker", ticker.upper())
        return df

    def get_earnings_calendar(
        self,
        from_date: str = "",
        to_date: str = "",
    ) -> pd.DataFrame:
        """
        Retorna calendario de earnings (todas as empresas).

        Args:
            from_date: Data inicio (YYYY-MM-DD)
            to_date: Data fim (YYYY-MM-DD)
        """
        params = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        data = self._request("/calendar/earnings", params=params)
        earnings = data.get("earningsCalendar", [])

        if not earnings:
            return pd.DataFrame()

        return pd.DataFrame(earnings)

    def get_recommendation_trends(self, ticker: str) -> pd.DataFrame:
        """
        Retorna tendencia de recomendacoes ao longo do tempo.

        Returns:
            DataFrame com colunas: buy, hold, sell, strongBuy, strongSell, period
        """
        symbol = self._to_finnhub_symbol(ticker)
        data = self._request("/stock/recommendation", params={"symbol": symbol})

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df.insert(0, "ticker", ticker.upper())
        return df

    def get_price_target(self, ticker: str) -> dict:
        """
        Retorna consenso de target price.

        Returns:
            Dict com targetHigh, targetLow, targetMean, targetMedian
        """
        symbol = self._to_finnhub_symbol(ticker)
        return self._request("/stock/price-target", params={"symbol": symbol})


class FinnhubError(Exception):
    pass


# ---------------------------------------------------------------------------
# Shortcuts
# ---------------------------------------------------------------------------
def get_estimates(ticker: str) -> dict:
    """Shortcut: retorna todas as estimativas (yfinance) para um ticker."""
    return EstimatesClient().get_full_estimates(ticker)

def get_analyst_info(ticker: str) -> dict:
    """Shortcut: retorna info de analistas (target price, recomendacao)."""
    return EstimatesClient().get_analyst_info(ticker)

def get_earnings_history(ticker: str) -> pd.DataFrame:
    """Shortcut: retorna historico de actual vs estimate."""
    return EstimatesClient().get_earnings_history(ticker)
