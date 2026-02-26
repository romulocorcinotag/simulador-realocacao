"""
AI-powered text generation for professional proposal sections.
Generates text in batched API calls to minimize cost.

Batches:
  1. Strategy & Philosophy (Sections 1, 2, 7, 15)
  2. Portfolio Analysis (Sections 5, 8)
  3. Bottom-Up Descriptions (Section 9)
  4. Fund Descriptions (fund cards from catalog)
  5. Investment Policy (with TAG principles)
  6. Patrimonial Analysis (succession, family structure)
"""
import json

from ai.client import ask_claude, is_ai_available


# ── Batch 1: Strategy & Philosophy (Sections 1, 2, 7, 15) ──

_BATCH1_SYSTEM = """Voce e um consultor senior de investimentos da TAG Investimentos.
Sua tarefa e gerar textos profissionais para 4 secoes de uma proposta de investimentos.

Regras:
- Escreva em portugues do Brasil, tom consultivo e confiante
- Nao use emojis
- Seja conciso mas completo
- Cite dados concretos quando fornecidos
- Use formatacao com bullets onde apropriado
- Separe as secoes com os delimitadores exatos indicados

Gere EXATAMENTE estas 4 secoes, usando os delimitadores:

### SECAO_1_SUMARIO_EXECUTIVO ###
(3-5 bullets comparando carteira atual vs proposta, principais decisoes de alocacao,
impactos esperados em risco/retorno/liquidez. Maximo 200 palavras.)

### SECAO_2_PREMISSAS_FILOSOFIA ###
(Horizonte de investimento do cliente, papel da carteira no patrimonio,
principios da casa: diversificacao real, liquidez como ativo, risco antes de retorno,
assimetria > previsibilidade. Maximo 200 palavras.)

### SECAO_7_OBJETIVOS_PROPOSTA ###
("Contrato psicologico": o que essa carteira entrega, o que nao promete,
em quais cenarios tende a ir bem/mal. Maximo 200 palavras.)

### SECAO_15_MONITORAMENTO ###
(Frequencia de revisao, indicadores acompanhados, gatilhos de reavaliacao,
papel do cliente na tomada de decisao. Maximo 150 palavras.)
"""


# ── Batch 2: Portfolio Analysis (Sections 5, 8) ──

_BATCH2_SYSTEM = """Voce e um gestor de carteiras da TAG Investimentos.
Gere textos profissionais para 2 secoes de uma proposta de investimentos.

Regras:
- Portugues do Brasil, tom consultivo
- Nao use emojis
- Nunca use linguagem negativa direta sobre ativos existentes
- Use a matriz de classificacao: Convictos / Neutros / Observacao / Saida Estrutural / Iliquidos
- Para justificativas de movimentos, foque em: diversificacao, governanca, eficiencia

Gere EXATAMENTE estas 2 secoes:

### SECAO_5_ANALISE_BOTTOM_UP ###
(Narrativa profissional sobre a classificacao dos ativos da carteira atual.
Explique a logica da matriz sem ser pejorativo. Maximo 300 palavras.)

### SECAO_8_PROPOSTA_TOP_DOWN ###
(Justificativa de cada grande movimento de alocacao: o que reduziu e por que,
o que aumentou e por que, novas estrategias incluidas. Maximo 300 palavras.)
"""


# ── Batch 3: Bottom-Up Descriptions (Section 9) ──

_BATCH3_SYSTEM = """Voce e um analista de fundos da TAG Investimentos.
Para cada ativo da carteira proposta, gere uma descricao profissional.

Regras:
- Portugues do Brasil
- Para cada ativo, use este formato:

**[NOME DO ATIVO]**
- O que e: [1 frase]
- Papel na carteira: [1 frase]
- Principal risco: [1 frase]
- Horizonte minimo: [ex: 6 meses, 1 ano, 3 anos]

Gere a secao inteira sob o delimitador:

### SECAO_9_PROPOSTA_BOTTOM_UP ###
"""


# ── Batch 4: Fund Card Descriptions ──

