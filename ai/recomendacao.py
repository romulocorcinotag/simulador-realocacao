"""
AI-powered portfolio recommendation engine.
Selects model portfolio and applies client-specific restrictions.
Supports rich model data with asset classes, subcategories, and min/max bands.
"""
import json

from ai.client import ask_claude_json, ask_claude, is_ai_available


SYSTEM_PROMPT = """Voce e o gestor de carteiras da TAG Investimentos. Sua funcao e recomendar uma carteira personalizada para o prospect.

Voce recebe:
1. Perfil do prospect (conservador/moderado/arrojado/agressivo)
2. Carteira modelo base da TAG para aquele perfil (com classes de ativos, bandas min/max e fundos recomendados)
3. Carteira atual do prospect
4. Restricoes especificas do cliente

Seu trabalho:
1. Partir da carteira modelo base da TAG
2. Aplicar as restricoes do cliente (ex: se "nao vender RF", manter os ativos de renda fixa da carteira atual)
3. Se o cliente tem restricao de manter ativos, calcule quanto % eles representam e redistribua o restante seguindo as proporcoes do modelo
4. Ajustar alocacoes para que a soma de 100%
5. Respeitar as bandas MIN e MAX de cada classe de ativo
6. Justificar cada mudanca em relacao ao modelo base

Regras importantes:
- A soma total DEVE ser exatamente 100%
- Cada ativo deve estar dentro das bandas MIN-MAX definidas no modelo
- Se o cliente tem ativos que devem ser mantidos (restricao), incorpore-os na classe adequada
- Use os fundos/ativos recomendados pela TAG (coluna "Ativo" do modelo)
- Para classes com multiplos fundos (ex: "VIT ACOES 30%, VIT LONG BIAS 60%, SPXR11 10%"), distribua proporcionalmente

Responda APENAS em JSON com esta estrutura:
{
    "carteira_proposta": [
        {
            "classe": "LOCAL RENDA FIXA INFLACAO",
            "subcategoria": "TPF",
            "ativo": "B5P211 (IMAB 5 ETF ITAU)",
            "pct_alvo": 15.0,
            "estrategia": "Renda Fixa",
            "justificativa": "Mantido conforme modelo base para protecao inflacionaria"
        }
    ],
    "ajustes_aplicados": [
        "Mantidos X ativos de renda fixa por restricao do cliente",
        "Redistribuido Y% entre classes de maior risco"
    ],
    "resumo": "Texto curto explicando a carteira proposta e os ajustes feitos"
}
"""


def generate_recomendacao(prospect_data, carteira_atual, modelo_base, fundos_disponiveis=None):
    """Generate a personalized portfolio recommendation."""
    if not is_ai_available():
        return _fallback_recomendacao(modelo_base, prospect_data)

    restricoes = prospect_data.get("restricoes", [])
    if isinstance(restricoes, str):
        try:
            restricoes = json.loads(restricoes)
        except Exception:
            restricoes = [restricoes] if restricoes else []

    restricoes_texto = prospect_data.get("restricoes_texto", "")

    objetivos = prospect_data.get("objetivos", [])
    if isinstance(objetivos, str):
        try:
            objetivos = json.loads(objetivos)
        except Exception:
            objetivos = [objetivos] if objetivos else []

    user_msg = f"""
PROSPECT:
- Nome: {prospect_data.get('nome', '')}
- Perfil: {prospect_data.get('perfil_investidor', 'Moderado')}
- Patrimonio: R$ {prospect_data.get('patrimonio_investivel', 0):,.0f}
- Horizonte: {prospect_data.get('horizonte_investimento', 'N/A')}
- Objetivos: {', '.join(objetivos) if objetivos else 'Nao informado'}
- Retirada mensal: R$ {prospect_data.get('retirada_mensal', 0):,.0f}

RESTRICOES DO CLIENTE:
{chr(10).join(f'- {r}' for r in restricoes) if restricoes else '- Nenhuma restricao especifica'}
{f'- Adicional: {restricoes_texto}' if restricoes_texto else ''}

CARTEIRA MODELO BASE TAG ({prospect_data.get('perfil_investidor', 'Moderado')}):
{_format_modelo_rico(modelo_base)}

CARTEIRA ATUAL DO PROSPECT:
{_format_carteira_atual(carteira_atual)}

Gere a carteira proposta personalizada aplicando as restricoes. A soma dos percentuais deve ser 100%.
Se a carteira atual tem ativos que devem ser mantidos por restricao, incorpore-os na proposta.
"""

    result = ask_claude_json(SYSTEM_PROMPT, user_msg)

    if "error" in result:
        return _fallback_recomendacao(modelo_base, prospect_data)

    return result


