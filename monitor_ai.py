"""
monitor_ai.py
Classifica cada notícia como positiva, negativa ou neutra para a pessoa
mencionada, usando a mesma OpenAI API já usada no restante do app.
"""

import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

PROMPT_BASE = """Você é um analista de mídia. Você vai receber o título e um trecho de uma
notícia, e o nome da pessoa pública que é o alvo da análise.

Classifique a notícia do PONTO DE VISTA DESSA PESSOA em uma destas 3 categorias:
- "positiva": a notícia é favorável, elogiosa, ou traz conquista/boa repercussão para a pessoa.
- "negativa": a notícia é crítica, expõe problema, escândalo, denúncia, ou repercussão ruim.
- "neutra": a notícia apenas menciona a pessoa de forma factual/informativa, sem tom claro.

Responda APENAS em JSON, sem nenhum texto antes ou depois, no formato:
{"sentimento": "positiva|negativa|neutra", "justificativa": "uma frase curta explicando por quê"}
"""


def classificar_sentimento(pessoa_nome: str, titulo: str, trecho: str) -> dict:
    """
    Retorna {"sentimento": "...", "justificativa": "..."}.
    Em caso de falha da API, retorna sentimento 'neutra' com justificativa de erro,
    para nunca travar o pipeline de coleta.
    """
    fallback = {"sentimento": "neutra", "justificativa": "Não foi possível classificar automaticamente."}

    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY não configurada — pulando classificação.")
        return fallback

    conteudo = f"Pessoa: {pessoa_nome}\nTítulo: {titulo}\nTrecho: {(trecho or '')[:1500]}"

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": PROMPT_BASE},
            {"role": "user", "content": conteudo}
        ],
        "max_tokens": 150,
        "temperature": 0.2
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(OPENAI_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error("OpenAI status %s: %s", resp.status_code, resp.text[:300])
            return fallback

        texto = resp.json()["choices"][0]["message"]["content"].strip()
        # remove eventuais ```json ... ``` que o modelo às vezes adiciona
        texto = texto.replace("```json", "").replace("```", "").strip()
        dados = json.loads(texto)

        sentimento = dados.get("sentimento", "neutra").lower()
        if sentimento not in ("positiva", "negativa", "neutra"):
            sentimento = "neutra"

        return {
            "sentimento": sentimento,
            "justificativa": dados.get("justificativa", "")
        }
    except Exception as e:
        logger.error("Erro ao classificar sentimento: %s", e)
        return fallback