_BATCH4_SYSTEM = """Voce e um analista de fundos da TAG Investimentos.
Para cada fundo sugerido, gere um texto de descricao conciso para o card de apresentacao.

Regras:
- Portugues do Brasil, tom profissional
- Nao use emojis
- Para cada fundo, formato:

**[NOME]** ([TIPO] - [SUBTIPO])
Estrategia: [2-3 frases sobre a estrategia, incluindo diferenciais]
Resgate: [prazo]
Retorno-alvo: [retorno]
Risco principal: [1 frase]
Horizonte: [prazo minimo sugerido]

Se dados do catalogo TAG estiverem disponiveis, USE-OS como base.
Se nao, gere com base no nome e categoria do ativo.

Gere sob o delimitador:
### SECAO_FUND_CARDS ###
"""


# ── Batch 5: Investment Policy ──

_BATCH5_SYSTEM = """Voce e um consultor de governanca de investimentos da TAG Investimentos.
Gere o documento de Politica de Investimentos personalizada para o prospect.

Principios TAG que DEVEM ser incorporados:
1. Conservadorismo como premissa: investimentos predominantemente em renda fixa em Reais
2. Diversificacao obrigatoria: limites claros por emissor, classe de ativo e gestor
3. Escalonamento de vencimentos: reducao do risco de reinvestimento concentrado
4. Gestao ativa dentro de limites: liberdade para avaliar melhores taxas e momentos
5. Foco em instituicoes S1 e S2 do Banco Central

Classificacao BACEN:
- S1: Banco do Brasil, Bradesco, BTG Pactual, Caixa, Itau, Santander
- S2: Sicoob, Banrisul, Sicredi, BNB, BNDES, Citi, Nu, Safra, Votorantim, XP

Formato da saida - gere 2 secoes:

### SECAO_POLITICA_INVESTIMENTOS ###
(Documento de politica com: objetivo, universo de ativos permitido,
limites por classe/emissor/gestor, benchmark, horizonte.
Use bullets organizados. Maximo 400 palavras.)

### SECAO_GOVERNANCA ###
(Modelo de governanca: frequencia de rebalanceamento, comite de investimentos,
relatorios periodicos, indicadores monitorados. Maximo 200 palavras.)
"""


# ── Batch 6: Patrimonial / Succession Analysis ──

_BATCH6_SYSTEM = """Voce e um consultor de planejamento patrimonial e sucessorio da TAG Investimentos.
Gere uma analise profissional da estrutura patrimonial e sucessoria do prospect.

Drivers de analise que voce deve considerar:
- Processo de Inventario
- Continuidade das Atividades Empresariais
- Atividade Imobiliaria
- Comunicabilidade da Heranca
- Liquidez na Sucessao
- Reforma do Codigo Civil
- Estruturas Internacionais
- Residencia Fiscal

Instrumentos disponiveis:
- Doacao em Adiantamento de Legitima
- Reserva de Usufruto
- Testamento
- Gravames
- Seguro de Vida e Previdencia Complementar
- Alteracao do Regime de Casamento
- Acordos de Acionistas / Protocolo Familiar
- Trust / PICs / Holdings

Gere 2 secoes:

### SECAO_ESTRUTURA_PATRIMONIAL ###
(Analise da estrutura atual do prospect: pontos de atencao, riscos identificados,
recomendacoes de melhoria. Tom consultivo. Maximo 300 palavras.)

### SECAO_ALTERNATIVAS_SUCESSAO ###
(Alternativas recomendadas com base no perfil do cliente:
2-3 alternativas com pros/contras resumidos. Maximo 300 palavras.)
"""


