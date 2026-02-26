"""
PGBL Tax Deduction Calculator.
Uses premissas from database (IRPF, INSS, deduction limits, PGBL rules)
to compute optimal PGBL contribution for a given client.
"""
from shared.planning_defaults import PGBL_DEFAULTS
from database.premissas_models import get_premissa_or_default


def load_pgbl_premissas():
    """Load PGBL premissas from database or defaults."""
    return get_premissa_or_default("pgbl", PGBL_DEFAULTS)


def calcular_inss_anual(renda_mensal, premissas=None):
    """
    Calculate annual INSS contribution using progressive table.
    Returns (total_anual, detalhamento_faixas).
    """
    if premissas is None:
        premissas = load_pgbl_premissas()

    faixas = premissas.get("inss_faixas", PGBL_DEFAULTS["inss_faixas"])
    teto_anual = premissas.get("teto_inss_anual", PGBL_DEFAULTS["teto_inss_anual"])

    inss_mensal = 0
    detalhamento = []

    for faixa in faixas:
        f_min = faixa["faixa_min"]
        f_max = faixa["faixa_max"]
        aliq = faixa["aliquota"] / 100

        if renda_mensal <= f_min:
            break

        base = min(renda_mensal, f_max) - f_min
        if base < 0:
            base = 0
        contribuicao = base * aliq
        inss_mensal += contribuicao
        detalhamento.append({
            "faixa": f"R$ {f_min:,.2f} - R$ {f_max:,.2f}",
            "aliquota": faixa["aliquota"],
            "base": base,
            "contribuicao": contribuicao,
        })

    inss_anual = inss_mensal * 12
    # Apply ceiling
    if inss_anual > teto_anual:
        inss_anual = teto_anual

    return inss_anual, detalhamento


def calcular_irpf(renda_anual_tributavel, premissas=None):
    """
    Calculate IRPF using progressive table.
    Returns (imposto_devido, aliquota_efetiva, detalhamento_faixas).
    """
    if premissas is None:
        premissas = load_pgbl_premissas()

    faixas = premissas.get("irpf_faixas", PGBL_DEFAULTS["irpf_faixas"])

    if renda_anual_tributavel <= 0:
        return 0, 0, []

    # Find the applicable bracket
    imposto = 0
    aliquota_marginal = 0
    parcela_deduzir = 0

    for faixa in faixas:
        f_min = faixa["faixa_min"]
        f_max = faixa["faixa_max"]
        aliq = faixa["aliquota"]
        parcela = faixa["parcela_deduzir"]

        if f_max is None or f_max == 0:
            # Last bracket (no upper limit)
            if renda_anual_tributavel >= f_min:
                imposto = renda_anual_tributavel * (aliq / 100) - parcela
                aliquota_marginal = aliq
                parcela_deduzir = parcela
                break
        elif renda_anual_tributavel <= f_max:
            imposto = renda_anual_tributavel * (aliq / 100) - parcela
            aliquota_marginal = aliq
            parcela_deduzir = parcela
            break

    if imposto < 0:
        imposto = 0

    aliquota_efetiva = (imposto / renda_anual_tributavel * 100) if renda_anual_tributavel > 0 else 0

    return imposto, aliquota_efetiva, aliquota_marginal


def calcular_deducoes(num_dependentes, gastos_educacao, gastos_saude, premissas=None):
    """
    Calculate total allowed deductions (excluding PGBL and INSS).
    Returns (total_deducoes, detalhamento).
    """
    if premissas is None:
        premissas = load_pgbl_premissas()

    ded_dependente = premissas.get("deducao_por_dependente", PGBL_DEFAULTS["deducao_por_dependente"])
    lim_educacao = premissas.get("limite_educacao", PGBL_DEFAULTS["limite_educacao"])

    ded_dep_total = num_dependentes * ded_dependente
    ded_educ = min(gastos_educacao, lim_educacao * num_dependentes) if num_dependentes > 0 else min(gastos_educacao, lim_educacao)
    ded_saude = gastos_saude  # No limit

    total = ded_dep_total + ded_educ + ded_saude

    detalhamento = {
        "dependentes": {"qtd": num_dependentes, "valor_unitario": ded_dependente, "total": ded_dep_total},
        "educacao": {"gasto": gastos_educacao, "limite": lim_educacao, "deduzido": ded_educ},
        "saude": {"gasto": gastos_saude, "deduzido": ded_saude},
        "total": total,
    }

    return total, detalhamento


