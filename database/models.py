"""
CRUD operations for prospects, propostas, and interações.
"""
import json
import uuid
from datetime import datetime

from database.db import get_connection


# ─────────────────────────────────────────────────────────
# PROSPECTS
# ─────────────────────────────────────────────────────────

def create_prospect(data):
    """Create a new prospect. Returns the new ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO prospects
        (nome, cpf_cnpj, email, telefone, tipo_pessoa,
         perfil_investidor, patrimonio_total, patrimonio_investivel,
         horizonte_investimento, objetivos, retirada_mensal,
         eventos_futuros, restricoes, restricoes_texto, observacoes,
         status, responsavel,
         estrutura_familiar, estrutura_patrimonial, plano_sucessorio, fee_negociada)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("nome", ""),
            data.get("cpf_cnpj", ""),
            data.get("email", ""),
            data.get("telefone", ""),
            data.get("tipo_pessoa", "PF"),
            data.get("perfil_investidor", "Moderado"),
            data.get("patrimonio_total", 0),
            data.get("patrimonio_investivel", 0),
            data.get("horizonte_investimento", ""),
            json.dumps(data.get("objetivos", []), ensure_ascii=False),
            data.get("retirada_mensal", 0),
            json.dumps(data.get("eventos_futuros", []), ensure_ascii=False),
            json.dumps(data.get("restricoes", []), ensure_ascii=False),
            data.get("restricoes_texto", ""),
            data.get("observacoes", ""),
            data.get("status", "Lead"),
            data.get("responsavel", ""),
            json.dumps(data.get("estrutura_familiar", []), ensure_ascii=False),
            json.dumps(data.get("estrutura_patrimonial", {}), ensure_ascii=False),
            json.dumps(data.get("plano_sucessorio", {}), ensure_ascii=False),
            json.dumps(data.get("fee_negociada", {}), ensure_ascii=False),
        ),
    )
    prospect_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return prospect_id


def update_prospect(prospect_id, data):
    """Update an existing prospect."""
    conn = get_connection()
    fields = []
    values = []
    _prospect_json_fields = {
        "objetivos", "eventos_futuros", "restricoes",
        "estrutura_familiar", "estrutura_patrimonial", "plano_sucessorio", "fee_negociada",
    }
    for key, val in data.items():
        if key in ("id", "created_at"):
            continue
        if key in _prospect_json_fields and isinstance(val, (list, dict)):
            val = json.dumps(val, ensure_ascii=False)
        fields.append(f"{key} = ?")
        values.append(val)
    fields.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(prospect_id)

    conn.execute(
        f"UPDATE prospects SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


def get_prospect(prospect_id):
    """Get a single prospect by ID. Returns dict or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    _list_fields = ("objetivos", "eventos_futuros", "restricoes", "estrutura_familiar")
    _dict_fields = ("estrutura_patrimonial", "plano_sucessorio", "fee_negociada")
    for key in _list_fields:
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key] = []
    for key in _dict_fields:
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key] = {}
    return d


