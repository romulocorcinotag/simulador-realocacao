"""
TAG Investimentos - Scoring de Adequacao de Proposta
Avalia a adequacao da carteira proposta ao perfil do investidor.
Gera notas por dimensao e recomendacoes automaticas.
"""


# ══════════════════════════════════════════════════════════
# PERFIL LIMITS (ref: tag_institucional.py LIMITES_POLITICA_DEFAULT)
# ══════════════════════════════════════════════════════════

_PERFIL_LIMITS = {
    "Conservador": {
        "max_renda_variavel": 0,
        "max_credito_privado": 15,
        "max_alternativos": 0,
        "max_por_emissor": 20,
        "min_liquidez_d5": 30,
        "max_offshore": 0,
        "max_volatilidade_target": 2.0,
    },
    "Moderado": {
        "max_renda_variavel": 20,
        "max_credito_privado": 20,
        "max_alternativos": 10,
        "max_por_emissor": 15,
        "min_liquidez_d5": 20,
        "max_offshore": 10,
        "max_volatilidade_target": 6.0,
    },
    "Agressivo": {
        "max_renda_variavel": 40,
        "max_credito_privado": 25,
        "max_alternativos": 20,
        "max_por_emissor": 15,
        "min_liquidez_d5": 15,
        "max_offshore": 20,
        "max_volatilidade_target": 12.0,
    },
}

_RV_KEYWORDS = {"acoes", "ações", "equity", "renda variavel", "renda variável", "long biased", "long only", "fof acoes"}
_CREDITO_KEYWORDS = {"credito", "crédito", "fidc", "cra", "cri", "debenture"}
_ALTERNATIVO_KEYWORDS = {"alternativo", "private equity", "venture capital", "fip", "special sits", "distressed"}
_OFFSHORE_KEYWORDS = {"offshore", "internacional", "global", "us$", "usd", "dolar", "dólar"}
_CAIXA_KEYWORDS = {"caixa", "selic", "di", "referenciado", "soberano"}


def _classify_asset_type(item):
    """Classify an asset into broad categories based on available data."""
    classe = str(item.get("classe", item.get("Classe", ""))).lower()
    tipo = str(item.get("tipo", "")).lower()
    nome = str(item.get("ativo", item.get("Ativo", item.get("nome", "")))).lower()
    estrategia = str(item.get("estrategia", "")).lower()
    combined = f"{classe} {tipo} {nome} {estrategia}"

    if any(kw in combined for kw in _RV_KEYWORDS):
        return "renda_variavel"
    if any(kw in combined for kw in _ALTERNATIVO_KEYWORDS):
        return "alternativo"
    if any(kw in combined for kw in _OFFSHORE_KEYWORDS):
        return "offshore"
    if any(kw in combined for kw in _CREDITO_KEYWORDS):
        return "credito_privado"
    if any(kw in combined for kw in _CAIXA_KEYWORDS):
        return "caixa"
    if "fii" in combined or "fiagro" in combined or "imobiliario" in combined:
        return "imobiliario"
    if "multimercado" in combined or "multimercados" in combined:
        return "multimercado"
    return "renda_fixa"


