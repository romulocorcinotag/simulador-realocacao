"""
TAG Investimentos - Brand Identity & Styling
Shared across all TAG applications.
"""
import streamlit as st

# ─────────────────────────────────────────────────────────
# TAG BRAND IDENTITY
# ─────────────────────────────────────────────────────────
TAG = {
    "vermelho": "#630D24",
    "vermelho_light": "#8B1A3A",
    "vermelho_dark": "#3D0816",
    "offwhite": "#E6E4DB",
    "laranja": "#FF8853",
    "laranja_dark": "#E06B35",
    "bg_dark": "#1A0A10",
    "bg_card": "#2A1520",
    "bg_card_alt": "#321A28",
    "text": "#E6E4DB",
    "text_muted": "#9A9590",
    "chart": [
        "#FF8853", "#5C85F7", "#6BDE97", "#FFBB00", "#ED5A6E",
        "#58C6F5", "#A485F2", "#477C88", "#002A6E", "#6A6864",
    ],
    # Extended palette for proposals
    "verde": "#6BDE97",
    "azul": "#5C85F7",
    "amarelo": "#FFBB00",
    "rosa": "#ED5A6E",
}

# Plotly template
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, Tahoma, sans-serif", color=TAG["offwhite"], size=13),
    margin=dict(t=30, b=50, l=50, r=20),
    xaxis=dict(
        gridcolor="rgba(230,228,219,0.10)",
        zerolinecolor="rgba(230,228,219,0.10)",
        showline=True,
        linecolor="rgba(230,228,219,0.15)",
        linewidth=1,
    ),
    yaxis=dict(
        gridcolor="rgba(230,228,219,0.10)",
        zerolinecolor="rgba(230,228,219,0.10)",
        showline=True,
        linecolor="rgba(230,228,219,0.15)",
        linewidth=1,
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
    colorway=TAG["chart"],
    hoverlabel=dict(
        bgcolor=TAG["bg_card"], font_size=12, font_color=TAG["offwhite"]
    ),
)