def generate_all_section_texts(prospect, carteira_atual, carteira_proposta,
                                diagnostico_texto, recomendacao_texto,
                                analytics_data, modelo_base=None):
    """Generate text for all AI-powered proposal sections.

    Makes up to 6 batched API calls. Returns dict with section texts.
    Falls back to templates if AI unavailable.
    """
    if not is_ai_available():
        return _generate_fallback_texts(prospect, analytics_data)

    results = {}

    # BATCH 1: Strategy sections (1, 2, 7, 15)
    try:
        b1 = _call_batch1(prospect, carteira_atual, carteira_proposta,
                          diagnostico_texto, analytics_data)
        results.update(b1)
    except Exception:
        results.update(_fallback_batch1(prospect, analytics_data))

    # BATCH 2: Portfolio analysis (5, 8)
    try:
        b2 = _call_batch2(prospect, carteira_atual, carteira_proposta,
                          analytics_data, modelo_base)
        results.update(b2)
    except Exception:
        results.update(_fallback_batch2(analytics_data))

    # BATCH 3: Bottom-up descriptions (9)
    try:
        b3 = _call_batch3(carteira_proposta)
        results.update(b3)
    except Exception:
        results.update(_fallback_batch3(carteira_proposta))

    # BATCH 4: Fund card descriptions
    try:
        b4 = _call_batch4(carteira_proposta)
        results.update(b4)
    except Exception:
        results.update(_fallback_batch4(carteira_proposta))

    # BATCH 5: Investment policy
    try:
        b5 = _call_batch5(prospect, carteira_proposta, analytics_data)
        results.update(b5)
    except Exception:
        results.update(_fallback_batch5(prospect))

    # BATCH 6: Patrimonial analysis (only if family data exists)
    estrutura_familiar = prospect.get("estrutura_familiar", [])
    estrutura_patrimonial = prospect.get("estrutura_patrimonial", {})
    plano_sucessorio = prospect.get("plano_sucessorio", {})
    has_patrimony_data = (
        (isinstance(estrutura_familiar, list) and any(m.get("nome") for m in estrutura_familiar))
        or (isinstance(estrutura_patrimonial, dict) and estrutura_patrimonial.get("tipo"))
        or (isinstance(plano_sucessorio, dict) and any(plano_sucessorio.values()))
    )
    if has_patrimony_data:
        try:
            b6 = _call_batch6(prospect)
            results.update(b6)
        except Exception:
            results.update(_fallback_batch6(prospect))
    else:
        results.update(_fallback_batch6(prospect))

    return results


def _call_batch1(prospect, carteira_atual, carteira_proposta,
                 diagnostico_texto, analytics_data):
    """Generate sections 1, 2, 7, 15."""
    allocation = analytics_data.get("allocation", {})
    risk = analytics_data.get("risk", {})
    liquidity = analytics_data.get("liquidity", {})

    restricoes = prospect.get("restricoes", [])
    if isinstance(restricoes, str):
        try:
            restricoes = json.loads(restricoes)
        except Exception:
            restricoes = []

    objetivos = prospect.get("objetivos", [])
    if isinstance(objetivos, str):
        try:
            objetivos = json.loads(objetivos)
        except Exception:
            objetivos = []

    msg = f"""DADOS DO PROSPECT:
- Nome: {prospect.get('nome', 'N/A')}
- Perfil: {prospect.get('perfil_investidor', 'N/A')}
- Patrimonio: R$ {prospect.get('patrimonio_investivel', 0):,.0f}
- Horizonte: {prospect.get('horizonte_investimento', 'N/A')}
- Objetivos: {', '.join(objetivos) if objetivos else 'Nao informado'}
- Restricoes: {', '.join(restricoes) if restricoes else 'Nenhuma'}
- Retirada Mensal: R$ {prospect.get('retirada_mensal', 0):,.0f}

DIAGNOSTICO (resumo):
{diagnostico_texto[:500] if diagnostico_texto else 'N/A'}

ALOCACAO POR CLASSE:
{json.dumps(allocation.get('class_breakdown', [])[:10], indent=2, ensure_ascii=False)}

RISCO - CONCENTRACAO:
- Top 5 emissores: {risk.get('top5_issuer_pct', 0):.1f}%
- HHI: {risk.get('hhi_issuer', 0):.0f}

LIQUIDEZ:
- Atual D+0-5: {liquidity.get('pct_cash_quickly_atual', 0):.1f}%
- Proposta D+0-5: {liquidity.get('pct_cash_quickly_proposta', 0):.1f}%
"""

    response = ask_claude(_BATCH1_SYSTEM, msg, max_tokens=3000)
    return _parse_sections(response, {
        "SECAO_1_SUMARIO_EXECUTIVO": "sumario_executivo",
        "SECAO_2_PREMISSAS_FILOSOFIA": "premissas_filosofia",
        "SECAO_7_OBJETIVOS_PROPOSTA": "objetivos_proposta",
        "SECAO_15_MONITORAMENTO": "monitoramento_governanca",
    })


