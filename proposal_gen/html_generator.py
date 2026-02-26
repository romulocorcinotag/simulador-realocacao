"""
HTML proposal generator.
Creates standalone HTML files for shareable proposals.
Supports v1 (basic), v2 (15-section professional), and v3 (full PPTX ~22 sections) formats.

V3 structure mirrors p4_visualizar.py:
  Part 0: Sobre a TAG (slides 1-5)
  Part I: Estrutura Patrimonial (slides 6-22) - conditional
  Part II: Gestao de Investimentos (slides 23-53) - 15 sections
  Part III: Governanca (slides 54-60)
  Part IV: Proposta Comercial (slides 61-64)
"""
import os
import json
from datetime import datetime

from shared.brand import TAG

# Chart imports for embedded Plotly visualizations
try:
    from proposal_gen.charts import (
        chart_donut, chart_allocation_comparison,
        chart_concentration_by_issuer, chart_bottom_up_matrix,
        chart_risk_return_frontier, chart_liquidity_comparison,
        chart_maturity_ladder, chart_tax_comparison,
    )
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False


def generate_proposal_html(prospect, proposta, charts_html=None):
    """Generate a standalone HTML proposal document.

    Auto-detects v3 (politica/fundos/comercial), v2 (section_texts/analytics),
    or v1 (legacy). Falls back gracefully.
    """
    politica_inv = proposta.get("politica_investimentos", {}) or {}
    fundos_sugeridos = proposta.get("fundos_sugeridos", []) or []
    proposta_comercial = proposta.get("proposta_comercial", {}) or {}
    section_texts = proposta.get("section_texts", {}) or {}
    analytics_data = proposta.get("analytics_data", {}) or {}

    has_v3 = bool(politica_inv or fundos_sugeridos or proposta_comercial)

    if has_v3:
        return _generate_html_v3(prospect, proposta, charts_html)
    elif section_texts or analytics_data:
        return _generate_html_v2(prospect, proposta, charts_html)
    else:
        return _generate_html_v1(prospect, proposta, charts_html)


def save_proposal_html(html_content, link_id):
    """Save HTML proposal to file and return the path."""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "propostas_html")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{link_id}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filepath


# ══════════════════════════════════════════════════════════
# CHART EMBEDDING HELPERS
# ══════════════════════════════════════════════════════════

def _embed_chart(fig, height=None):
    """Convert a Plotly figure to an embeddable HTML div (requires Plotly.js CDN in <head>)."""
    try:
        chart_html = fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={"displayModeBar": False, "responsive": True},
        )
        return f'<div class="chart-container">{chart_html}</div>'
    except Exception:
        return ""


def _html_donut_from_portfolio(carteira, title="Alocacao Proposta"):
    """Generate a donut chart HTML from carteira_proposta data."""
    if not HAS_CHARTS or not carteira:
        return ""
    labels = [c.get("ativo", c.get("Ativo", ""))[:25] for c in carteira]
    values = [float(c.get("pct_alvo", c.get("% Alvo", 0))) for c in carteira]
    if not any(v > 0 for v in values):
        return ""
    try:
        fig = chart_donut(labels, values, title, height=320)
        return _embed_chart(fig)
    except Exception:
        return ""


