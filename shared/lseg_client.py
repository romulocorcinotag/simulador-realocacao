"""
Cliente para a LSEG Refinitiv Data Platform (RDP) API - Estimativas de Consenso I/B/E/S.

Suporta dois modos de operacao:
  1. Via biblioteca `lseg-data` (recomendado se tiver Eikon/Workspace)
  2. Via REST API direta com `requests` (funciona sem desktop app)

Documentacao:
  - https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/refinitiv-data-platform-apis
  - https://developers.lseg.com/en/api-catalog/lseg-data-platform/lseg-data-library-for-python

Requer licenca LSEG/Refinitiv com scope: trapi.data.est.sum
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
LSEG_BASE_URL = "https://api.refinitiv.com"
LSEG_USERNAME = os.getenv("LSEG_USERNAME", "")
LSEG_PASSWORD = os.getenv("LSEG_PASSWORD", "")
LSEG_APP_KEY = os.getenv("LSEG_APP_KEY", "")

# Para autenticacao V2 (Service Account / Client Credentials)
LSEG_CLIENT_ID = os.getenv("LSEG_CLIENT_ID", "")
LSEG_CLIENT_SECRET = os.getenv("LSEG_CLIENT_SECRET", "")

# Sufixo para RICs brasileiros
B3_RIC_SUFFIX = ".SA"

# Campos TR. mais utilizados para estimativas
DEFAULT_ESTIMATE_FIELDS = [
    # EPS
    "TR.EPSMean",
    "TR.EPSMedian",
    "TR.EPSHigh",
    "TR.EPSLow",
    "TR.EPSNumIncEstimates",
    "TR.EpsSmartEst",
    "TR.EPSActValue",
    "TR.EPSActSurprise",
    # Receita
    "TR.RevenueMean",
    "TR.RevenueHigh",
    "TR.RevenueLow",
    # EBITDA
    "TR.EBITDAMean",
    # EBIT
    "TR.EBITMean",
    # Lucro Liquido
    "TR.NetProfitMean",
    # DPS (Dividendo por acao)
    "TR.DPSMean",
    # Recomendacoes
    "TR.NumOfStrongBuys",
    "TR.NumOfBuys",
    "TR.NumOfHolds",
    "TR.NumOfSells",
    "TR.NumOfStrongSells",
    "TR.ConsRecom",
]


# ---------------------------------------------------------------------------
# Classe principal - REST API (sem dependencia de lseg-data)
# ---------------------------------------------------------------------------
class LSEGRestClient:
    """
    Cliente REST para a LSEG RDP API.
    Funciona sem a biblioteca lseg-data, usando apenas requests.

    Uso:
        client = LSEGRestClient(username="...", password="...", app_key="...")
        client.authenticate()
        df = client.get_estimates_summary("PETR4", period="annual")
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        app_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        auth_version: str = "v1",
    ):
        self.username = username or LSEG_USERNAME
        self.password = password or LSEG_PASSWORD
        self.app_key = app_key or LSEG_APP_KEY
        self.client_id = client_id or LSEG_CLIENT_ID
        self.client_secret = client_secret or LSEG_CLIENT_SECRET
        self.auth_version = auth_version
        self.base_url = LSEG_BASE_URL

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: float = 0

        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Autenticacao
    # ------------------------------------------------------------------
    def authenticate(self) -> None:
        """
        Autentica na RDP API.
        Usa V2 (client_credentials) se client_id/secret estiverem configurados,
        senao usa V1 (password grant).
        """
        if self.client_id and self.client_secret:
            self._auth_v2()
        elif self.username and self.password and self.app_key:
            self._auth_v1()
        else:
            raise LSEGAuthError(
                "Credenciais LSEG nao configuradas. Configure no .env:\n"
                "  Opcao 1 (V1): LSEG_USERNAME, LSEG_PASSWORD, LSEG_APP_KEY\n"
                "  Opcao 2 (V2): LSEG_CLIENT_ID, LSEG_CLIENT_SECRET"
            )

    def _auth_v1(self) -> None:
        """Autenticacao V1 - Password Grant."""
        url = f"{self.base_url}/auth/oauth2/v1/token"
        payload = {
            "username": self.username,
            "password": self.password,
            "client_id": self.app_key,
            "grant_type": "password",
            "scope": "trapi",
            "takeExclusiveSignOnControl": "true",
        }

        resp = requests.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if resp.status_code != 200:
            raise LSEGAuthError(f"Falha na autenticacao V1: {resp.status_code} - {resp.text}")

        tokens = resp.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens.get("refresh_token")
        self.token_expiry = time.time() + tokens.get("expires_in", 3600) - 60
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

        logger.info("Autenticacao LSEG V1 realizada com sucesso.")

    def _auth_v2(self) -> None:
        """Autenticacao V2 - Client Credentials Grant."""
        url = f"{self.base_url}/auth/oauth2/v2/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        resp = requests.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if resp.status_code != 200:
            raise LSEGAuthError(f"Falha na autenticacao V2: {resp.status_code} - {resp.text}")

        tokens = resp.json()
        self.access_token = tokens["access_token"]
        self.token_expiry = time.time() + tokens.get("expires_in", 3600) - 60
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

        logger.info("Autenticacao LSEG V2 realizada com sucesso.")

    def _refresh_if_needed(self) -> None:
        """Renova o token se estiver proximo da expiracao."""
        if time.time() < self.token_expiry:
            return

        if self.auth_version == "v2" or (self.client_id and self.client_secret):
            self._auth_v2()
            return

        if not self.refresh_token:
            self._auth_v1()
            return

        url = f"{self.base_url}/auth/oauth2/v1/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.app_key,
            "refresh_token": self.refresh_token,
        }

        resp = requests.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning("Refresh token falhou. Re-autenticando...")
            self._auth_v1()
            return

        tokens = resp.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens.get("refresh_token", self.refresh_token)
        self.token_expiry = time.time() + tokens.get("expires_in", 3600) - 60
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def to_ric(ticker: str) -> str:
        """Converte ticker B3 para RIC Refinitiv (ex: PETR4 -> PETR4.SA)."""
        ticker = ticker.upper().strip()
        if not ticker.endswith(B3_RIC_SUFFIX):
            return f"{ticker}{B3_RIC_SUFFIX}"
        return ticker

    def _parse_tabular_response(self, data: dict) -> pd.DataFrame:
        """Converte resposta tabular da RDP API em DataFrame."""
        headers = [h["name"] for h in data.get("headers", [])]
        rows = data.get("data", [])

        if not headers or not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows, columns=headers)

    # ------------------------------------------------------------------
    # Endpoints de Estimativas
    # ------------------------------------------------------------------
    def get_estimates_summary(
        self,
        ticker: str,
        period: str = "annual",
    ) -> pd.DataFrame:
        """
        Retorna o consenso de estimativas (summary) de uma empresa.

        Args:
            ticker: Codigo B3 (ex: "PETR4") ou RIC (ex: "PETR4.SA")
            period: "annual" ou "interim" (trimestral)

        Returns:
            DataFrame com estimativas de consenso (EPS, Revenue, EBITDA, etc)
        """
        self._refresh_if_needed()
        ric = self.to_ric(ticker)

        endpoint = f"/data/estimates/v1/view-summary/{period}"
        resp = self.session.get(
            f"{self.base_url}{endpoint}",
            params={"universe": ric},
            timeout=30,
        )

        if resp.status_code == 403:
            raise LSEGPermissionError(
                "Sem permissao para acessar estimativas. "
                "Verifique se sua licenca inclui o scope 'trapi.data.est.sum'."
            )
        elif resp.status_code != 200:
            raise LSEGApiError(f"Erro na API: {resp.status_code} - {resp.text}")

        df = self._parse_tabular_response(resp.json())
        if not df.empty:
            df.insert(0, "ticker", ticker.upper())
        return df

    def get_estimates_actuals(
        self,
        ticker: str,
        period: str = "annual",
    ) -> pd.DataFrame:
        """
        Retorna os valores realizados (actuals) reportados.
        Util para calcular surpresa vs consenso.

        Args:
            ticker: Codigo B3 ou RIC
            period: "annual" ou "interim"
        """
        self._refresh_if_needed()
        ric = self.to_ric(ticker)

        endpoint = f"/data/estimates/v1/view-actuals/{period}"
        resp = self.session.get(
            f"{self.base_url}{endpoint}",
            params={"universe": ric},
            timeout=30,
        )

        if resp.status_code != 200:
            raise LSEGApiError(f"Erro na API: {resp.status_code} - {resp.text}")

        df = self._parse_tabular_response(resp.json())
        if not df.empty:
            df.insert(0, "ticker", ticker.upper())
        return df

    def get_recommendations(self, ticker: str) -> pd.DataFrame:
        """
        Retorna o resumo de recomendacoes de analistas.

        Returns:
            DataFrame com contagem de Strong Buy, Buy, Hold, Sell, Strong Sell.
        """
        self._refresh_if_needed()
        ric = self.to_ric(ticker)

        endpoint = "/data/estimates/v1/view-summary/recommendations"
        resp = self.session.get(
            f"{self.base_url}{endpoint}",
            params={"universe": ric},
            timeout=30,
        )

        if resp.status_code != 200:
            raise LSEGApiError(f"Erro na API: {resp.status_code} - {resp.text}")

        df = self._parse_tabular_response(resp.json())
        if not df.empty:
            df.insert(0, "ticker", ticker.upper())
        return df

    def get_kpi_estimates(
        self,
        ticker: str,
        period: str = "annual",
    ) -> pd.DataFrame:
        """
        Retorna estimativas de KPIs (metricas operacionais especificas do setor).
        """
        self._refresh_if_needed()
        ric = self.to_ric(ticker)

        endpoint = f"/data/estimates/v1/view-summary/kpi/{period}"
        resp = self.session.get(
            f"{self.base_url}{endpoint}",
            params={"universe": ric},
            timeout=30,
        )

        if resp.status_code != 200:
            raise LSEGApiError(f"Erro na API: {resp.status_code} - {resp.text}")

        df = self._parse_tabular_response(resp.json())
        if not df.empty:
            df.insert(0, "ticker", ticker.upper())
        return df

    def get_batch_estimates(
        self,
        tickers: list[str],
        period: str = "annual",
    ) -> pd.DataFrame:
        """
        Busca estimativas de consenso para multiplos tickers.

        Args:
            tickers: Lista de codigos B3 (ex: ["PETR4", "VALE3", "ITUB4"])
            period: "annual" ou "interim"
        """
        frames = []
        for ticker in tickers:
            try:
                df = self.get_estimates_summary(ticker, period)
                if not df.empty:
                    frames.append(df)
                logger.info(f"OK: {ticker} - estimates {period}")
            except LSEGError as e:
                logger.warning(f"Erro ao buscar estimativas de {ticker}: {e}")
                continue

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Classe com lseg-data library (para quem tem Eikon/Workspace)
# ---------------------------------------------------------------------------
class LSEGLibraryClient:
    """
    Cliente usando a biblioteca oficial lseg-data.
    Requer Eikon/Workspace rodando localmente OU credenciais LDP.

    Uso:
        client = LSEGLibraryClient()
        client.open_session()
        df = client.get_consensus_estimates(["PETR4", "VALE3"])
        client.close_session()
    """

    def __init__(self):
        self._ld = None
        self._session_open = False

    def open_session(self, session_type: str = "platform.ldp") -> None:
        """
        Abre sessao com a LSEG.

        Args:
            session_type: "platform.ldp" (cloud) ou "desktop.workspace" (local)
        """
        try:
            import lseg.data as ld
            self._ld = ld
            ld.open_session(session_type)
            self._session_open = True
            logger.info(f"Sessao LSEG aberta: {session_type}")
        except ImportError:
            raise LSEGLibraryError(
                "Biblioteca lseg-data nao instalada. Execute: pip install lseg-data\n"
                "Ou use LSEGRestClient para acesso via REST API."
            )
        except Exception as e:
            raise LSEGAuthError(f"Erro ao abrir sessao LSEG: {e}")

    def close_session(self) -> None:
        """Fecha a sessao."""
        if self._ld and self._session_open:
            self._ld.close_session()
            self._session_open = False

    def get_consensus_estimates(
        self,
        tickers: list[str],
        fields: Optional[list[str]] = None,
        period: str = "FY1",
        currency: str = "BRL",
    ) -> pd.DataFrame:
        """
        Busca estimativas de consenso usando campos TR.

        Args:
            tickers: Lista de tickers B3 (ex: ["PETR4", "VALE3"])
            fields: Lista de campos TR. (usa DEFAULT_ESTIMATE_FIELDS se None)
            period: Periodo fiscal (FY0, FY1, FY2, FQ0, FQ1, etc)
            currency: Moeda (BRL, USD)

        Returns:
            DataFrame com estimativas de consenso.
        """
        if not self._session_open:
            raise LSEGError("Sessao nao aberta. Execute open_session() primeiro.")

        rics = [LSEGRestClient.to_ric(t) for t in tickers]
        fields = fields or DEFAULT_ESTIMATE_FIELDS

        # Adiciona o periodo aos campos
        fields_with_period = [f"{f}(Period={period})" for f in fields]

        df = self._ld.get_data(
            universe=rics,
            fields=fields_with_period,
            parameters={"Curn": currency},
        )

        return df

    def get_historical_consensus(
        self,
        ticker: str,
        fields: Optional[list[str]] = None,
        start_date: str = "2020-01-01",
        periods_back: int = 5,
        period: str = "FY1",
        currency: str = "BRL",
    ) -> pd.DataFrame:
        """
        Busca historico de estimativas de consenso (point-in-time).

        Args:
            ticker: Ticker B3
            fields: Campos TR. (default: EPS, Revenue, EBITDA means)
            start_date: Data de inicio (YYYY-MM-DD)
            periods_back: Numero de periodos para tras
            period: Periodo fiscal
            currency: Moeda
        """
        if not self._session_open:
            raise LSEGError("Sessao nao aberta. Execute open_session() primeiro.")

        ric = LSEGRestClient.to_ric(ticker)
        fields = fields or ["TR.EPSMean", "TR.RevenueMean", "TR.EBITDAMean"]

        df = self._ld.get_data(
            universe=ric,
            fields=fields + ["TR.EPSMean.periodenddate"],
            parameters={
                "SDate": start_date,
                "EDate": f"-{periods_back}",
                "Period": period,
                "Frq": "FY",
                "Curn": currency,
            },
        )

        return df


# ---------------------------------------------------------------------------
# Excecoes customizadas
# ---------------------------------------------------------------------------
class LSEGError(Exception):
    """Erro base da LSEG API."""
    pass

class LSEGAuthError(LSEGError):
    """Erro de autenticacao."""
    pass

class LSEGPermissionError(LSEGError):
    """Sem permissao para acessar recurso."""
    pass

class LSEGApiError(LSEGError):
    """Erro generico da API."""
    pass

class LSEGLibraryError(LSEGError):
    """Erro relacionado a biblioteca lseg-data."""
    pass
