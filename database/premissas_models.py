"""
CRUD operations for planning premissas (PGBL, actuarial, succession, macro).
"""
import json
from datetime import datetime

from database.db import get_connection


def get_premissa(tipo):
    """Get premissa data by type. Returns dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM premissas WHERE tipo = ?", (tipo,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    try:
        d["dados"] = json.loads(d["dados"])
    except (json.JSONDecodeError, TypeError):
        d["dados"] = {}
    return d


def upsert_premissa(tipo, dados):
    """Insert or update a premissa. Returns the row id."""
    conn = get_connection()
    cursor = conn.cursor()
    dados_json = json.dumps(dados, ensure_ascii=False)
    now = datetime.now().isoformat()

    existing = conn.execute(
        "SELECT id FROM premissas WHERE tipo = ?", (tipo,)
    ).fetchone()

    if existing:
        cursor.execute(
            "UPDATE premissas SET dados = ?, updated_at = ? WHERE tipo = ?",
            (dados_json, now, tipo),
        )
        row_id = existing["id"]
    else:
        cursor.execute(
            "INSERT INTO premissas (tipo, dados, updated_at) VALUES (?, ?, ?)",
            (tipo, dados_json, now),
        )
        row_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return row_id


def list_premissas():
    """List all premissas. Returns list of dicts."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM premissas ORDER BY tipo").fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        try:
            d["dados"] = json.loads(d["dados"])
        except (json.JSONDecodeError, TypeError):
            d["dados"] = {}
        results.append(d)
    return results


def get_premissa_or_default(tipo, defaults):
    """Get premissa data or return defaults if not set."""
    premissa = get_premissa(tipo)
    if premissa and premissa.get("dados"):
        return premissa["dados"]
    return defaults


def delete_premissa(tipo):
    """Delete a premissa by type."""
    conn = get_connection()
    conn.execute("DELETE FROM premissas WHERE tipo = ?", (tipo,))
    conn.commit()
    conn.close()