def _call_batch2(prospect, carteira_atual, carteira_proposta,
                 analytics_data, modelo_base):
    """Generate sections 5, 8."""
    bottom_up_data = analytics_data.get("bottom_up", [])
    allocation = analytics_data.get("allocation", {})

    bu_text = ""
    if bottom_up_data:
        for item in bottom_up_data[:20]:
            bu_text += f"- {item['ativo']}: {item['classificacao']} ({item['motivo']})\n"

    alloc_text = ""
    for item in allocation.get("class_breakdown", []):
        if abs(item.get("delta", 0)) > 0.5:
            direction = "+" if item["delta"] > 0 else ""
            alloc_text += (f"- {item['classe']}: {item['pct_atual']:.1f}% -> "
                          f"{item['pct_proposta']:.1f}% ({direction}{item['delta']:.1f}pp)\n")

    msg = f"""PROSPECT: {prospect.get('nome', 'N/A')} - {prospect.get('perfil_investidor', 'N/A')}

CLASSIFICACAO BOTTOM-UP DOS ATIVOS ATUAIS:
{bu_text or 'Dados nao disponiveis'}

MUDANCAS DE ALOCACAO:
{alloc_text or 'Dados nao disponiveis'}

NUMERO DE ATIVOS: {len(carteira_atual or [])} atual -> {len(carteira_proposta or [])} proposta
"""

    response = ask_claude(_BATCH2_SYSTEM, msg, max_tokens=2000)
    return _parse_sections(response, {
        "SECAO_5_ANALISE_BOTTOM_UP": "analise_bottom_up_texto",
        "SECAO_8_PROPOSTA_TOP_DOWN": "proposta_top_down_texto",
    })


def _call_batch3(carteira_proposta):
    """Generate section 9 - per-asset descriptions."""
    assets_text = ""
    for item in (carteira_proposta or [])[:20]:
        name = item.get("ativo", item.get("Ativo", "N/A"))
        cat = item.get("classe", item.get("Classe", item.get("categoria",
              item.get("Categoria", item.get("estrategia", "")))))
        pct = item.get("pct_alvo", item.get("% Alvo", item.get("proposta_pct", 0)))
        just = item.get("justificativa", item.get("Justificativa", ""))
        assets_text += f"- {name} ({cat}) - {pct}% {f'- {just}' if just else ''}\n"

    msg = f"""ATIVOS DA CARTEIRA PROPOSTA:
{assets_text or 'Nenhum ativo definido'}

Gere a descricao para cada ativo acima."""

    response = ask_claude(_BATCH3_SYSTEM, msg, max_tokens=3000)
    return _parse_sections(response, {
        "SECAO_9_PROPOSTA_BOTTOM_UP": "proposta_bottom_up_texto",
    })


def _call_batch4(carteira_proposta):
    """Generate fund card descriptions using catalog data."""
    from shared.fund_catalog import match_fund_catalog

    funds_text = ""
    for item in (carteira_proposta or [])[:20]:
        name = item.get("ativo", item.get("Ativo", ""))
        cat = item.get("classe", item.get("Classe", ""))
        pct = item.get("pct_alvo", item.get("% Alvo", 0))

        # Try to match fund catalog
        catalog_info = match_fund_catalog(name)
        if catalog_info:
            funds_text += (
                f"\n- {name} ({pct}%)\n"
                f"  CATALOGO TAG: {json.dumps(catalog_info, ensure_ascii=False)[:500]}\n"
            )
        else:
            funds_text += f"\n- {name} ({cat}, {pct}%) - sem dados de catalogo\n"

    msg = f"""ATIVOS DA CARTEIRA PROPOSTA COM DADOS DE CATALOGO:
{funds_text or 'Nenhum ativo definido'}

Gere a descricao de card para cada ativo. Use os dados do catalogo quando disponiveis."""

    response = ask_claude(_BATCH4_SYSTEM, msg, max_tokens=3000)
    return _parse_sections(response, {
        "SECAO_FUND_CARDS": "fund_cards_texto",
    })


def _call_batch5(prospect, carteira_proposta, analytics_data):
    """Generate investment policy sections."""
    perfil = prospect.get("perfil_investidor", "Moderado")
    patrimonio = prospect.get("patrimonio_investivel", 0)
    horizonte = prospect.get("horizonte_investimento", "N/A")

    # Load default limits for profile
    from shared.tag_institucional import LIMITES_POLITICA_DEFAULT
    limites = LIMITES_POLITICA_DEFAULT.get(perfil, LIMITES_POLITICA_DEFAULT.get("Moderado", {}))

    msg = f"""PROSPECT:
- Nome: {prospect.get('nome', 'N/A')}
- Perfil: {perfil}
- Patrimonio: R$ {patrimonio:,.0f}
- Horizonte: {horizonte}

LIMITES PADRAO PARA PERFIL {perfil.upper()}:
{json.dumps(limites, indent=2, ensure_ascii=False)}

NUMERO DE ATIVOS NA CARTEIRA PROPOSTA: {len(carteira_proposta or [])}

Gere a politica de investimentos e o modelo de governanca personalizados."""

    response = ask_claude(_BATCH5_SYSTEM, msg, max_tokens=3000)
    return _parse_sections(response, {
        "SECAO_POLITICA_INVESTIMENTOS": "politica_investimentos_texto",
        "SECAO_GOVERNANCA": "governanca_texto",
    })


