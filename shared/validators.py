"""
TAG Investimentos - Validacao de Dados
Validadores para CPF, CNPJ, email, telefone, carteira de ativos.
Usado em formularios de cadastro e importacao.
"""
import re


# ══════════════════════════════════════════════════════════
# CPF / CNPJ
# ══════════════════════════════════════════════════════════

def _only_digits(value):
    return re.sub(r"\D", "", str(value or ""))


def validate_cpf(cpf):
    """Validate Brazilian CPF number.
    Returns (is_valid, formatted_cpf, error_message).
    """
    digits = _only_digits(cpf)
    if not digits:
        return True, "", ""  # Empty is OK (optional)
    if len(digits) != 11:
        return False, digits, "CPF deve ter 11 digitos"
    if digits == digits[0] * 11:
        return False, digits, "CPF invalido (todos os digitos iguais)"

    # First check digit
    total = sum(int(digits[i]) * (10 - i) for i in range(9))
    d1 = (total * 10 % 11) % 10
    if int(digits[9]) != d1:
        return False, digits, "CPF invalido (digito verificador)"

    # Second check digit
    total = sum(int(digits[i]) * (11 - i) for i in range(10))
    d2 = (total * 10 % 11) % 10
    if int(digits[10]) != d2:
        return False, digits, "CPF invalido (digito verificador)"

    formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return True, formatted, ""


def validate_cnpj(cnpj):
    """Validate Brazilian CNPJ number.
    Returns (is_valid, formatted_cnpj, error_message).
    """
    digits = _only_digits(cnpj)
    if not digits:
        return True, "", ""  # Empty is OK
    if len(digits) != 14:
        return False, digits, "CNPJ deve ter 14 digitos"
    if digits == digits[0] * 14:
        return False, digits, "CNPJ invalido (todos os digitos iguais)"

    # First check digit
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights[i] for i in range(12))
    d1 = 11 - (total % 11)
    d1 = 0 if d1 >= 10 else d1
    if int(digits[12]) != d1:
        return False, digits, "CNPJ invalido (digito verificador)"

    # Second check digit
    weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights[i] for i in range(13))
    d2 = 11 - (total % 11)
    d2 = 0 if d2 >= 10 else d2
    if int(digits[13]) != d2:
        return False, digits, "CNPJ invalido (digito verificador)"

    formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return True, formatted, ""


def validate_cpf_cnpj(value):
    """Auto-detect and validate CPF or CNPJ.
    Returns (is_valid, formatted, error_message, tipo).
    """
    digits = _only_digits(value)
    if not digits:
        return True, "", "", ""
    if len(digits) <= 11:
        ok, fmt, err = validate_cpf(digits)
        return ok, fmt, err, "CPF"
    else:
        ok, fmt, err = validate_cnpj(digits)
        return ok, fmt, err, "CNPJ"


# ══════════════════════════════════════════════════════════
# EMAIL
# ══════════════════════════════════════════════════════════

_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def validate_email(email):
    """Validate email format.
    Returns (is_valid, error_message).
    """
    if not email or not email.strip():
        return True, ""  # Empty OK
    email = email.strip().lower()
    if not _EMAIL_REGEX.match(email):
        return False, "Formato de email invalido"
    return True, ""


# ══════════════════════════════════════════════════════════
# TELEFONE
# ══════════════════════════════════════════════════════════

def validate_phone(phone):
    """Validate Brazilian phone number.
    Returns (is_valid, formatted, error_message).
    """
    if not phone or not phone.strip():
        return True, "", ""
    digits = _only_digits(phone)
    if len(digits) < 10 or len(digits) > 13:
        return False, digits, "Telefone deve ter entre 10 e 13 digitos"

    # Remove country code if present
    if digits.startswith("55") and len(digits) >= 12:
        digits = digits[2:]

    if len(digits) == 11:
        # Cell phone: (XX) 9XXXX-XXXX
        formatted = f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:
        # Landline: (XX) XXXX-XXXX
        formatted = f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    else:
        formatted = phone.strip()

    return True, formatted, ""


# ══════════════════════════════════════════════════════════
# PORTFOLIO VALIDATION
# ══════════════════════════════════════════════════════════

def validate_portfolio_allocation(carteira_proposta, tolerance=2.0):
    """Validate portfolio allocation sums to ~100%.
    Returns (is_valid, total_pct, warnings[]).
    """
    if not carteira_proposta:
        return True, 0, []

    warnings = []
    total = 0
    for item in carteira_proposta:
        pct = float(item.get("pct_alvo", item.get("% Alvo", 0)) or 0)
        total += pct

    is_valid = abs(total - 100) <= tolerance

    if total < 100 - tolerance:
        warnings.append(f"Alocacao total ({total:.1f}%) esta abaixo de 100%. Faltam {100 - total:.1f}pp.")
    elif total > 100 + tolerance:
        warnings.append(f"Alocacao total ({total:.1f}%) excede 100% em {total - 100:.1f}pp.")

    # Check for negative or zero allocations
    for item in carteira_proposta:
        name = item.get("ativo", item.get("Ativo", ""))
        pct = float(item.get("pct_alvo", item.get("% Alvo", 0)) or 0)
        if pct < 0:
            warnings.append(f"Alocacao negativa: {name} ({pct:.1f}%)")
            is_valid = False
        elif pct == 0:
            warnings.append(f"Alocacao zerada: {name}")

    # Check for duplicates
    names = [item.get("ativo", item.get("Ativo", "")).upper() for item in carteira_proposta if item.get("ativo") or item.get("Ativo")]
    seen = set()
    for name in names:
        if name in seen:
            warnings.append(f"Ativo duplicado: {name}")
        seen.add(name)

    return is_valid, total, warnings


