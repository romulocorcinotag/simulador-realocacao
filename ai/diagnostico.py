"""
AI-powered portfolio diagnostic generation.
"""
import json

from ai.client import ask_claude, is_ai_available


SYSTEM_PROMPT = """Voce e um analista de investimentos senior da TAG Investimentos, uma das principais gestoras independentes do Brasil.

Sua tarefa e analisar a carteira de investimentos de um prospect e gerar um diagnostico profissional, objetivo e direto.

Diretrizes:
- Use linguagem profissional mas acessivel
- Cite numeros especificos da carteira
- Identifique pontos fortes e fracos
- Sugira oportunidades de melhoria sem ser agressivo
- Nao use emojis
- Mantenha tom consultivo e confiante
- Escreva em portugues do Brasil
- Seja conciso (maximo 400 palavras)

Classes de ativos TAG (referencia):
- LOCAL CAIXA (TPF, Credito D0) - liquidez imediata
- LOCAL RENDA FIXA POS (Credito HG, FIDC, HY) - pos-fixado CDI
- LOCAL RENDA FIXA PRE (TPF, Credito) - pre-fixado
- LOCAL RENDA FIXA CDI+ (Credito) - CDI + spread
- LOCAL RENDA FIXA INFLACAO (TPF, Credito) - IPCA+
- RF FUNDOS LISTADOS ISENTOS (Credito) - FIIs, CRIs listados
- RF CAMBIAL (Cambial) - hedge cambial
- LOCAL RENDA VARIAVEL (RV) - acoes, ETFs
- LOCAL MULTIMERCADO (MM) - fundos multimercado
- LOCAL ALTERNATIVOS (ALTS, Cripto) - private equity, special sits
- LOCAL HEDGES (ALTS) - protecao

Estrutura do diagnostico:
1. VISAO GERAL (2-3 frases resumindo a carteira)
2. PONTOS DE ATENCAO (bullets com problemas identificados)
3. OPORTUNIDADES (bullets com melhorias possiveis, referenciando as classes TAG)
4. RECOMENDACAO (1 frase com a conclusao principal)
"""


def generate_diagnostico(prospect_data, carteira_data, diagnostico_metricas):
    """Generate AI-powered diagnostic text for the prospect's portfolio."""
    if not is_ai_available():
        return _generate_fallback(diagnostico_metricas)

    restricoes = prospect_data.get("restricoes", [])
    if isinstance(restricoes, str):
        try:
            restricoes = json.loads(restricoes)
        except Exception:
            restricoes = [restricoes] if restricoes else []

    objetivos = prospect_data.get("objetivos", [])
    if isinstance(objetivos, str):
        try:
            objetivos = json.loads(objetivos)
        except Exception:
            objetivos = [objetivos] if objetivos else []

    user_msg = f"""Analise esta carteira de um prospect:

PERFIL DO PROSPECT:
- Nome: {prospect_data.get('nome', 'N/A')}
- Perfil: {prospect_data.get('perfil_investidor', 'N/A')}
- Patrimonio Investivel: R$ {prospect_data.get('patrimonio_investivel', 0):,.0f}
- Horizonte: {prospect_data.get('horizonte_investimento', 'N/A')}
- Objetivos: {', '.join(objetivos) if objetivos else 'Nao informado'}
- Retirada Mensal: R$ {prospect_data.get('retirada_mensal', 0):,.0f}
- Restricoes: {', '.join(restricoes) if restricoes else 'Nenhuma'}
{f"- Restricoes adicionais: {prospect_data.get('restricoes_texto', '')}" if prospect_data.get('restricoes_texto') else ''}

CARTEIRA ATUAL ({diagnostico_metricas.get('num_ativos', 0)} ativos):
{_format_carteira(carteira_data)}

METRICAS CALCULADAS:
- PL Total: R$ {diagnostico_metricas.get('total_pl', 0):,.0f}
- Concentracao Top 3: {diagnostico_metricas.get('top3_pct', 0):.1f}%
- HHI (indice de concentracao): {diagnostico_metricas.get('hhi', 0):.0f}
- Liquidez D+0-1: {diagnostico_metricas.get('liq_buckets', {}).get('D+0-1', 0):.1f}%
- Liquidez D+2-5: {diagnostico_metricas.get('liq_buckets', {}).get('D+2-5', 0):.1f}%
- Liquidez D+6-30: {diagnostico_metricas.get('liq_buckets', {}).get('D+6-30', 0):.1f}%
- Liquidez D+30+: {diagnostico_metricas.get('liq_buckets', {}).get('D+30+', 0):.1f}%
- Categorias: {diagnostico_metricas.get('categorias', {})}
"""

    return ask_claude(SYSTEM_PROMPT, user_msg)


def _format_carteira(carteira_data):
    """Format portfolio data for the prompt."""
    if not carteira_data:
        return "Dados nao disponiveis"
    lines = []
    for item in carteira_data[:25]:  # Limit to 25 assets
        name = str(item.get("Ativo", "N/A"))[:40]
        fin = item.get("Financeiro", 0)
        cat = item.get("Estrategia", item.get("Categoria", item.get("estrategia", "")))
        line = f"  - {name}: R$ {fin:,.0f}"
        if cat:
            line += f" ({cat})"
        lines.append(line)
    if len(carteira_data) > 25:
        lines.append(f"  ... e mais {len(carteira_data) - 25} ativos")
    return "\n".join(lines)


def _generate_fallback(metricas):
    """Generate a basic diagnostic without AI."""
    parts = ["DIAGNOSTICO DA CARTEIRA\n"]

    total = metricas.get("total_pl", 0)
    num = metricas.get("num_ativos", 0)
    top3 = metricas.get("top3_pct", 0)

    parts.append(f"A carteira possui {num} ativos com patrimonio total de R$ {total:,.0f}.\n")

    # Concentration
    if top3 > 60:
        parts.append(f"ATENCAO: Alta concentracao - os 3 maiores ativos representam {top3:.1f}% do portfolio.")
    elif top3 > 40:
        parts.append(f"Concentracao moderada - top 3 ativos representam {top3:.1f}% do PL.")
    else:
        parts.append(f"Boa diversificacao - top 3 ativos representam {top3:.1f}% do PL.")

    # Liquidity
    liq = metricas.get("liq_buckets", {})
    d01 = liq.get("D+0-1", 0)
    d30 = liq.get("D+30+", 0)
    if d01 < 10:
        parts.append(f"ATENCAO: Apenas {d01:.1f}% da carteira tem liquidez imediata (D+0/D+1).")
    if d30 > 30:
        parts.append(f"ATENCAO: {d30:.1f}% da carteira tem liquidez acima de D+30.")

    # Categories
    cats = metricas.get("categorias", {})
    if cats:
        parts.append("\nAlocacao por categoria:")
        for cat, pct in sorted(cats.items(), key=lambda x: -x[1]):
            parts.append(f"  - {cat}: {pct:.1f}%")

    parts.append("\n[Diagnostico basico - configure a API Key da Anthropic para analise completa com IA]")
    return "\n".join(parts)