def _call_batch6(prospect):
    """Generate patrimonial/succession analysis."""
    estrutura_familiar = prospect.get("estrutura_familiar", [])
    estrutura_patrimonial = prospect.get("estrutura_patrimonial", {})
    plano_sucessorio = prospect.get("plano_sucessorio", {})

    family_text = ""
    if isinstance(estrutura_familiar, list):
        for m in estrutura_familiar:
            if m.get("nome"):
                family_text += f"- {m['nome']} ({m.get('relacao', '')}, {m.get('idade', '?')} anos, {m.get('regime_casamento', 'N/A')})\n"

    patrim_text = ""
    if isinstance(estrutura_patrimonial, dict):
        patrim_text = (
            f"- Tipo: {estrutura_patrimonial.get('tipo', 'N/A')}\n"
            f"- Offshore: {'Sim' if estrutura_patrimonial.get('possui_offshore') else 'Nao'}\n"
            f"- Jurisdicao: {estrutura_patrimonial.get('jurisdicao', 'N/A')}\n"
            f"- Holdings: {estrutura_patrimonial.get('holdings_texto', 'N/A')}\n"
            f"- Patrimonio Sucessao: R$ {estrutura_patrimonial.get('patrimonio_sucessao', 0):,.0f}\n"
        )

    plano_text = ""
    if isinstance(plano_sucessorio, dict):
        instruments = []
        if plano_sucessorio.get("testamento"):
            instruments.append("Testamento")
        if plano_sucessorio.get("doacao_antecipada"):
            instruments.append("Doacao antecipada")
        if plano_sucessorio.get("seguro_vida"):
            instruments.append("Seguro de vida/Previdencia")
        if plano_sucessorio.get("trust"):
            instruments.append("Trust/PIC")
        if plano_sucessorio.get("holding_familiar"):
            instruments.append("Holding familiar")
        if plano_sucessorio.get("protocolo_familiar"):
            instruments.append("Protocolo familiar")
        plano_text = (
            f"Instrumentos ja utilizados: {', '.join(instruments) if instruments else 'Nenhum'}\n"
            f"Observacoes: {plano_sucessorio.get('observacoes', 'N/A')}"
        )

    msg = f"""PROSPECT:
- Nome: {prospect.get('nome', 'N/A')}
- Perfil: {prospect.get('perfil_investidor', 'N/A')}
- Patrimonio Total: R$ {prospect.get('patrimonio_total', 0):,.0f}
- Patrimonio Investivel: R$ {prospect.get('patrimonio_investivel', 0):,.0f}

ESTRUTURA FAMILIAR:
{family_text or 'Nao informada'}

ESTRUTURA PATRIMONIAL:
{patrim_text or 'Nao informada'}

PLANO SUCESSORIO ATUAL:
{plano_text or 'Nao informado'}

Gere a analise patrimonial e as alternativas de sucessao."""

    response = ask_claude(_BATCH6_SYSTEM, msg, max_tokens=3000)
    return _parse_sections(response, {
        "SECAO_ESTRUTURA_PATRIMONIAL": "estrutura_patrimonial_texto",
        "SECAO_ALTERNATIVAS_SUCESSAO": "alternativas_sucessao_texto",
    })


def _parse_sections(text, mapping):
    """Parse AI response into individual section texts."""
    result = {}
    for delimiter, key in mapping.items():
        marker = f"### {delimiter} ###"
        if marker in text:
            start = text.index(marker) + len(marker)
            # Find next marker or end
            end = len(text)
            for other_delim in mapping:
                other_marker = f"### {other_delim} ###"
                if other_marker in text and text.index(other_marker) > start:
                    pos = text.index(other_marker)
                    if pos < end:
                        end = pos
            result[key] = text[start:end].strip()
        else:
            result[key] = ""
    return result


# ── Fallback texts (no AI) ──

