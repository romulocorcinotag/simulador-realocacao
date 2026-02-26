"""
TAG Investimentos - Catalogo de Fundos e Ativos Sugeridos
Referencia: GT Proposta_v2.pptx slides 42-53.
Usado para gerar fund cards nas propostas.
"""

# ── Fundos de Caixa (slides 42-43, 34) ──

FUND_CATALOG = {
    # ── FUNDOS CAIXA ──
    "TB PORTO SELIC SIMPLES FI RF": {
        "nome": "TB Porto Selic Simples FI RF",
        "tipo": "Fundo Caixa",
        "subtipo": "Soberano",
        "gestor": "TAG Investimentos",
        "estrategia": (
            "Fundo soberano de caixa da TAG, mais barato que fundos de plataforma. "
            "Alocacao exclusiva em titulos publicos federais pos-fixados e operacoes compromissadas. "
            "Risco muito baixo, fundo passivo exclusivo TAG (nao afetado por movimentos de resgate de mercado)."
        ),
        "resgate": "D+0",
        "retorno_alvo": "100% CDI",
        "retorno_12m": 14.45,
        "volatilidade": 0.07,
        "risco_principal": "Risco soberano (muito baixo)",
        "horizonte_minimo": "Imediato",
    },
    "TB PORTO FIM": {
        "nome": "TB Porto FIM",
        "tipo": "Fundo Caixa",
        "subtipo": "Enhanced",
        "gestor": "TAG Investimentos",
        "estrategia": (
            "Fundo enhanced de caixa da TAG. Reserva de caixa com liquidez quase imediata, "
            "com alocacao complementar em credito e inflacao em momentos oportunos. "
            "Volatilidade baixa, apostas pequenas. Proxy para o fundo que a TAG pretende criar "
            "(mais de 15 anos de experiencia em gestao)."
        ),
        "resgate": "D+1",
        "retorno_alvo": "105% CDI",
        "risco_principal": "Risco de credito (baixo, limitado a oportunidades taticas)",
        "horizonte_minimo": "3 meses",
    },
    "BOCOM BBM CASH FIC REF DI CP": {
        "nome": "BOCOM BBM Cash FIC Ref DI CP",
        "tipo": "Fundo Caixa",
        "subtipo": "Referenciado DI",
        "gestor": "BBM",
        "estrategia": (
            "Fundo referenciado DI com portfolio bem diversificado. "
            "Boa opcao para caixa de curto prazo com retorno proximo ao CDI."
        ),
        "resgate": "D+0",
        "retorno_alvo": "100% CDI",
        "retorno_12m": 14.50,
        "volatilidade": 0.04,
        "risco_principal": "Risco de credito bancario (baixo)",
        "horizonte_minimo": "Imediato",
    },
    "BNP PARIBAS MATCH RF DI CP": {
        "nome": "BNP Paribas Match RF DI CP",
        "tipo": "Fundo Caixa",
        "subtipo": "Credito Bancario",
        "gestor": "BNP Paribas",
        "estrategia": (
            "Fundo de renda fixa com portfolio bem diversificado, predominantemente em "
            "titulos bancarios. Historico de retorno de 103% CDI sem eventos de drawdown."
        ),
        "resgate": "D+30",
        "retorno_alvo": "103% CDI",
        "retorno_12m": 14.67,
        "volatilidade": 0.04,
        "risco_principal": "Risco de credito bancario (baixo a moderado)",
        "horizonte_minimo": "3 meses",
    },
    "SAFRA CAPITAL MARKET VIP RF DI CP": {
        "nome": "Safra Capital Market VIP RF DI CP",
        "tipo": "Fundo Caixa",
        "subtipo": "Credito Misto",
        "gestor": "Safra",
        "estrategia": (
            "Fundo de credito com portfolio diversificado entre titulos bancarios e "
            "corporativos (~20% corporativo). Retorno historico de 104% CDI."
        ),
        "resgate": "D+0",
        "retorno_alvo": "104% CDI",
        "retorno_12m": 14.60,
        "volatilidade": 0.09,
        "risco_principal": "Risco de credito diversificado (baixo a moderado)",
        "horizonte_minimo": "1 mes",
    },
    "MAPFRE CONFIANZA FIF RF REF DI CP": {
        "nome": "Mapfre Confianza FIF RF Ref DI Cred Priv",
        "tipo": "Fundo Caixa",
        "subtipo": "Credito Bancario",
        "gestor": "Mapfre",
        "estrategia": (
            "Fundo de renda fixa com portfolio bem diversificado, predominantemente em "
            "titulos bancarios. Retorno historico superior de 110% CDI."
        ),
        "resgate": "D+0",
        "retorno_alvo": "110% CDI",
        "retorno_12m": 15.29,
        "volatilidade": 0.09,
        "risco_principal": "Risco de credito bancario (baixo a moderado)",
        "horizonte_minimo": "1 mes",
    },

    # ── FUNDOS DE CREDITO ──
    "VALORA TITAN TI FIC FIM CP": {
        "nome": "Valora Titan TI FIC FIM CP",
        "tipo": "Fundo de Credito",
        "subtipo": "FIDC",
        "gestor": "Valora",
        "estrategia": (
            "Fundo de FIDCs (Fundo de Investimento em Direitos Creditorios) bem diversificado, "
            "sem concentracao. Track record de 14 anos com retorno desde o inicio de 140% CDI. "
            "Passivo exclusivo TAG."
        ),
        "resgate": "D+92",
        "retorno_alvo": "CDI + 2% a.a.",
        "retorno_12m": 15.96,
        "volatilidade": 0.22,
        "risco_principal": "Risco de credito estruturado (moderado)",
        "horizonte_minimo": "6 meses",
    },

    # ── FUNDOS DE ACOES / MULTIMERCADO (slides 48-50) ──
    "VIT ACOES": {
        "nome": "VIT Acoes",
        "tipo": "Fundo de Acoes",
        "subtipo": "FoF Long Only",
        "gestor": "TAG Investimentos",
        "estrategia": (
            "FoF Long Only: selecao de gestores fundamentalistas (long-side only). "
            "Busca crescimento de valor em empresas de alta qualidade ao longo do tempo. "
            "Diversificacao de estilos e setores, abordagem de longo prazo, "
            "foco em retorno real e preservacao de capital."
        ),
        "resgate": "D+30",
        "retorno_alvo": "IBOV + alpha",
        "risco_principal": "Risco de mercado de acoes (alto)",
        "horizonte_minimo": "3 anos",
    },
    "VIT LONG BIASED": {
        "nome": "VIT Long Biased",
        "tipo": "Fundo de Acoes",
        "subtipo": "FoF Long Biased",
        "gestor": "TAG Investimentos",
        "estrategia": (
            "FoF Long Biased: gestores com flexibilidade para ajustar exposicao direcional "
            "e usar instrumentos de protecao. Geracao de alpha com gestao ativa de risco "
            "ao longo de ciclos de mercado. Captura assimetrias positivas em cenarios "
            "construtivos e preserva capital em momentos de volatilidade."
        ),
        "resgate": "D+30",
        "retorno_alvo": "CDI + 5% a.a.",
        "risco_principal": "Risco direcional de mercado (moderado a alto)",
        "horizonte_minimo": "2 anos",
    },
    "VIT MULTIMERCADO": {
        "nome": "VIT Multimercado",
        "tipo": "Multimercado",
        "subtipo": "FoF Multi-Strategy",
        "gestor": "TAG Investimentos",
        "estrategia": (
            "FoF Multi-strategy: diferentes estilos de gestao, objetivo de ganhar "
            "'dinheiro diferente'. Alocacao equilibrada entre macro, valor relativo e long biased. "
            "Casas com track record forte, gestao especializada. "
            "Navega diferentes cenarios, nao apenas 'kit Brasil' positivo."
        ),
        "resgate": "D+30",
        "retorno_alvo": "CDI + 3% a.a.",
        "risco_principal": "Risco multimercado diversificado (moderado)",
        "horizonte_minimo": "1 ano",
    },

    # ── CRAs (slide 51) ──
    "CRA FUTURA AGRONEGOCIOS": {
        "nome": "CRA Futura Agronegocios Ltda",
        "tipo": "CRA",
        "subtipo": "Credito Agro",
        "emissor": "Futura Agronegocios Ltda",
        "estrategia": (
            "Fundada em 2003 em Araguari-MG, 21 lojas e 6 centros de distribuicao. "
            "Atua em sementes, fertilizantes, defensivos e especialidades. "
            "Receita: R$ 1,07 bilhao, EBITDA: R$ 70M, Lucro Liquido: R$ 58M. "
            "Auditada pela KPMG. Maximo 5% por cliente, top 5 ate 20%, media 3%."
        ),
        "taxa": "CDI + 4,95%",
        "vencimento": "06/2027",
        "subordinacao": "40%",
        "risco_principal": "Risco de credito corporativo agro (moderado)",
        "horizonte_minimo": "Ate o vencimento",
    },
    "CRA NIMOFAST": {
        "nome": "CRA Nimofast Brasil S.A.",
        "tipo": "CRA",
        "subtipo": "Credito Agro",
        "emissor": "Nimofast Brasil S.A.",
        "estrategia": (
            "Importadora de combustiveis fundada em 2014, Curitiba, 13 estados e 7 filiais. "
            "Garantia: 115% do saldo do CRA em combustivel armazenado na Ultracargo (Santos) "
            "mais caixa na securitizadora. Control Union realiza verificacao fisica periodica."
        ),
        "taxa": "CDI + 4,95%",
        "vencimento": "08/2027",
        "risco_principal": "Risco de credito com garantia real (moderado)",
        "horizonte_minimo": "Ate o vencimento",
    },
    "CRA CRIALT": {
        "nome": "CRA Crialt Comercio e Representacoes",
        "tipo": "CRA",
        "subtipo": "Credito Agro",
        "emissor": "Crialt Comercio e Representacoes",
        "estrategia": (
            "Fundada em 1995, produtos agricolas, foco em Sao Paulo. "
            "Receita: R$ 132M, EBITDA: R$ 9M. TAG teve exposicao anterior (divida pre-paga). "
            "Garantia: AF de estoque + CF de min 110% + aval dos socios."
        ),
        "taxa": "CDI + 4,45%",
        "vencimento": "29/12/2028",
        "subordinacao": "40%",
        "risco_principal": "Risco de credito corporativo agro (moderado)",
        "horizonte_minimo": "Ate o vencimento",
    },

    # ── FIIs (slides 52-53) ──
    "KNIP11": {
        "nome": "KNIP11 - Kinea Indices de Precos FII",
        "tipo": "FII",
        "subtipo": "Papeis",
        "gestor": "Kinea",
        "estrategia": (
            "Fundo imobiliario de papeis com 118 ativos no portfolio. "
            "Concentracao maxima de 5% em um unico shopping. "
            "P/VP proximo de 1,00, dividendo ~1% a.m. "
            "Liquidez acima de R$ 8M/mes."
        ),
        "retorno_alvo": "IPCA + 7% a.a.",
        "risco_principal": "Risco de credito imobiliario e taxa de juros",
        "horizonte_minimo": "2 anos",
        "isento_ir": True,
    },
    "KNRI11": {
        "nome": "KNRI11 - Kinea Renda Imobiliaria FII",
        "tipo": "FII",
        "subtipo": "Hibrido (Lajes + Logistica)",
        "gestor": "Kinea",
        "estrategia": (
            "Fundo hibrido: escritorios e galpoes logisticos. "
            "Vacancia baixa, entrega do projeto Biosquare prevista para 2026. "
            "Boa distribuicao de receita entre setores/regioes. "
            "Contratos atipicos aumentam previsibilidade."
        ),
        "retorno_alvo": "CDI + 2% a.a. (isento)",
        "risco_principal": "Risco imobiliario e vacancia",
        "horizonte_minimo": "2 anos",
        "isento_ir": True,
    },
    "KDIF11": {
        "nome": "KDIF11 - Kinea Infra FII",
        "tipo": "FII",
        "subtipo": "Infraestrutura",
        "gestor": "Kinea",
        "estrategia": (
            "Fundo de infraestrutura com debentures incentivadas de alta qualidade. "
            "Dividendos: ~0,9-1,2% ao mes. "
            "Negocia proximo ao valor patrimonial, duration moderada. "
            "Politica conservadora de risco, componente estavel para renda isenta."
        ),
        "retorno_alvo": "IPCA + 6% a.a. (isento)",
        "risco_principal": "Risco de credito de infra e taxa de juros",
        "horizonte_minimo": "2 anos",
        "isento_ir": True,
    },
    "RURA11": {
        "nome": "RURA11 - Itau Asset Rural FIAGRO FII",
        "tipo": "FIAGRO",
        "subtipo": "Credito Agro",
        "gestor": "Itau Asset",
        "estrategia": (
            "FIAGRO de credito agricola com renda recorrente. "
            "Operacoes estruturadas diversificadas (graos, proteina animal, insumos, logistica). "
            "Multiplos indexadores e vencimentos, negocia proximo ao valor patrimonial."
        ),
        "retorno_alvo": "CDI + 3% a.a. (isento)",
        "risco_principal": "Risco de credito agro diversificado",
        "horizonte_minimo": "1 ano",
        "isento_ir": True,
    },
    "AZIN11": {
        "nome": "AZIN11 - AZ Quest Infra Yield FII",
        "tipo": "FII",
        "subtipo": "Infraestrutura Energia",
        "gestor": "AZ Quest",
        "estrategia": (
            "FIP-IE de infraestrutura, ativos de energia com renda isenta de IR. "
            "Portfolio concentrado em geracao e transmissao. "
            "Indicado para investidores de longo prazo buscando diversificacao e renda isenta."
        ),
        "retorno_alvo": "IPCA + 8% a.a. (isento)",
        "risco_principal": "Risco de projeto de infraestrutura (concentrado)",
        "horizonte_minimo": "3 anos",
        "isento_ir": True,
    },
    "XPML11": {
        "nome": "XPML11 - XP Malls FII",
        "tipo": "FII",
        "subtipo": "Shoppings",
        "gestor": "XP Asset",
        "estrategia": (
            "Fundo de grandes shoppings com 28 centros comerciais. "
            "Gestao ativa com estrategia de reciclagem de ativos. "
            "Concentracao em SP/Sudeste. Vacancia baixa, inadimplencia controlada. "
            "Top 5 ativos representam menos de 30% do portfolio."
        ),
        "retorno_alvo": "CDI + 2% a.a. (isento)",
        "risco_principal": "Risco de mercado imobiliario e varejo",
        "horizonte_minimo": "2 anos",
        "isento_ir": True,
    },
}


def match_fund_catalog(asset_name):
    """Try to match an asset name to a fund catalog entry.

    Returns the catalog entry dict or None.
    """
    if not asset_name:
        return None

    name_upper = str(asset_name).strip().upper()

    # Exact key match
    if name_upper in FUND_CATALOG:
        return FUND_CATALOG[name_upper]

    # Try matching by catalog key or name
    for key, info in FUND_CATALOG.items():
        key_upper = key.upper()
        nome_upper = info["nome"].upper()

        # Check if asset name contains key or vice-versa
        if key_upper in name_upper or name_upper in key_upper:
            return info
        if nome_upper in name_upper or name_upper in nome_upper:
            return info

        # Check partial matches (first 15 chars)
        if len(name_upper) > 5 and len(key_upper) > 5:
            if name_upper[:15] in key_upper or key_upper[:15] in name_upper:
                return info

    return None


def get_funds_by_type(tipo):
    """Get all funds of a given type (e.g., 'FII', 'CRA', 'Fundo Caixa')."""
    return {k: v for k, v in FUND_CATALOG.items() if v.get("tipo") == tipo}
