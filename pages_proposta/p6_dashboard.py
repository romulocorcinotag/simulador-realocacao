"""
Tela 6: Dashboard Executivo
KPIs avancados, funil de conversao, receita projetada, graficos de pipeline.
Referencia: melhores praticas de CRM para wealth management.
"""
import json
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from shared.brand import TAG, PLOTLY_LAYOUT, fmt_brl, fmt_pct
from database.models import (
    list_prospects,
    list_propostas,
    get_pipeline_stats,
    list_interacoes,
)


def render_dashboard():
    st.title("Dashboard Executivo")

    stats = get_pipeline_stats()
    all_prospects = list_prospects()
    now = datetime.now()

    if not all_prospects:
        st.info("Nenhum prospect cadastrado. Comece pelo 'Cadastro de Prospect'.")
        return

    # ══════════════════════════════════════════════════════════
    # TOP KPIs
    # ══════════════════════════════════════════════════════════

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Prospects", stats["total"])
    with col2:
        st.metric("AUM Pipeline", fmt_brl(stats["total_pl"]))
    with col3:
        clientes = stats["by_status"].get("Cliente", {}).get("count", 0)
        total = stats["total"]
        taxa = (clientes / total * 100) if total > 0 else 0
        st.metric("Taxa de Conversao", f"{taxa:.1f}%")
    with col4:
        aum_clientes = stats["by_status"].get("Cliente", {}).get("pl", 0)
        st.metric("AUM Convertido", fmt_brl(aum_clientes))
    with col5:
        leads = stats["by_status"].get("Lead", {}).get("count", 0)
        qualif = stats["by_status"].get("Qualificado", {}).get("count", 0)
        st.metric("Em Prospeccao", leads + qualif)
    with col6:
        prop = stats["by_status"].get("Proposta Enviada", {}).get("count", 0)
        neg = stats["by_status"].get("Negociação", {}).get("count", 0)
        st.metric("Em Negociacao", prop + neg)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # ROW 2: FUNNEL + REVENUE
    # ══════════════════════════════════════════════════════════

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown("### Funil de Conversao")
        _render_funnel_chart(stats)

    with col_right:
        st.markdown("### Receita Projetada")
        _render_revenue_projection(all_prospects, stats)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # ROW 3: DISTRIBUICOES
    # ══════════════════════════════════════════════════════════

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Distribuicao por Perfil")
        _render_profile_distribution(all_prospects)

    with col2:
        st.markdown("### Patrimonio por Status")
        _render_pl_by_status(stats)

    with col3:
        st.markdown("### Faixas de Patrimonio")
        _render_patrimony_bands(all_prospects)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # ROW 4: ATIVIDADE + PROXIMAS ACOES
    # ══════════════════════════════════════════════════════════

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### Atividade Recente")
        _render_recent_activity(all_prospects)

    with col_right:
        st.markdown("### Proximas Acoes")
        _render_upcoming_actions(stats)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # ROW 5: RESPONSAVEIS + PROPOSALS
    # ══════════════════════════════════════════════════════════

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### Performance por Responsavel")
        _render_responsavel_performance(all_prospects)

    with col_right:
        st.markdown("### Status das Propostas")
        _render_proposal_stats(all_prospects)

    # ══════════════════════════════════════════════════════════
    # ROW 6: TOP PROSPECTS TABLE
    # ══════════════════════════════════════════════════════════

    st.markdown("---")
    st.markdown("### Top Prospects por Patrimonio")
    _render_top_prospects_table(all_prospects)


# ── CHART HELPERS ──