def validate_prospect_completeness(prospect):
    """Check how complete the prospect registration is.
    Returns (score 0-100, missing_fields[], recommendations[]).
    """
    fields = {
        # (field_name, weight, label)
        "nome": (15, "Nome"),
        "cpf_cnpj": (5, "CPF/CNPJ"),
        "email": (5, "Email"),
        "telefone": (5, "Telefone"),
        "perfil_investidor": (15, "Perfil de investidor"),
        "patrimonio_investivel": (15, "Patrimonio investivel"),
        "horizonte_investimento": (10, "Horizonte de investimento"),
        "objetivos": (10, "Objetivos"),
        "responsavel": (5, "Responsavel"),
        "status": (5, "Status do pipeline"),
    }

    extra_fields = {
        "estrutura_familiar": (3, "Estrutura familiar"),
        "estrutura_patrimonial": (3, "Estrutura patrimonial"),
        "plano_sucessorio": (2, "Plano sucessorio"),
        "fee_negociada": (2, "Fee negociada"),
    }

    score = 0
    total_weight = sum(w for w, _ in fields.values()) + sum(w for w, _ in extra_fields.values())
    missing = []
    recommendations = []

    for field, (weight, label) in fields.items():
        value = prospect.get(field)
        if value and str(value).strip() and value not in (0, "0", [], {}, None):
            score += weight
        else:
            missing.append(label)

    # Check extra fields (JSON)
    for field, (weight, label) in extra_fields.items():
        value = prospect.get(field)
        if isinstance(value, list) and any(v.get("nome") for v in value if isinstance(v, dict)):
            score += weight
        elif isinstance(value, dict) and any(value.values()):
            score += weight
        else:
            missing.append(label)

    final_score = round(score / total_weight * 100)

    if final_score < 50:
        recommendations.append("Cadastro incompleto. Preencha pelo menos nome, perfil e patrimonio.")
    elif final_score < 75:
        recommendations.append("Cadastro basico. Adicione dados de familia e patrimonio para propostas mais completas.")
    elif final_score < 90:
        recommendations.append("Bom cadastro. Adicione estrutura patrimonial e fee para proposta v3 completa.")

    if "Perfil de investidor" in missing:
        recommendations.append("Defina o perfil de investidor para gerar propostas personalizadas.")
    if "Patrimonio investivel" in missing:
        recommendations.append("Informe o patrimonio investivel para calculos de R$ na proposta.")

    return final_score, missing, recommendations


def validate_proposal_readiness(prospect, proposta):
    """Check if a proposal is ready for delivery.
    Returns (score 0-100, issues[], ready_for_delivery).
    """
    issues = []
    score = 0
    max_score = 0

    # Prospect data
    checks = [
        (bool(prospect.get("nome")), 10, "Nome do prospect"),
        (bool(prospect.get("perfil_investidor")), 10, "Perfil de investidor"),
        (float(prospect.get("patrimonio_investivel", 0) or 0) > 0, 10, "Patrimonio investivel"),
    ]

    # Proposal content
    cart = proposta.get("carteira_proposta", [])
    if isinstance(cart, str):
        try:
            import json
            cart = json.loads(cart)
        except Exception:
            cart = []

    section_texts = proposta.get("section_texts", {}) or {}

    checks += [
        (bool(proposta.get("diagnostico_texto")), 10, "Diagnostico da carteira"),
        (len(cart) > 0, 15, "Carteira proposta"),
        (bool(section_texts.get("sumario_executivo")), 10, "Sumario executivo"),
        (bool(section_texts.get("premissas_filosofia")), 5, "Premissas e filosofia"),
        (bool(section_texts.get("objetivos_proposta")), 5, "Objetivos da proposta"),
        (bool(section_texts.get("monitoramento_governanca")), 5, "Monitoramento"),
    ]

    # V3 specific
    checks += [
        (bool(proposta.get("politica_investimentos")), 5, "Politica de investimentos"),
        (bool(proposta.get("fundos_sugeridos")), 5, "Fund cards"),
        (bool(proposta.get("proposta_comercial")), 5, "Proposta comercial"),
    ]

    # Allocation check
    if cart:
        valid_alloc, total_pct, alloc_warnings = validate_portfolio_allocation(cart)
        checks.append((valid_alloc, 5, f"Alocacao soma 100% (atual: {total_pct:.1f}%)"))
        for w in alloc_warnings:
            issues.append(f"Carteira: {w}")

    for condition, weight, label in checks:
        max_score += weight
        if condition:
            score += weight
        else:
            issues.append(f"Faltando: {label}")

    final_score = round(score / max_score * 100) if max_score > 0 else 0
    ready = final_score >= 70 and len(cart) > 0

    return final_score, issues, ready
