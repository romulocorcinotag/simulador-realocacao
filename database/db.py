"""
SQLite database initialization and connection management.
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "propostas.db")


def get_connection():
    """Get a SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf_cnpj TEXT,
            email TEXT,
            telefone TEXT,
            tipo_pessoa TEXT CHECK(tipo_pessoa IN ('PF', 'PJ')),

            perfil_investidor TEXT,
            patrimonio_total REAL DEFAULT 0,
            patrimonio_investivel REAL DEFAULT 0,
            horizonte_investimento TEXT,

            objetivos TEXT DEFAULT '[]',
            retirada_mensal REAL DEFAULT 0,
            eventos_futuros TEXT DEFAULT '[]',
            restricoes TEXT DEFAULT '[]',
            restricoes_texto TEXT DEFAULT '',
            observacoes TEXT DEFAULT '',

            status TEXT DEFAULT 'Lead' CHECK(status IN
                ('Lead', 'Qualificado', 'Proposta Enviada', 'Negociação', 'Cliente', 'Perdido')),
            responsavel TEXT DEFAULT '',

            carteira_arquivo TEXT,
            carteira_dados TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS propostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER REFERENCES prospects(id) ON DELETE CASCADE,
            versao INTEGER DEFAULT 1,

            perfil_modelo TEXT,
            modelo_dados TEXT,
            restricoes_aplicadas TEXT DEFAULT '[]',

            diagnostico_texto TEXT DEFAULT '',
            diagnostico_dados TEXT DEFAULT '{}',
            recomendacao_texto TEXT DEFAULT '',
            carteira_proposta TEXT DEFAULT '[]',
            plano_transicao TEXT DEFAULT '[]',
            cenarios TEXT DEFAULT '{}',

            status TEXT DEFAULT 'Rascunho' CHECK(status IN
                ('Rascunho', 'Revisão', 'Aprovada', 'Enviada', 'Aceita', 'Rejeitada')),

            pdf_path TEXT,
            html_path TEXT,
            link_compartilhamento TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS interacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER REFERENCES prospects(id) ON DELETE CASCADE,
            tipo TEXT CHECK(tipo IN ('Reunião', 'Ligação', 'Email', 'WhatsApp', 'Proposta', 'Outro')),
            descricao TEXT,
            responsavel TEXT,
            proxima_acao TEXT,
            data_proxima_acao DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);
        CREATE INDEX IF NOT EXISTS idx_propostas_prospect ON propostas(prospect_id);
        CREATE INDEX IF NOT EXISTS idx_interacoes_prospect ON interacoes(prospect_id);
    """)

    # Migration: add new columns for 15-section proposal
    _new_columns_propostas = [
        ("analytics_data", "TEXT DEFAULT '{}'"),
        ("section_texts", "TEXT DEFAULT '{}'"),
        ("backtest_data", "TEXT DEFAULT '{}'"),
        ("bottom_up_classification", "TEXT DEFAULT '[]'"),
        # Sprint 1: columns for full PPTX-style proposals
        ("politica_investimentos", "TEXT DEFAULT '{}'"),
        ("fundos_sugeridos", "TEXT DEFAULT '[]'"),
        ("proposta_comercial", "TEXT DEFAULT '{}'"),
    ]
    for col_name, col_def in _new_columns_propostas:
        try:
            cursor.execute(f"ALTER TABLE propostas ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass  # Column already exists

    # Migration: add new columns for prospect (family, patrimony, fees)
    _new_columns_prospects = [
        ("estrutura_familiar", "TEXT DEFAULT '[]'"),
        ("estrutura_patrimonial", "TEXT DEFAULT '{}'"),
        ("plano_sucessorio", "TEXT DEFAULT '{}'"),
        ("fee_negociada", "TEXT DEFAULT '{}'"),
    ]
    for col_name, col_def in _new_columns_prospects:
        try:
            cursor.execute(f"ALTER TABLE prospects ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass  # Column already exists

    # ── Premissas table for planning/financial settings ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS premissas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL UNIQUE,
            dados TEXT NOT NULL DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
