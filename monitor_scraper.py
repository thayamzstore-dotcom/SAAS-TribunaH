"""
monitor_scraper.py
Varre os sites configurados em sites_config.json.

Comportamento novo:
- Salva TODA notícia de política encontrada em cada site (pra aba "News").
- Se a notícia menciona Renan Filho ou JHC (no título OU no corpo), marca a
  pessoa e chama a IA pra classificar o sentimento (pra aba "Monitoramento").
- Guarda o corpo completo da matéria, pra permitir busca por palavra-chave
  livre depois.
"""

import json
import os
import time
import logging
import unicodedata
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import monitor_db as db
import monitor_ai as ai

logger = logging.getLogger(__name__)

SITES_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sites_config.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

KEYWORDS = {
    "renan_filho": ["renanzinho", "renan filho"],
    "jhc": ["jhc", "joao henrique caldas"],
}

PESSOA_NOME_EXIBICAO = {
    "renan_filho": "Renan Filho (Renanzinho)",
    "jhc": "JHC (João Henrique Caldas)",
}

TAMANHO_MIN_TITULO = 25       # ignora links curtos (menu, "leia mais", etc.)
TAMANHO_MAX_CORPO = 4000      # quanto do texto da matéria guardamos


def _normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _pessoa_mencionada(titulo: str, corpo: str):
    """Procura menção no título OU no corpo. Retorna a chave da pessoa ou None."""
    texto_norm = _normalizar((titulo or "") + " " + (corpo or ""))
    for pessoa, termos in KEYWORDS.items():
        for termo in termos:
            if termo in texto_norm:
                return pessoa
    return None


def _mesmo_dominio(link: str, url_base: str) -> bool:
    dominio_link = urlparse(link).netloc.replace("www.", "")
    dominio_base = urlparse(url_base).netloc.replace("www.", "")
    return dominio_link == dominio_base


def carregar_sites():
    if not os.path.exists(SITES_CONFIG_PATH):
        logger.warning("sites_config.json não encontrado.")
        return []
    with open(SITES_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _extrair_corpo_da_materia(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        paragrafos = [p.get_text(strip=True) for p in soup.find_all("p")]
        return " ".join(paragrafos)[:TAMANHO_MAX_CORPO]
    except Exception as e:
        logger.warning("Não deu pra abrir matéria %s: %s", url, e)
        return ""


def varrer_site(site: dict) -> int:
    nome_site = site.get("nome", site.get("url"))
    url_base = site["url"]
    novas = 0

    try:
        resp = requests.get(url_base, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning("⚠️ %s respondeu %s", nome_site, resp.status_code)
            return 0
    except Exception as e:
        logger.warning("⚠️ Falha ao acessar %s: %s", nome_site, e)
        return 0

    soup = BeautifulSoup(resp.text, "html.parser")
    links_vistos = set()

    for a in soup.find_all("a", href=True):
        texto_link = a.get_text(strip=True)
        if not texto_link or len(texto_link) < TAMANHO_MIN_TITULO:
            continue

        link_absoluto = urljoin(url_base, a["href"])
        parsed = urlparse(link_absoluto)
        if parsed.scheme not in ("http", "https"):
            continue
        if not _mesmo_dominio(link_absoluto, url_base):
            continue  # ignora link externo (ads, redes sociais, etc.)
        if link_absoluto in links_vistos:
            continue
        links_vistos.add(link_absoluto)

        if db.url_existe(link_absoluto):
            continue  # já coletamos essa matéria antes

        corpo = _extrair_corpo_da_materia(link_absoluto)
        pessoa = _pessoa_mencionada(texto_link, corpo)

        sentimento = None
        justificativa = None
        if pessoa:
            classificacao = ai.classificar_sentimento(PESSOA_NOME_EXIBICAO[pessoa], texto_link, corpo)
            sentimento = classificacao["sentimento"]
            justificativa = classificacao["justificativa"]

        salvou = db.salvar_noticia(
            url=link_absoluto,
            titulo=texto_link,
            trecho=corpo[:400] if corpo else "",
            corpo_completo=corpo,
            site=nome_site,
            pessoa=pessoa,
            sentimento=sentimento,
            justificativa=justificativa,
        )
        if salvou:
            novas += 1
            marcador = f"👤 {pessoa} ({sentimento})" if pessoa else "—"
            logger.info("📰 [%s] %s | %s", nome_site, texto_link[:60], marcador)

        time.sleep(0.4)

    return novas


def rodar_varredura_completa() -> dict:
    sites = carregar_sites()
    total_novas = 0
    resultado_por_site = {}

    for site in sites:
        try:
            novas = varrer_site(site)
            resultado_por_site[site.get("nome", site["url"])] = novas
            total_novas += novas
        except Exception as e:
            logger.error("Erro inesperado varrendo %s: %s", site, e)
            resultado_por_site[site.get("nome", site["url"])] = f"erro: {e}"

    logger.info("✅ Varredura completa: %s notícias novas no total", total_novas)
    return {"total_novas": total_novas, "por_site": resultado_por_site}
