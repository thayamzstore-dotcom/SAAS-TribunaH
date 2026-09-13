"""
monitor_db.py
Camada de banco de dados (SQLite) para o módulo de Monitoramento de Notícias.
Guarda cada notícia encontrada sobre as pessoas monitoradas, já com a
classificação de sentimento aplicada pela IA.
"""

import sqlite3
import os
import logging
from datetime import datetime, date
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitoramento.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Cria a tabela se não existir. Chamar uma vez na subida do app."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS noticias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                trecho TEXT,
                site TEXT NOT NULL,
                pessoa TEXT NOT NULL,          -- 'renan_filho' ou 'jhc'
                sentimento TEXT,               -- 'positiva' | 'negativa' | 'neutra'
                justificativa TEXT,
                data_publicacao TEXT,
                coletado_em TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pessoa ON noticias(pessoa)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_coletado_em ON noticias(coletado_em)")
    logger.info("✅ Banco de monitoramento pronto em %s", DB_PATH)


def url_existe(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM noticias WHERE url = ?", (url,)).fetchone()
        return row is not None


def salvar_noticia(url, titulo, trecho, site, pessoa, sentimento, justificativa, data_publicacao=None):
    with get_conn() as conn:
        try:
            conn.execute("""
                INSERT INTO noticias (url, titulo, trecho, site, pessoa, sentimento, justificativa, data_publicacao, coletado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                url, titulo, trecho, site, pessoa, sentimento, justificativa,
                data_publicacao, datetime.now().isoformat(timespec="seconds")
            ))
            return True
        except sqlite3.IntegrityError:
            # já existe (url é UNIQUE) — ignora silenciosamente
            return False


def listar_noticias(pessoa=None, apenas_hoje=False, limit=200):
    query = "SELECT * FROM noticias WHERE 1=1"
    params = []

    if pessoa:
        query += " AND pessoa = ?"
        params.append(pessoa)

    if apenas_hoje:
        hoje = date.today().isoformat()
        query += " AND substr(coletado_em, 1, 10) = ?"
        params.append(hoje)

    query += " ORDER BY coletado_em DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def resumo_do_dia():
    """Contagem rápida por pessoa/sentimento, pra cards de resumo na dashboard."""
    hoje = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT pessoa, sentimento, COUNT(*) as total
            FROM noticias
            WHERE substr(coletado_em, 1, 10) = ?
            GROUP BY pessoa, sentimento
        """, (hoje,)).fetchall()
        return [dict(r) for r in rows]
