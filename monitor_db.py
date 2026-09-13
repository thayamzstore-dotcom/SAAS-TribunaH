"""
monitor_db.py
Camada de banco de dados (SQLite) para o módulo de Notícias/Monitoramento.

Guarda TODA notícia de política coletada dos sites (pra aba "News"), e
quando a notícia menciona Renan Filho ou JHC, guarda também a classificação
de sentimento (pra aba "Monitoramento").

⚠️ Se você já tinha rodado uma versão anterior deste arquivo e criado o
monitoramento.db, apague esse arquivo antes de subir esta versão — o esquema
mudou e ele recria sozinho na próxima subida do app.
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
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS noticias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                trecho TEXT,
                corpo_completo TEXT,
                site TEXT NOT NULL,
                pessoa TEXT,                   -- 'renan_filho' | 'jhc' | NULL (sem menção)
                sentimento TEXT,               -- 'positiva' | 'negativa' | 'neutra' | NULL
                justificativa TEXT,
                data_publicacao TEXT,
                coletado_em TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pessoa ON noticias(pessoa)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_coletado_em ON noticias(coletado_em)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_site ON noticias(site)")
    logger.info("✅ Banco de notícias pronto em %s", DB_PATH)


def url_existe(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM noticias WHERE url = ?", (url,)).fetchone()
        return row is not None


def salvar_noticia(url, titulo, trecho, corpo_completo, site, pessoa=None,
                    sentimento=None, justificativa=None, data_publicacao=None):
    with get_conn() as conn:
        try:
            conn.execute("""
                INSERT INTO noticias
                    (url, titulo, trecho, corpo_completo, site, pessoa, sentimento, justificativa, data_publicacao, coletado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                url, titulo, trecho, corpo_completo, site, pessoa, sentimento, justificativa,
                data_publicacao, datetime.now().isoformat(timespec="seconds")
            ))
            return True
        except sqlite3.IntegrityError:
            return False  # já existe (url é UNIQUE)


def listar_noticias(pessoa=None, apenas_hoje=False, limit=200):
    """Usado pela aba Monitoramento: filtra por pessoa (renan_filho/jhc)."""
    query = "SELECT * FROM noticias WHERE pessoa IS NOT NULL"
    params = []

    if pessoa:
        query += " AND pessoa = ?"
        params.append(pessoa)

    if apenas_hoje:
        query += " AND substr(coletado_em, 1, 10) = ?"
        params.append(date.today().isoformat())

    query += " ORDER BY coletado_em DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def listar_todas_noticias(site=None, apenas_hoje=False, limit=300):
    """Usado pela aba News: feed geral, com ou sem filtro de site."""
    query = "SELECT id, url, titulo, trecho, site, pessoa, sentimento, coletado_em FROM noticias WHERE 1=1"
    params = []

    if site:
        query += " AND site = ?"
        params.append(site)

    if apenas_hoje:
        query += " AND substr(coletado_em, 1, 10) = ?"
        params.append(date.today().isoformat())

    query += " ORDER BY coletado_em DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def buscar_por_palavra(termo: str, limit=200):
    """Usado pela busca livre da aba Monitoramento: procura no título e no corpo completo."""
    termo_like = f"%{termo.lower()}%"
    query = """
        SELECT id, url, titulo, trecho, site, pessoa, sentimento, coletado_em
        FROM noticias
        WHERE lower(titulo) LIKE ? OR lower(corpo_completo) LIKE ?
        ORDER BY coletado_em DESC
        LIMIT ?
    """
    with get_conn() as conn:
        rows = conn.execute(query, (termo_like, termo_like, limit)).fetchall()
        return [dict(r) for r in rows]


def listar_sites_distintos():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT site FROM noticias ORDER BY site").fetchall()
        return [r["site"] for r in rows]


def resumo_do_dia():
    """Contagem por pessoa/sentimento, só considerando notícias com pessoa identificada."""
    hoje = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT pessoa, sentimento, COUNT(*) as total
            FROM noticias
            WHERE substr(coletado_em, 1, 10) = ? AND pessoa IS NOT NULL
            GROUP BY pessoa, sentimento
        """, (hoje,)).fetchall()
        return [dict(r) for r in rows]