def simular_pgbl(
    renda_bruta_anual,
    num_dependentes=0,
    gastos_educacao=0,
    gastos_saude=0,
    aporte_pgbl=None,
    premissas=None,
):
    """
    Full PGBL simulation:
    1. Calculate INSS
    2. Calculate other deductions
    3. Determine optimal PGBL contribution (12% limit)
    4. Compare IR with vs without PGBL
    5. Return comprehensive results

    Parameters:
        renda_bruta_anual: Annual gross income (R$)
        num_dependentes: Number of dependents
        gastos_educacao: Annual education expenses (R$)
        gastos_saude: Annual health expenses (R$)
        aporte_pgbl: Custom PGBL amount (None = use optimal 12%)
        premissas: PGBL premissas dict (None = load from DB)

    Returns dict with all calculations.
    """
    if premissas is None:
        premissas = load_pgbl_premissas()

    pct_max_pgbl = premissas.get("pct_maximo_pgbl", PGBL_DEFAULTS["pct_maximo_pgbl"])

    # 1. INSS
    renda_mensal = renda_bruta_anual / 12
    inss_anual, inss_det = calcular_inss_anual(renda_mensal, premissas)

    # 2. Other deductions
    ded_total, ded_det = calcular_deducoes(
        num_dependentes, gastos_educacao, gastos_saude, premissas
    )

    # 3. Max PGBL contribution (12% of gross taxable income)
    pgbl_limite = renda_bruta_anual * (pct_max_pgbl / 100)

    if aporte_pgbl is None:
        aporte_pgbl_efetivo = pgbl_limite
    else:
        aporte_pgbl_efetivo = min(aporte_pgbl, pgbl_limite)

    # 4. Taxable income WITHOUT PGBL
    base_sem_pgbl = renda_bruta_anual - inss_anual - ded_total
    if base_sem_pgbl < 0:
        base_sem_pgbl = 0

    ir_sem_pgbl, aliq_efetiva_sem, aliq_marginal_sem = calcular_irpf(base_sem_pgbl, premissas)

    # 5. Taxable income WITH PGBL
    base_com_pgbl = renda_bruta_anual - inss_anual - ded_total - aporte_pgbl_efetivo
    if base_com_pgbl < 0:
        base_com_pgbl = 0

    ir_com_pgbl, aliq_efetiva_com, aliq_marginal_com = calcular_irpf(base_com_pgbl, premissas)

    # 6. Tax savings
    economia_ir = ir_sem_pgbl - ir_com_pgbl
    economia_pct = (economia_ir / ir_sem_pgbl * 100) if ir_sem_pgbl > 0 else 0

    return {
        "renda_bruta_anual": renda_bruta_anual,
        "renda_mensal": renda_mensal,

        # INSS
        "inss_anual": inss_anual,
        "inss_mensal": inss_anual / 12,
        "inss_detalhamento": inss_det,

        # Deduções
        "deducoes_total": ded_total,
        "deducoes_detalhamento": ded_det,

        # PGBL
        "pgbl_limite": pgbl_limite,
        "pgbl_aporte": aporte_pgbl_efetivo,
        "pgbl_aporte_mensal": aporte_pgbl_efetivo / 12,
        "pct_max_pgbl": pct_max_pgbl,

        # SEM PGBL
        "base_tributavel_sem_pgbl": base_sem_pgbl,
        "ir_sem_pgbl": ir_sem_pgbl,
        "aliquota_efetiva_sem_pgbl": aliq_efetiva_sem,
        "aliquota_marginal_sem_pgbl": aliq_marginal_sem,

        # COM PGBL
        "base_tributavel_com_pgbl": base_com_pgbl,
        "ir_com_pgbl": ir_com_pgbl,
        "aliquota_efetiva_com_pgbl": aliq_efetiva_com,
        "aliquota_marginal_com_pgbl": aliq_marginal_com,

        # ECONOMIA
        "economia_ir": economia_ir,
        "economia_ir_mensal": economia_ir / 12,
        "economia_pct": economia_pct,
    }
