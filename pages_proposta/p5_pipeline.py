"""
Tela 5: Pipeline / CRM Dashboard
Kanban view, funnel chart, conversion metrics, and interaction history.
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

from shared.brand import TAG, PLOTLY_LAYOUT, fmt_brl, fmt_pct, render_status_badge
from database.models import (
    list_prospects,
    get_pipeline_stats,
    update_prospect,
    add_interacao,
    list_interacoes,
    get_prospect,
    list_propostas,
)


PIPELINE_STAGES = [
    ("Lead", TAG["azul"]),
    ("Qualificado", TAG["amarelo"]),
    ("Proposta Enviada", TAG["laranja"]),
    ("Negociação", TAG["rosa"]),
    ("Cliente", TAG["verde"]),
]

# Probabilidade de conversao por estagio (para revenue forecast)
_CONV_PROB = {
    "Lead": 0.05,
    "Qualificado": 0.15,
    "Proposta Enviada": 0.35,
    "Negociação": 0.60,
    "Cliente": 1.0,
    "Perdido": 0.0,
}


def render_pipeline():
    st.title("Pipeline de Prospects")

    stats = get_pipeline_stats()
    all_prospects = list_prospects()

    # ══════════════════════════════════════════════════════
    # TOP METRICS
    # ══════════════════════════════════════════════════════
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Prospects", stats["total"])
    with col2:
        st.metric("Patrimônio Pipeline", fmt_brl(stats["total_pl"]))
    with col3:
        leads = stats["by_status"].get("Lead", {}).get("count", 0)
        qualif = stats["by_status"].get("Qualificado", {}).get("count", 0)
        st.metric("Em Prospecção", leads + qualif)
    with col4:
        prop = stats["by_status"].get("Proposta Enviada", {}).get("count", 0)
        neg = stats["by_status"].get("Negociação", {}).get("count", 0)
        st.metric("Em Negociação", prop + neg)
    with col5:
        clientes = stats["by_status"].get("Cliente", {}).get("count", 0)
        st.metric("Convertidos", clientes)
    with col6:
        perdidos = stats["by_status"].get("Perdido", {}).get("count", 0)
        st.metric("Perdidos", perdidos)

    st.markdown("---")

    # ══════════════════════════════════════════════════════
    # TABS: Kanban | Funil & Métricas | CRM
    # ══════════════════════════════════════════════════════
    tab_kanban, tab_funnel, tab_crm = st.tabs([
        "📋 Kanban",
        "📊 Funil & Métricas",
        "💬 CRM / Interações",
    ])

    # ──────────────────────────────────────────────────────
    # TAB 1: KANBAN
    # ──────────────────────────────────────────────────────
    with tab_kanban:
        _render_kanban(all_prospects, stats)

    # ──────────────────────────────────────────────────────
    # TAB 2: FUNIL & MÉTRICAS
    # ──────────────────────────────────────────────────────
    with tab_funnel:
        _render_funnel_metrics(all_prospects, stats)

    # ──────────────────────────────────────────────────────
    # TAB 3: CRM / INTERAÇÕES
    # ──────────────────────────────────────────────────────
    with tab_crm:
        _render_crm(all_prospects, stats)


# ═══════════════════════════════════════════════════════════
# KANBAN VIEW
# ═══════════════════════════════════════════════════════════

def _render_kanban(all_prospects, stats):
    """Kanban board with inline status change."""
    st.subheader("Quadro Kanban")

    # Quick filter
    col1, col2 = st.columns([2, 1])
    with col1:
        search_kanban = st.text_input(
            "Buscar no Kanban",
            placeholder="Filtrar por nome...",
            key="kanban_search",
        )
    with col2:
        filter_resp_kanban = st.text_input(
            "Filtrar por responsável",
            key="kanban_resp_filter",
        )

    filtered = all_prospects
    if search_kanban:
        s = search_kanban.lower()
        filtered = [p for p in filtered if s in p.get("nome", "").lower()]
    if filter_resp_kanban:
        r = filter_resp_kanban.lower()
        filtered = [p for p in filtered if r in p.get("responsavel", "").lower()]

    cols = st.columns(len(PIPELINE_STAGES))

    for i, (stage_name, stage_color) in enumerate(PIPELINE_STAGES):
        with cols[i]:
            stage_prospects = [p for p in filtered if p["status"] == stage_name]
            count = len(stage_prospects)
            total_pl = sum(p.get("patrimonio_investivel", 0) or 0 for p in stage_prospects)

            st.markdown(
                f'<div class="kanban-col">'
                f'<div style="color:{stage_color};font-weight:600;font-size:0.95rem;'
                f'border-bottom:2px solid {stage_color};padding-bottom:8px;margin-bottom:4px">'
                f'{stage_name} <span style="color:{TAG["text_muted"]};font-weight:400">({count})</span>'
                f'</div>'
                f'<div style="color:{TAG["text_muted"]};font-size:0.75rem;margin-bottom:12px">'
                f'{fmt_brl(total_pl)}</div>',
                unsafe_allow_html=True,
            )

            for p in stage_prospects[:12]:
                patrimonio = fmt_brl(p.get("patrimonio_investivel", 0))
                perfil = p.get("perfil_investidor", "")
                resp = p.get("responsavel", "")

                # Card with prospect info
                st.markdown(
                    f'<div class="kanban-card">'
                    f'<div style="color:{TAG["offwhite"]};font-weight:500;font-size:0.85rem">'
                    f'{p["nome"][:25]}</div>'
                    f'<div style="color:{TAG["text_muted"]};font-size:0.72rem">'
                    f'{perfil} · {patrimonio}</div>'
                    + (f'<div style="color:{TAG["text_muted"]};font-size:0.68rem;margin-top:2px">'
                       f'👤 {resp}</div>' if resp else "")
                    + f'</div>',
                    unsafe_allow_html=True,
                )

            if count > 12:
                st.caption(f"+{count - 12} mais...")

            st.markdown("</div>", unsafe_allow_html=True)

    # ── Quick status change ──
    st.markdown("---")
    st.markdown(
        f'<div style="color:{TAG["laranja"]};font-weight:600;font-size:0.95rem;margin-bottom:8px">'
        f'⚡ Mover Prospect de Estágio</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        prospect_names_move = [f"{p['nome']} ({p['status']})" for p in all_prospects if p["status"] != "Perdido"]
        selected_move = st.selectbox(
            "Prospect",
            ["Selecionar..."] + prospect_names_move,
            key="move_prospect_select",
        )
    with col2:
        all_statuses = [s[0] for s in PIPELINE_STAGES] + ["Perdido"]
        new_status = st.selectbox("Novo status", all_statuses, key="move_new_status")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Mover", key="move_btn", type="primary", use_container_width=True):
            if selected_move != "Selecionar...":
                idx = prospect_names_move.index(selected_move)
                active_prospects = [p for p in all_prospects if p["status"] != "Perdido"]
                pid = active_prospects[idx]["id"]
                update_prospect(pid, {"status": new_status})
                # Log the status change as interaction
                add_interacao(pid, {
                    "tipo": "Outro",
                    "descricao": f"Status alterado para: {new_status}",
                    "responsavel": "Sistema",
                    "proxima_acao": "",
                    "data_proxima_acao": None,
                })
                st.success(f"Prospect movido para '{new_status}'!")
                st.rerun()

    # ── Prospect table ──
    st.markdown("---")
    _render_prospect_table(all_prospects)


# ═══════════════════════════════════════════════════════════
# FUNNEL & METRICS
# ═══════════════════════════════════════════════════════════

def _render_funnel_metrics(all_prospects, stats):
    """Funnel chart + conversion rates + avg time per stage."""

    col_left, col_right = st.columns([1.3, 1])

    # ── Funnel Chart ──
    with col_left:
        st.subheader("Funil de Conversão")
        _render_funnel_chart(stats)

    # ── Conversion Rates ──
    with col_right:
        st.subheader("Taxas de Conversão")
        _render_conversion_rates(stats)

    st.markdown("---")

    # ── Time in Stage Analysis ──
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Tempo Médio por Estágio")
        _render_avg_time_per_stage(all_prospects)
    with col2:
        st.subheader("Receita Ponderada por Estágio")
        _render_weighted_revenue(all_prospects)

    st.markdown("---")

    # ── Velocity & Forecast ──
    st.subheader("Indicadores de Velocidade")
    _render_velocity_metrics(all_prospects, stats)


def _render_funnel_chart(stats):
    """Plotly funnel chart."""
    stages = []
    counts = []
    colors = []

    for stage_name, stage_color in PIPELINE_STAGES:
        c = stats["by_status"].get(stage_name, {}).get("count", 0)
        stages.append(stage_name)
        counts.append(c)
        colors.append(stage_color)

    if sum(counts) == 0:
        st.info("Nenhum prospect no pipeline para exibir o funil.")
        return

    fig = go.Figure(go.Funnel(
        y=stages,
        x=counts,
        textinfo="value+percent initial",
        textposition="inside",
        marker=dict(color=colors),
        connector=dict(line=dict(color=TAG["vermelho"], width=1)),
        textfont=dict(family="Inter", size=14, color="white"),
    ))
    fig.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        height=350,
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_conversion_rates(stats):
    """Show conversion rates between stages with visual bars."""
    stage_names = [s[0] for s in PIPELINE_STAGES]

    # Calculate pass-through rates
    for i in range(len(stage_names) - 1):
        current = stats["by_status"].get(stage_names[i], {}).get("count", 0)
        next_stage = stats["by_status"].get(stage_names[i + 1], {}).get("count", 0)
        # Include all prospects that passed through (current + all after)
        passed_through = sum(
            stats["by_status"].get(stage_names[j], {}).get("count", 0)
            for j in range(i + 1, len(stage_names))
        )
        total_at_stage = current + passed_through

        if total_at_stage > 0:
            rate = passed_through / total_at_stage * 100
        else:
            rate = 0

        color = PIPELINE_STAGES[i + 1][1]
        bar_width = max(rate, 5)

        st.markdown(
            f'<div style="margin-bottom:12px">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
            f'<span style="color:{TAG["text_muted"]};font-size:0.8rem">'
            f'{stage_names[i]} → {stage_names[i+1]}</span>'
            f'<span style="color:{color};font-weight:600;font-size:0.9rem">'
            f'{rate:.0f}%</span>'
            f'</div>'
            f'<div style="background:{TAG["bg_card"]};border-radius:6px;height:8px;overflow:hidden">'
            f'<div style="width:{bar_width}%;height:100%;background:{color};border-radius:6px;'
            f'transition:width 0.3s"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # Overall conversion
    total = stats["total"]
    clientes = stats["by_status"].get("Cliente", {}).get("count", 0)
    perdidos = stats["by_status"].get("Perdido", {}).get("count", 0)
    overall = (clientes / total * 100) if total > 0 else 0
    loss_rate = (perdidos / total * 100) if total > 0 else 0

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="tag-card" style="text-align:center;padding:16px">'
            f'<div style="color:{TAG["verde"]};font-size:1.8rem;font-weight:700">{overall:.1f}%</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.8rem">Taxa de Conversão Total</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="tag-card" style="text-align:center;padding:16px">'
            f'<div style="color:{TAG["rosa"]};font-size:1.8rem;font-weight:700">{loss_rate:.1f}%</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.8rem">Taxa de Perda</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_avg_time_per_stage(all_prospects):
    """Calculate and display average time per stage based on created/updated dates."""
    # Estimate time per stage from interactions/timestamps
    stage_times = {s[0]: [] for s in PIPELINE_STAGES}

    for p in all_prospects:
        created = p.get("created_at", "")
        updated = p.get("updated_at", "")
        if not created or not updated:
            continue
        try:
            dt_created = datetime.fromisoformat(created)
            dt_updated = datetime.fromisoformat(updated)
            days = (dt_updated - dt_created).days
            status = p.get("status", "Lead")
            if status in stage_times:
                stage_times[status].append(days)
        except Exception:
            continue

    has_data = any(len(v) > 0 for v in stage_times.values())
    if not has_data:
        st.info("Dados insuficientes para calcular tempo médio por estágio. "
                "As métricas serão preenchidas conforme prospects progridam no pipeline.")
        return

    for stage_name, stage_color in PIPELINE_STAGES:
        times = stage_times.get(stage_name, [])
        avg_days = sum(times) / len(times) if times else 0
        count = len(times)

        # Visual bar (max 90 days reference)
        bar_pct = min(avg_days / 90 * 100, 100) if avg_days > 0 else 2

        if avg_days == 0:
            time_str = "—"
        elif avg_days < 1:
            time_str = "< 1 dia"
        elif avg_days == 1:
            time_str = "1 dia"
        else:
            time_str = f"{avg_days:.0f} dias"

        st.markdown(
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
            f'<span style="color:{stage_color};font-weight:500;font-size:0.85rem">'
            f'{stage_name}</span>'
            f'<span style="color:{TAG["offwhite"]};font-weight:600;font-size:0.85rem">'
            f'{time_str}'
            f'<span style="color:{TAG["text_muted"]};font-weight:400;font-size:0.72rem"> '
            f'({count} prospect{"s" if count != 1 else ""})</span></span>'
            f'</div>'
            f'<div style="background:{TAG["bg_card"]};border-radius:6px;height:6px;overflow:hidden">'
            f'<div style="width:{bar_pct}%;height:100%;background:{stage_color};border-radius:6px">'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )


def _render_weighted_revenue(all_prospects):
    """Show weighted revenue by stage (expected AUM)."""
    stage_data = []
    for stage_name, stage_color in PIPELINE_STAGES:
        prospects_in = [p for p in all_prospects if p["status"] == stage_name]
        pl_total = sum(p.get("patrimonio_investivel", 0) or 0 for p in prospects_in)
        prob = _CONV_PROB.get(stage_name, 0)
        weighted = pl_total * prob
        stage_data.append((stage_name, stage_color, pl_total, prob, weighted, len(prospects_in)))

    total_weighted = sum(d[4] for d in stage_data)

    if total_weighted == 0:
        st.info("Nenhum patrimônio no pipeline para projetar receita.")
        return

    for name, color, pl, prob, weighted, count in stage_data:
        bar_pct = (weighted / total_weighted * 100) if total_weighted > 0 else 0
        st.markdown(
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
            f'<span style="color:{color};font-weight:500;font-size:0.85rem">'
            f'{name} <span style="color:{TAG["text_muted"]};font-size:0.72rem">'
            f'({count}) × {prob*100:.0f}%</span></span>'
            f'<span style="color:{TAG["offwhite"]};font-weight:600;font-size:0.85rem">'
            f'{fmt_brl(weighted)}</span>'
            f'</div>'
            f'<div style="background:{TAG["bg_card"]};border-radius:6px;height:6px;overflow:hidden">'
            f'<div style="width:{max(bar_pct, 2)}%;height:100%;background:{color};border-radius:6px">'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="tag-card" style="text-align:center;padding:16px;margin-top:12px">'
        f'<div style="color:{TAG["laranja"]};font-size:1.5rem;font-weight:700">'
        f'{fmt_brl(total_weighted)}</div>'
        f'<div style="color:{TAG["text_muted"]};font-size:0.8rem">'
        f'AUM Ponderado Esperado</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_velocity_metrics(all_prospects, stats):
    """Pipeline velocity indicators."""
    # Calculate metrics
    total = stats["total"]
    clientes = stats["by_status"].get("Cliente", {}).get("count", 0)
    perdidos = stats["by_status"].get("Perdido", {}).get("count", 0)
    ativos = total - clientes - perdidos

    # Win rate (clientes / (clientes + perdidos))
    closed = clientes + perdidos
    win_rate = (clientes / closed * 100) if closed > 0 else 0

    # Average deal size
    clientes_pl = stats["by_status"].get("Cliente", {}).get("total_pl", 0)
    avg_deal = clientes_pl / clientes if clientes > 0 else 0

    # Prospects with proposals
    prospects_with_proposals = 0
    for p in all_prospects:
        props = list_propostas(p["id"])
        if props:
            prospects_with_proposals += 1
    prop_coverage = (prospects_with_proposals / total * 100) if total > 0 else 0

    # Recent activity (last 30 days)
    recent_count = 0
    cutoff = datetime.now() - timedelta(days=30)
    for p in all_prospects:
        try:
            updated = datetime.fromisoformat(p.get("updated_at", ""))
            if updated >= cutoff:
                recent_count += 1
        except Exception:
            pass

    # Display
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(
            f'<div class="tag-card" style="text-align:center;padding:14px">'
            f'<div style="color:{TAG["verde"]};font-size:1.6rem;font-weight:700">{win_rate:.0f}%</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">Win Rate</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.68rem">'
            f'{clientes}W / {perdidos}L</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="tag-card" style="text-align:center;padding:14px">'
            f'<div style="color:{TAG["azul"]};font-size:1.6rem;font-weight:700">{ativos}</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">Pipeline Ativo</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.68rem">'
            f'de {total} total</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="tag-card" style="text-align:center;padding:14px">'
            f'<div style="color:{TAG["laranja"]};font-size:1.6rem;font-weight:700">'
            f'{fmt_brl(avg_deal)}</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">Ticket Médio</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.68rem">'
            f'(clientes convertidos)</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div class="tag-card" style="text-align:center;padding:14px">'
            f'<div style="color:{TAG["amarelo"]};font-size:1.6rem;font-weight:700">'
            f'{prop_coverage:.0f}%</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">Com Proposta</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.68rem">'
            f'{prospects_with_proposals} de {total}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col5:
        st.markdown(
            f'<div class="tag-card" style="text-align:center;padding:14px">'
            f'<div style="color:{TAG["rosa"]};font-size:1.6rem;font-weight:700">{recent_count}</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.75rem">Ativos (30d)</div>'
            f'<div style="color:{TAG["text_muted"]};font-size:0.68rem">'
            f'atualizados recentemente</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Status distribution bar chart ──
    st.markdown("---")
    st.subheader("Distribuição por Estágio (Patrimônio)")
    _render_pl_distribution_chart(stats)


def _render_pl_distribution_chart(stats):
    """Horizontal bar chart showing PL distribution by stage."""
    stages = []
    pls = []
    colors = []

    for stage_name, stage_color in PIPELINE_STAGES:
        pl = stats["by_status"].get(stage_name, {}).get("total_pl", 0)
        stages.append(stage_name)
        pls.append(pl)
        colors.append(stage_color)

    # Add Perdido
    perdido_pl = stats["by_status"].get("Perdido", {}).get("total_pl", 0)
    if perdido_pl > 0:
        stages.append("Perdido")
        pls.append(perdido_pl)
        colors.append(TAG["text_muted"])

    if sum(pls) == 0:
        st.info("Nenhum patrimônio cadastrado no pipeline.")
        return

    fig = go.Figure(go.Bar(
        y=stages,
        x=pls,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(width=0),
        ),
        text=[fmt_brl(v) for v in pls],
        textposition="auto",
        textfont=dict(color="white", size=12),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=250,
        margin=dict(t=10, b=30, l=120, r=20),
        showlegend=False,
        yaxis=dict(
            **PLOTLY_LAYOUT.get("yaxis", {}),
            autorange="reversed",
        ),
        xaxis=dict(
            **PLOTLY_LAYOUT.get("xaxis", {}),
            title="Patrimônio Investível (R$)",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
# CRM / INTERACTIONS
# ═══════════════════════════════════════════════════════════

def _render_crm(all_prospects, stats):
    """CRM panel with interactions and upcoming actions."""

    # ── Select prospect ──
    st.subheader("Gerenciar Interações")
    prospect_options = ["Selecionar prospect..."] + [
        f"{p['nome']} ({p['status']})" for p in all_prospects
    ]

    # Check if there's a pre-selected prospect
    pre_selected = 0
    if st.session_state.get("selected_prospect_id"):
        for i, p in enumerate(all_prospects):
            if p["id"] == st.session_state["selected_prospect_id"]:
                pre_selected = i + 1
                break

    selected_idx = st.selectbox(
        "Prospect",
        prospect_options,
        index=pre_selected,
        key="crm_prospect_select",
    )

    if selected_idx != "Selecionar prospect...":
        idx = prospect_options.index(selected_idx) - 1
        prospect = get_prospect(all_prospects[idx]["id"])

        if prospect:
            # Prospect summary card
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(render_status_badge(prospect["status"]), unsafe_allow_html=True)
            with col2:
                st.markdown(
                    f'<div style="color:{TAG["offwhite"]};font-size:0.9rem">'
                    f'{fmt_brl(prospect.get("patrimonio_investivel", 0))}</div>',
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f'<div style="color:{TAG["text_muted"]};font-size:0.9rem">'
                    f'{prospect.get("perfil_investidor", "N/A")}</div>',
                    unsafe_allow_html=True,
                )
            with col4:
                st.markdown(
                    f'<div style="color:{TAG["text_muted"]};font-size:0.9rem">'
                    f'👤 {prospect.get("responsavel", "—")}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # ── Add interaction form ──
            with st.expander("➕ Registrar Nova Interação", expanded=False):
                with st.form("new_interaction", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        tipo = st.selectbox(
                            "Tipo",
                            ["Reunião", "Ligação", "Email", "WhatsApp", "Proposta", "Outro"],
                        )
                    with col2:
                        resp = st.text_input(
                            "Responsável",
                            value=prospect.get("responsavel", ""),
                        )

                    descricao = st.text_area(
                        "Descrição",
                        placeholder="O que foi discutido...",
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        proxima_acao = st.text_input(
                            "Próxima ação",
                            placeholder="Ex: Enviar proposta",
                        )
                    with col2:
                        data_proxima = st.date_input("Data da próxima ação", value=None)

                    if st.form_submit_button("Registrar", type="primary"):
                        add_interacao(prospect["id"], {
                            "tipo": tipo,
                            "descricao": descricao,
                            "responsavel": resp,
                            "proxima_acao": proxima_acao,
                            "data_proxima_acao": data_proxima.isoformat() if data_proxima else None,
                        })
                        st.success("Interação registrada!")
                        st.rerun()

            # ── Interaction History ──
            interacoes = list_interacoes(prospect["id"])
            if interacoes:
                st.markdown(
                    f'<div style="color:{TAG["laranja"]};font-weight:600;font-size:0.95rem;'
                    f'margin-bottom:12px">Histórico ({len(interacoes)} interações)</div>',
                    unsafe_allow_html=True,
                )
                for inter in interacoes:
                    tipo_emoji = {
                        "Reunião": "🤝", "Ligação": "📞", "Email": "📧",
                        "WhatsApp": "💬", "Proposta": "📄", "Outro": "📌",
                    }.get(inter["tipo"], "📌")

                    # Check if overdue
                    is_overdue = False
                    if inter.get("data_proxima_acao"):
                        try:
                            data_acao = datetime.fromisoformat(inter["data_proxima_acao"]).date()
                            is_overdue = data_acao < datetime.now().date()
                        except Exception:
                            pass

                    overdue_badge = ""
                    if is_overdue:
                        overdue_badge = (
                            f'<span style="background:{TAG["rosa"]}30;color:{TAG["rosa"]};'
                            f'padding:2px 8px;border-radius:10px;font-size:0.68rem;'
                            f'font-weight:600;margin-left:8px">ATRASADA</span>'
                        )

                    st.markdown(
                        f'<div class="tag-card" style="padding:12px 16px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<span style="font-weight:500;color:{TAG["offwhite"]}">'
                        f'{tipo_emoji} {inter["tipo"]}{overdue_badge}</span>'
                        f'<span style="color:{TAG["text_muted"]};font-size:0.75rem">'
                        f'{inter["created_at"][:16]}</span>'
                        f'</div>'
                        f'<div style="color:{TAG["text"]};font-size:0.85rem;margin-top:6px">'
                        f'{inter["descricao"]}</div>'
                        + (
                            f'<div style="color:{TAG["laranja"]};font-size:0.8rem;margin-top:4px">'
                            f'📅 Próximo: {inter["proxima_acao"]} ({inter["data_proxima_acao"]})</div>'
                            if inter.get("proxima_acao") else ""
                        )
                        + f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Nenhuma interação registrada para este prospect.")

    # ── Upcoming Actions (global) ──
    st.markdown("---")
    st.subheader("📅 Próximas Ações (todos os prospects)")
    if stats.get("upcoming_actions"):
        for action in stats["upcoming_actions"]:
            # Calculate urgency
            urgency_color = TAG["text_muted"]
            try:
                data_acao = datetime.fromisoformat(action["data_proxima_acao"]).date()
                days_until = (data_acao - datetime.now().date()).days
                if days_until < 0:
                    urgency_color = TAG["rosa"]
                elif days_until == 0:
                    urgency_color = TAG["laranja"]
                elif days_until <= 3:
                    urgency_color = TAG["amarelo"]
                else:
                    urgency_color = TAG["verde"]
            except Exception:
                pass

            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:center;'
                f'padding:10px 14px;background:{TAG["bg_card"]};border-radius:8px;'
                f'margin-bottom:6px;border-left:3px solid {urgency_color}">'
                f'<span style="color:{urgency_color};font-weight:600;min-width:100px;font-size:0.85rem">'
                f'{action["data_proxima_acao"]}</span>'
                f'<span style="color:{TAG["offwhite"]};font-weight:500">'
                f'{action["prospect_nome"]}</span>'
                f'<span style="color:{TAG["text_muted"]};font-size:0.85rem;flex:1">'
                f'{action["proxima_acao"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("Nenhuma ação futura agendada.")


# ═══════════════════════════════════════════════════════════
# PROSPECT TABLE
# ═══════════════════════════════════════════════════════════

def _render_prospect_table(all_prospects):
    """Searchable prospect table."""
    st.subheader("Todos os Prospects")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input(
            "Buscar",
            placeholder="Nome, CPF/CNPJ ou email...",
            key="pipeline_search",
        )
    with col2:
        filter_status = st.selectbox(
            "Status",
            ["Todos"] + [s[0] for s in PIPELINE_STAGES] + ["Perdido"],
            key="pipeline_filter_status",
        )
    with col3:
        filter_responsavel = st.text_input("Responsável", key="pipeline_filter_resp")

    filtered = list_prospects(
        status=filter_status if filter_status != "Todos" else None,
        responsavel=filter_responsavel if filter_responsavel else None,
        search=search if search else None,
    )

    if filtered:
        for p in filtered:
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1.5, 1.5, 1.5, 1, 1])
            with col1:
                st.markdown(
                    f'<div style="font-weight:500;color:{TAG["offwhite"]}">{p["nome"]}</div>'
                    f'<div style="font-size:0.75rem;color:{TAG["text_muted"]}">'
                    f'{p.get("email", "")} · {p.get("telefone", "")}</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(render_status_badge(p["status"]), unsafe_allow_html=True)
            with col3:
                st.markdown(
                    f'<div style="color:{TAG["offwhite"]};font-size:0.85rem">'
                    f'{fmt_brl(p.get("patrimonio_investivel", 0))}</div>',
                    unsafe_allow_html=True,
                )
            with col4:
                st.markdown(
                    f'<div style="color:{TAG["text_muted"]};font-size:0.85rem">'
                    f'{p.get("perfil_investidor", "N/A")}</div>',
                    unsafe_allow_html=True,
                )
            with col5:
                st.markdown(
                    f'<div style="color:{TAG["text_muted"]};font-size:0.8rem">'
                    f'{p.get("responsavel", "")}</div>',
                    unsafe_allow_html=True,
                )
            with col6:
                if st.button("👁", key=f"ver_{p['id']}", use_container_width=True):
                    st.session_state["selected_prospect_id"] = p["id"]
                    st.rerun()

            st.markdown(
                f'<hr style="margin:4px 0;border-color:{TAG["vermelho"]}10">',
                unsafe_allow_html=True,
            )
    else:
        st.info("Nenhum prospect encontrado. Cadastre um novo na aba 'Cadastro de Prospect'.")