def _html_allocation_bars_css(carteira):
    """Pure CSS horizontal bars showing portfolio allocation weights. No JS needed."""
    if not carteira:
        return ""
    colors = TAG["chart"]
    html = '<div class="alloc-visual"><h3>Distribuicao Visual da Carteira Proposta</h3>'
    for i, item in enumerate(carteira):
        name = item.get("ativo", item.get("Ativo", ""))[:35]
        pct = float(item.get("pct_alvo", item.get("% Alvo", 0)))
        classe = item.get("classe", item.get("Classe", ""))
        color = colors[i % len(colors)]
        bar_w = max(pct, 2)
        html += (
            f'<div class="alloc-row">'
            f'<div class="alloc-info">'
            f'<span class="alloc-name">{name}</span>'
            f'<span class="alloc-class">{classe}</span>'
            f'</div>'
            f'<div class="alloc-bar-wrap">'
            f'<div class="alloc-bar" style="width:{bar_w}%;background:{color}">'
            f'<span>{pct:.1f}%</span>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    total_pct = sum(float(c.get("pct_alvo", c.get("% Alvo", 0))) for c in carteira)
    html += f'<div class="alloc-total">Total: {total_pct:.1f}% | {len(carteira)} ativos</div>'
    html += '</div>'
    return html


def _html_comparison_bars_css(items, title="Comparativo"):
    """Pure CSS comparison bars: atual vs proposta. items = [(label, atual_pct, proposta_pct)]"""
    if not items:
        return ""
    html = f'<div class="comp-visual"><h3>{title}</h3>'
    for label, atual, proposta in items:
        max_val = max(atual, proposta, 1)
        bar_a = max(atual / max_val * 80, 2) if atual > 0 else 0
        bar_p = max(proposta / max_val * 80, 2) if proposta > 0 else 0
        delta = proposta - atual
        delta_color = TAG["verde"] if delta > 0 else (TAG["rosa"] if delta < 0 else TAG["text_muted"])
        html += (
            f'<div class="comp-row">'
            f'<div class="comp-label">{label}</div>'
            f'<div class="comp-bars">'
            f'<div class="comp-pair">'
            f'<span class="comp-tag">Atual</span>'
            f'<div class="comp-bar-bg"><div class="comp-bar" style="width:{bar_a}%;background:{TAG["rosa"]}">'
            f'</div></div><span class="comp-val">{atual:.1f}%</span>'
            f'</div>'
            f'<div class="comp-pair">'
            f'<span class="comp-tag">Proposta</span>'
            f'<div class="comp-bar-bg"><div class="comp-bar" style="width:{bar_p}%;background:{TAG["laranja"]}">'
            f'</div></div><span class="comp-val">{proposta:.1f}%</span>'
            f'</div>'
            f'</div>'
            f'<div class="comp-delta" style="color:{delta_color}">{delta:+.1f}pp</div>'
            f'</div>'
        )
    html += '</div>'
    return html


def _html_score_gauge(score, label, max_score=100):
    """Pure CSS circular gauge for scores."""
    pct = min(score / max_score * 100, 100) if max_score > 0 else 0
    if pct >= 80:
        color = TAG["verde"]
    elif pct >= 60:
        color = TAG["azul"]
    elif pct >= 40:
        color = TAG["amarelo"]
    else:
        color = TAG["rosa"]
    return (
        f'<div class="gauge-card">'
        f'<div class="gauge-circle" style="background:conic-gradient({color} {pct * 3.6}deg, '
        f'{TAG["bg_card_alt"]} {pct * 3.6}deg)">'
        f'<div class="gauge-inner">{score:.0f}</div>'
        f'</div>'
        f'<div class="gauge-label">{label}</div>'
        f'</div>'
    )


# ══════════════════════════════════════════════════════════
# V3 - FULL PPTX ~22 SECTION PROPOSAL
# ══════════════════════════════════════════════════════════

def _generate_html_v3(prospect, proposta, charts_html=None):
    """Generate full PPTX-equivalent proposal HTML with ~22 sections in 4 parts."""
    nome = prospect.get("nome", "")
    perfil = prospect.get("perfil_investidor", "")
    patrimonio = prospect.get("patrimonio_investivel", 0)
    horizonte = prospect.get("horizonte_investimento", "N/A")
    data_hoje = datetime.now().strftime("%d/%m/%Y")

    diagnostico = proposta.get("diagnostico_texto", "")
    recomendacao = proposta.get("recomendacao_texto", "")
    section_texts = proposta.get("section_texts", {}) or {}
    analytics = proposta.get("analytics_data", {}) or {}
    bottom_up = proposta.get("bottom_up_classification", []) or []
    politica_inv = proposta.get("politica_investimentos", {}) or {}
    fundos_sugeridos = proposta.get("fundos_sugeridos", []) or []
    proposta_comercial = proposta.get("proposta_comercial", {}) or {}

    carteira_proposta = proposta.get("carteira_proposta", [])
    if isinstance(carteira_proposta, str):
        try:
            carteira_proposta = json.loads(carteira_proposta)
        except Exception:
            carteira_proposta = []

    plano = proposta.get("plano_transicao", [])
    if isinstance(plano, str):
        try:
            plano = json.loads(plano)
        except Exception:
            plano = []

    logo_b64 = _load_logo()

    # Prospect family/patrimony data
    estrutura_familiar = prospect.get("estrutura_familiar", [])
    if isinstance(estrutura_familiar, str):
        try:
            estrutura_familiar = json.loads(estrutura_familiar)
        except Exception:
            estrutura_familiar = []
    estrutura_patrimonial = prospect.get("estrutura_patrimonial", {})
    if isinstance(estrutura_patrimonial, str):
        try:
            estrutura_patrimonial = json.loads(estrutura_patrimonial)
        except Exception:
            estrutura_patrimonial = {}
    plano_sucessorio = prospect.get("plano_sucessorio", {})
    if isinstance(plano_sucessorio, str):
        try:
            plano_sucessorio = json.loads(plano_sucessorio)
        except Exception:
            plano_sucessorio = {}

    has_patrimony = (
        (isinstance(estrutura_familiar, list) and any(m.get("nome") for m in estrutura_familiar if isinstance(m, dict)))
        or section_texts.get("estrutura_patrimonial_texto")
    )

    # ── Generate chart HTML fragments ──
    allocation = analytics.get("allocation", {})

    hero_donut = _html_donut_from_portfolio(carteira_proposta, "Alocacao Proposta TAG")
    alloc_bars = _html_allocation_bars_css(carteira_proposta)

    # Allocation comparison chart (Plotly)
    alloc_chart = ""
    if HAS_CHARTS and allocation.get("class_breakdown"):
        try:
            alloc_chart = _embed_chart(chart_allocation_comparison(allocation))
        except Exception:
            pass

    # Concentration chart
    concentration = analytics.get("concentration", [])
    conc_chart = ""
    if HAS_CHARTS and concentration:
        try:
            conc_chart = _embed_chart(chart_concentration_by_issuer(concentration))
        except Exception:
            pass

    # Bottom-up matrix chart
    bu_chart = ""
    if HAS_CHARTS and bottom_up:
        try:
            bu_chart = _embed_chart(chart_bottom_up_matrix(bottom_up))
        except Exception:
            pass

    # Efficiency scatter chart
    efficiency = analytics.get("efficiency", {})
    eff_chart = ""
    if HAS_CHARTS and efficiency.get("efficiency_by_window"):
        try:
            eff_chart = _embed_chart(chart_risk_return_frontier(efficiency))
        except Exception:
            pass

    # Liquidity comparison chart
    liquidity = analytics.get("liquidity", {})
    liq_chart = ""
    if HAS_CHARTS and liquidity.get("atual_buckets") and liquidity.get("proposta_buckets"):
        try:
            liq_chart = _embed_chart(chart_liquidity_comparison(
                liquidity["atual_buckets"], liquidity["proposta_buckets"]
            ))
        except Exception:
            pass

    # Maturity ladder chart
    maturity = analytics.get("maturity", [])
    mat_chart = ""
    if HAS_CHARTS and maturity:
        try:
            mat_chart = _embed_chart(chart_maturity_ladder(maturity))
        except Exception:
            pass

    # Tax comparison chart
    tax = analytics.get("tax", {})
    tax_chart = ""
    if HAS_CHARTS and tax:
        try:
            tax_chart = _embed_chart(chart_tax_comparison(tax))
        except Exception:
            pass

    # Allocation comparison bars (CSS fallback when no analytics)
    alloc_comp_css = ""
    if allocation.get("class_breakdown"):
        items = [(b["classe"], b.get("pct_atual", 0), b.get("pct_proposta", 0))
                 for b in allocation["class_breakdown"]]
        alloc_comp_css = _html_comparison_bars_css(items, "Atual vs Proposta por Classe")

    # Objectives as visual badges
    objetivos = prospect.get("objetivos", [])
    if isinstance(objetivos, str):
        try:
            objetivos = json.loads(objetivos)
        except Exception:
            objetivos = []

    # ── Build all sections ──
    sections_html = []
    toc_items = []
    sec_num = 0

    # ━━━ PART 0: SOBRE A TAG ━━━
    sections_html.append(_html_part_header("Sobre a TAG Investimentos"))
    sec_num += 1
    sections_html.append(_html_section_sobre_tag(sec_num))
    toc_items.append((sec_num, "A TAG Investimentos"))

    # ━━━ PART I: ESTRUTURA PATRIMONIAL (conditional) ━━━
    if has_patrimony:
        sections_html.append(_html_part_header("Parte I - Estrutura Patrimonial e Sucessoria"))

        sec_num += 1
        sections_html.append(_html_section_familia(sec_num, estrutura_familiar, estrutura_patrimonial, plano_sucessorio, section_texts))
        toc_items.append((sec_num, "Estrutura Familiar e Sucessoria"))

        sec_num += 1
        sections_html.append(_html_section_patrimonio(sec_num, estrutura_patrimonial, section_texts))
        toc_items.append((sec_num, "Analise Patrimonial e Alternativas"))

    # ━━━ PART II: GESTAO DE INVESTIMENTOS ━━━
    sections_html.append(_html_part_header("Parte II - Gestao de Investimentos"))

    # Sumario Executivo
    sec_num += 1
    sections_html.append(_html_section(sec_num, "Sumario Executivo",
                                       _md_to_html(section_texts.get("sumario_executivo", ""))))
    toc_items.append((sec_num, "Sumario Executivo"))

    # Premissas e Filosofia
    sec_num += 1
    sections_html.append(_html_section(sec_num, "Premissas e Filosofia de Investimento",
                                       _md_to_html(section_texts.get("premissas_filosofia", ""))))
    toc_items.append((sec_num, "Premissas e Filosofia"))

    # Diagnostico Top Down
    sec_num += 1
    s_td_content = _md_to_html(diagnostico)
    if alloc_chart:
        s_td_content += '<h3>Alocacao por Classe: Atual vs Proposta</h3>'
        s_td_content += alloc_chart
    if alloc_comp_css:
        s_td_content += alloc_comp_css
    if allocation.get("class_breakdown"):
        s_td_content += _html_allocation_table(allocation)
    sections_html.append(_html_section(sec_num, "Diagnostico Top Down", s_td_content))
    toc_items.append((sec_num, "Diagnostico Top Down"))

    # Diagnostico de Risco
    sec_num += 1
    risk = analytics.get("risk", {})
    s_risk = ""
    if risk:
        s_risk += _html_metrics_grid([
            ("HHI por Emissor", f"{risk.get('hhi_issuer', 0):,.0f}"),
            ("Top 5 Emissores", f"{risk.get('top5_issuer_pct', 0):.1f}%"),
            ("PL Total", f"R$ {risk.get('total_pl', 0):,.0f}"),
        ])
        concentration = analytics.get("concentration", [])
        if concentration:
            if conc_chart:
                s_risk += '<h3>Concentracao por Emissor</h3>'
                s_risk += conc_chart
            s_risk += _html_concentration_table(concentration)
        strategy = risk.get("concentration_by_strategy", [])
        if strategy:
            s_risk += "<h3>Concentracao por Estrategia</h3>"
            s_risk += _html_generic_table(
                ["Estrategia", "Financeiro", "%", "# Ativos"],
                [[s["estrategia"], f"R$ {s['financeiro']:,.0f}", f"{s['pct']:.1f}%",
                  str(s["num_ativos"])] for s in strategy],
            )
    else:
        s_risk = "<p class='muted'>Dados de risco nao disponiveis.</p>"
    sections_html.append(_html_section(sec_num, "Diagnostico de Risco e Concentracao", s_risk))
    toc_items.append((sec_num, "Diagnostico de Risco"))

    # Analise Bottom Up
    sec_num += 1
    s_bu = _md_to_html(section_texts.get("analise_bottom_up_texto", ""))
    if bottom_up:
        if bu_chart:
            s_bu += '<h3>Matriz de Classificacao</h3>'
            s_bu += bu_chart
        s_bu += _html_bottom_up_table(bottom_up)
        s_bu += _html_bottom_up_summary(bottom_up)
    sections_html.append(_html_section(sec_num, "Analise Bottom Up", s_bu))
    toc_items.append((sec_num, "Analise Bottom Up"))

    # Diagnostico de Eficiencia
    sec_num += 1
    s_eff = ""
    if eff_chart:
        s_eff += '<h3>Fronteira Risco x Retorno</h3>'
        s_eff += eff_chart
    if efficiency.get("efficiency_by_window"):
        s_eff += _html_generic_table(
            ["Janela", "Retorno", "Volatilidade", "Sharpe", "Sortino", "Alpha CDI"],
            [[w["janela"], f"{w['retorno']:.2f}%", f"{w['volatilidade']:.2f}%",
              f"{w['sharpe']:.2f}", f"{w['sortino']:.2f}", f"{w['alpha_cdi']:.2f}%"]
             for w in efficiency["efficiency_by_window"]],
        )
    else:
        s_eff = "<p class='muted'>Execute o backtest para metricas de eficiencia.</p>"
    sections_html.append(_html_section(sec_num, "Diagnostico de Eficiencia", s_eff))
    toc_items.append((sec_num, "Diagnostico de Eficiencia"))

    # Objetivos da Proposta
    sec_num += 1
    sections_html.append(_html_section(sec_num, "Objetivos da Carteira Proposta",
                                       _md_to_html(section_texts.get("objetivos_proposta", ""))))
    toc_items.append((sec_num, "Objetivos da Proposta"))

    # Proposta Top Down
    sec_num += 1
    s_ptd = _md_to_html(section_texts.get("proposta_top_down_texto", ""))
    # Donut chart of proposed portfolio
    donut_proposta = _html_donut_from_portfolio(carteira_proposta, "Alocacao Proposta TAG")
    if donut_proposta:
        s_ptd += donut_proposta
    if allocation.get("class_breakdown"):
        s_ptd += _html_allocation_table(allocation)
    if not donut_proposta and carteira_proposta:
        s_ptd += _html_allocation_bars_css(carteira_proposta)
    sections_html.append(_html_section(sec_num, "Carteira Proposta - Visao Top Down", s_ptd))
    toc_items.append((sec_num, "Proposta Top Down"))

    # Proposta Bottom Up (detailed table)
    sec_num += 1
    s_pbu = _md_to_html(section_texts.get("proposta_bottom_up_texto", ""))
    if carteira_proposta:
        s_pbu += _html_portfolio_detail_table_v3(carteira_proposta, patrimonio)
    sections_html.append(_html_section(sec_num, "Carteira Proposta - Detalhamento por Ativo", s_pbu))
    toc_items.append((sec_num, "Proposta Bottom Up"))

    # Ativos Sugeridos (fund cards)
    sec_num += 1
    s_fc = _md_to_html(section_texts.get("fund_cards_texto", ""))
    if fundos_sugeridos:
        s_fc += _html_fund_cards_v3(fundos_sugeridos)
    elif carteira_proposta:
        s_fc += _html_fund_cards(carteira_proposta)
    sections_html.append(_html_section(sec_num, "Ativos Sugeridos", s_fc))
    toc_items.append((sec_num, "Ativos Sugeridos"))

    # Historico de Retornos
    sec_num += 1
    s_hist = charts_html or ""
    s_hist += (
        '<p class="muted" style="margin-top:12px">Retornos calculados com proxies de mercado '
        'por classe de ativo. Rentabilidade passada nao e garantia de rentabilidade futura.</p>'
    )
    sections_html.append(_html_section(sec_num, "Historico de Retornos", s_hist))
    toc_items.append((sec_num, "Historico de Retornos"))

    # Backtest
    sec_num += 1
    s_bt = (
        "<p>O backtest completo esta disponivel na versao interativa da proposta. "
        "Solicite ao seu assessor a demonstracao das simulacoes historicas.</p>"
    )
    sections_html.append(_html_section(sec_num, "Backtest - Simulacao Historica", s_bt))
    toc_items.append((sec_num, "Backtest"))

    # Liquidez e Vencimentos
    sec_num += 1
    s_liq = ""
    if liquidity:
        s_liq += _html_metrics_grid([
            ("Caixa Rapido (D+5) - Atual", f"{liquidity.get('pct_cash_quickly_atual', 0):.1f}%"),
            ("Caixa Rapido (D+5) - Proposta", f"{liquidity.get('pct_cash_quickly_proposta', 0):.1f}%"),
        ])
        if liq_chart:
            s_liq += '<h3>Perfil de Liquidez: Atual vs Proposta</h3>'
            s_liq += liq_chart
        s_liq += _html_liquidity_table(liquidity)
    if maturity:
        s_liq += "<h3>Escalonamento de Vencimentos</h3>"
        if mat_chart:
            s_liq += mat_chart
        s_liq += _html_generic_table(
            ["Periodo", "Financeiro", "% PL"],
            [[m["label"], f"R$ {m['total_financeiro']:,.0f}", f"{m['pct']:.1f}%"]
             for m in maturity],
        )
    if not liquidity and not maturity:
        s_liq = "<p class='muted'>Dados de liquidez nao disponiveis.</p>"
    sections_html.append(_html_section(sec_num, "Liquidez e Vencimentos", s_liq))
    toc_items.append((sec_num, "Liquidez e Vencimentos"))

    # Eficiencia Tributaria
    sec_num += 1
    s_tax = ""
    if tax:
        s_tax += _html_metrics_grid([
            ("% Isentos - Atual", f"{tax.get('atual_isentos_pct', 0):.1f}%"),
            ("% Isentos - Proposta", f"{tax.get('proposta_isentos_pct', 0):.1f}%"),
            ("Delta", f"{tax.get('delta_isentos', 0):+.1f}pp"),
        ])
        if tax_chart:
            s_tax += tax_chart
        turnover = tax.get("turnover", {})
        if turnover:
            s_tax += (
                f'<div class="turnover-grid">'
                f'<div class="turnover-item saindo">'
                f'<div class="turnover-num">{turnover.get("saindo", 0)}</div>'
                f'<div class="turnover-label">Ativos Saindo</div></div>'
                f'<div class="turnover-item entrando">'
                f'<div class="turnover-num">{turnover.get("entrando", 0)}</div>'
                f'<div class="turnover-label">Ativos Entrando</div></div>'
                f'<div class="turnover-item mantidos">'
                f'<div class="turnover-num">{turnover.get("mantidos", 0)}</div>'
                f'<div class="turnover-label">Ativos Mantidos</div></div>'
                f'</div>'
            )
    else:
        s_tax = "<p class='muted'>Dados tributarios nao disponiveis.</p>"
    sections_html.append(_html_section(sec_num, "Eficiencia Tributaria", s_tax))
    toc_items.append((sec_num, "Eficiencia Tributaria"))

    # Plano de Implementacao
    sec_num += 1
    s_plan = ""
    if plano:
        headers = list(plano[0].keys()) if plano else []
        rows = [list(item.values()) for item in plano]
        s_plan += _html_generic_table(headers, [[str(v) for v in row] for row in rows])
    elif recomendacao:
        s_plan += "<h3>Recomendacao de Implementacao</h3>"
        s_plan += _md_to_html(recomendacao)
    else:
        s_plan = "<p class='muted'>Plano de transicao nao definido.</p>"
    sections_html.append(_html_section(sec_num, "Plano de Implementacao", s_plan))
    toc_items.append((sec_num, "Plano de Implementacao"))

    # ━━━ PART III: GOVERNANCA ━━━
    sections_html.append(_html_part_header("Parte III - Governanca e Politica de Investimentos"))

    # Politica de Investimentos
    sec_num += 1
    sections_html.append(_html_section_politica(sec_num, politica_inv, section_texts, prospect))
    toc_items.append((sec_num, "Politica de Investimentos"))

    # Monitoramento e Governanca
    sec_num += 1
    s_mon = _md_to_html(section_texts.get("monitoramento_governanca", ""))
    gov_text = section_texts.get("governanca_texto", "")
    if gov_text:
        if s_mon:
            s_mon += "<hr>"
        s_mon += _md_to_html(gov_text)
    sections_html.append(_html_section(sec_num, "Monitoramento e Governanca", s_mon))
    toc_items.append((sec_num, "Monitoramento e Governanca"))

    # ━━━ PART IV: PROPOSTA COMERCIAL ━━━
    sections_html.append(_html_part_header("Parte IV - Proposta Comercial"))

    # Proposta Comercial (fee table)
    sec_num += 1
    sections_html.append(_html_section_comercial(sec_num, proposta_comercial, prospect))
    toc_items.append((sec_num, "Proposta Comercial"))

    # Contato
    sec_num += 1
    sections_html.append(_html_section_contato(sec_num))
    toc_items.append((sec_num, "Contato"))

    # ── Build TOC (2-column layout) ──
    half = (len(toc_items) + 1) // 2
    toc_col1 = toc_items[:half]
    toc_col2 = toc_items[half:]

    toc_html = '<div class="toc"><h2>Sumario</h2><div class="toc-columns">'
    toc_html += '<ol>'
    for num, title in toc_col1:
        toc_html += f'<li value="{num}"><a href="#section-{num}">{title}</a></li>'
    toc_html += '</ol><ol>'
    for num, title in toc_col2:
        toc_html += f'<li value="{num}"><a href="#section-{num}">{title}</a></li>'
    toc_html += '</ol></div></div>'

    # ── Disclaimers ──
    disclaimers_html = _html_disclaimers()

    all_sections = "\n".join(sections_html)

    obj_badges = ""
    if objetivos:
        obj_badges = '<div class="obj-badges">'
        for obj in objetivos:
            obj_badges += f'<span class="obj-badge">{obj}</span>'
        obj_badges += '</div>'

    # Retirada mensal info
    retirada = prospect.get("retirada_mensal", 0)
    retirada_html = ""
    if retirada and float(retirada) > 0:
        retirada_html = (
            f'<div class="metric-card">'
            f'<div class="label">Retirada Mensal</div>'
            f'<div class="value">R$ {float(retirada):,.0f}</div>'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proposta de Investimento - {nome} | TAG Investimentos</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.35.0.min.js" charset="utf-8"></script>
    <style>
        {_css_v3()}
    </style>
</head>
<body>
    <div class="container">
        <!-- COVER -->
        <div class="cover">
            {_logo_html(logo_b64)}
            <h1>Proposta de Investimento</h1>
            <div class="subtitle">{nome}</div>
            <div class="badge">Perfil {perfil}</div>
            <div class="date">{data_hoje}</div>
        </div>

        <!-- METRICS -->
        <div class="section">
            <div class="metrics">
                <div class="metric-card">
                    <div class="label">Patrimonio</div>
                    <div class="value">R$ {patrimonio:,.0f}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Perfil</div>
                    <div class="value">{perfil}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Ativos Propostos</div>
                    <div class="value">{len(carteira_proposta)}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Horizonte</div>
                    <div class="value">{horizonte[:15]}</div>
                </div>
                {retirada_html}
            </div>
            {obj_badges}
        </div>

        <!-- HERO CHART: Portfolio Allocation Overview -->
        <div class="section">
            <div class="section-header">
                <span class="section-num">&#9733;</span>
                <h2>Visao Geral da Alocacao</h2>
            </div>
            <div class="hero-charts">
                <div class="hero-chart-left">
                    {hero_donut}
                </div>
                <div class="hero-chart-right">
                    {alloc_bars}
                </div>
            </div>
        </div>

        <!-- TABLE OF CONTENTS -->
        {toc_html}

        <!-- ALL SECTIONS -->
        {all_sections}

        <!-- DISCLAIMERS -->
        {disclaimers_html}

        <!-- FOOTER -->
        <div class="footer">
            <p>TAG Investimentos &copy; {datetime.now().year} - Documento confidencial</p>
        </div>
    </div>
</body>
</html>"""

    return html


# ── V3 Section Builders ──

def _html_part_header(title):
    """Render a part divider in the proposal."""
    return (
        f'<div class="part-header">'
        f'<span>{title}</span>'
        f'</div>'
    )


def _html_section_sobre_tag(sec_num):
    """Render 'About TAG' section from institutional data."""
    try:
        from shared.tag_institucional import TAG_INFO, SOLUCOES_360
        info = TAG_INFO
    except ImportError:
        info = {
            "descricao_jornada": (
                "A TAG Investimentos e uma gestora independente com mais de 20 anos de historia, "
                "R$ 15 bilhoes sob gestao e uma equipe de 60 profissionais dedicados."
            ),
            "anos_historia": 20, "aum": "R$ 15 bilhoes",
            "familias": 100, "profissionais": 60,
        }
        SOLUCOES_360 = {}

    # Institutional metrics
    metrics_html = _html_metrics_grid([
        ("Anos de Historia", f"{info.get('anos_historia', 20)}+"),
        ("AUM", info.get("aum", "R$ 15 bilhoes")),
        ("Familias", str(info.get("familias", 100))),
        ("Profissionais", str(info.get("profissionais", 60))),
    ])

    # Description
    desc = info.get("descricao_jornada", info.get("descricao_curta", ""))

    # 360 solutions
    sol_html = ""
    if SOLUCOES_360:
        sol_html = '<h3>Solucoes 360 graus</h3><div class="solutions-grid">'
        for key, solucao in SOLUCOES_360.items():
            sol_html += f'<div class="solution-card"><strong>{solucao["titulo"]}</strong><ul>'
            for item in solucao["itens"][:4]:
                sol_html += f'<li>{item}</li>'
            sol_html += '</ul></div>'
        sol_html += '</div>'

    content = f"<p>{desc}</p>{metrics_html}{sol_html}"
    return _html_section(sec_num, "A TAG Investimentos", content)


def _html_section_familia(sec_num, estrutura_familiar, estrutura_patrimonial, plano_sucessorio, section_texts):
    """Render family structure and succession section."""
    content = ""

    # Family table
    valid_members = [m for m in estrutura_familiar if isinstance(m, dict) and m.get("nome")] if isinstance(estrutura_familiar, list) else []
    if valid_members:
        content += '<h3>Composicao Familiar</h3>'
        content += '<table><thead><tr><th>Nome</th><th>Relacao</th><th>Idade</th><th>Regime</th></tr></thead><tbody>'
        for m in valid_members:
            content += (
                f'<tr><td>{m.get("nome", "")}</td><td>{m.get("relacao", "")}</td>'
                f'<td class="num">{m.get("idade", "")}</td>'
                f'<td>{m.get("regime_casamento", "")}</td></tr>'
            )
        content += '</tbody></table>'

    # Patrimonio para sucessao
    if isinstance(estrutura_patrimonial, dict) and estrutura_patrimonial.get("patrimonio_sucessao"):
        val = estrutura_patrimonial["patrimonio_sucessao"]
        content += f'<p><strong>Patrimonio para Sucessao:</strong> R$ {float(val):,.0f}</p>'

    # Succession instruments
    if isinstance(plano_sucessorio, dict) and any(plano_sucessorio.values()):
        content += '<h3>Instrumentos de Planejamento Atuais</h3><ul>'
        instruments = {
            "testamento": "Testamento",
            "doacao_antecipada": "Doacao em adiantamento de legitima",
            "seguro_vida": "Seguro de vida / Previdencia",
            "trust": "Trust / PIC",
            "holding_familiar": "Holding familiar",
            "protocolo_familiar": "Protocolo familiar",
        }
        for key, label in instruments.items():
            if plano_sucessorio.get(key):
                content += f'<li>{label}</li>'
        content += '</ul>'
        if plano_sucessorio.get("observacoes"):
            content += f'<p><strong>Observacoes:</strong> {plano_sucessorio["observacoes"]}</p>'

    # AI text
    text = section_texts.get("estrutura_patrimonial_texto", "")
    if text:
        content += "<hr>" + _md_to_html(text)

    return _html_section(sec_num, "Estrutura Familiar e Sucessoria", content)


def _html_section_patrimonio(sec_num, estrutura_patrimonial, section_texts):
    """Render patrimonial analysis and restructuring alternatives section."""
    content = ""

    if isinstance(estrutura_patrimonial, dict) and estrutura_patrimonial.get("tipo"):
        estr = estrutura_patrimonial
        content += f'<p><strong>Tipo de estrutura:</strong> {estr.get("tipo", "N/A")}</p>'
        if estr.get("possui_offshore"):
            content += (
                f'<p><strong>Offshore:</strong> {estr.get("jurisdicao", "")} '
                f'- {estr.get("tipo_offshore", "")}</p>'
            )
        if estr.get("patrimonio_offshore"):
            content += f'<p><strong>Patrimonio Offshore:</strong> US$ {float(estr["patrimonio_offshore"]):,.0f}</p>'
        if estr.get("holdings_texto"):
            content += f'<p><strong>Holdings / PICs:</strong> {estr["holdings_texto"]}</p>'

    # AI alternatives
    text = section_texts.get("alternativas_sucessao_texto", "")
    if text:
        if content:
            content += "<hr>"
        content += _md_to_html(text)

    if not content:
        content = "<p class='muted'>Dados patrimoniais nao cadastrados.</p>"

    return _html_section(sec_num, "Analise Patrimonial e Alternativas de Reestruturacao", content)


def _html_section_politica(sec_num, politica_inv, section_texts, prospect):
    """Render investment policy section (slides 54-60)."""
    content = ""

    # AI-generated policy text
    pol_text = ""
    if isinstance(politica_inv, dict):
        pol_text = politica_inv.get("texto", "")
    if not pol_text:
        pol_text = section_texts.get("politica_investimentos_texto", "")
    if pol_text:
        content += _md_to_html(pol_text)

    # Limits table
    limites = {}
    if isinstance(politica_inv, dict):
        limites = politica_inv.get("limites", {})
    if not limites:
        try:
            from shared.tag_institucional import LIMITES_POLITICA_DEFAULT
            perfil = prospect.get("perfil_investidor", "Moderado")
            limites = LIMITES_POLITICA_DEFAULT.get(perfil, {})
        except Exception:
            pass

    if limites:
        content += '<h3>Limites da Politica</h3>'
        label_map = {
            "max_por_emissor": "Max por emissor (%)",
            "max_por_gestor": "Max por gestor (%)",
            "max_renda_variavel": "Max renda variavel (%)",
            "max_credito_privado": "Max credito privado (%)",
            "max_alternativos": "Max alternativos (%)",
            "min_liquidez_d5": "Min liquidez D+5 (%)",
            "rating_minimo": "Rating minimo",
        }
        rows = []
        for key, label in label_map.items():
            val = limites.get(key, "")
            if val != "" and val is not None:
                display_val = f"{val}%" if isinstance(val, (int, float)) else str(val)
                rows.append([label, display_val])
        if rows:
            content += _html_generic_table(["Limite", "Valor"], rows)

    # S1/S2 classification
    try:
        from shared.tag_institucional import BACEN_S1, BACEN_S2
        content += '<h3>Classificacao BACEN - Instituicoes Autorizadas</h3>'
        content += (
            f'<p><strong>S1:</strong> {", ".join(BACEN_S1)}</p>'
            f'<p><strong>S2:</strong> {", ".join(BACEN_S2)}</p>'
        )
    except Exception:
        pass

    if not content:
        content = "<p class='muted'>Politica de investimentos nao gerada.</p>"

    return _html_section(sec_num, "Politica de Investimentos", content)


def _html_section_comercial(sec_num, proposta_comercial, prospect):
    """Render commercial proposal section (slides 61-64)."""
    content = ""

    fee_table = []
    servicos = []
    if isinstance(proposta_comercial, dict):
        fee_table = proposta_comercial.get("fee_table", [])
        servicos = proposta_comercial.get("servicos", [])

    if not fee_table:
        try:
            from shared.tag_institucional import FEE_TABLE_DEFAULT, SERVICOS_DISPONIVEIS
            fee_table = FEE_TABLE_DEFAULT
            if not servicos:
                servicos = SERVICOS_DISPONIVEIS
        except Exception:
            pass

    if fee_table:
        content += '<h3>Tabela de Taxas</h3>'
        rows = []
        for f in fee_table:
            faixa = f.get("faixa", "")
            taxa = f.get("taxa_adm", 0)
            rows.append([faixa, f"{taxa:.2f}%"])
        content += _html_generic_table(["Faixa", "Taxa Adm (% a.a.)"], rows)

    taxa_perf = proposta_comercial.get("taxa_performance", 0) if isinstance(proposta_comercial, dict) else 0
    if taxa_perf and taxa_perf > 0:
        content += f'<p><strong>Taxa de Performance:</strong> {taxa_perf:.1f}%</p>'

    if servicos:
        content += '<h3>Servicos Incluidos</h3><ul>'
        for svc in servicos:
            content += f'<li>{svc}</li>'
        content += '</ul>'

    condicoes = proposta_comercial.get("condicoes_especiais", "") if isinstance(proposta_comercial, dict) else ""
    if condicoes:
        content += f'<p><strong>Condicoes Especiais:</strong> {condicoes}</p>'

    if not content:
        content = "<p class='muted'>Proposta comercial nao definida.</p>"

    return _html_section(sec_num, "Proposta Comercial", content)


def _html_section_contato(sec_num):
    """Render contact section."""
    try:
        from shared.tag_institucional import TAG_INFO
        info = TAG_INFO
    except ImportError:
        info = {
            "nome": "TAG Investimentos",
            "endereco": "Av. Brig. Faria Lima, 3.311 - 12 andar",
            "cep": "04538-133", "cidade": "Sao Paulo", "uf": "SP",
            "telefone": "(11) 3474-0000", "email": "ouvidoria@taginvest.com.br",
        }

    content = (
        f'<div class="contact-card">'
        f'<h3>{info.get("nome", "TAG Investimentos")}</h3>'
        f'<p>{info.get("endereco", "")}</p>'
        f'<p>CEP: {info.get("cep", "")} - {info.get("cidade", "")}/{info.get("uf", "")}</p>'
        f'<p>Telefone: {info.get("telefone", "")}</p>'
        f'<p>Email: {info.get("email", "")}</p>'
        f'</div>'
    )
    return _html_section(sec_num, "Contato", content)


def _html_disclaimers():
    """Render full disclaimers from tag_institucional."""
    try:
        from shared.tag_institucional import DISCLAIMERS
    except ImportError:
        DISCLAIMERS = [
            "Este documento e uma proposta de investimento e nao constitui oferta, "
            "solicitacao ou recomendacao de compra ou venda de ativos.",
            "Rentabilidade passada nao e garantia de rentabilidade futura.",
            "Investimentos envolvem riscos e podem resultar em perdas patrimoniais.",
        ]

    html = '<div class="disclaimers"><h3>Consideracoes Importantes</h3>'
    for i, d in enumerate(DISCLAIMERS):
        html += f'<p class="disclaimer-item">{i + 1}. {d}</p>'
    html += '</div>'
    return html


def _html_portfolio_detail_table_v3(carteira_proposta, patrimonio):
    """Render detailed portfolio table v3 with enriched columns (slides 34-36 style)."""
    if not carteira_proposta:
        return "<p class='muted'>Nenhuma carteira proposta disponivel.</p>"

    patrimonio = float(patrimonio or 0)

    html = '<h3 style="margin-top:24px">Detalhamento Completo da Carteira Proposta</h3>'
    html += '<table class="table-detail"><thead><tr>'
    html += ('<th>Ativo</th><th>Classe</th><th>Instituicao</th><th>Liquidez</th>'
             '<th class="num">R$ Proposta</th><th class="num">% Alvo</th>'
             '<th>Retorno Alvo</th><th class="num">Ret 12m</th>'
             '<th class="num">Vol</th><th>Acao</th>')
    html += '</tr></thead><tbody>'

    total_pct = 0
    total_rs = 0

    for item in carteira_proposta:
        name = item.get("ativo", item.get("Ativo", ""))
        classe = item.get("classe", item.get("Classe", ""))
        inst = item.get("instituicao", item.get("gestor", ""))
        resgate = item.get("resgate", "")
        pct = float(item.get("pct_alvo", item.get("% Alvo", 0)))
        ret_alvo = item.get("retorno_alvo", "")
        ret_12m = item.get("retorno_12m", 0)
        vol = item.get("volatilidade", 0)
        acao = item.get("acao_recomendada", "Aplicar")
        rs = float(item.get("proposta_rs", 0))
        if rs == 0 and patrimonio > 0 and pct > 0:
            rs = patrimonio * pct / 100

        total_pct += pct
        total_rs += rs

        # Color for action
        acao_color = TAG["verde"] if acao in ("Manter", "Aplicar") else (
            TAG["rosa"] if "Resgat" in acao or "Said" in acao else TAG["laranja"]
        )

        ret_12m_str = f"{ret_12m:.2f}%" if ret_12m else "-"
        vol_str = f"{vol:.2f}%" if vol else "-"

        html += (
            f'<tr>'
            f'<td><strong>{name}</strong></td>'
            f'<td>{classe}</td>'
            f'<td>{inst}</td>'
            f'<td>{resgate}</td>'
            f'<td class="num">R$ {rs:,.0f}</td>'
            f'<td class="num">{pct:.1f}%</td>'
            f'<td>{ret_alvo}</td>'
            f'<td class="num">{ret_12m_str}</td>'
            f'<td class="num">{vol_str}</td>'
            f'<td><span style="color:{acao_color};font-weight:600">{acao}</span></td>'
            f'</tr>'
        )

    # Total row
    html += (
        f'<tr class="total-row">'
        f'<td colspan="4"><strong>TOTAL</strong></td>'
        f'<td class="num"><strong>R$ {total_rs:,.0f}</strong></td>'
        f'<td class="num"><strong>{total_pct:.1f}%</strong></td>'
        f'<td colspan="4"></td>'
        f'</tr>'
    )
    html += '</tbody></table>'
    html += f'<p class="muted" style="margin-top:8px">{len(carteira_proposta)} ativos na carteira proposta</p>'
    return html


def _html_fund_cards_v3(fundos_sugeridos):
    """Render enriched fund cards with catalog data (slides 42-53 style)."""
    if not fundos_sugeridos:
        return ""

    html = '<div class="fund-cards">'
    for fund in fundos_sugeridos:
        nome = fund.get("nome", "")
        tipo = fund.get("tipo", fund.get("classe", ""))
        subtipo = fund.get("subtipo", "")
        pct = fund.get("pct_alvo", 0)
        gestor = fund.get("gestor", "")
        resgate = fund.get("resgate", "")
        retorno_alvo = fund.get("retorno_alvo", "")
        ret_12m = fund.get("retorno_12m", 0)
        estrategia = fund.get("estrategia", "")
        risco = fund.get("risco_principal", "")
        horizonte = fund.get("horizonte_minimo", "")

        tag_text = tipo + (f" - {subtipo}" if subtipo else "")

        html += (
            f'<div class="fund-card">'
            f'<div class="fund-card-header">'
            f'<strong>{nome}</strong>'
            f'<span class="fund-pct">{pct:.1f}%</span>'
            f'</div>'
            f'<div class="fund-class">{tag_text}</div>'
        )
        # Details line
        details = []
        if gestor:
            details.append(f"Gestor: {gestor}")
        if resgate:
            details.append(f"Resgate: {resgate}")
        if details:
            html += f'<div class="fund-detail">{" | ".join(details)}</div>'

        # Returns line
        ret_parts = []
        if retorno_alvo:
            ret_parts.append(f"Alvo: {retorno_alvo}")
        if ret_12m:
            ret_parts.append(f"12m: {ret_12m:.2f}%")
        if ret_parts:
            html += f'<div class="fund-returns">{" | ".join(ret_parts)}</div>'

        # Strategy description
        if estrategia:
            html += f'<div class="fund-just">{estrategia[:250]}</div>'

        # Risk and horizon
        meta_parts = []
        if risco:
            meta_parts.append(f"Risco: {risco}")
        if horizonte:
            meta_parts.append(f"Horizonte: {horizonte}")
        if meta_parts:
            html += f'<div class="fund-meta">{" | ".join(meta_parts)}</div>'

        html += '</div>'
    html += '</div>'
    return html


# ── V3 CSS ──

def _css_v3():
    """CSS styles for v3 proposal (extends v2 with new elements)."""
    return f"""
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: {TAG["bg_dark"]};
            color: {TAG["offwhite"]};
            line-height: 1.7;
        }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 24px; }}

        /* Cover */
        .cover {{
            text-align: center;
            padding: 80px 40px;
            background: linear-gradient(135deg, {TAG["vermelho_dark"]} 0%, {TAG["bg_dark"]} 70%);
            border-radius: 16px;
            margin-bottom: 40px;
            border: 1px solid {TAG["vermelho"]}30;
        }}
        .cover img {{ max-width: 180px; margin-bottom: 32px; }}
        .cover h1 {{
            font-size: 2rem; font-weight: 600; color: {TAG["offwhite"]};
            margin-bottom: 8px;
        }}
        .cover .subtitle {{ color: {TAG["laranja"]}; font-size: 1.2rem; font-weight: 500; }}
        .cover .badge {{
            display: inline-block; margin-top: 12px; padding: 6px 20px;
            background: {TAG["laranja"]}20; border: 1px solid {TAG["laranja"]}40;
            border-radius: 20px; color: {TAG["laranja"]}; font-size: 0.85rem; font-weight: 500;
        }}
        .cover .date {{ color: {TAG["text_muted"]}; margin-top: 16px; font-size: 0.9rem; }}

        /* Part Headers */
        .part-header {{
            text-align: center;
            padding: 16px;
            margin: 32px 0 12px 0;
            border-top: 2px solid {TAG["laranja"]}30;
            border-bottom: 2px solid {TAG["laranja"]}30;
        }}
        .part-header span {{
            color: {TAG["laranja"]};
            font-size: 1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
        }}

        /* TOC */
        .toc {{
            background: {TAG["bg_card"]}; border-radius: 12px;
            padding: 24px 32px; margin-bottom: 32px;
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .toc h2 {{
            color: {TAG["laranja"]}; font-size: 1.1rem; margin-bottom: 12px;
            padding-bottom: 8px; border-bottom: 2px solid {TAG["laranja"]}30;
        }}
        .toc-columns {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0 32px;
        }}
        .toc ol {{ padding-left: 20px; }}
        .toc li {{ margin-bottom: 4px; font-size: 0.9rem; }}
        .toc a {{ color: {TAG["offwhite"]}; text-decoration: none; }}
        .toc a:hover {{ color: {TAG["laranja"]}; }}

        /* Sections */
        .section {{
            background: {TAG["bg_card"]}; border-radius: 12px;
            padding: 32px; margin-bottom: 24px;
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .section-header {{
            display: flex; align-items: center; gap: 12px;
            margin-bottom: 20px; padding-bottom: 12px;
            border-bottom: 2px solid {TAG["laranja"]}30;
        }}
        .section-num {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 36px; height: 36px; min-width: 36px;
            background: {TAG["laranja"]}; color: white;
            border-radius: 50%; font-weight: 700; font-size: 0.9rem;
        }}
        .section h2 {{
            color: {TAG["laranja"]}; font-size: 1.2rem; font-weight: 600;
            margin: 0; padding: 0; border: none;
        }}
        .section h3 {{
            color: {TAG["offwhite"]}; font-size: 1rem; font-weight: 600;
            margin: 20px 0 12px 0;
        }}
        .section h4 {{
            color: {TAG["text_muted"]}; font-size: 0.9rem; font-weight: 600;
            margin: 16px 0 8px 0;
        }}
        .section p {{ margin-bottom: 10px; font-size: 0.92rem; }}
        .section ul {{ padding-left: 20px; margin-bottom: 12px; }}
        .section li {{ margin-bottom: 4px; font-size: 0.92rem; }}
        .section hr {{
            border: none; border-top: 1px solid {TAG["vermelho"]}20;
            margin: 16px 0;
        }}

        /* Tables */
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; margin-bottom: 16px; }}
        th {{
            text-align: left; padding: 10px 14px;
            background: {TAG["vermelho_dark"]}; color: {TAG["laranja"]};
            font-weight: 600; font-size: 0.8rem;
            text-transform: uppercase; letter-spacing: 0.05em;
        }}
        td {{
            padding: 8px 14px; border-bottom: 1px solid {TAG["vermelho"]}15;
            font-size: 0.85rem;
        }}
        tr:hover td {{ background: {TAG["vermelho"]}08; }}
        .total-row td {{
            border-top: 2px solid {TAG["laranja"]}40;
            background: {TAG["vermelho_dark"]}80;
            font-weight: 600;
        }}
        .num {{ text-align: right; font-weight: 500; color: {TAG["laranja"]}; }}
        .muted {{ color: {TAG["text_muted"]}; font-size: 0.82rem; }}

        /* Detail table */
        .table-detail th {{ font-size: 0.72rem; padding: 8px 10px; }}
        .table-detail td {{ font-size: 0.8rem; padding: 6px 10px; }}

        /* Metrics */
        .metrics {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px; margin: 16px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, {TAG["bg_card_alt"]} 0%, {TAG["bg_card"]} 100%);
            border-radius: 10px; padding: 16px;
            border: 1px solid {TAG["vermelho"]}20; text-align: center;
        }}
        .metric-card .label {{
            color: {TAG["text_muted"]}; font-size: 0.72rem;
            text-transform: uppercase; letter-spacing: 0.05em;
        }}
        .metric-card .value {{
            color: {TAG["offwhite"]}; font-size: 1.4rem; font-weight: 600; margin-top: 4px;
        }}

        /* Fund cards v3 */
        .fund-cards {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 16px; margin: 20px 0;
        }}
        .fund-card {{
            background: {TAG["bg_card_alt"]}; border-radius: 10px;
            padding: 16px; border-left: 4px solid {TAG["laranja"]};
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .fund-card-header {{
            display: flex; justify-content: space-between; align-items: flex-start;
            margin-bottom: 8px;
        }}
        .fund-card-header strong {{ color: {TAG["offwhite"]}; font-size: 0.9rem; }}
        .fund-pct {{
            background: {TAG["laranja"]}20; color: {TAG["laranja"]};
            padding: 2px 10px; border-radius: 12px;
            font-size: 0.8rem; font-weight: 600; white-space: nowrap;
        }}
        .fund-class {{
            color: {TAG["text_muted"]}; font-size: 0.75rem;
            text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 6px;
        }}
        .fund-detail {{
            color: {TAG["offwhite"]}; font-size: 0.82rem; opacity: 0.85; margin-bottom: 4px;
        }}
        .fund-returns {{
            color: {TAG["laranja"]}; font-size: 0.82rem; font-weight: 500; margin-bottom: 4px;
        }}
        .fund-just {{
            color: {TAG["offwhite"]}; font-size: 0.78rem; opacity: 0.75;
            margin-top: 6px; line-height: 1.4;
        }}
        .fund-meta {{
            color: {TAG["text_muted"]}; font-size: 0.72rem; margin-top: 6px;
            font-style: italic;
        }}

        /* Solutions grid */
        .solutions-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 12px; margin: 16px 0;
        }}
        .solution-card {{
            background: {TAG["bg_card_alt"]}; border-radius: 8px;
            padding: 12px; border: 1px solid {TAG["vermelho"]}15;
        }}
        .solution-card strong {{
            color: {TAG["laranja"]}; font-size: 0.82rem; display: block; margin-bottom: 6px;
        }}
        .solution-card ul {{ padding-left: 14px; margin: 0; }}
        .solution-card li {{ font-size: 0.75rem; color: {TAG["text_muted"]}; margin-bottom: 2px; }}

        /* Contact card */
        .contact-card {{
            text-align: center; padding: 24px;
            background: {TAG["bg_card_alt"]}; border-radius: 10px;
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .contact-card h3 {{
            color: {TAG["laranja"]}; margin-bottom: 12px;
        }}
        .contact-card p {{
            color: {TAG["offwhite"]}; font-size: 0.9rem; margin-bottom: 6px;
        }}

        /* Disclaimers */
        .disclaimers {{
            background: {TAG["bg_card"]}; border-radius: 12px;
            padding: 24px 32px; margin-bottom: 24px;
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .disclaimers h3 {{
            color: {TAG["text_muted"]}; font-size: 0.9rem; margin-bottom: 12px;
            padding-bottom: 8px; border-bottom: 1px solid {TAG["vermelho"]}15;
        }}
        .disclaimer-item {{
            color: {TAG["text_muted"]}; font-size: 0.75rem;
            margin-bottom: 6px; line-height: 1.5;
        }}

        /* Chart containers */
        .chart-container {{
            margin: 16px 0;
            border-radius: 8px;
            overflow: hidden;
        }}

        /* Hero charts */
        .hero-charts {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            align-items: start;
        }}
        .hero-chart-left, .hero-chart-right {{
            min-width: 0;
        }}

        /* Allocation visual bars */
        .alloc-visual {{
            margin: 16px 0;
        }}
        .alloc-visual h3 {{
            color: {TAG["offwhite"]}; font-size: 0.95rem; margin-bottom: 12px;
        }}
        .alloc-row {{
            display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
        }}
        .alloc-info {{
            min-width: 180px; max-width: 200px;
        }}
        .alloc-name {{
            display: block; color: {TAG["offwhite"]}; font-size: 0.78rem;
            font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .alloc-class {{
            display: block; color: {TAG["text_muted"]}; font-size: 0.65rem;
            text-transform: uppercase; letter-spacing: 0.03em;
        }}
        .alloc-bar-wrap {{
            flex: 1; background: {TAG["bg_card_alt"]}; border-radius: 4px;
            height: 22px; overflow: hidden;
        }}
        .alloc-bar {{
            height: 100%; border-radius: 4px; display: flex;
            align-items: center; justify-content: flex-end; padding-right: 8px;
            transition: width 0.3s;
        }}
        .alloc-bar span {{
            color: white; font-size: 0.7rem; font-weight: 600;
        }}
        .alloc-total {{
            text-align: right; color: {TAG["text_muted"]}; font-size: 0.78rem;
            margin-top: 8px; padding-top: 8px; border-top: 1px solid {TAG["vermelho"]}20;
        }}

        /* Comparison bars */
        .comp-visual {{
            margin: 16px 0;
        }}
        .comp-visual h3 {{
            color: {TAG["offwhite"]}; font-size: 0.95rem; margin-bottom: 12px;
        }}
        .comp-row {{
            display: flex; align-items: center; gap: 12px;
            margin-bottom: 12px; padding: 10px 14px;
            background: {TAG["bg_card_alt"]}; border-radius: 8px;
        }}
        .comp-label {{
            min-width: 120px; color: {TAG["offwhite"]}; font-size: 0.82rem;
            font-weight: 500;
        }}
        .comp-bars {{ flex: 1; }}
        .comp-pair {{
            display: flex; align-items: center; gap: 6px; margin-bottom: 4px;
        }}
        .comp-tag {{
            min-width: 55px; color: {TAG["text_muted"]}; font-size: 0.65rem;
            text-transform: uppercase;
        }}
        .comp-bar-bg {{
            flex: 1; background: {TAG["bg_card"]}; border-radius: 3px;
            height: 14px; overflow: hidden;
        }}
        .comp-bar {{
            height: 100%; border-radius: 3px; transition: width 0.3s;
        }}
        .comp-val {{
            min-width: 45px; text-align: right; color: {TAG["offwhite"]};
            font-size: 0.78rem; font-weight: 500;
        }}
        .comp-delta {{
            min-width: 55px; text-align: right; font-weight: 600; font-size: 0.82rem;
        }}

        /* Objective badges */
        .obj-badges {{
            display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px;
            justify-content: center;
        }}
        .obj-badge {{
            display: inline-block; padding: 4px 14px;
            background: {TAG["laranja"]}15; border: 1px solid {TAG["laranja"]}30;
            border-radius: 16px; color: {TAG["laranja"]}; font-size: 0.75rem;
            font-weight: 500;
        }}

        /* Turnover grid */
        .turnover-grid {{
            display: grid; grid-template-columns: repeat(3, 1fr);
            gap: 12px; margin: 16px 0;
        }}
        .turnover-item {{
            text-align: center; padding: 14px; border-radius: 8px;
            background: {TAG["bg_card_alt"]};
        }}
        .turnover-item.saindo {{ border-left: 3px solid {TAG["rosa"]}; }}
        .turnover-item.entrando {{ border-left: 3px solid {TAG["verde"]}; }}
        .turnover-item.mantidos {{ border-left: 3px solid {TAG["azul"]}; }}
        .turnover-num {{
            font-size: 1.5rem; font-weight: 700; color: {TAG["offwhite"]};
        }}
        .turnover-label {{
            font-size: 0.72rem; color: {TAG["text_muted"]}; margin-top: 4px;
        }}

        /* Footer */
        .footer {{
            text-align: center; padding: 32px;
            color: {TAG["text_muted"]}; font-size: 0.78rem;
            border-top: 1px solid {TAG["vermelho"]}15; margin-top: 40px;
        }}

        /* Print */
        @media print {{
            body {{ background: white; color: #333; }}
            .container {{ max-width: 100%; padding: 20px; }}
            .cover {{
                background: #f5f5f5; border: 1px solid #ddd;
                page-break-after: always;
            }}
            .toc {{ page-break-after: always; }}
            .section {{
                background: #fff; border: 1px solid #eee;
                page-break-inside: avoid;
            }}
            .part-header {{
                border-color: #ddd;
                page-break-after: avoid;
            }}
            .part-header span {{ color: {TAG["vermelho"]}; }}
            .cover h1, .section h2, .toc h2 {{ color: {TAG["vermelho"]}; }}
            .section-num {{ background: {TAG["vermelho"]}; }}
            .metric-card {{ background: #f8f8f8; border: 1px solid #ddd; }}
            .metric-card .label {{ color: #666; }}
            .metric-card .value {{ color: #333; }}
            .fund-card {{ background: #f8f8f8; border: 1px solid #ddd; border-left: 4px solid {TAG["vermelho"]}; }}
            .solution-card {{ background: #f8f8f8; border: 1px solid #ddd; }}
            .contact-card {{ background: #f8f8f8; border: 1px solid #ddd; }}
            .disclaimers {{ background: #fafafa; border: 1px solid #eee; }}
            th {{ background: {TAG["vermelho"]}15; color: {TAG["vermelho"]}; }}
            td {{ border-bottom: 1px solid #eee; }}
            tr:hover td {{ background: transparent; }}
            .num {{ color: {TAG["vermelho"]}; }}
            .muted {{ color: #999; }}
            a {{ color: #333; text-decoration: none; }}
            .hero-charts {{ grid-template-columns: 1fr; }}
            .chart-container {{ page-break-inside: avoid; }}
            .alloc-bar-wrap {{ background: #eee; }}
            .alloc-name, .alloc-class {{ color: #333; }}
            .alloc-total {{ color: #666; border-color: #ddd; }}
            .comp-row {{ background: #f8f8f8; }}
            .comp-bar-bg {{ background: #eee; }}
            .comp-label, .comp-val {{ color: #333; }}
            .comp-tag {{ color: #666; }}
            .obj-badge {{ background: #f0f0f0; border-color: #ddd; color: {TAG["vermelho"]}; }}
            .turnover-item {{ background: #f8f8f8; }}
            .turnover-num {{ color: #333; }}
            .turnover-label {{ color: #666; }}
        }}
    """


# ══════════════════════════════════════════════════════════
# V2 - 15 SECTION PROFESSIONAL PROPOSAL
# ══════════════════════════════════════════════════════════

def _generate_html_v2(prospect, proposta, charts_html=None):
    """Generate 15-section professional proposal HTML."""
    nome = prospect.get("nome", "")
    perfil = prospect.get("perfil_investidor", "")
    patrimonio = prospect.get("patrimonio_investivel", 0)
    horizonte = prospect.get("horizonte_investimento", "N/A")
    data_hoje = datetime.now().strftime("%d/%m/%Y")

    diagnostico = proposta.get("diagnostico_texto", "")
    recomendacao = proposta.get("recomendacao_texto", "")
    section_texts = proposta.get("section_texts", {}) or {}
    analytics = proposta.get("analytics_data", {}) or {}
    bottom_up = proposta.get("bottom_up_classification", []) or []
    carteira_proposta = proposta.get("carteira_proposta", [])
    if isinstance(carteira_proposta, str):
        try:
            carteira_proposta = json.loads(carteira_proposta)
        except Exception:
            carteira_proposta = []

    plano = proposta.get("plano_transicao", [])
    if isinstance(plano, str):
        try:
            plano = json.loads(plano)
        except Exception:
            plano = []

    logo_b64 = _load_logo()

    # Build all 15 sections
    sections_html = []

    # 1. Sumario Executivo
    sections_html.append(_html_section(
        1, "Sumario Executivo",
        _md_to_html(section_texts.get("sumario_executivo", "")),
    ))

    # 2. Premissas e Filosofia
    sections_html.append(_html_section(
        2, "Premissas e Filosofia de Investimento",
        _md_to_html(section_texts.get("premissas_filosofia", "")),
    ))

    # 3. Diagnostico Top Down
    s3_content = _md_to_html(diagnostico)
    allocation = analytics.get("allocation", {})
    if allocation.get("class_breakdown"):
        s3_content += _html_allocation_table(allocation)
    sections_html.append(_html_section(3, "Diagnostico Top Down", s3_content))

    # 4. Diagnostico de Risco
    risk = analytics.get("risk", {})
    s4_content = ""
    if risk:
        s4_content += _html_metrics_grid([
            ("HHI por Emissor", f"{risk.get('hhi_issuer', 0):,.0f}"),
            ("Top 5 Emissores", f"{risk.get('top5_issuer_pct', 0):.1f}%"),
            ("PL Total", f"R$ {risk.get('total_pl', 0):,.0f}"),
        ])
        concentration = analytics.get("concentration", [])
        if concentration:
            s4_content += _html_concentration_table(concentration)
        strategy = risk.get("concentration_by_strategy", [])
        if strategy:
            s4_content += "<h3>Concentracao por Estrategia</h3>"
            s4_content += _html_generic_table(
                ["Estrategia", "Financeiro", "%", "# Ativos"],
                [[s["estrategia"], f"R$ {s['financeiro']:,.0f}", f"{s['pct']:.1f}%",
                  str(s["num_ativos"])] for s in strategy],
            )
    else:
        s4_content = "<p class='muted'>Dados de risco nao disponiveis.</p>"
    sections_html.append(_html_section(4, "Diagnostico de Risco e Concentracao", s4_content))

    # 5. Analise Bottom Up
    s5_content = _md_to_html(section_texts.get("analise_bottom_up_texto", ""))
    if bottom_up:
        s5_content += _html_bottom_up_table(bottom_up)
        s5_content += _html_bottom_up_summary(bottom_up)
    sections_html.append(_html_section(5, "Analise Bottom Up", s5_content))

    # 6. Diagnostico de Eficiencia
    efficiency = analytics.get("efficiency", {})
    s6_content = ""
    if efficiency.get("efficiency_by_window"):
        s6_content += _html_generic_table(
            ["Janela", "Retorno", "Volatilidade", "Sharpe", "Sortino", "Alpha CDI"],
            [[w["janela"], f"{w['retorno']:.2f}%", f"{w['volatilidade']:.2f}%",
              f"{w['sharpe']:.2f}", f"{w['sortino']:.2f}", f"{w['alpha_cdi']:.2f}%"]
             for w in efficiency["efficiency_by_window"]],
        )
    else:
        s6_content = "<p class='muted'>Execute o backtest para metricas de eficiencia.</p>"
    sections_html.append(_html_section(6, "Diagnostico de Eficiencia", s6_content))

    # 7. Objetivos da Proposta
    sections_html.append(_html_section(
        7, "Objetivos da Carteira Proposta",
        _md_to_html(section_texts.get("objetivos_proposta", "")),
    ))

    # 8. Proposta Top Down
    s8_content = _md_to_html(section_texts.get("proposta_top_down_texto", ""))
    if allocation.get("class_breakdown"):
        s8_content += _html_allocation_table(allocation)
    sections_html.append(_html_section(8, "Carteira Proposta - Visao Top Down", s8_content))

    # 9. Proposta Bottom Up
    s9_content = _md_to_html(section_texts.get("proposta_bottom_up_texto", ""))
    if carteira_proposta:
        s9_content += _html_fund_cards(carteira_proposta)
        s9_content += _html_portfolio_detail_table(carteira_proposta)
    sections_html.append(_html_section(9, "Carteira Proposta - Visao Bottom Up", s9_content))

    # 10. Historico de Retornos
    s10_content = charts_html or ""
    s10_content += (
        '<p class="muted" style="margin-top:12px">Retornos calculados com proxies de mercado '
        'por classe de ativo. Rentabilidade passada nao e garantia de rentabilidade futura.</p>'
    )
    sections_html.append(_html_section(10, "Historico de Retornos", s10_content))

    # 11. Backtest
    s11_content = (
        "<p>O backtest completo esta disponivel na versao interativa da proposta. "
        "Solicite ao seu assessor a demonstracao das simulacoes historicas.</p>"
    )
    sections_html.append(_html_section(11, "Backtest - Simulacao Historica", s11_content))

    # 12. Liquidez
    liquidity = analytics.get("liquidity", {})
    s12_content = ""
    if liquidity:
        s12_content += _html_metrics_grid([
            ("Caixa Rapido (D+5) - Atual", f"{liquidity.get('pct_cash_quickly_atual', 0):.1f}%"),
            ("Caixa Rapido (D+5) - Proposta", f"{liquidity.get('pct_cash_quickly_proposta', 0):.1f}%"),
        ])
        s12_content += _html_liquidity_table(liquidity)
    maturity = analytics.get("maturity", [])
    if maturity:
        s12_content += "<h3>Escalonamento de Vencimentos</h3>"
        s12_content += _html_generic_table(
            ["Periodo", "Financeiro", "% PL"],
            [[m["label"], f"R$ {m['total_financeiro']:,.0f}", f"{m['pct']:.1f}%"]
             for m in maturity],
        )
    if not liquidity and not maturity:
        s12_content = "<p class='muted'>Dados de liquidez nao disponiveis.</p>"
    sections_html.append(_html_section(12, "Liquidez e Vencimentos", s12_content))

    # 13. Eficiencia Tributaria
    tax = analytics.get("tax", {})
    s13_content = ""
    if tax:
        s13_content += _html_metrics_grid([
            ("% Isentos - Atual", f"{tax.get('atual_isentos_pct', 0):.1f}%"),
            ("% Isentos - Proposta", f"{tax.get('proposta_isentos_pct', 0):.1f}%"),
            ("Delta", f"{tax.get('delta_isentos', 0):+.1f}pp"),
        ])
        turnover = tax.get("turnover", {})
        if turnover:
            s13_content += (
                f"<p><strong>Giro da Carteira:</strong> "
                f"{turnover.get('saindo', 0)} saindo | "
                f"{turnover.get('entrando', 0)} entrando | "
                f"{turnover.get('mantidos', 0)} mantidos</p>"
            )
    else:
        s13_content = "<p class='muted'>Dados tributarios nao disponiveis.</p>"
    sections_html.append(_html_section(13, "Eficiencia Tributaria", s13_content))

    # 14. Plano de Implementacao
    s14_content = ""
    if plano:
        headers = list(plano[0].keys()) if plano else []
        rows = [list(item.values()) for item in plano]
        s14_content += _html_generic_table(headers, [[str(v) for v in row] for row in rows])
    elif recomendacao:
        s14_content += "<h3>Recomendacao de Implementacao</h3>"
        s14_content += _md_to_html(recomendacao)
    else:
        s14_content = "<p class='muted'>Plano de transicao nao definido.</p>"
    sections_html.append(_html_section(14, "Plano de Implementacao", s14_content))

    # 15. Monitoramento
    sections_html.append(_html_section(
        15, "Monitoramento e Governanca",
        _md_to_html(section_texts.get("monitoramento_governanca", "")),
    ))

    # Build TOC
    toc_items = [
        (1, "Sumario Executivo"), (2, "Premissas e Filosofia"),
        (3, "Diagnostico Top Down"), (4, "Diagnostico de Risco"),
        (5, "Analise Bottom Up"), (6, "Diagnostico de Eficiencia"),
        (7, "Objetivos da Proposta"), (8, "Proposta Top Down"),
        (9, "Proposta Bottom Up"), (10, "Historico de Retornos"),
        (11, "Backtest"), (12, "Liquidez e Vencimentos"),
        (13, "Eficiencia Tributaria"), (14, "Plano de Implementacao"),
        (15, "Monitoramento e Governanca"),
    ]
    toc_html = '<div class="toc"><h2>Sumario</h2><ol>'
    for num, title in toc_items:
        toc_html += f'<li><a href="#section-{num}">{title}</a></li>'
    toc_html += '</ol></div>'

    all_sections = "\n".join(sections_html)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proposta de Investimento - {nome} | TAG Investimentos</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        {_css_v2()}
    </style>
</head>
<body>
    <div class="container">
        <!-- COVER -->
        <div class="cover">
            {_logo_html(logo_b64)}
            <h1>Proposta de Investimento</h1>
            <div class="subtitle">{nome}</div>
            <div class="badge">Perfil {perfil}</div>
            <div class="date">{data_hoje}</div>
        </div>

        <!-- METRICS -->
        <div class="section">
            <div class="metrics">
                <div class="metric-card">
                    <div class="label">Patrimonio</div>
                    <div class="value">R$ {patrimonio:,.0f}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Perfil</div>
                    <div class="value">{perfil}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Ativos Propostos</div>
                    <div class="value">{len(carteira_proposta)}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Horizonte</div>
                    <div class="value">{horizonte[:15]}</div>
                </div>
            </div>
        </div>

        <!-- TABLE OF CONTENTS -->
        {toc_html}

        <!-- 15 SECTIONS -->
        {all_sections}

        <!-- ABOUT TAG -->
        <div class="section">
            <h2>Sobre a TAG Investimentos</h2>
            <p>A TAG Investimentos e uma gestora independente comprometida com a excelencia
            na gestao de patrimonio. Nossa equipe de profissionais experientes utiliza tecnologia
            avancada e analise rigorosa para construir carteiras que atendem as necessidades
            especificas de cada cliente.</p>
        </div>

        <!-- DISCLAIMER -->
        <div class="footer">
            <p>Este documento e uma proposta de investimento e nao constitui oferta, solicitacao ou recomendacao
            de compra ou venda de qualquer ativo financeiro. Rentabilidade passada nao e garantia de rentabilidade futura.
            Investimentos envolvem riscos e podem resultar em perdas.</p>
            <p style="margin-top:8px">As informacoes aqui apresentadas foram elaboradas com base em dados e premissas
            consideradas confiaveis, porem nao ha garantia de exatidao ou completude.</p>
            <p style="margin-top:12px">TAG Investimentos &copy; {datetime.now().year} - Documento confidencial</p>
        </div>
    </div>
</body>
</html>"""

    return html


# ── Shared HTML Helpers ──

def _html_section(number, title, content):
    """Wrap content in a numbered section div."""
    if not content or not content.strip():
        content = "<p class='muted'>Conteudo nao disponivel.</p>"
    return (
        f'<div class="section" id="section-{number}">'
        f'<div class="section-header">'
        f'<span class="section-num">{number}</span>'
        f'<h2>{title}</h2>'
        f'</div>'
        f'{content}'
        f'</div>'
    )


def _md_to_html(text):
    """Convert simple markdown to HTML."""
    if not text:
        return ""
    lines = text.strip().split("\n")
    html_parts = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            item = stripped[2:]
            while "**" in item:
                item = item.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            html_parts.append(f"<li>{item}</li>")
        elif stripped.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h4>{stripped[4:]}</h4>")
        elif stripped.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append(f"<h3>{stripped[3:]}</h3>")
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            while "**" in stripped:
                stripped = stripped.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            html_parts.append(f"<p>{stripped}</p>")
    if in_list:
        html_parts.append("</ul>")
    return "\n".join(html_parts)


def _html_metrics_grid(items):
    """Render a grid of metric cards. items: list of (label, value)."""
    html = '<div class="metrics">'
    for label, value in items:
        html += (
            f'<div class="metric-card">'
            f'<div class="label">{label}</div>'
            f'<div class="value">{value}</div>'
            f'</div>'
        )
    html += '</div>'
    return html


def _html_generic_table(headers, rows):
    """Build a generic HTML table."""
    html = '<table><thead><tr>'
    for h in headers:
        html += f'<th>{h}</th>'
    html += '</tr></thead><tbody>'
    for row in rows:
        html += '<tr>'
        for cell in row:
            html += f'<td>{cell}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


def _html_allocation_table(allocation):
    """Render allocation comparison table."""
    breakdown = allocation.get("class_breakdown", [])
    if not breakdown:
        return ""
    html = '<h3>Alocacao por Classe de Ativo</h3>'
    html += '<table><thead><tr>'
    html += '<th>Classe</th><th class="num">Atual (%)</th><th class="num">Proposta (%)</th><th class="num">Delta (pp)</th>'
    html += '</tr></thead><tbody>'
    for item in breakdown:
        delta = item.get("delta", 0)
        delta_color = f'color:{TAG["verde"]}' if delta > 0 else (f'color:{TAG["rosa"]}' if delta < 0 else "")
        html += (
            f'<tr>'
            f'<td>{item["classe"]}</td>'
            f'<td class="num">{item["pct_atual"]:.1f}%</td>'
            f'<td class="num">{item["pct_proposta"]:.1f}%</td>'
            f'<td class="num" style="{delta_color}">{delta:+.1f}pp</td>'
            f'</tr>'
        )
    html += '</tbody></table>'

    exposure = allocation.get("exposure_summary", {})
    if exposure:
        html += '<h3 style="margin-top:20px">Resumo de Exposicao</h3>'
        html += '<table><thead><tr><th>Exposicao</th><th class="num">Atual</th><th class="num">Proposta</th></tr></thead><tbody>'
        for key, vals in exposure.items():
            label = key.replace("_", " ").title()
            html += (
                f'<tr><td>{label}</td>'
                f'<td class="num">{vals.get("atual", 0):.1f}%</td>'
                f'<td class="num">{vals.get("proposta", 0):.1f}%</td></tr>'
            )
        html += '</tbody></table>'

    return html


def _html_concentration_table(concentration):
    """Render concentration by issuer table."""
    html = '<h3>Concentracao por Emissor/Instituicao</h3>'
    html += '<table><thead><tr>'
    html += '<th>Instituicao</th><th class="num">Financeiro</th><th class="num">%</th><th class="num"># Ativos</th>'
    html += '</tr></thead><tbody>'
    for item in concentration[:10]:
        html += (
            f'<tr>'
            f'<td>{item["instituicao"]}</td>'
            f'<td class="num">R$ {item["total_financeiro"]:,.0f}</td>'
            f'<td class="num">{item["pct"]:.1f}%</td>'
            f'<td class="num">{item["num_ativos"]}</td>'
            f'</tr>'
        )
    html += '</tbody></table>'
    return html


def _html_bottom_up_table(bottom_up):
    """Render bottom-up classification table."""
    html = '<h3>Classificacao dos Ativos</h3>'
    html += '<table><thead><tr>'
    html += '<th>Ativo</th><th>Classificacao</th><th>Motivo</th><th class="num">% Atual</th><th class="num">% Proposta</th>'
    html += '</tr></thead><tbody>'

    color_map = {
        "Convicto": TAG["verde"],
        "Neutro": TAG["azul"],
        "Observacao": TAG["amarelo"],
        "Saida Estrutural": TAG["rosa"],
        "Iliquido em Carregamento": TAG["text_muted"],
    }

    for item in bottom_up:
        cat = item.get("classificacao", "")
        color = color_map.get(cat, TAG["text_muted"])
        html += (
            f'<tr>'
            f'<td>{item.get("ativo", "")}</td>'
            f'<td><span style="color:{color};font-weight:600">{cat}</span></td>'
            f'<td class="muted">{item.get("motivo", "")}</td>'
            f'<td class="num">{item.get("pct_atual", 0):.2f}%</td>'
            f'<td class="num">{item.get("pct_proposta", 0):.2f}%</td>'
            f'</tr>'
        )
    html += '</tbody></table>'
    return html


def _html_bottom_up_summary(bottom_up):
    """Render summary counts for bottom-up classification."""
    counts = {}
    for item in bottom_up:
        cat = item.get("classificacao", "?")
        counts[cat] = counts.get(cat, 0) + 1

    color_map = {
        "Convicto": TAG["verde"],
        "Neutro": TAG["azul"],
        "Observacao": TAG["amarelo"],
        "Saida Estrutural": TAG["rosa"],
        "Iliquido em Carregamento": TAG["text_muted"],
    }

    html = '<div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:12px">'
    for cat, cnt in counts.items():
        color = color_map.get(cat, TAG["text_muted"])
        html += (
            f'<span style="padding:4px 12px;border-radius:16px;'
            f'background:{color}20;color:{color};font-size:0.8rem;font-weight:600">'
            f'{cat}: {cnt}</span>'
        )
    html += '</div>'
    return html


def _html_fund_cards(carteira_proposta):
    """Render fund description cards for v2 section 9."""
    html = '<div class="fund-cards">'
    for item in carteira_proposta:
        name = item.get("ativo", item.get("Ativo", ""))
        classe = item.get("classe", item.get("Classe", item.get("estrategia", item.get("Estrategia", ""))))
        pct = item.get("pct_alvo", item.get("% Alvo", 0))
        just = item.get("justificativa", item.get("Justificativa", ""))

        html += (
            f'<div class="fund-card">'
            f'<div class="fund-card-header">'
            f'<strong>{name}</strong>'
            f'<span class="fund-pct">{pct:.1f}%</span>'
            f'</div>'
        )
        if classe:
            html += f'<div class="fund-class">{classe}</div>'
        if just:
            html += f'<div class="fund-just">{just}</div>'
        html += '</div>'
    html += '</div>'
    return html


def _html_portfolio_detail_table(carteira_proposta):
    """Render detailed portfolio table (v2 - basic columns)."""
    html = '<h3 style="margin-top:24px">Detalhamento Completo</h3>'
    html += '<table><thead><tr>'
    html += '<th>Ativo</th><th>Classe/Estrategia</th><th class="num">% Alvo</th><th>Justificativa</th>'
    html += '</tr></thead><tbody>'
    for item in carteira_proposta:
        name = item.get("ativo", item.get("Ativo", ""))
        classe = item.get("classe", item.get("Classe", item.get("estrategia", "")))
        pct = item.get("pct_alvo", item.get("% Alvo", 0))
        just = item.get("justificativa", item.get("Justificativa", ""))
        html += (
            f'<tr>'
            f'<td>{name}</td>'
            f'<td>{classe}</td>'
            f'<td class="num">{pct:.1f}%</td>'
            f'<td class="muted">{just}</td>'
            f'</tr>'
        )
    html += '</tbody></table>'
    return html


def _html_liquidity_table(liquidity):
    """Render liquidity comparison table."""
    atual = liquidity.get("atual_buckets", {})
    proposta = liquidity.get("proposta_buckets", {})
    if not atual:
        return ""

    html = '<h3>Perfil de Liquidez</h3>'
    html += '<table><thead><tr><th>Prazo</th><th class="num">Atual (%)</th><th class="num">Proposta (%)</th></tr></thead><tbody>'
    for key in ["D+0-1", "D+2-5", "D+6-30", "D+30+"]:
        html += (
            f'<tr>'
            f'<td>{key}</td>'
            f'<td class="num">{atual.get(key, 0):.1f}%</td>'
            f'<td class="num">{proposta.get(key, 0):.1f}%</td>'
            f'</tr>'
        )
    html += '</tbody></table>'
    return html


def _load_logo():
    """Load logo as base64 string."""
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo_b64.txt")
    if os.path.exists(logo_path):
        with open(logo_path, "r") as f:
            return f.read().strip()
    return ""


def _logo_html(logo_b64):
    """Return logo HTML."""
    if logo_b64:
        return f"<img src='data:image/png;base64,{logo_b64}' alt='TAG'>"
    return f"<h2 style='color:{TAG['laranja']}'>TAG INVESTIMENTOS</h2>"


def _css_v2():
    """CSS styles for v2 proposal."""
    return f"""
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: {TAG["bg_dark"]};
            color: {TAG["offwhite"]};
            line-height: 1.7;
        }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 24px; }}

        /* Cover */
        .cover {{
            text-align: center;
            padding: 80px 40px;
            background: linear-gradient(135deg, {TAG["vermelho_dark"]} 0%, {TAG["bg_dark"]} 70%);
            border-radius: 16px;
            margin-bottom: 40px;
            border: 1px solid {TAG["vermelho"]}30;
        }}
        .cover img {{ max-width: 180px; margin-bottom: 32px; }}
        .cover h1 {{
            font-size: 2rem; font-weight: 600; color: {TAG["offwhite"]};
            margin-bottom: 8px;
        }}
        .cover .subtitle {{ color: {TAG["laranja"]}; font-size: 1.2rem; font-weight: 500; }}
        .cover .badge {{
            display: inline-block; margin-top: 12px; padding: 6px 20px;
            background: {TAG["laranja"]}20; border: 1px solid {TAG["laranja"]}40;
            border-radius: 20px; color: {TAG["laranja"]}; font-size: 0.85rem; font-weight: 500;
        }}
        .cover .date {{ color: {TAG["text_muted"]}; margin-top: 16px; font-size: 0.9rem; }}

        /* TOC */
        .toc {{
            background: {TAG["bg_card"]}; border-radius: 12px;
            padding: 24px 32px; margin-bottom: 32px;
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .toc h2 {{
            color: {TAG["laranja"]}; font-size: 1.1rem; margin-bottom: 12px;
            padding-bottom: 8px; border-bottom: 2px solid {TAG["laranja"]}30;
        }}
        .toc ol {{ padding-left: 20px; }}
        .toc li {{ margin-bottom: 4px; font-size: 0.9rem; }}
        .toc a {{ color: {TAG["offwhite"]}; text-decoration: none; }}
        .toc a:hover {{ color: {TAG["laranja"]}; }}

        /* Sections */
        .section {{
            background: {TAG["bg_card"]}; border-radius: 12px;
            padding: 32px; margin-bottom: 24px;
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .section-header {{
            display: flex; align-items: center; gap: 12px;
            margin-bottom: 20px; padding-bottom: 12px;
            border-bottom: 2px solid {TAG["laranja"]}30;
        }}
        .section-num {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 36px; height: 36px; min-width: 36px;
            background: {TAG["laranja"]}; color: white;
            border-radius: 50%; font-weight: 700; font-size: 0.9rem;
        }}
        .section h2 {{
            color: {TAG["laranja"]}; font-size: 1.2rem; font-weight: 600;
            margin: 0; padding: 0; border: none;
        }}
        .section h3 {{
            color: {TAG["offwhite"]}; font-size: 1rem; font-weight: 600;
            margin: 20px 0 12px 0;
        }}
        .section h4 {{
            color: {TAG["text_muted"]}; font-size: 0.9rem; font-weight: 600;
            margin: 16px 0 8px 0;
        }}
        .section p {{ margin-bottom: 10px; font-size: 0.92rem; }}
        .section ul {{ padding-left: 20px; margin-bottom: 12px; }}
        .section li {{ margin-bottom: 4px; font-size: 0.92rem; }}

        /* Tables */
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; margin-bottom: 16px; }}
        th {{
            text-align: left; padding: 10px 14px;
            background: {TAG["vermelho_dark"]}; color: {TAG["laranja"]};
            font-weight: 600; font-size: 0.8rem;
            text-transform: uppercase; letter-spacing: 0.05em;
        }}
        td {{
            padding: 8px 14px; border-bottom: 1px solid {TAG["vermelho"]}15;
            font-size: 0.85rem;
        }}
        tr:hover td {{ background: {TAG["vermelho"]}08; }}
        .num {{ text-align: right; font-weight: 500; color: {TAG["laranja"]}; }}
        .muted {{ color: {TAG["text_muted"]}; font-size: 0.82rem; }}

        /* Metrics */
        .metrics {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px; margin: 16px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, {TAG["bg_card_alt"]} 0%, {TAG["bg_card"]} 100%);
            border-radius: 10px; padding: 16px;
            border: 1px solid {TAG["vermelho"]}20; text-align: center;
        }}
        .metric-card .label {{
            color: {TAG["text_muted"]}; font-size: 0.72rem;
            text-transform: uppercase; letter-spacing: 0.05em;
        }}
        .metric-card .value {{
            color: {TAG["offwhite"]}; font-size: 1.4rem; font-weight: 600; margin-top: 4px;
        }}

        /* Fund cards */
        .fund-cards {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px; margin: 20px 0;
        }}
        .fund-card {{
            background: {TAG["bg_card_alt"]}; border-radius: 10px;
            padding: 16px; border-left: 4px solid {TAG["laranja"]};
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .fund-card-header {{
            display: flex; justify-content: space-between; align-items: flex-start;
            margin-bottom: 8px;
        }}
        .fund-card-header strong {{ color: {TAG["offwhite"]}; font-size: 0.9rem; }}
        .fund-pct {{
            background: {TAG["laranja"]}20; color: {TAG["laranja"]};
            padding: 2px 10px; border-radius: 12px;
            font-size: 0.8rem; font-weight: 600;
        }}
        .fund-class {{
            color: {TAG["text_muted"]}; font-size: 0.78rem;
            text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 6px;
        }}
        .fund-just {{ color: {TAG["offwhite"]}; font-size: 0.82rem; opacity: 0.85; }}

        /* Footer */
        .footer {{
            text-align: center; padding: 32px;
            color: {TAG["text_muted"]}; font-size: 0.78rem;
            border-top: 1px solid {TAG["vermelho"]}15; margin-top: 40px;
        }}

        /* Print */
        @media print {{
            body {{ background: white; color: #333; }}
            .cover {{ background: #f5f5f5; border: 1px solid #ddd; page-break-after: always; }}
            .toc {{ page-break-after: always; }}
            .section {{
                background: #fff; border: 1px solid #eee;
                page-break-inside: avoid;
            }}
            .cover h1, .section h2, .toc h2 {{ color: {TAG["vermelho"]}; }}
            .section-num {{ background: {TAG["vermelho"]}; }}
            .metric-card {{ background: #f8f8f8; border: 1px solid #ddd; }}
            .metric-card .label {{ color: #666; }}
            .metric-card .value {{ color: #333; }}
            .fund-card {{ background: #f8f8f8; border: 1px solid #ddd; }}
            th {{ background: {TAG["vermelho"]}15; color: {TAG["vermelho"]}; }}
            td {{ border-bottom: 1px solid #eee; }}
            tr:hover td {{ background: transparent; }}
            .num {{ color: {TAG["vermelho"]}; }}
            .muted {{ color: #999; }}
            a {{ color: #333; text-decoration: none; }}
        }}
    """


# ══════════════════════════════════════════════════════════
# V1 - BASIC PROPOSAL (backwards compatibility)
# ══════════════════════════════════════════════════════════

def _generate_html_v1(prospect, proposta, charts_html=None):
    """Generate basic proposal HTML (legacy format)."""
    nome = prospect.get("nome", "")
    perfil = prospect.get("perfil_investidor", "")
    patrimonio = prospect.get("patrimonio_investivel", 0)
    diagnostico = proposta.get("diagnostico_texto", "")
    recomendacao = proposta.get("recomendacao_texto", "")
    carteira_proposta = proposta.get("carteira_proposta", [])
    data_hoje = datetime.now().strftime("%d/%m/%Y")

    logo_b64 = _load_logo()

    # Build portfolio table
    table_rows = ""
    for item in carteira_proposta:
        ativo = item.get("ativo", item.get("Ativo", ""))
        pct = item.get("pct_alvo", item.get("% Alvo", 0))
        just = item.get("justificativa", "")
        table_rows += f"""
        <tr>
            <td>{ativo}</td>
            <td class="num">{pct:.1f}%</td>
            <td class="muted">{just}</td>
        </tr>"""

    charts_section = charts_html or ""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proposta de Investimento - {nome} | TAG Investimentos</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: {TAG["bg_dark"]};
            color: {TAG["offwhite"]};
            line-height: 1.7;
        }}

        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 24px; }}

        .cover {{
            text-align: center;
            padding: 80px 40px;
            background: linear-gradient(135deg, {TAG["vermelho_dark"]} 0%, {TAG["bg_dark"]} 70%);
            border-radius: 16px;
            margin-bottom: 40px;
            border: 1px solid {TAG["vermelho"]}30;
        }}
        .cover img {{ max-width: 180px; margin-bottom: 32px; }}
        .cover h1 {{
            font-size: 2rem;
            font-weight: 600;
            color: {TAG["offwhite"]};
            margin-bottom: 8px;
        }}
        .cover .subtitle {{
            color: {TAG["laranja"]};
            font-size: 1.1rem;
            font-weight: 500;
        }}
        .cover .date {{
            color: {TAG["text_muted"]};
            margin-top: 16px;
            font-size: 0.9rem;
        }}
        .cover .badge {{
            display: inline-block;
            margin-top: 12px;
            padding: 6px 20px;
            background: {TAG["laranja"]}20;
            border: 1px solid {TAG["laranja"]}40;
            border-radius: 20px;
            color: {TAG["laranja"]};
            font-size: 0.85rem;
            font-weight: 500;
        }}

        .section {{
            background: {TAG["bg_card"]};
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 24px;
            border: 1px solid {TAG["vermelho"]}20;
        }}
        .section h2 {{
            color: {TAG["laranja"]};
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 20px;
            padding-bottom: 8px;
            border-bottom: 2px solid {TAG["laranja"]}30;
        }}
        .section p {{ margin-bottom: 12px; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }}
        th {{
            text-align: left;
            padding: 12px 16px;
            background: {TAG["vermelho_dark"]};
            color: {TAG["laranja"]};
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        td {{
            padding: 10px 16px;
            border-bottom: 1px solid {TAG["vermelho"]}15;
            font-size: 0.9rem;
        }}
        tr:hover td {{ background: {TAG["vermelho"]}08; }}
        .num {{ text-align: right; font-weight: 500; color: {TAG["laranja"]}; }}
        .muted {{ color: {TAG["text_muted"]}; font-size: 0.82rem; }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, {TAG["bg_card_alt"]} 0%, {TAG["bg_card"]} 100%);
            border-radius: 10px;
            padding: 16px;
            border: 1px solid {TAG["vermelho"]}20;
            text-align: center;
        }}
        .metric-card .label {{
            color: {TAG["text_muted"]};
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .metric-card .value {{
            color: {TAG["offwhite"]};
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: 4px;
        }}

        .footer {{
            text-align: center;
            padding: 32px;
            color: {TAG["text_muted"]};
            font-size: 0.8rem;
            border-top: 1px solid {TAG["vermelho"]}15;
            margin-top: 40px;
        }}

        @media print {{
            body {{ background: white; color: #333; }}
            .cover {{ background: #f8f8f8; border: 1px solid #ddd; }}
            .section {{ background: #fff; border: 1px solid #eee; }}
            .cover h1, .section h2 {{ color: #630D24; }}
        }}

        .chart-container {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="cover">
            {_logo_html(logo_b64)}
            <h1>Proposta de Investimento</h1>
            <div class="subtitle">{nome}</div>
            <div class="badge">Perfil {perfil}</div>
            <div class="date">{data_hoje}</div>
        </div>

        <div class="section">
            <h2>Resumo</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="label">Patrimonio</div>
                    <div class="value">R$ {patrimonio:,.0f}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Perfil</div>
                    <div class="value">{perfil}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Ativos Propostos</div>
                    <div class="value">{len(carteira_proposta)}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Horizonte</div>
                    <div class="value">{prospect.get('horizonte_investimento', 'N/A')[:15]}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Diagnostico da Carteira Atual</h2>
            {"".join(f"<p>{line}</p>" for line in diagnostico.split(chr(10)) if line.strip())}
        </div>

        <div class="section">
            <h2>Nossa Recomendacao</h2>
            {"".join(f"<p>{line}</p>" for line in recomendacao.split(chr(10)) if line.strip())}
        </div>

        <div class="section">
            <h2>Carteira Proposta</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ativo</th>
                        <th style="text-align:right">Alocacao</th>
                        <th>Justificativa</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>

        {f'<div class="section"><h2>Analise Visual</h2>{charts_section}</div>' if charts_section else ''}

        <div class="section">
            <h2>Sobre a TAG Investimentos</h2>
            <p>A TAG Investimentos e uma gestora independente comprometida com a excelencia na gestao de patrimonio.
            Nossa equipe de profissionais experientes utiliza tecnologia avancada e analise rigorosa
            para construir carteiras que atendem as necessidades especificas de cada cliente.</p>
        </div>

        <div class="footer">
            <p>Este documento e uma proposta de investimento e nao constitui oferta, solicitacao ou recomendacao
            de compra ou venda de qualquer ativo financeiro. Rentabilidade passada nao e garantia de rentabilidade futura.
            Investimentos envolvem riscos e podem resultar em perdas.</p>
            <p style="margin-top:12px">TAG Investimentos &copy; {datetime.now().year} - Documento confidencial</p>
        </div>
    </div>
</body>
</html>"""

    return html