def list_prospects(status=None, responsavel=None, search=None):
    """List prospects with optional filters."""
    conn = get_connection()
    query = "SELECT * FROM prospects WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if responsavel:
        query += " AND responsavel = ?"
        params.append(responsavel)
    if search:
        query += " AND (nome LIKE ? OR cpf_cnpj LIKE ? OR email LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    query += " ORDER BY updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        for key in ("objetivos", "eventos_futuros", "restricoes", "estrutura_familiar"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    d[key] = []
        for key in ("estrutura_patrimonial", "plano_sucessorio", "fee_negociada"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    d[key] = {}
        results.append(d)
    return results


def delete_prospect(prospect_id):
    """Delete a prospect and all related data."""
    conn = get_connection()
    conn.execute("DELETE FROM prospects WHERE id = ?", (prospect_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────
# PROPOSTAS
# ─────────────────────────────────────────────────────────

def create_proposta(prospect_id, data=None):
    """Create a new proposta for a prospect. Returns the new ID."""
    if data is None:
        data = {}
    conn = get_connection()

    # Get next version number
    row = conn.execute(
        "SELECT COALESCE(MAX(versao), 0) + 1 as next_v FROM propostas WHERE prospect_id = ?",
        (prospect_id,),
    ).fetchone()
    next_version = row["next_v"]

    link_id = str(uuid.uuid4())[:8]

    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO propostas
        (prospect_id, versao, perfil_modelo, modelo_dados,
         restricoes_aplicadas, diagnostico_texto, diagnostico_dados,
         recomendacao_texto, carteira_proposta, plano_transicao,
         cenarios, status, link_compartilhamento,
         analytics_data, section_texts, backtest_data, bottom_up_classification,
         politica_investimentos, fundos_sugeridos, proposta_comercial)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            prospect_id,
            next_version,
            data.get("perfil_modelo", ""),
            json.dumps(data.get("modelo_dados", []), ensure_ascii=False),
            json.dumps(data.get("restricoes_aplicadas", []), ensure_ascii=False),
            data.get("diagnostico_texto", ""),
            json.dumps(data.get("diagnostico_dados", {}), ensure_ascii=False),
            data.get("recomendacao_texto", ""),
            json.dumps(data.get("carteira_proposta", []), ensure_ascii=False),
            json.dumps(data.get("plano_transicao", []), ensure_ascii=False),
            json.dumps(data.get("cenarios", {}), ensure_ascii=False),
            data.get("status", "Rascunho"),
            link_id,
            json.dumps(data.get("analytics_data", {}), ensure_ascii=False),
            json.dumps(data.get("section_texts", {}), ensure_ascii=False),
            json.dumps(data.get("backtest_data", {}), ensure_ascii=False),
            json.dumps(data.get("bottom_up_classification", []), ensure_ascii=False),
            json.dumps(data.get("politica_investimentos", {}), ensure_ascii=False),
            json.dumps(data.get("fundos_sugeridos", []), ensure_ascii=False),
            json.dumps(data.get("proposta_comercial", {}), ensure_ascii=False),
        ),
    )
    proposta_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return proposta_id


def update_proposta(proposta_id, data):
    """Update an existing proposta."""
    conn = get_connection()
    fields = []
    values = []
    json_fields = {
        "modelo_dados", "restricoes_aplicadas", "diagnostico_dados",
        "carteira_proposta", "plano_transicao", "cenarios",
        "analytics_data", "section_texts", "backtest_data",
        "bottom_up_classification",
        "politica_investimentos", "fundos_sugeridos", "proposta_comercial",
    }
    for key, val in data.items():
        if key in ("id", "created_at", "prospect_id"):
            continue
        if key in json_fields and isinstance(val, (list, dict)):
            val = json.dumps(val, ensure_ascii=False)
        fields.append(f"{key} = ?")
        values.append(val)
    fields.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(proposta_id)

    conn.execute(
        f"UPDATE propostas SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


def get_proposta(proposta_id):
    """Get a single proposta by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM propostas WHERE id = ?", (proposta_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    json_fields = {
        "modelo_dados", "restricoes_aplicadas", "diagnostico_dados",
        "carteira_proposta", "plano_transicao", "cenarios",
        "analytics_data", "section_texts", "backtest_data",
        "bottom_up_classification",
        "politica_investimentos", "fundos_sugeridos", "proposta_comercial",
    }
    for key in json_fields:
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                _dict_keys = ("diagnostico_dados", "cenarios", "analytics_data",
                              "section_texts", "backtest_data",
                              "politica_investimentos", "proposta_comercial")
                d[key] = {} if key in _dict_keys else []
    return d


def get_proposta_by_link(link_id):
    """Get a proposta by its shareable link ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM propostas WHERE link_compartilhamento = ?", (link_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    json_fields = {
        "modelo_dados", "restricoes_aplicadas", "diagnostico_dados",
        "carteira_proposta", "plano_transicao", "cenarios",
        "analytics_data", "section_texts", "backtest_data",
        "bottom_up_classification",
        "politica_investimentos", "fundos_sugeridos", "proposta_comercial",
    }
    for key in json_fields:
        if d.get(key):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                _dict_keys = ("diagnostico_dados", "cenarios", "analytics_data",
                              "section_texts", "backtest_data",
                              "politica_investimentos", "proposta_comercial")
                d[key] = {} if key in _dict_keys else []
    return d


def list_propostas(prospect_id=None):
    """List propostas, optionally filtered by prospect."""
    conn = get_connection()
    if prospect_id:
        rows = conn.execute(
            "SELECT * FROM propostas WHERE prospect_id = ? ORDER BY versao DESC",
            (prospect_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM propostas ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────
# INTERAÇÕES
# ─────────────────────────────────────────────────────────

def add_interacao(prospect_id, data):
    """Add a new interaction for a prospect."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO interacoes
        (prospect_id, tipo, descricao, responsavel, proxima_acao, data_proxima_acao)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (
            prospect_id,
            data.get("tipo", "Outro"),
            data.get("descricao", ""),
            data.get("responsavel", ""),
            data.get("proxima_acao", ""),
            data.get("data_proxima_acao"),
        ),
    )
    conn.commit()
    conn.close()


def list_interacoes(prospect_id):
    """List all interactions for a prospect."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM interacoes WHERE prospect_id = ? ORDER BY created_at DESC",
        (prospect_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────
# PIPELINE STATS
# ─────────────────────────────────────────────────────────

def get_pipeline_stats():
    """Get pipeline statistics for dashboard."""
    conn = get_connection()

    # Count by status
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt, SUM(patrimonio_investivel) as total_pl "
        "FROM prospects GROUP BY status"
    ).fetchall()

    stats = {
        "by_status": {r["status"]: {"count": r["cnt"], "total_pl": r["total_pl"] or 0} for r in rows},
        "total": 0,
        "total_pl": 0,
    }
    for r in rows:
        stats["total"] += r["cnt"]
        stats["total_pl"] += r["total_pl"] or 0

    # Count propostas by status
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM propostas GROUP BY status"
    ).fetchall()
    stats["propostas_by_status"] = {r["status"]: r["cnt"] for r in rows}

    # Recent interactions
    rows = conn.execute(
        "SELECT i.*, p.nome as prospect_nome FROM interacoes i "
        "JOIN prospects p ON i.prospect_id = p.id "
        "ORDER BY i.created_at DESC LIMIT 10"
    ).fetchall()
    stats["recent_interacoes"] = [dict(r) for r in rows]

    # Upcoming actions
    rows = conn.execute(
        "SELECT i.*, p.nome as prospect_nome FROM interacoes i "
        "JOIN prospects p ON i.prospect_id = p.id "
        "WHERE i.data_proxima_acao >= date('now') AND i.proxima_acao != '' "
        "ORDER BY i.data_proxima_acao ASC LIMIT 10"
    ).fetchall()
    stats["upcoming_actions"] = [dict(r) for r in rows]

    conn.close()
    return stats


def get_responsaveis():
    """Get list of unique responsáveis from prospects."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT responsavel FROM prospects WHERE responsavel != '' ORDER BY responsavel"
    ).fetchall()
    conn.close()
    return [r["responsavel"] for r in rows]
