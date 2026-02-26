"""
Chart generation for proposals.
Creates Plotly figures for portfolio analysis and comparison.
"""
import plotly.graph_objects as go
from shared.brand import TAG, PLOTLY_LAYOUT


def chart_donut(labels, values, title="", height=350):
    """Create a branded donut chart."""
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            textinfo="label+percent",
            textposition="outside",
            textfont=dict(size=11, color=TAG["offwhite"]),
            marker=dict(
                colors=TAG["chart"][: len(labels)],
                line=dict(color=TAG["bg_dark"], width=1.5),
            ),
            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=height, showlegend=False)
    if title:
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=14, color=TAG["offwhite"]),
                x=0.5,
            )
        )
    return fig


def chart_comparativo_barras(atual_labels, atual_values, proposta_labels, proposta_values, height=450):
    """Create side-by-side bar chart comparing current vs proposed allocation."""
    # Merge all labels
    all_labels = list(dict.fromkeys(atual_labels + proposta_labels))

    atual_map = dict(zip(atual_labels, atual_values))
    proposta_map = dict(zip(proposta_labels, proposta_values))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Carteira Atual",
            y=all_labels,
            x=[atual_map.get(l, 0) for l in all_labels],
            orientation="h",
            marker_color=TAG["chart"][4],
            marker_line_width=0,
            text=[f"{atual_map.get(l, 0):.1f}%" for l in all_labels],
            textposition="auto",
            textfont=dict(size=11),
        )
    )

    fig.add_trace(
        go.Bar(
            name="Proposta TAG",
            y=all_labels,
            x=[proposta_map.get(l, 0) for l in all_labels],
            orientation="h",
            marker_color=TAG["laranja"],
            marker_line_width=0,
            text=[f"{proposta_map.get(l, 0):.1f}%" for l in all_labels],
            textposition="auto",
            textfont=dict(size=11),
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def chart_liquidez_barras(buckets, height=300):
    """Create horizontal bar chart for liquidity profile."""
    labels = list(buckets.keys())
    values = list(buckets.values())
    colors = [TAG["verde"], TAG["azul"], TAG["amarelo"], TAG["rosa"]]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors[: len(labels)],
            text=[f"{v:.1f}%" for v in values],
            textposition="auto",
            textfont=dict(color=TAG["offwhite"]),
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=height, showlegend=False)
    fig.update_xaxes(title_text="% do PL")
    return fig


def chart_cenarios(meses, base, otimista, pessimista, patrimonio_inicial, height=400):
    """Create line chart showing scenario projections."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=meses, y=otimista, mode="lines",
            name="Otimista", line=dict(color=TAG["verde"], width=2, dash="dot"),
            fill=None,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=meses, y=base, mode="lines",
            name="Base", line=dict(color=TAG["laranja"], width=3),
            fill="tonexty", fillcolor=f"rgba(107,222,151,0.1)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=meses, y=pessimista, mode="lines",
            name="Pessimista", line=dict(color=TAG["rosa"], width=2, dash="dot"),
            fill="tonexty", fillcolor=f"rgba(255,136,83,0.1)",
        )
    )

    # Reference line
    fig.add_hline(
        y=patrimonio_inicial,
        line_dash="dash",
        line_color=TAG["text_muted"],
        annotation_text="Patrimônio Atual",
        annotation_font_color=TAG["text_muted"],
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="Meses")
    fig.update_yaxes(title_text="Patrimônio (R$)")
    return fig


# ── New charts for 15-section proposal ──

def chart_allocation_comparison(allocation_data, height=450):
    """Grouped horizontal bar: Atual vs Proposta by asset class (Section 3 & 8)."""
    breakdown = allocation_data.get("class_breakdown", [])
    if not breakdown:
        return _empty_chart("Sem dados de alocacao")

    labels = [item["classe"] for item in breakdown]
    atual = [item["pct_atual"] for item in breakdown]
    proposta = [item["pct_proposta"] for item in breakdown]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Carteira Atual",
        y=labels, x=atual,
        orientation="h",
        marker_color=TAG["chart"][4],
        text=[f"{v:.1f}%" for v in atual],
        textposition="auto",
        textfont=dict(size=11),
    ))
    fig.add_trace(go.Bar(
        name="Proposta TAG",
        y=labels, x=proposta,
        orientation="h",
        marker_color=TAG["laranja"],
        text=[f"{v:.1f}%" for v in proposta],
        textposition="auto",
        textfont=dict(size=11),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=max(height, len(labels) * 40 + 100),
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="% do PL",
    )
    return fig


def chart_concentration_by_issuer(concentration_data, height=400):
    """Horizontal bar: concentration by bank/issuer (Section 4, ref: PPTX slide 29)."""
    if not concentration_data:
        return _empty_chart("Sem dados de concentracao")

    # Top 10
    data = concentration_data[:10]
    labels = [item["instituicao"] for item in data]
    values = [item["pct"] for item in data]

    # Color gradient: more concentrated = more red
    max_pct = max(values) if values else 1
    colors = []
    for v in values:
        ratio = v / max_pct
        if ratio > 0.7:
            colors.append(TAG["vermelho"])
        elif ratio > 0.4:
            colors.append(TAG["laranja"])
        else:
            colors.append(TAG["verde"])

    fig = go.Figure(go.Bar(
        y=labels[::-1], x=values[::-1],
        orientation="h",
        marker_color=colors[::-1],
        text=[f"{v:.1f}%" for v in values[::-1]],
        textposition="auto",
        textfont=dict(color=TAG["offwhite"], size=12),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=max(height, len(labels) * 35 + 80),
        showlegend=False,
        xaxis_title="% do PL",
    )
    return fig


def chart_maturity_ladder(maturity_data, height=400):
    """Bar chart: maturity schedule by period (Section 12, ref: PPTX slide 31)."""
    if not maturity_data:
        return _empty_chart("Sem dados de vencimento")

    labels = [item["label"] for item in maturity_data]
    values = [item["pct"] for item in maturity_data]

    colors = []
    for item in maturity_data:
        if item["periodo"] == "SEM_VENC":
            colors.append(TAG["text_muted"])
        else:
            colors.append(TAG["laranja"])

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in values],
        textposition="auto",
        textfont=dict(color=TAG["offwhite"], size=11),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        showlegend=False,
        yaxis_title="% do PL",
        xaxis_tickangle=-45,
    )
    return fig


def chart_liquidity_comparison(atual_buckets, proposta_buckets, height=350):
    """Side-by-side bar: liquidity profile atual vs proposta (Section 12)."""
    labels = list(atual_buckets.keys())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Carteira Atual",
        x=labels, y=[atual_buckets[k] for k in labels],
        marker_color=TAG["chart"][4],
        text=[f"{atual_buckets[k]:.1f}%" for k in labels],
        textposition="auto",
    ))
    fig.add_trace(go.Bar(
        name="Proposta TAG",
        x=labels, y=[proposta_buckets.get(k, 0) for k in labels],
        marker_color=TAG["laranja"],
        text=[f"{proposta_buckets.get(k, 0):.1f}%" for k in labels],
        textposition="auto",
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_title="% do PL",
    )
    return fig


def chart_risk_return_frontier(efficiency_data, height=400):
    """Scatter: asset classes on risk/return plane (Section 6)."""
    windows = efficiency_data.get("efficiency_by_window", [])
    if not windows:
        return _empty_chart("Sem dados de eficiencia")

    # Use each window as a point
    fig = go.Figure()
    for i, w in enumerate(windows):
        fig.add_trace(go.Scatter(
            x=[w["volatilidade"]],
            y=[w["retorno"]],
            mode="markers+text",
            name=w["janela"],
            marker=dict(
                color=TAG["chart"][i % len(TAG["chart"])],
                size=14,
                line=dict(width=1, color=TAG["offwhite"]),
            ),
            text=[f"{w['janela']}"],
            textposition="top center",
            textfont=dict(size=10, color=TAG["offwhite"]),
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        xaxis_title="Volatilidade (%)",
        yaxis_title="Retorno (%)",
    )
    return fig


def chart_bottom_up_matrix(classification_data, height=350):
    """Stacked horizontal bar: asset classification matrix (Section 5)."""
    if not classification_data:
        return _empty_chart("Sem dados de classificacao")

    categories = {
        "Convicto": TAG["verde"],
        "Neutro": TAG["azul"],
        "Observação": TAG["amarelo"],
        "Saída Estrutural": TAG["rosa"],
        "Ilíquido em Carregamento": TAG["text_muted"],
    }

    # Count totals by classification
    totals = {}
    for item in classification_data:
        cat = item.get("classificacao", "Outros")
        totals[cat] = totals.get(cat, 0) + item.get("financeiro", 0)

    grand_total = sum(totals.values())
    if grand_total == 0:
        return _empty_chart("Sem dados")

    # Single stacked bar
    fig = go.Figure()
    for cat_name, color in categories.items():
        val = totals.get(cat_name, 0)
        pct = val / grand_total * 100
        if pct > 0:
            count = sum(1 for item in classification_data
                       if item.get("classificacao") == cat_name)
            fig.add_trace(go.Bar(
                name=cat_name,
                y=["Carteira"],
                x=[pct],
                orientation="h",
                marker_color=color,
                text=[f"{cat_name}<br>{pct:.1f}% ({count})"],
                textposition="inside",
                textfont=dict(size=11, color="white" if color != TAG["amarelo"] else TAG["bg_dark"]),
            ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        xaxis_title="% do PL",
        showlegend=True,
    )
    return fig


def chart_tax_comparison(tax_data, height=300):
    """Bar: % tax-exempt atual vs proposta (Section 13)."""
    atual = tax_data.get("atual_isentos_pct", 0)
    proposta = tax_data.get("proposta_isentos_pct", 0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="% Isentos",
        x=["Carteira Atual", "Proposta TAG"],
        y=[atual, proposta],
        marker_color=[TAG["chart"][4], TAG["laranja"]],
        text=[f"{atual:.1f}%", f"{proposta:.1f}%"],
        textposition="auto",
        textfont=dict(size=14, color=TAG["offwhite"]),
    ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=height,
        showlegend=False,
        yaxis_title="% em Ativos Isentos de IR",
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
