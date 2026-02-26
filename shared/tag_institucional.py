"""
TAG Investimentos - Dados Institucionais
Informacoes da empresa, disclaimers, classificacao S1/S2 BACEN.
Referencia: GT Proposta_v2.pptx slides 1-5, 55-60, 62-64.
"""

TAG_INFO = {
    "nome": "TAG Investimentos",
    "razao_social": "TAG Investimentos Ltda.",
    "anos_historia": 20,
    "aum": "R$ 15 bilhoes",
    "aum_valor": 15_000_000_000,
    "familias": 100,
    "clientes_institucionais": 12,
    "profissionais": 60,
    "endereco": "Av. Brig. Faria Lima, 3.311 - 12 andar",
    "cep": "04538-133",
    "cidade": "Sao Paulo",
    "uf": "SP",
    "telefone": "(11) 3474-0000",
    "email": "ouvidoria@taginvest.com.br",
    "slogan": "A experiencia faz a diferenca",
    "descricao_curta": (
        "A TAG Investimentos e uma gestora independente com mais de 20 anos de historia, "
        "R$ 15 bilhoes sob gestao e uma equipe de 60 profissionais dedicados. "
        "Atendemos 100 familias e 12 clientes institucionais com excelencia "
        "na gestao de patrimonio."
    ),
    "descricao_jornada": (
        "Em duas decadas de operacao a TAG se consolidou no mercado por sua abordagem "
        "independente e estrategica. Hoje, com mais de 15 bilhoes sob gestao e uma equipe "
        "dedicada, nosso compromisso e com a excelencia e a construcao de uma jornada "
        "solida e consistente com nossos clientes."
    ),
}

# ── Solucoes 360 graus (slide 4) ──

SOLUCOES_360 = {
    "planejamento_patrimonial": {
        "titulo": "Planejamento Patrimonial",
        "itens": [
            "Formacao de herdeiros",
            "Assessoria tributaria e sucessoria",
            "Criacao de conselhos e holdings familiares",
            "Gerenciamento de conflitos sucessorios",
            "Planejamento financeiro familiar",
            "Estruturacao de fundos exclusivos",
            "Criacao de estruturas offshore",
            "Relatorio unificado de posicoes on e offshore",
        ],
    },
    "gestao_patrimonio_imobiliario": {
        "titulo": "Gestao de Patrimonio Imobiliario",
        "itens": [
            "Estruturacao de fundos exclusivos",
            "Owner Representation em projetos",
            "Desenvolvimento imobiliario sobre ativos de clientes",
            "Administracao de ativos imobiliarios",
        ],
    },
    "investimentos_alternativos": {
        "titulo": "Investimentos Alternativos",
        "itens": [
            "Originacao, analise e monitoramento",
            "Acesso a produtos exclusivos: venture capital, private equity, special sits",
            "Ativos judiciais, distressed assets e credito estruturado",
        ],
    },
    "produtos_estruturados": {
        "titulo": "Produtos Estruturados",
        "itens": [
            "Acesso ao mercado de capitais",
            "Estruturacao e securitizacao: CRIs, CRAs, Debentures, CCBs, FIDCs",
            "Financiamento via mercado de capitais para Project Finance",
        ],
    },
    "gestao_investimentos": {
        "titulo": "Gestao de Investimentos",
        "itens": [
            "Estrategias personalizadas para investimentos on e offshore",
            "Carteiras Administradas e Fundos Exclusivos",
            "Analise e gestao robusta em nivel institucional",
            "Gestao de Risco",
            "Modelo exclusivo de classificacao de gestores",
            "Processo ativo, sistemico e disciplinado de categorizacao de fundos",
            "Monitoramento quantitativo e qualitativo constante",
        ],
    },
}

# ── Classificacao S1/S2 BACEN (slide 56) ──

BACEN_S1 = [
    "Banco do Brasil", "Bradesco", "BTG Pactual",
    "Caixa Economica Federal", "Itau", "Santander",
]

BACEN_S2 = [
    "Banco Sicoob", "Banrisul", "Banco Cooperativo Sicredi",
    "Banco do Nordeste do Brasil", "BNDES", "Citibank",
    "Nu Pagamentos", "Safra", "Banco Votorantim", "Banco XP",
]

# ── Fee Table Padrao (slide 62) ──

FEE_TABLE_DEFAULT = [
    {"faixa": "Ate R$ 500.000.000,00", "taxa_adm": 0.25},
    {"faixa": "Acima de R$ 500.000.001,00", "taxa_adm": 0.20},
]

SERVICOS_DISPONIVEIS = [
    "Taxa de administracao",
    "Planejamento sucessorio",
    "Consolidacao patrimonial",
]

# ── Disclaimers Completos (slide 63) ──