def inject_css():
    """Inject TAG branded CSS into Streamlit app."""
    st.markdown(
        f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', 'Tahoma', sans-serif;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {TAG["vermelho_dark"]} 0%, {TAG["bg_dark"]} 100%);
        border-right: 1px solid {TAG["vermelho"]}33;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        font-size: 0.9rem;
        padding: 6px 0;
    }}

    /* ── Headers ── */
    h1 {{
        color: {TAG["offwhite"]} !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        border-bottom: 2px solid {TAG["laranja"]}40;
        padding-bottom: 12px !important;
    }}
    h2, h3 {{
        color: {TAG["offwhite"]} !important;
        font-weight: 500 !important;
    }}

    /* ── Metrics ── */
    [data-testid="stMetric"] {{
        background: linear-gradient(135deg, {TAG["bg_card"]} 0%, {TAG["bg_card_alt"]} 100%);
        border: 1px solid {TAG["vermelho"]}30;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 16px rgba(99,13,36,0.15);
    }}
    [data-testid="stMetric"] label {{
        color: {TAG["text_muted"]} !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    [data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {TAG["offwhite"]} !important;
        font-weight: 600 !important;
    }}

    /* ── Expanders ── */
    .streamlit-expanderHeader {{
        background: {TAG["bg_card"]} !important;
        border: 1px solid {TAG["vermelho"]}25 !important;
        border-radius: 8px !important;
        color: {TAG["offwhite"]} !important;
    }}

    /* ── Dataframes ── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {TAG["vermelho"]}20;
        border-radius: 8px;
        overflow: hidden;
    }}

    /* ── Buttons ── */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {TAG["laranja"]} 0%, {TAG["laranja_dark"]} 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(255,136,83,0.3) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        box-shadow: 0 6px 20px rgba(255,136,83,0.5) !important;
        transform: translateY(-1px);
    }}
    .stDownloadButton > button {{
        background: linear-gradient(135deg, {TAG["vermelho"]} 0%, {TAG["vermelho_dark"]} 100%) !important;
        color: {TAG["offwhite"]} !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: 2px solid {TAG["vermelho"]}30;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        padding: 8px 24px;
        font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{
        background: {TAG["vermelho"]}20 !important;
        border-bottom: 3px solid {TAG["laranja"]} !important;
    }}

    /* ── Dividers ── */
    hr {{
        border-color: {TAG["vermelho"]}25 !important;
    }}

    /* ── Info/Warning boxes ── */
    [data-testid="stAlert"] {{
        border-radius: 8px;
    }}

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {{
        border: 2px dashed {TAG["vermelho"]}40 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }}

    /* ── Captions in sidebar ── */
    [data-testid="stSidebar"] .stCaption {{
        color: {TAG["text_muted"]} !important;
    }}

    /* ── Legend bar ── */
    .tag-legend {{
        display: flex;
        gap: 20px;
        font-size: 0.82rem;
        margin-top: 8px;
        padding: 8px 12px;
        background: {TAG["bg_card"]};
        border-radius: 8px;
        border: 1px solid {TAG["vermelho"]}20;
    }}

    /* ── Custom card component ── */
    .tag-card {{
        background: linear-gradient(135deg, {TAG["bg_card"]} 0%, {TAG["bg_card_alt"]} 100%);
        border: 1px solid {TAG["vermelho"]}25;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(99,13,36,0.1);
    }}
    .tag-card h3 {{
        margin-top: 0 !important;
        font-size: 1.1rem !important;
    }}

    /* ── Status badges ── */
    .tag-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .tag-badge-lead {{ background: {TAG["azul"]}30; color: {TAG["azul"]}; }}
    .tag-badge-qualificado {{ background: {TAG["amarelo"]}30; color: {TAG["amarelo"]}; }}
    .tag-badge-proposta {{ background: {TAG["laranja"]}30; color: {TAG["laranja"]}; }}
    .tag-badge-negociacao {{ background: {TAG["rosa"]}30; color: {TAG["rosa"]}; }}
    .tag-badge-cliente {{ background: {TAG["verde"]}30; color: {TAG["verde"]}; }}
    .tag-badge-perdido {{ background: {TAG["text_muted"]}30; color: {TAG["text_muted"]}; }}

    /* ── Kanban columns ── */
    .kanban-col {{
        background: {TAG["bg_card"]};
        border-radius: 12px;
        padding: 12px;
        min-height: 200px;
        border: 1px solid {TAG["vermelho"]}15;
    }}
    .kanban-card {{
        background: {TAG["bg_card_alt"]};
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        border-left: 3px solid {TAG["laranja"]};
        cursor: pointer;
        transition: transform 0.1s;
    }}
    .kanban-card:hover {{
        transform: translateX(4px);
    }}

    /* ── Proposal preview ── */
    .proposal-section {{
        background: {TAG["bg_card"]};
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        border: 1px solid {TAG["vermelho"]}20;
    }}

    /* ── Progress indicator ── */
    .step-indicator {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 24px;
    }}
    .step {{
        flex: 1;
        text-align: center;
        padding: 12px 8px;
        position: relative;
        color: {TAG["text_muted"]};
        font-size: 0.85rem;
    }}
    .step.active {{
        color: {TAG["laranja"]};
        font-weight: 600;
    }}
    .step.completed {{
        color: {TAG["verde"]};
    }}
    .step::after {{
        content: '';
        position: absolute;
        bottom: 0;
        left: 10%;
        width: 80%;
        height: 3px;
        background: {TAG["vermelho"]}30;
        border-radius: 2px;
    }}
    .step.active::after {{
        background: {TAG["laranja"]};
    }}
    .step.completed::after {{
        background: {TAG["verde"]};
    }}

    /* ── Hide default decoration ── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
</style>
""",
        unsafe_allow_html=True,
    )


def render_status_badge(status):
    """Return HTML for a status badge."""
    badge_map = {
        "Lead": "lead",
        "Qualificado": "qualificado",
        "Proposta Enviada": "proposta",
        "Negociação": "negociacao",
        "Cliente": "cliente",
        "Perdido": "perdido",
    }
    css_class = badge_map.get(status, "lead")
    return f'<span class="tag-badge tag-badge-{css_class}">{status}</span>'


def render_card(title, content_html):
    """Render a styled card."""
    return f"""
    <div class="tag-card">
        <h3>{title}</h3>
        {content_html}
    </div>
    """


def render_step_indicator(steps, current_step):
    """Render a horizontal step indicator showing progress."""
    html = '<div class="step-indicator">'
    for i, step_name in enumerate(steps):
        if i < current_step:
            cls = "step completed"
        elif i == current_step:
            cls = "step active"
        else:
            cls = "step"
        html += f'<div class="{cls}">{step_name}</div>'
    html += "</div>"
    return html


def fmt_brl(value):
    """Format a number as BRL currency."""
    if value is None:
        return "R$ 0"
    if abs(value) >= 1_000_000:
        return f"R$ {value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"R$ {value:,.0f}"
    return f"R$ {value:,.2f}"


def fmt_pct(value):
    """Format a number as percentage."""
    if value is None:
        return "0%"
    return f"{value:.1f}%"
