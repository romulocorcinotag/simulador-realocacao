"""
Cliente para a API brapi.dev - Dados de balancos e demonstracoes financeiras.

Endpoints utilizados:
  - /api/quote/{ticker}?modules=... -> Balanco Patrimonial, DRE, Fluxo de Caixa, DVA
  - /api/quote/list                 -> Lista de acoes disponiveis na B3

Documentacao: https://brapi.dev/docs
"""

import os
import time
import logging
from typing import Optional

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------
BRAPI_BASE_URL = "https://brapi.dev/api"
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN", "")

# Modulos disponiveis para demonstracoes financeiras
MODULES_FINANCIALS_ANNUAL = [
    "balanceSheetHistory",
    "incomeStatementHistory",
    "cashflowHistory",
    "valueAddedHistory",
    "defaultKeyStatistics",
    "financialData",
]

MODULES_FINANCIALS_QUARTERLY = [
    "balanceSheetHistoryQuarterly",
    "incomeStatementHistoryQuarterly",
    "cashflowHistoryQuarterly",
    "valueAddedHistoryQuarterly",
    "defaultKeyStatisticsHistoryQuarterly",
    "financialDataHistoryQuarterly",
]

MODULES_ALL = MODULES_FINANCIALS_ANNUAL + MODULES_FINANCIALS_QUARTERLY + ["summaryProfile"]


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------
class BrapiClient:
    """
    Cliente para a API brapi.dev.

    Uso basico:
        client = BrapiClient(token="SEU_TOKEN")
        df_bp = client.get_balance_sheet("PETR4", quarterly=True)
        df_dre = client.get_income_statement("PETR4")
        df_fc = client.get_cashflow("PETR4")
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or BRAPI_TOKEN
        self.base_url = BRAPI_BASE_URL
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self._rate_limit_wait = 0.5  # segundos entre requests (safety)

    # ------------------------------------------------------------------
    # Metodos internos
    # ------------------------------------------------------------------
    def _request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Faz GET request com tratamento de erros e rate limiting."""
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        # Fallback: token via query param se header nao estiver setado
        if not self.token:
            logger.warning("BRAPI_TOKEN nao configurado. Usando apenas tickers gratuitos (PETR4, VALE3, MGLU3, ITUB4).")

        time.sleep(self._rate_limit_wait)

        try:
            resp = self.session.get(url, params=params, timeout=30)

            if resp.status_code == 401:
                raise BrapiAuthError("Token invalido ou ausente. Configure BRAPI_TOKEN no .env")
            elif resp.status_code == 402:
                raise BrapiRateLimitError("Limite de requisicoes excedido. Aguarde ou upgrade o plano.")
            elif resp.status_code == 404:
                raise BrapiNotFoundError(f"Ticker ou endpoint nao encontrado: {endpoint}")

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            raise BrapiConnectionError("Timeout na conexao com brapi.dev")
        except requests.exceptions.ConnectionError:
            raise BrapiConnectionError("Erro de conexao com brapi.dev")

    def _get_quote_modules(self, ticker: str, modules: list[str]) -> dict:
        """Busca dados de um ticker com modulos especificos."""
        modules_str = ",".join(modules)
        data = self._request(f"/quote/{ticker}", params={"modules": modules_str})

        results = data.get("results", [])
        if not results:
            raise BrapiNotFoundError(f"Nenhum resultado para ticker: {ticker}")

        return results[0]

    def _module_to_dataframe(self, result: dict, module_key: str) -> pd.DataFrame:
        """Converte um modulo do resultado em DataFrame."""
        items = result.get(module_key, [])
        if not items:
            return pd.DataFrame()

        # Se for lista de dicts (historico)
        if isinstance(items, list):
            df = pd.DataFrame(items)
            if "endDate" in df.columns:
                df["endDate"] = pd.to_datetime(df["endDate"])
                df = df.sort_values("endDate", ascending=False).reset_index(drop=True)
            return df

        # Se for dict unico (dados TTM como financialData, defaultKeyStatistics)
        if isinstance(items, dict):
            return pd.DataFrame([items])

        return pd.DataFrame()

    # ------------------------------------------------------------------
    # API Publica - Dados Financeiros
    # ------------------------------------------------------------------
    def get_balance_sheet(self, ticker: str, quarterly: bool = False) -> pd.DataFrame:
        """
        Retorna o Balanco Patrimonial (BP) de uma empresa.

        Args:
            ticker: Codigo da acao (ex: "PETR4", "VALE3")
            quarterly: Se True, retorna dados trimestrais. Se False, anuais.

        Returns:
            DataFrame com colunas: endDate, type, cash, totalAssets, totalLiabilities,
            shareholdersEquity, longTermDebt, shortTermDebt, etc.
        """
        module = "balanceSheetHistoryQuarterly" if quarterly else "balanceSheetHistory"
        result = self._get_quote_modules(ticker, [module])
        df = self._module_to_dataframe(result, module)
        if not df.empty:
            df.insert(0, "ticker", ticker)
        return df

    def get_income_statement(self, ticker: str, quarterly: bool = False) -> pd.DataFrame:
        """
        Retorna a DRE (Demonstracao do Resultado do Exercicio).

        Args:
            ticker: Codigo da acao (ex: "PETR4")
            quarterly: Se True, retorna dados trimestrais.

        Returns:
            DataFrame com colunas: endDate, totalRevenue, grossProfit, operatingIncome,
            netIncome, ebit, cleanEbitda, earningsPerShare, etc.
        """
        module = "incomeStatementHistoryQuarterly" if quarterly else "incomeStatementHistory"
        result = self._get_quote_modules(ticker, [module])
        df = self._module_to_dataframe(result, module)
        if not df.empty:
            df.insert(0, "ticker", ticker)
        return df

    def get_cashflow(self, ticker: str, quarterly: bool = False) -> pd.DataFrame:
        """
        Retorna o Fluxo de Caixa.

        Args:
            ticker: Codigo da acao (ex: "PETR4")
            quarterly: Se True, retorna dados trimestrais.

        Returns:
            DataFrame com colunas: endDate, operatingCashFlow, investmentCashFlow,
            financingCashFlow, freeCashFlow, etc.
        """
        module = "cashflowHistoryQuarterly" if quarterly else "cashflowHistory"
        result = self._get_quote_modules(ticker, [module])
        df = self._module_to_dataframe(result, module)
        if not df.empty:
            df.insert(0, "ticker", ticker)
        return df

    def get_value_added(self, ticker: str, quarterly: bool = False) -> pd.DataFrame:
        """
        Retorna a DVA (Demonstracao do Valor Adicionado).
        """
        module = "valueAddedHistoryQuarterly" if quarterly else "valueAddedHistory"
        result = self._get_quote_modules(ticker, [module])
        df = self._module_to_dataframe(result, module)
        if not df.empty:
            df.insert(0, "ticker", ticker)
        return df

    def get_key_statistics(self, ticker: str) -> pd.DataFrame:
        """
        Retorna indicadores-chave TTM (P/L, P/VP, ROE, beta, etc).
        """
        result = self._get_quote_modules(ticker, ["defaultKeyStatistics"])
        df = self._module_to_dataframe(result, "defaultKeyStatistics")
        if not df.empty:
            df.insert(0, "ticker", ticker)
        return df

    def get_financial_data(self, ticker: str) -> pd.DataFrame:
        """
        Retorna dados financeiros TTM (EBITDA, receita, margens, target price, etc).
        Inclui target price e recomendacoes de analistas.
        """
        result = self._get_quote_modules(ticker, ["financialData"])
        df = self._module_to_dataframe(result, "financialData")
        if not df.empty:
            df.insert(0, "ticker", ticker)
        return df

    def get_company_profile(self, ticker: str) -> dict:
        """
        Retorna perfil da empresa (setor, industria, CNPJ, descricao, etc).
        """
        result = self._get_quote_modules(ticker, ["summaryProfile"])
        return result.get("summaryProfile", {})

    def get_all_financials(self, ticker: str, quarterly: bool = False) -> dict[str, pd.DataFrame]:
        """
        Retorna TODOS os dados financeiros de uma vez (otimiza requests).

        Args:
            ticker: Codigo da acao
            quarterly: Se True, retorna dados trimestrais

        Returns:
            Dict com chaves: 'balance_sheet', 'income_statement', 'cashflow',
            'value_added', 'key_statistics', 'financial_data', 'profile'
        """
        if quarterly:
            modules = MODULES_FINANCIALS_QUARTERLY + ["financialData", "defaultKeyStatistics", "summaryProfile"]
        else:
            modules = MODULES_FINANCIALS_ANNUAL + ["summaryProfile"]

        result = self._get_quote_modules(ticker, modules)

        # Monta o dict de DataFrames
        bp_key = "balanceSheetHistoryQuarterly" if quarterly else "balanceSheetHistory"
        dre_key = "incomeStatementHistoryQuarterly" if quarterly else "incomeStatementHistory"
        fc_key = "cashflowHistoryQuarterly" if quarterly else "cashflowHistory"
        dva_key = "valueAddedHistoryQuarterly" if quarterly else "valueAddedHistory"

        output = {}
        for key, label in [
            (bp_key, "balance_sheet"),
            (dre_key, "income_statement"),
            (fc_key, "cashflow"),
            (dva_key, "value_added"),
        ]:
            df = self._module_to_dataframe(result, key)
            if not df.empty:
                df.insert(0, "ticker", ticker)
            output[label] = df

        # Key statistics e financial data (TTM)
        for key, label in [
            ("defaultKeyStatistics", "key_statistics"),
            ("financialData", "financial_data"),
        ]:
            df = self._module_to_dataframe(result, key)
            if not df.empty:
                df.insert(0, "ticker", ticker)
            output[label] = df

        # Profile (dict, nao DataFrame)
        output["profile"] = result.get("summaryProfile", {})

        return output

    # ------------------------------------------------------------------
    # API Publica - Multiplos Tickers (batch)
    # ------------------------------------------------------------------
    def get_batch_financials(
        self,
        tickers: list[str],
        quarterly: bool = False,
        statement: str = "income_statement",
    ) -> pd.DataFrame:
        """
        Busca demonstracoes financeiras para multiplos tickers e concatena.

        Args:
            tickers: Lista de tickers (ex: ["PETR4", "VALE3", "ITUB4"])
            quarterly: Se True, retorna dados trimestrais
            statement: Tipo de demonstracao:
                - "balance_sheet"
                - "income_statement"
                - "cashflow"
                - "value_added"

        Returns:
            DataFrame concatenado com coluna 'ticker' identificando cada empresa.
        """
        method_map = {
            "balance_sheet": self.get_balance_sheet,
            "income_statement": self.get_income_statement,
            "cashflow": self.get_cashflow,
            "value_added": self.get_value_added,
        }

        if statement not in method_map:
            raise ValueError(f"statement deve ser um de: {list(method_map.keys())}")

        fetch_fn = method_map[statement]
        frames = []

        for ticker in tickers:
            try:
                df = fetch_fn(ticker, quarterly=quarterly)
                if not df.empty:
                    frames.append(df)
                logger.info(f"OK: {ticker} - {statement}")
            except BrapiError as e:
                logger.warning(f"Erro ao buscar {ticker}: {e}")
                continue

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # API Publica - Lista de Acoes
    # ------------------------------------------------------------------
    def list_stocks(
        self,
        sort_by: str = "volume",
        sort_order: str = "desc",
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Lista acoes disponiveis na B3.

        Args:
            sort_by: Campo para ordenacao (volume, close, change, market_cap_basic)
            sort_order: "asc" ou "desc"
            limit: Numero maximo de resultados

        Returns:
            DataFrame com acoes listadas na B3.
        """
        params = {
            "sortBy": sort_by,
            "sortOrder": sort_order,
            "limit": limit,
        }
        data = self._request("/quote/list", params=params)
        stocks = data.get("stocks", [])
        return pd.DataFrame(stocks)

    # ------------------------------------------------------------------
    # API Publica - Cotacoes
    # ------------------------------------------------------------------
    def get_quote(
        self,
        tickers: list[str],
        range_period: str = "1mo",
        interval: str = "1d",
        fundamental: bool = False,
        dividends: bool = False,
    ) -> dict:
        """
        Retorna cotacoes e dados de preco.

        Args:
            tickers: Lista de tickers
            range_period: Periodo (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            interval: Intervalo (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)
            fundamental: Incluir P/L e LPA
            dividends: Incluir historico de dividendos

        Returns:
            Dict com dados brutos da API.
        """
        tickers_str = ",".join(tickers)
        params = {
            "range": range_period,
            "interval": interval,
            "fundamental": str(fundamental).lower(),
            "dividends": str(dividends).lower(),
        }
        return self._request(f"/quote/{tickers_str}", params=params)


# ---------------------------------------------------------------------------
# Excecoes customizadas
# ---------------------------------------------------------------------------
class BrapiError(Exception):
    """Erro base da API brapi."""
    pass

class BrapiAuthError(BrapiError):
    """Erro de autenticacao (token invalido)."""
    pass

class BrapiRateLimitError(BrapiError):
    """Limite de requisicoes excedido."""
    pass

class BrapiNotFoundError(BrapiError):
    """Ticker ou recurso nao encontrado."""
    pass

class BrapiConnectionError(BrapiError):
    """Erro de conexao com a API."""
    pass


# ---------------------------------------------------------------------------
# Funcoes utilitarias (shortcuts)
# ---------------------------------------------------------------------------
def get_balance_sheet(ticker: str, quarterly: bool = False) -> pd.DataFrame:
    """Shortcut: retorna Balanco Patrimonial."""
    return BrapiClient().get_balance_sheet(ticker, quarterly)

def get_income_statement(ticker: str, quarterly: bool = False) -> pd.DataFrame:
    """Shortcut: retorna DRE."""
    return BrapiClient().get_income_statement(ticker, quarterly)

def get_cashflow(ticker: str, quarterly: bool = False) -> pd.DataFrame:
    """Shortcut: retorna Fluxo de Caixa."""
    return BrapiClient().get_cashflow(ticker, quarterly)

def get_all_financials(ticker: str, quarterly: bool = False) -> dict:
    """Shortcut: retorna todos os dados financeiros."""
    return BrapiClient().get_all_financials(ticker, quarterly)

def get_financial_data(ticker: str) -> pd.DataFrame:
    """Shortcut: retorna dados financeiros TTM (inclui target price de analistas)."""
    return BrapiClient().get_financial_data(ticker)