DISCLAIMERS = [
    (
        "Este material foi preparado pela TAG Investimentos Ltda. e nao pode ser "
        "reproduzido ou distribuido sem consentimento previo e por escrito."
    ),
    (
        "Este material nao constitui uma oferta ou solicitacao de compra ou venda "
        "de qualquer instrumento financeiro, nem uma recomendacao de investimento."
    ),
    (
        "As opinioes, estimativas e projecoes aqui contidas podem ser alteradas "
        "sem previo aviso. As informacoes foram obtidas de fontes de mercado, "
        "nao havendo garantia quanto a sua exatidao e completude."
    ),
    (
        "Rentabilidade passada nao e garantia de rentabilidade futura. "
        "Os investimentos em fundos nao sao garantidos pelo administrador, "
        "pelo gestor, por qualquer mecanismo de seguro ou pelo Fundo Garantidor "
        "de Credito (FGC)."
    ),
    (
        "FIPs, FIIs e fundos fechados: as cotas somente serao resgatadas "
        "ao termino do prazo de duracao do fundo."
    ),
    (
        "Fundos de investimento podem utilizar instrumentos derivativos como "
        "parte de sua estrategia, o que pode resultar em perdas patrimoniais "
        "superiores ao capital aplicado."
    ),
    (
        "FICs (Fundos de Investimento em Cotas) podem investir em ativos "
        "financeiros no exterior."
    ),
    (
        "Os retornos apresentados sao brutos de impostos. A tributacao aplicavel "
        "pode variar conforme o tipo de investimento e o prazo de permanencia."
    ),
]

DISCLAIMER_RESUMIDO = (
    "Este documento e uma proposta de investimento e nao constitui oferta, "
    "solicitacao ou recomendacao de compra ou venda de ativos. "
    "Rentabilidade passada nao garante rentabilidade futura. "
    "Investimentos envolvem riscos e podem resultar em perdas patrimoniais."
)

# ── Politica de Investimentos - Principios Base (slides 55-60) ──

PRINCIPIOS_POLITICA = {
    "conservadorismo": (
        "Conservadorismo como premissa: investimentos restritos a renda fixa em Reais, "
        "vedacao a derivativos, exposicao internacional e estruturas complexas. "
        "Benchmark explicito: CDI."
    ),
    "diversificacao": (
        "Diversificacao obrigatoria: limites claros por emissor, classe de ativo "
        "e gestor. Reducao do risco de concentracao."
    ),
    "escalonamento": (
        "Escalonamento de vencimentos como ferramenta central de gestao. "
        "Reducao do risco de reinvestimento concentrado. "
        "Maior previsibilidade do fluxo de caixa."
    ),
    "gestao_ativa": (
        "Gestao ativa dentro de limites: liberdade para avaliar melhores taxas "
        "e momentos de mercado, com disciplina para decidir renovacoes. "
        "Definicao clara de fronteiras de risco e atuacao."
    ),
    "instituicoes_s1_s2": (
        "Foco em instituicoes S1 e S2 do Banco Central: "
        "S1 (Banco do Brasil, Bradesco, BTG Pactual, Caixa, Itau, Santander) e "
        "S2 (Sicoob, Banrisul, Sicredi, BNB, BNDES, Citi, Nu, Safra, Votorantim, XP)."
    ),
}

# Limites padrao da politica (personalizaveis por perfil)
LIMITES_POLITICA_DEFAULT = {
    "Conservador": {
        "max_por_emissor": 20,
        "max_por_gestor": 25,
        "max_renda_variavel": 0,
        "max_credito_privado": 15,
        "max_alternativos": 0,
        "min_liquidez_d5": 30,
        "rating_minimo": "AA",
    },
    "Moderado": {
        "max_por_emissor": 15,
        "max_por_gestor": 20,
        "max_renda_variavel": 20,
        "max_credito_privado": 20,
        "max_alternativos": 10,
        "min_liquidez_d5": 20,
        "rating_minimo": "A",
    },
    "Agressivo": {
        "max_por_emissor": 15,
        "max_por_gestor": 20,
        "max_renda_variavel": 40,
        "max_credito_privado": 25,
        "max_alternativos": 20,
        "min_liquidez_d5": 15,
        "rating_minimo": "A",
    },
}

# Drivers de analise patrimonial (slide 12)
DRIVERS_ANALISE_PATRIMONIAL = [
    "Processo de Inventario",
    "Continuidade das Atividades Empresariais",
    "Atividade Imobiliaria",
    "Comunicabilidade da Heranca",
    "Liquidez na Sucessao",
    "Reforma do Codigo Civil",
    "Estruturas Internacionais",
    "Residencia Fiscal",
]

# Instrumentos de planejamento (slide 13)
INSTRUMENTOS_PLANEJAMENTO = [
    "Doacao em Adiantamento de Legitima",
    "Reserva de Usufruto",
    "Testamento",
    "Gravames",
    "Seguro de Vida e Previdencia Complementar",
    "Alteracao do Regime de Casamento",
    "Acordos de Acionistas / Protocolo Familiar",
    "Trust / PICs / Holdings",
]