def _render_funnel_chart(stats):
    """Render conversion funnel visualization."""
    stages = [
        ("Lead", stats["by_status"].get("Lead", {}).get("count", 0)),
        ("Qualificado", stats["by_status"].get("Qualificado", {}).get("count", 0)),
        ("Proposta Enviada", stats["by_status"].get("Proposta Enviada", {}).get("count", 0)),
        ("Negociacao", stats["by_status"].get("Negociação", {}).get("count", 0)),
        ("Cliente", stats["by_status"].get("Cliente", {}).get("count", 0)),
    ]

    # Accumulate from bottom (clients are the base that passed through all stages)
    labels = [s[0] for s in stages]
    values = [s[1] for s in stages]

    # Cumulative from top
    cumulative = []
    running = 0
    for v in values:
        running += v
        cumulative.append(running)

    colors = [TAG["azul"], TAG["amarelo"], TAG["laranja"], TAG["rosa"], TAG["verde"]]

    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo="value+percent initial",
        textfont=dict(size=13, color="white"),
        marker=dict(color=colors),
        connector=dict(line=dict(color=TAG["vermelho"], width=1)),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=350,
        margin=dict(t=10, b=10, l=100, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_revenue_projection(all_prospects, stats):
    """Project potential revenue based on fee table."""
    from shared.tag_institucional import FEE_TABLE_DEFAULT

    # Default fee: 0.25% for < 500M, 0.20% for > 500M
    base_fee = 0.25 / 100  # Annual fee

    stages_weight = {
        "Lead": 0.05,
        "Qualificado": 0.15,
        "Proposta Enviada": 0.35,
        "Negociação": 0.60,
        "Cliente": 1.0,
    }

    # Revenue by stage
    revenue_by_stage = {}
    for p in all_prospects:
        status = p.get("status", "Lead")
        pl = float(p.get("patrimonio_investivel", 0) or 0)
        weight = stages_weight.get(status, 0.05)
        revenue = pl * base_fee * weight
        revenue_by_stage[status] = revenue_by_stage.get(status, 0) + revenue

    # Display
    total_potential = sum(revenue_by_stage.values())
    total_confirmed = revenue_by_stage.get("Cliente", 0) / stages_weight.get("Cliente", 1) * 1  # Full confirmed

    # Recalculate confirmed (100% probability)
    confirmed_pl = sum(
        float(p.get("patrimonio_investivel", 0) or 0)
        for p in all_prospects if p.get("status") == "Cliente"
    )
    confirmed_revenue = confirmed_pl * base_fee

    potential_pl = sum(
        float(p.get("patrimonio_investivel", 0) or 0)
        for p in all_prospects if p.get("status") != "Cliente" and p.get("status") != "Perdido"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Receita Confirmada (a.a.)", fmt_brl(confirmed_revenue))
    with col2:
        st.metric("Receita Potencial Pipeline", fmt_brl(potential_pl * base_fee))

    # Weighted pipeline bar chart
    ordered_stages = ["Lead", "Qualificado", "Proposta Enviada", "Negociação", "Cliente"]
    stage_values = [revenue_by_stage.get(s, 0) for s in ordered_stages]
    stage_colors = [TAG["azul"], TAG["amarelo"], TAG["laranja"], TAG["rosa"], TAG["verde"]]

    fig = go.Figure(go.Bar(
        x=ordered_stages,
        y=stage_values,
        marker_color=stage_colors,
        text=[fmt_brl(v) for v in stage_values],
        textposition="auto",
        textfont=dict(size=11, color="white"),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=220,
        margin=dict(t=10, b=40, l=40, r=10),
        yaxis_title="Receita Ponderada (R$)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Receita estimada: taxa de administracao {base_fee * 100:.2f}% a.a., ponderada por probabilidade de conversao")


def _render_profile_distribution(all_prospects):
    """Donut chart of investor profile distribution."""
    profile_counts = {}
    for p in all_prospects:
        perfil = p.get("perfil_investidor", "N/A") or "N/A"
        profile_counts[perfil] = profile_counts.get(perfil, 0) + 1

    labels = list(profile_counts.keys())
    values = list(profile_counts.values())

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.5,
        textinfo="label+value",
        textfont=dict(size=11, color=TAG["offwhite"]),
        marker=dict(colors=TAG["chart"][:len(labels)]),
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False,
                      margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)


def _render_pl_by_status(stats):
    """Horizontal bar chart of PL by pipeline status."""
    ordered = ["Lead", "Qualificado", "Proposta Enviada", "Negociação", "Cliente"]
    colors = [TAG["azul"], TAG["amarelo"], TAG["laranja"], TAG["rosa"], TAG["verde"]]

    labels = []
    values = []
    bar_colors = []
    for i, status in enumerate(ordered):
        info = stats["by_status"].get(status, {})
        pl = info.get("pl", 0)
        if pl > 0:
            labels.append(status)
            values.append(pl)
            bar_colors.append(colors[i])

    fig = go.Figure(go.Bar(
        y=labels, x=values,
        orientation="h",
        marker_color=bar_colors,
        text=[fmt_brl(v) for v in values],
        textposition="auto",
        textfont=dict(size=11, color="white"),
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False,
                      margin=dict(t=10, b=10, l=100, r=10),
                      xaxis_title="Patrimonio (R$)")
    st.plotly_chart(fig, use_container_width=True)


def _render_patrimony_bands(all_prospects):
    """Bar chart of prospects by patrimony band."""
    bands = {
        "< R$ 1M": (0, 1_000_000),
        "R$ 1-5M": (1_000_000, 5_000_000),
        "R$ 5-10M": (5_000_000, 10_000_000),
        "R$ 10-50M": (10_000_000, 50_000_000),
        "R$ 50-100M": (50_000_000, 100_000_000),
        "> R$ 100M": (100_000_000, float("inf")),
    }

    band_counts = {k: 0 for k in bands}
    for p in all_prospects:
        pl = float(p.get("patrimonio_investivel", 0) or 0)
        for label, (low, high) in bands.items():
            if low <= pl < high:
                band_counts[label] += 1
                break

    labels = list(band_counts.keys())
    values = list(band_counts.values())

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=TAG["laranja"],
        text=[str(v) for v in values],
        textposition="auto",
        textfont=dict(size=12, color="white"),
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False,
                      margin=dict(t=10, b=40, l=40, r=10),
                      yaxis_title="# Prospects")
    st.plotly_chart(fig, use_container_width=True)


def _render_recent_activity(all_prospects):
    """Show recent interactions across all prospects."""
    all_interactions = []
    for p in all_prospects[:50]:  # Limit to avoid performance issues
        interacoes = list_interacoes(p["id"])
        for inter in interacoes:
            inter["prospect_nome"] = p["nome"]
            all_interactions.append(inter)

    # Sort by created_at desc
    all_interactions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if not all_interactions:
        st.caption("Nenhuma interacao registrada.")
        return

    for inter in all_interactions[:8]:
        tipo_emoji = {
            "Reunião": "🤝", "Ligação": "📞", "Email": "📧",
            "WhatsApp": "💬", "Proposta": "📄", "Outro": "📌",
        }.get(inter.get("tipo", ""), "📌")

        st.markdown(
            f'<div style="display:flex;gap:8px;align-items:flex-start;'
            f'padding:6px 10px;background:{TAG["bg_card"]};border-radius:6px;margin-bottom:4px;'
            f'border-left:3px solid {TAG["laranja"]}">'
            f'<span>{tipo_emoji}</span>'
            f'<div style="flex:1">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span style="color:{TAG["offwhite"]};font-size:0.82rem;font-weight:500">'
            f'{inter["prospect_nome"]}</span>'
            f'<span style="color:{TAG["text_muted"]};font-size:0.7rem">'
            f'{inter.get("created_at", "")[:10]}</span>'
            f'</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.78rem">'
            f'{(inter.get("descricao") or "")[:80]}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


def _render_upcoming_actions(stats):
    """Show upcoming scheduled actions."""
    actions = stats.get("upcoming_actions", [])

    if not actions:
        st.caption("Nenhuma acao agendada.")
        return

    today = datetime.now().date()
    for action in actions[:10]:
        data_str = action.get("data_proxima_acao", "")
        try:
            data = datetime.fromisoformat(data_str).date()
            days_diff = (data - today).days
            if days_diff < 0:
                urgency_color = TAG["rosa"]
                urgency_label = f"ATRASADO ({abs(days_diff)}d)"
            elif days_diff == 0:
                urgency_color = TAG["laranja"]
                urgency_label = "HOJE"
            elif days_diff <= 3:
                urgency_color = TAG["amarelo"]
                urgency_label = f"em {days_diff}d"
            else:
                urgency_color = TAG["verde"]
                urgency_label = f"em {days_diff}d"
        except Exception:
            urgency_color = TAG["text_muted"]
            urgency_label = data_str[:10]

        st.markdown(
            f'<div style="display:flex;gap:8px;align-items:center;'
            f'padding:6px 10px;background:{TAG["bg_card"]};border-radius:6px;margin-bottom:4px">'
            f'<span style="color:{urgency_color};font-weight:700;font-size:0.75rem;'
            f'min-width:80px;text-transform:uppercase">{urgency_label}</span>'
            f'<span style="color:{TAG["offwhite"]};font-size:0.85rem">'
            f'{action.get("prospect_nome", "")}</span>'
            f'<span style="color:{TAG["text_muted"]};font-size:0.78rem;flex:1">'
            f'{action.get("proxima_acao", "")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_responsavel_performance(all_prospects):
    """Show performance metrics by responsible person."""
    resp_data = {}
    for p in all_prospects:
        resp = p.get("responsavel", "N/A") or "N/A"
        if resp not in resp_data:
            resp_data[resp] = {"total": 0, "clientes": 0, "pl": 0, "pl_convertido": 0}
        resp_data[resp]["total"] += 1
        resp_data[resp]["pl"] += float(p.get("patrimonio_investivel", 0) or 0)
        if p.get("status") == "Cliente":
            resp_data[resp]["clientes"] += 1
            resp_data[resp]["pl_convertido"] += float(p.get("patrimonio_investivel", 0) or 0)

    if not resp_data or (len(resp_data) == 1 and "N/A" in resp_data):
        st.caption("Defina responsaveis nos prospects para ver metricas.")
        return

    for resp, data in sorted(resp_data.items(), key=lambda x: x[1]["pl_convertido"], reverse=True):
        if resp == "N/A":
            continue
        conv_rate = (data["clientes"] / data["total"] * 100) if data["total"] > 0 else 0
        st.markdown(
            f'<div style="padding:8px 12px;background:{TAG["bg_card"]};border-radius:8px;'
            f'margin-bottom:6px;border-left:3px solid {TAG["laranja"]}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span style="color:{TAG["offwhite"]};font-weight:600">{resp}</span>'
            f'<span style="color:{TAG["verde"]};font-size:0.85rem;font-weight:500">'
            f'{conv_rate:.0f}% conv.</span>'
            f'</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.78rem">'
            f'{data["total"]} prospects | {data["clientes"]} clientes | '
            f'PL: {fmt_brl(data["pl"])} | Convertido: {fmt_brl(data["pl_convertido"])}'
            f'</div></div>',
            unsafe_allow_html=True,
        )


def _render_proposal_stats(all_prospects):
    """Show proposal generation and delivery stats."""
    total_proposals = 0
    status_counts = {}
    for p in all_prospects:
        propostas = list_propostas(p["id"])
        total_proposals += len(propostas)
        for prop in propostas:
            status = prop.get("status", "Rascunho")
            status_counts[status] = status_counts.get(status, 0) + 1

    if total_proposals == 0:
        st.caption("Nenhuma proposta gerada ainda.")
        return

    st.metric("Total de Propostas", total_proposals)

    if status_counts:
        ordered = ["Rascunho", "Revisão", "Aprovada", "Enviada", "Aceita", "Rejeitada"]
        status_colors = {
            "Rascunho": TAG["text_muted"],
            "Revisão": TAG["amarelo"],
            "Aprovada": TAG["azul"],
            "Enviada": TAG["laranja"],
            "Aceita": TAG["verde"],
            "Rejeitada": TAG["rosa"],
        }

        for status in ordered:
            count = status_counts.get(status, 0)
            if count > 0:
                color = status_colors.get(status, TAG["text_muted"])
                pct = count / total_proposals * 100
                bar_width = max(5, pct)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'
                    f'<span style="color:{TAG["text_muted"]};font-size:0.78rem;min-width:80px">{status}</span>'
                    f'<div style="flex:1;background:{TAG["bg_card"]};border-radius:4px;height:20px;overflow:hidden">'
                    f'<div style="width:{bar_width}%;background:{color};height:100%;border-radius:4px;'
                    f'display:flex;align-items:center;justify-content:center">'
                    f'<span style="color:white;font-size:0.7rem;font-weight:600">{count}</span>'
                    f'</div></div>'
                    f'<span style="color:{TAG["text_muted"]};font-size:0.72rem;min-width:35px">'
                    f'{pct:.0f}%</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def _render_top_prospects_table(all_prospects):
    """Show top prospects sorted by patrimonio."""
    import pandas as pd

    sorted_prospects = sorted(
        all_prospects,
        key=lambda x: float(x.get("patrimonio_investivel", 0) or 0),
        reverse=True,
    )[:15]

    rows = []
    for p in sorted_prospects:
        pl = float(p.get("patrimonio_investivel", 0) or 0)
        rows.append({
            "Nome": p.get("nome", ""),
            "Status": p.get("status", ""),
            "Perfil": p.get("perfil_investidor", ""),
            "Patrimonio": pl,
            "Responsavel": p.get("responsavel", ""),
            "Cadastro": (p.get("created_at") or "")[:10],
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.format({"Patrimonio": "R$ {:,.0f}"}),
            use_container_width=True,
            hide_index=True,
            height=min(560, 35 * len(df) + 40),
        )
