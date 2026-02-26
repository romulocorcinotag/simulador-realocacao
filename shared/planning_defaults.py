"""
Default values for all planning/financial premissas.
Based on TAG 360° system (Legislação 2025).
"""

# ─────────────────────────────────────────────────────────
# PGBL DEFAULTS
# ─────────────────────────────────────────────────────────

PGBL_DEFAULTS = {
    "irpf_faixas": [
        {"faixa_min": 0, "faixa_max": 26963.20, "aliquota": 0, "parcela_deduzir": 0},
        {"faixa_min": 26963.21, "faixa_max": 33919.80, "aliquota": 7.5, "parcela_deduzir": 2022.24},
        {"faixa_min": 33919.81, "faixa_max": 45012.60, "aliquota": 15, "parcela_deduzir": 4566.23},
        {"faixa_min": 45012.61, "faixa_max": 55976.16, "aliquota": 22.5, "parcela_deduzir": 7942.17},
        {"faixa_min": 55976.17, "faixa_max": None, "aliquota": 27.5, "parcela_deduzir": 10740.98},
    ],
    "inss_faixas": [
        {"faixa_min": 0, "faixa_max": 1518.00, "aliquota": 7.5},
        {"faixa_min": 1518.01, "faixa_max": 2793.88, "aliquota": 9},
        {"faixa_min": 2793.89, "faixa_max": 4190.83, "aliquota": 12},
        {"faixa_min": 4190.84, "faixa_max": 8157.41, "aliquota": 14},
    ],
    "teto_inss_anual": 97888.92,
    "deducao_por_dependente": 2275.08,
    "limite_educacao": 3561.50,
    "regra_saude": "Sem limite de dedução. Gastos com saúde são integralmente dedutíveis, desde que comprovados.",
    "pct_maximo_pgbl": 12,
    "obs_pgbl": "A dedução de PGBL só se aplica para quem faz a declaração completa do Imposto de Renda.",
}


# ─────────────────────────────────────────────────────────
# CÁLCULO ATUARIAL - BRASIL
# ─────────────────────────────────────────────────────────

BRASIL_DEFAULTS = {
    "selic_media_10a": 11.5,
    "inflacao_media_10a": 6.5,
    "idade_final_usufruto": 100,
    "idade_aposentadoria": 65,
    "aliquota_ir": 15,
}


# ─────────────────────────────────────────────────────────
# CÁLCULO ATUARIAL - OFFSHORE
# ─────────────────────────────────────────────────────────

OFFSHORE_DEFAULTS = {
    "taxa_risk_free_10a": 3.0,
    "inflacao_media_10a": 1.5,
    "idade_final_usufruto": 100,
    "idade_aposentadoria": 65,
    "aliquota_ir": 20,
    "cambio_usd_brl": 5.20,
}


# ─────────────────────────────────────────────────────────
# PREMISSAS SUCESSÓRIO
# ─────────────────────────────────────────────────────────

SUCESSORIO_DEFAULTS = {
    "honorarios_advocaticios": 5.0,
    "itcmd_por_estado": {
        "AC": {"nome": "Acre", "aliquota": 4},
        "AL": {"nome": "Alagoas", "aliquota": 4},
        "AP": {"nome": "Amapá", "aliquota": 4},
        "AM": {"nome": "Amazonas", "aliquota": 4},
        "BA": {"nome": "Bahia", "aliquota": 8},
        "CE": {"nome": "Ceará", "aliquota": 8},
        "DF": {"nome": "Distrito Federal", "aliquota": 6},
        "ES": {"nome": "Espírito Santo", "aliquota": 4},
        "GO": {"nome": "Goiás", "aliquota": 8},
        "MA": {"nome": "Maranhão", "aliquota": 7},
        "MT": {"nome": "Mato Grosso", "aliquota": 8},
        "MS": {"nome": "Mato Grosso do Sul", "aliquota": 6},
        "MG": {"nome": "Minas Gerais", "aliquota": 5},
        "PA": {"nome": "Pará", "aliquota": 4},
        "PB": {"nome": "Paraíba", "aliquota": 8},
        "PR": {"nome": "Paraná", "aliquota": 4},
        "PE": {"nome": "Pernambuco", "aliquota": 8},
        "PI": {"nome": "Piauí", "aliquota": 6},
        "RJ": {"nome": "Rio de Janeiro", "aliquota": 8},
        "RN": {"nome": "Rio Grande do Norte", "aliquota": 6},
        "RS": {"nome": "Rio Grande do Sul", "aliquota": 6},
        "RO": {"nome": "Rondônia", "aliquota": 4},
        "RR": {"nome": "Roraima", "aliquota": 4},
        "SC": {"nome": "Santa Catarina", "aliquota": 8},
        "SP": {"nome": "São Paulo", "aliquota": 4},
        "SE": {"nome": "Sergipe", "aliquota": 8},
        "TO": {"nome": "Tocantins", "aliquota": 8},
    },
}