def _generate_fallback_texts(prospect, analytics_data):
    """Generate template-based texts when AI is unavailable."""
    result = {}
    result.update(_fallback_batch1(prospect, analytics_data))
    result.update(_fallback_batch2(analytics_data))
    result.update(_fallback_batch3(None))
    result.update(_fallback_batch4(None))
    result.update(_fallback_batch5(prospect))
    result.update(_fallback_batch6(prospect))
    return result


def _fallback_batch1(prospect, analytics_data):
    nome = prospect.get("nome", "o prospect")
    perfil = prospect.get("perfil_investidor", "N/A")
    horizonte = prospect.get("horizonte_investimento", "N/A")

    return {
        "sumario_executivo": (
            f"A presente proposta visa reestruturar a carteira de {nome}, "
            f"perfil {perfil}, com horizonte de {horizonte}. "
            f"A analise identificou oportunidades de melhoria em diversificacao, "
            f"eficiencia e governanca da gestao de investimentos."
        ),
        "premissas_filosofia": (
            f"A TAG Investimentos adota uma filosofia baseada em: "
            f"diversificacao real entre classes e gestores; liquidez como ativo estrategico; "
            f"analise de risco antes de retorno; e busca por assimetrias positivas. "
            f"O horizonte de investimento considerado e {horizonte}."
        ),
        "objetivos_proposta": (
            f"Esta carteira busca entregar: preservacao de capital no curto prazo, "
            f"rentabilidade consistente acima do CDI, e liquidez compativel com as "
            f"necessidades operacionais. Nao promete retornos acima do mercado em todos "
            f"os cenarios. Tende a ir bem em cenarios de estabilidade e juros estaveis, "
            f"e pode ter desempenho relativo inferior em movimentos abruptos de mercado."
        ),
        "monitoramento_governanca": (
            f"Revisao trimestral da alocacao e dos gestores. "
            f"Indicadores acompanhados: retorno vs CDI, volatilidade, drawdown, concentracao. "
            f"Gatilhos de reavaliacao: drawdown > 5%, mudanca relevante de cenario, "
            f"desvio > 5pp da politica de investimentos."
        ),
    }


def _fallback_batch2(analytics_data):
    return {
        "analise_bottom_up_texto": (
            "A classificacao dos ativos segue uma matriz que busca "
            "organizar cada posicao de acordo com sua contribuicao para a carteira, "
            "sem julgamentos pejorativos. Os ativos foram classificados em: "
            "Convictos (manter), Neutros (acompanhar), Observacao (reavaliar), "
            "Saida Estrutural (resgatar quando possivel) e Iliquidos em Carregamento "
            "(aguardar vencimento)."
        ),
        "proposta_top_down_texto": (
            "A proposta busca reduzir a concentracao por emissor e classe, "
            "aumentar a diversificacao entre gestores e instrumentos, "
            "e melhorar a governanca na gestao do caixa. As mudancas sao "
            "implementadas de forma gradual, aproveitando vencimentos naturais."
        ),
    }


def _fallback_batch3(carteira_proposta):
    return {
        "proposta_bottom_up_texto": (
            "[Configure a API Key da Anthropic para descricoes detalhadas "
            "dos ativos propostos]"
        ),
    }


def _fallback_batch4(carteira_proposta):
    return {
        "fund_cards_texto": "",
    }


def _fallback_batch5(prospect):
    perfil = prospect.get("perfil_investidor", "Moderado")
    return {
        "politica_investimentos_texto": (
            f"**Politica de Investimentos - Perfil {perfil}**\n\n"
            f"- Objetivo: Rentabilidade consistente acima do CDI com risco controlado\n"
            f"- Benchmark: CDI\n"
            f"- Universo: Titulos publicos, bancarios S1/S2, fundos regulados CVM\n"
            f"- Limite por emissor: ate 20%\n"
            f"- Limite por gestor: ate 25%\n"
            f"- Escalonamento de vencimentos obrigatorio\n"
            f"- Revisao trimestral obrigatoria\n\n"
            f"[Configure a API Key para politica personalizada com IA]"
        ),
        "governanca_texto": (
            "Modelo de governanca: revisao trimestral com relatorio completo, "
            "rebalanceamento quando desvio > 5pp da politica, "
            "comite de investimentos semestral. "
            "Indicadores: retorno vs CDI, HHI, drawdown, concentracao por emissor."
        ),
    }


def _fallback_batch6(prospect):
    return {
        "estrutura_patrimonial_texto": "",
        "alternativas_sucessao_texto": "",
    }