def score_proposal(prospect, proposta, analytics=None):
    """Compute proposal adequacy score across multiple dimensions.

    Returns:
        {
            "score_total": float (0-100),
            "dimensoes": [
                {"nome": str, "score": float, "max": float, "nota": str, "detalhes": str},
            ],
            "alertas": [str],
            "selo": str,  # "Excelente", "Bom", "Atencao", "Critico"
        }
    """
    perfil = prospect.get("perfil_investidor", "Moderado")
    patrimonio = float(prospect.get("patrimonio_investivel", 0) or 0)
    limits = _PERFIL_LIMITS.get(perfil, _PERFIL_LIMITS["Moderado"])

    cart = proposta.get("carteira_proposta", [])
    if isinstance(cart, str):
        try:
            import json
            cart = json.loads(cart)
        except Exception:
            cart = []

    if not cart:
        return {
            "score_total": 0,
            "dimensoes": [],
            "alertas": ["Nenhuma carteira proposta definida"],
            "selo": "Critico",
        }

    dimensoes = []
    alertas = []

    # ── 1. DIVERSIFICACAO (25 pts) ──
    div_score = 25
    n_assets = len(cart)
    if n_assets < 3:
        div_score -= 10
        alertas.append(f"Carteira com apenas {n_assets} ativo(s) - baixa diversificacao")
    elif n_assets < 5:
        div_score -= 5

    # Check concentration
    pcts = [float(item.get("pct_alvo", item.get("% Alvo", 0)) or 0) for item in cart]
    max_pct = max(pcts) if pcts else 0
    if max_pct > limits["max_por_emissor"]:
        excess = max_pct - limits["max_por_emissor"]
        penalty = min(10, excess * 0.5)
        div_score -= penalty
        top_asset = cart[pcts.index(max_pct)].get("ativo", cart[pcts.index(max_pct)].get("Ativo", ""))
        alertas.append(f"Concentracao: {top_asset} com {max_pct:.1f}% excede limite de {limits['max_por_emissor']}%")

    # Unique classes
    classes = set()
    for item in cart:
        cls = _classify_asset_type(item)
        classes.add(cls)
    if len(classes) < 2:
        div_score -= 5
        alertas.append("Baixa diversificacao entre classes de ativos")

    div_score = max(0, div_score)
    dimensoes.append({
        "nome": "Diversificacao",
        "score": div_score, "max": 25,
        "nota": _grade(div_score, 25),
        "detalhes": f"{n_assets} ativos, {len(classes)} classes, max concentracao {max_pct:.1f}%",
    })

    # ── 2. ADEQUACAO AO PERFIL (25 pts) ──
    adeq_score = 25

    # Aggregate by type
    type_pcts = {}
    for item in cart:
        asset_type = _classify_asset_type(item)
        pct = float(item.get("pct_alvo", item.get("% Alvo", 0)) or 0)
        type_pcts[asset_type] = type_pcts.get(asset_type, 0) + pct

    rv_pct = type_pcts.get("renda_variavel", 0)
    cred_pct = type_pcts.get("credito_privado", 0)
    alt_pct = type_pcts.get("alternativo", 0)
    off_pct = type_pcts.get("offshore", 0)

    # Check RV
    if rv_pct > limits["max_renda_variavel"]:
        excess = rv_pct - limits["max_renda_variavel"]
        penalty = min(10, excess * 0.5)
        adeq_score -= penalty
        alertas.append(
            f"Renda variavel ({rv_pct:.1f}%) excede limite do perfil {perfil} "
            f"({limits['max_renda_variavel']}%)"
        )

    # Check credito privado
    if cred_pct > limits["max_credito_privado"]:
        excess = cred_pct - limits["max_credito_privado"]
        penalty = min(5, excess * 0.3)
        adeq_score -= penalty
        alertas.append(
            f"Credito privado ({cred_pct:.1f}%) excede limite ({limits['max_credito_privado']}%)"
        )

    # Check alternativos
    if alt_pct > limits["max_alternativos"]:
        excess = alt_pct - limits["max_alternativos"]
        penalty = min(5, excess * 0.5)
        adeq_score -= penalty
        alertas.append(
            f"Alternativos ({alt_pct:.1f}%) excede limite ({limits['max_alternativos']}%)"
        )

    adeq_score = max(0, adeq_score)
    dimensoes.append({
        "nome": "Adequacao ao Perfil",
        "score": adeq_score, "max": 25,
        "nota": _grade(adeq_score, 25),
        "detalhes": (
            f"RV: {rv_pct:.0f}% (max {limits['max_renda_variavel']}%), "
            f"Cred: {cred_pct:.0f}% (max {limits['max_credito_privado']}%), "
            f"Alt: {alt_pct:.0f}% (max {limits['max_alternativos']}%)"
        ),
    })

    # ── 3. LIQUIDEZ (20 pts) ──
    liq_score = 20

    # Estimate D+5 liquidity from available data
    caixa_pct = type_pcts.get("caixa", 0)
    quick_assets_pct = caixa_pct  # D+0 to D+5

    # Check resgate fields for better estimate
    d5_total = 0
    for item in cart:
        resgate = str(item.get("resgate", "")).lower()
        pct = float(item.get("pct_alvo", item.get("% Alvo", 0)) or 0)
        if "d+0" in resgate or "d+1" in resgate or "d+2" in resgate or "d+5" in resgate:
            d5_total += pct
        elif "imediato" in resgate:
            d5_total += pct

    effective_d5 = max(quick_assets_pct, d5_total)

    if effective_d5 < limits["min_liquidez_d5"]:
        deficit = limits["min_liquidez_d5"] - effective_d5
        penalty = min(15, deficit * 0.5)
        liq_score -= penalty
        alertas.append(
            f"Liquidez D+5 estimada ({effective_d5:.0f}%) abaixo do minimo ({limits['min_liquidez_d5']}%)"
        )

    # Use analytics if available
    if analytics:
        liquidity = analytics.get("liquidity", {})
        if liquidity.get("pct_cash_quickly_proposta"):
            actual_d5 = liquidity["pct_cash_quickly_proposta"]
            if actual_d5 < limits["min_liquidez_d5"]:
                liq_score = max(0, liq_score - 5)

    liq_score = max(0, liq_score)
    dimensoes.append({
        "nome": "Liquidez",
        "score": liq_score, "max": 20,
        "nota": _grade(liq_score, 20),
        "detalhes": f"Caixa rapido (D+5) estimado: {effective_d5:.0f}% (min: {limits['min_liquidez_d5']}%)",
    })

    # ── 4. COMPLETUDE DA PROPOSTA (15 pts) ──
    comp_score = 0
    section_texts = proposta.get("section_texts", {}) or {}

    completeness_checks = [
        (bool(proposta.get("diagnostico_texto")), 2, "Diagnostico"),
        (bool(section_texts.get("sumario_executivo")), 2, "Sumario executivo"),
        (bool(section_texts.get("premissas_filosofia")), 1, "Premissas"),
        (bool(section_texts.get("objetivos_proposta")), 1, "Objetivos"),
        (bool(section_texts.get("monitoramento_governanca")), 1, "Monitoramento"),
        (bool(proposta.get("politica_investimentos")), 2, "Politica de investimentos"),
        (bool(proposta.get("fundos_sugeridos")), 2, "Fund cards"),
        (bool(proposta.get("proposta_comercial")), 2, "Proposta comercial"),
        (bool(proposta.get("analytics_data")), 1, "Analytics"),
        (bool(proposta.get("backtest_data")), 1, "Backtest"),
    ]

    for condition, weight, label in completeness_checks:
        if condition:
            comp_score += weight

    comp_score = min(15, comp_score)
    missing_sections = [label for cond, _, label in completeness_checks if not cond]
    dimensoes.append({
        "nome": "Completude",
        "score": comp_score, "max": 15,
        "nota": _grade(comp_score, 15),
        "detalhes": f"{len(completeness_checks) - len(missing_sections)}/{len(completeness_checks)} secoes preenchidas",
    })

    # ── 5. QUALIDADE DOS ATIVOS (15 pts) ──
    qual_score = 15

    # Check if assets have proper justification
    no_justification = sum(
        1 for item in cart
        if not item.get("justificativa") and not item.get("Justificativa") and not item.get("estrategia")
    )
    if no_justification > len(cart) * 0.5:
        qual_score -= 5
        alertas.append(f"{no_justification} ativo(s) sem justificativa")

    # Check if enriched with catalog data
    enriched = sum(1 for item in cart if item.get("retorno_alvo") or item.get("resgate"))
    if enriched < len(cart) * 0.5 and len(cart) > 2:
        qual_score -= 3
        alertas.append("Menos de 50% dos ativos com dados do catalogo (retorno alvo, resgate)")

    # Check allocation totals
    total_pct = sum(pcts)
    if abs(total_pct - 100) > 2:
        qual_score -= 5
        alertas.append(f"Alocacao total ({total_pct:.1f}%) nao soma 100%")

    qual_score = max(0, qual_score)
    dimensoes.append({
        "nome": "Qualidade",
        "score": qual_score, "max": 15,
        "nota": _grade(qual_score, 15),
        "detalhes": f"{enriched}/{len(cart)} ativos enriquecidos, alocacao: {total_pct:.1f}%",
    })

    # ── TOTAL ──
    score_total = sum(d["score"] for d in dimensoes)

    if score_total >= 85:
        selo = "Excelente"
    elif score_total >= 70:
        selo = "Bom"
    elif score_total >= 50:
        selo = "Atencao"
    else:
        selo = "Critico"

    return {
        "score_total": score_total,
        "dimensoes": dimensoes,
        "alertas": alertas,
        "selo": selo,
    }


def _grade(score, max_score):
    """Convert numeric score to letter grade."""
    if max_score == 0:
        return "N/A"
    pct = score / max_score * 100
    if pct >= 90:
        return "A"
    elif pct >= 75:
        return "B"
    elif pct >= 60:
        return "C"
    elif pct >= 40:
        return "D"
    return "F"


def score_color(score):
    """Return brand color based on score."""
    if score >= 85:
        return "#6BDE97"  # verde
    elif score >= 70:
        return "#5C85F7"  # azul
    elif score >= 50:
        return "#FFBB00"  # amarelo
    else:
        return "#ED5A6E"  # rosa