# ─────────────────────────────────────────────────────────
# CENÁRIO MACROECONÔMICO
# ─────────────────────────────────────────────────────────

CENARIO_MACRO_DEFAULTS = {
    "brasil": [
        "A dívida pública atingiu 85% do PIB, com aumento de 12 p.p. nos últimos 4 anos, impulsionado pela expansão dos gastos primários.",
        "A política monetária mantém a taxa Selic em 15% a.a. para conter a inflação persistente, gerando juros reais elevados.",
        "Cenário político de incerteza fiscal e eleitoral para 2026, com possibilidade de ajuste fiscal em 2027.",
    ],
    "global": [
        "A inteligência artificial é o principal motor de investimento global, com Big Techs direcionando centenas de bilhões de dólares.",
        "A disponibilidade de energia tornou-se gargalo crítico para a expansão da infraestrutura de IA.",
        "O Federal Reserve iniciou cortes de juros, mesmo com economia aquecida e inflação acima da meta.",
    ],
}


# ─────────────────────────────────────────────────────────
# TEXTOS DO PLANEJAMENTO
# ─────────────────────────────────────────────────────────

TEXTOS_PLANEJAMENTO_DEFAULTS = {
    "contribuicao": (
        "Esta fase consiste na construção do seu patrimônio, onde os aportes "
        "e os juros compostos serão cruciais."
    ),
    "acumulacao": (
        "A partir daqui, você precisará entender o seu padrão de vida de acordo "
        "com patrimônio acumulado e o retorno real que ele pode te gerar."
    ),
    "sucessao": "",
    "pgbl": "",
}


# ─────────────────────────────────────────────────────────
# CLASSES DE ATIVOS
# ─────────────────────────────────────────────────────────

CLASSES_ATIVOS_DEFAULTS = [
    {"nome": "Caixa", "objetivo": "Liquidez imediata para resgates e oportunidades táticas, preservando capital com volatilidade próxima de zero."},
    {"nome": "Renda Fixa Pós", "objetivo": "Acompanhar a taxa de juros básica (CDI), oferecendo retorno previsível com baixa volatilidade."},
    {"nome": "Renda Fixa Pré", "objetivo": "Travar taxas nominais para capturar ganhos em cenários de queda de juros, com horizonte definido."},
    {"nome": "Renda Fixa CDI+", "objetivo": "Gerar retorno acima do CDI via crédito privado ou estruturas com spread, assumindo risco de crédito moderado."},
    {"nome": "Renda Fixa Inflação", "objetivo": "Proteger o poder de compra real do portfólio, travando juros reais acima da inflação."},
    {"nome": "RF Fundos Listados Isentos", "objetivo": "Capturar isenção de IR via FI-Infra e similares, otimizando retorno líquido em renda fixa de longo prazo."},
    {"nome": "Exterior", "objetivo": "Diversificar geograficamente e acessar moeda forte, reduzindo correlação com o risco Brasil."},
    {"nome": "Renda Variável", "objetivo": "Buscar valorização de capital no longo prazo via ações, aceitando maior volatilidade em troca de retorno potencial superior."},
    {"nome": "Multimercado", "objetivo": "Gerar alpha com flexibilidade de estratégias (juros, câmbio, ações), atuando como diversificador ativo na carteira."},
    {"nome": "Alternativos", "objetivo": "Acessar retornos descorrelacionados e prêmio de iliquidez via private equity, venture capital, precatórios e estruturas especiais."},
    {"nome": "Hedges", "objetivo": "Proteger o portfólio contra cenários de estresse (câmbio, inflação, cauda), funcionando como seguro estrutural da carteira."},
]