def generate_texto_recomendacao(prospect_data, proposta_data, diagnostico_texto):
    """Generate professional recommendation text."""
    if not is_ai_available():
        return "Configure a API Key para gerar texto personalizado com IA."

    system = """Voce e o gestor de carteiras da TAG Investimentos. Gere um texto profissional de recomendacao
de investimento para o prospect. O texto deve ser consultivo, usar dados concretos, e transmitir confianca.

Diretrizes:
- Maximo 400 palavras
- Sem emojis
- Tom profissional e direto
- Referencie os dados do prospect (nome, perfil, patrimonio)
- Explique o racional das mudancas propostas
- Mencione as classes de ativos e por que foram escolhidas
- Portugues do Brasil

Estrutura sugerida:
1. Saudacao e contexto (perfil e necessidades do cliente)
2. Diagnostico resumido (principais pontos de atencao da carteira atual)
3. Nossa recomendacao (mudancas principais com justificativa)
4. Beneficios esperados (diversificacao, liquidez, retorno, protecao)
5. Proximos passos
"""

    # Prepare proposta summary
    proposta_resumo = ""
    if isinstance(proposta_data, dict):
        carteira = proposta_data.get("carteira_proposta", [])
        if carteira:
            lines = []
            for item in carteira[:15]:
                name = item.get("ativo", "")
                pct = item.get("pct_alvo", item.get("% Alvo", 0))
                classe = item.get("classe", item.get("estrategia", ""))
                if pct > 0:
                    lines.append(f"  - {name}: {pct:.1f}% ({classe})")
            proposta_resumo = "\n".join(lines)

        ajustes = proposta_data.get("ajustes_aplicados", [])
        if ajustes:
            proposta_resumo += "\n\nAjustes aplicados:\n"
            proposta_resumo += "\n".join(f"  - {a}" for a in ajustes)

    user_msg = f"""
PROSPECT: {prospect_data.get('nome', '')}
PERFIL: {prospect_data.get('perfil_investidor', '')}
PATRIMONIO: R$ {prospect_data.get('patrimonio_investivel', 0):,.0f}
HORIZONTE: {prospect_data.get('horizonte_investimento', 'N/A')}

DIAGNOSTICO:
{diagnostico_texto[:800] if diagnostico_texto else 'Sem diagnostico disponivel'}

CARTEIRA PROPOSTA:
{proposta_resumo if proposta_resumo else json.dumps(proposta_data, ensure_ascii=False, indent=2)[:1000]}

Gere o texto de recomendacao profissional.
"""
    return ask_claude(system, user_msg)


def _format_modelo_rico(modelo):
    """Format model portfolio for prompt, handling both rich and simple formats."""
    if not modelo:
        return "Modelo nao definido"

    lines = []
    for item in modelo:
        # Rich format (with Classe, Subcategoria, Min, Max)
        classe = item.get("Classe", item.get("classe", ""))
        sub = item.get("Subcategoria", item.get("subcategoria", ""))
        name = item.get("Ativo", item.get("ativo", ""))
        pct = item.get("% Alvo", item.get("pct_alvo", 0))
        min_pct = item.get("Min %", item.get("min_pct", ""))
        max_pct = item.get("Max %", item.get("max_pct", ""))

        if classe and sub:
            line = f"  - [{classe} / {sub}] {name}: {pct:.1f}%"
            if min_pct != "" and max_pct != "":
                line += f" (banda: {min_pct}-{max_pct}%)"
        else:
            code = item.get("Codigo", item.get("codigo", ""))
            line = f"  - {name}"
            if code:
                line += f" ({code})"
            line += f": {pct:.1f}%"

        lines.append(line)

    return "\n".join(lines)


def _format_carteira_atual(carteira):
    """Format current portfolio for prompt."""
    if not carteira:
        return "Carteira nao informada"
    lines = []
    for item in carteira[:25]:
        name = str(item.get("Ativo", "N/A"))[:40]
        fin = item.get("Financeiro", 0)
        cat = item.get("Estrategia", item.get("Categoria", item.get("estrategia", "")))
        line = f"  - {name}: R$ {fin:,.0f}"
        if cat:
            line += f" ({cat})"
        lines.append(line)
    return "\n".join(lines)


def _fallback_recomendacao(modelo_base, prospect_data):
    """Fallback when AI is not available - return the base model as-is."""
    carteira = []
    if modelo_base:
        for item in modelo_base:
            pct = float(item.get("% Alvo", item.get("pct_alvo", 0)))
            if pct <= 0:
                continue
            carteira.append({
                "classe": item.get("Classe", item.get("classe", "")),
                "subcategoria": item.get("Subcategoria", item.get("subcategoria", "")),
                "ativo": item.get("Ativo", item.get("ativo", "")),
                "pct_alvo": pct,
                "estrategia": item.get("Classe", item.get("classe", "")),
                "justificativa": "Modelo base (sem ajuste IA)",
            })

    return {
        "carteira_proposta": carteira,
        "ajustes_aplicados": ["Modelo base aplicado sem ajustes (IA nao disponivel)"],
        "resumo": f"Carteira modelo {prospect_data.get('perfil_investidor', 'Moderado')} aplicada diretamente. Configure a API Key para recomendacao personalizada.",
    }
