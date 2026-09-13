"""
monitor_scraper.py
Varredura genérica de sites de notícias: entra na URL configurada, pega todos
os links da página, e filtra os que mencionam as pessoas monitoradas pelo
texto do link (título da matéria). Depois abre cada matéria nova pra pegar
um trecho do conteúdo, manda pra classificação de sentimento e salva no banco.

Não depende da estrutura HTML de cada site — funciona em qualquer portal,
só que por isso é "raso" (lê o que está no <a> e no <p> da página).
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

# Palavras-chave por pessoa (tudo em minúsculo e sem acento — normalizamos antes de comparar)
KEYWORDS = {
    "renan_filho": ["renanzinho", "renan filho"],
    "jhc": ["jhc", "joao henrique caldas"],
}

PESSOA_NOME_EXIBICAO = {
    "renan_filho": "Renan Filho (Renanzinho)",
    "jhc": "JHC (João Henrique Caldas)",
}


def _normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _pessoa_mencionada(texto: str):
    """Retorna a chave da pessoa (ex: 'jhc') se o texto menciona ela, senão None."""
    texto_norm = _normalizar(texto)
    for pessoa, termos in KEYWORDS.items():
        for termo in termos:
            if termo in texto_norm:
                return pessoa
    return None


def carregar_sites():
    if not os.path.exists(SITES_CONFIG_PATH):
        logger.warning("sites_config.json não encontrado.")
        return []
    with open(SITES_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _extrair_trecho_da_materia(url: str) -> str:
    """Abre a matéria e junta o texto dos parágrafos, como um resumo cru."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        paragrafos = [p.get_text(strip=True) for p in soup.find_all("p")]
        texto = " ".join(paragrafos)
        return texto[:2000]
    except Exception as e:
        logger.warning("Não deu pra abrir matéria %s: %s", url, e)
        return ""


def varrer_site(site: dict) -> int:
    """Varre um site e retorna quantas notícias novas foram salvas."""
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
        if not texto_link or len(texto_link) < 10:
            continue

        pessoa = _pessoa_mencionada(texto_link)
        if not pessoa:
            continue

        link_absoluto = urljoin(url_base, a["href"])

        # ignora âncoras internas, javascript:, etc.
        parsed = urlparse(link_absoluto)
        if parsed.scheme not in ("http", "https"):
            continue

        if link_absoluto in links_vistos:
            continue
        links_vistos.add(link_absoluto)

        if db.url_existe(link_absoluto):
            continue  # já coletamos essa matéria antes

        trecho = _extrair_trecho_da_materia(link_absoluto)
        classificacao = ai.classificar_sentimento(
            PESSOA_NOME_EXIBICAO[pessoa], texto_link, trecho
        )

        salvou = db.salvar_noticia(
            url=link_absoluto,
            titulo=texto_link,
            trecho=trecho[:500],
            site=nome_site,
            pessoa=pessoa,
            sentimento=classificacao["sentimento"],
            justificativa=classificacao["justificativa"],
        )
        if salvou:
            novas += 1
            logger.info("📰 [%s] Nova notícia sobre %s: %s (%s)",
                        nome_site, pessoa, texto_link[:60], classificacao["sentimento"])

        time.sleep(0.5)  # educado com os servidores dos sites

    return novas


def rodar_varredura_completa() -> dict:
    """Varre todos os sites configurados. Retorna um resumo do que foi coletado."""
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
