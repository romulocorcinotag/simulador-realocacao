import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

st.set_page_config(page_title="Ativos vs Commodities", layout="wide")
st.title("Comparativo: Ativos vs Commodities")

# ---------------------------------------------------------------------------
# Botões de período para o range selector do Plotly
# ---------------------------------------------------------------------------
RANGE_BUTTONS = [
    dict(count=1, label="1M", step="month", stepmode="backward"),
    dict(count=3, label="3M", step="month", stepmode="backward"),
    dict(count=6, label="6M", step="month", stepmode="backward"),
    dict(count=1, label="YTD", step="year", stepmode="todate"),
    dict(count=1, label="1A", step="year", stepmode="backward"),
    dict(count=2, label="2A", step="year", stepmode="backward"),
    dict(count=5, label="5A", step="year", stepmode="backward"),
    dict(step="all", label="MAX"),
]

# ---------------------------------------------------------------------------
# Funções de carregamento de dados
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def load_yf(ticker: str, period: str = "10y") -> pd.Series:
    """Baixa série de fechamento via Yahoo Finance."""
    df = yf.download(ticker, period=period, progress=False)
    if df.empty:
        return pd.Series(dtype=float)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.dropna()


@st.cache_data(ttl=3600, show_spinner=False)
def load_iron_ore_dalian() -> pd.Series:
    """Tenta carregar minério de ferro (Dalian) via akshare."""
    try:
        import akshare as ak
        df = ak.futures_zh_daily_sina(symbol="I0")
        df.columns = [c.lower().strip() for c in df.columns]
        date_col = "date" if "date" in df.columns else df.columns[0]
        close_col = "close" if "close" in df.columns else df.columns[4]
        df[date_col] = pd.to_datetime(df[date_col])
        s = df.set_index(date_col)[close_col].astype(float).sort_index()
        s.index = s.index.tz_localize(None)
        return s.dropna()
    except ImportError:
        return pd.Series(dtype=float)
    except Exception:
        return pd.Series(dtype=float)


# ---------------------------------------------------------------------------
# Função para montar gráfico com dois eixos Y
# ---------------------------------------------------------------------------

def make_chart(
    s1: pd.Series, name1: str, color1: str, unit1: str,
    s2: pd.Series, name2: str, color2: str, unit2: str,
    title: str,
    normalize: bool = False,
):
    if normalize:
        s1 = (s1 / s1.iloc[0]) * 100
        s2 = (s2 / s2.iloc[0]) * 100
        unit1 = f"{name1} (base 100)"
        unit2 = f"{name2} (base 100)"

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=s1.index, y=s1.values, name=name1,
            line=dict(color=color1, width=2),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=s2.index, y=s2.values, name=name2,
            line=dict(color=color2, width=2),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        height=540,
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        xaxis=dict(
            rangeselector=dict(buttons=RANGE_BUTTONS),
            rangeslider=dict(visible=True),
            type="date",
        ),
        margin=dict(t=60, b=20),
    )

    fig.update_yaxes(title_text=unit1, secondary_y=False, color=color1)
    fig.update_yaxes(title_text=unit2, secondary_y=True, color=color2)
    return fig


# ---------------------------------------------------------------------------
# Carregamento dos dados
# ---------------------------------------------------------------------------

with st.spinner("Carregando dados de mercado..."):
    petr4 = load_yf("PETR4.SA")
    brent = load_yf("BZ=F")
    vale3 = load_yf("VALE3.SA")
    iron_ore = load_iron_ore_dalian()

# ---------------------------------------------------------------------------
# Opção de normalização
# ---------------------------------------------------------------------------

normalize = st.checkbox(
    "Normalizar séries (base 100 no início dos dados carregados)",
    value=False,
)

# ---------------------------------------------------------------------------
# Gráfico 1 — PETR4 vs Petróleo Brent
# ---------------------------------------------------------------------------

st.subheader("PETR4 vs Petróleo Brent")

if not petr4.empty and not brent.empty:
    fig1 = make_chart(
        petr4, "PETR4", "#2E7D32", "PETR4 (BRL)",
        brent, "Petróleo Brent", "#212121", "Brent (USD/bbl)",
        "PETR4 vs Petróleo Brent",
        normalize=normalize,
    )
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.error("Não foi possível carregar dados de PETR4 ou Brent.")

# ---------------------------------------------------------------------------
# Gráfico 2 — VALE3 vs Minério de Ferro (Dalian)
# ---------------------------------------------------------------------------

st.subheader("VALE3 vs Minério de Ferro (Dalian)")

if not vale3.empty and not iron_ore.empty:
    fig2 = make_chart(
        vale3, "VALE3", "#1565C0", "VALE3 (BRL)",
        iron_ore, "Minério de Ferro (Dalian)", "#E65100", "Minério (CNY/ton)",
        "VALE3 vs Minério de Ferro (Dalian)",
        normalize=normalize,
    )
    st.plotly_chart(fig2, use_container_width=True)

elif not vale3.empty:
    st.warning(
        "Dados de minério de ferro (Dalian) não disponíveis. "
        "Instale o pacote **akshare**: `pip install akshare`"
    )
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=vale3.index, y=vale3.values, name="VALE3",
            line=dict(color="#1565C0", width=2),
        )
    )
    fig2.update_layout(
        title="VALE3 (sem dados de minério de ferro)",
        height=540,
        xaxis=dict(
            rangeselector=dict(buttons=RANGE_BUTTONS),
            rangeslider=dict(visible=True),
            type="date",
        ),
    )
    fig2.update_yaxes(title_text="VALE3 (BRL)")
    st.plotly_chart(fig2, use_container_width=True)

else:
    st.error("Não foi possível carregar dados de VALE3.")

# ---------------------------------------------------------------------------
st.caption(
    "Fontes: Yahoo Finance (PETR4, VALE3, Brent) · "
    "Sina Finance / Dalian Commodity Exchange (Minério de Ferro)"
)
