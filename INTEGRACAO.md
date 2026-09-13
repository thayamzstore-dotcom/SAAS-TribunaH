# Como integrar o Monitoramento de Notícias no seu app

## 1. Adicione os arquivos ao repositório
Coloque estes 5 arquivos na raiz do repo `SAAS-TribunaH`, ao lado do `main.py`:
- `monitor_db.py`
- `monitor_ai.py`
- `monitor_scraper.py`
- `monitor_routes.py`
- `sites_config.json` (edite e coloque seus 20+ sites reais aqui)

## 2. Atualize o `requirements.txt`
Adicione estas linhas (se ainda não existirem):
```
beautifulsoup4
lxml
APScheduler
```

## 3. Edite o `main.py`
Perto do topo, junto dos outros imports:
```python
from monitor_routes import init_monitor_module
```

Perto do final do arquivo, **antes** do bloco `if __name__ == '__main__':`, adicione:
```python
# ✅ MONITORAMENTO DE NOTÍCIAS
init_monitor_module(app, login_required=login_required, intervalo_horas=3)
```
(`intervalo_horas=3` é de quanto em quanto tempo ele varre os sites sozinho —
mude pra 1, 2, 6, o que fizer sentido pro seu volume de sites.)

## 4. Link na sua tela principal (opcional, mas recomendado)
No `HTML_TEMPLATE`, dentro do `.header` do app principal, adicione um link:
```html
<a href="/monitoramento" style="color:white; text-decoration:none; background:rgba(255,255,255,0.2); padding:10px 20px; border-radius:5px; margin-top:15px; display:inline-block;">
    🔎 Monitoramento
</a>
```

## 5. Preencha o `sites_config.json`
Formato de cada site:
```json
{ "nome": "Nome do Portal", "url": "https://dominio-do-site.com" }
```
Dica: use a URL da **home** do site ou de uma editoria específica (ex: "Política"),
porque o scraper lê os links de título que aparecem naquela página. Se um site
tiver muitas notícias por dia, prefira apontar pra editoria de política/cidade
em vez da home geral — evita perder notícias que "rolam" rápido da home.

## 6. Suba o deploy no Easypanel normalmente
Depois do rebuild, acesse `https://seu-dominio/monitoramento` (logado com a
mesma senha do app) pra ver a dashboard.

## Como funciona, resumidamente
- O agendador roda sozinho a cada X horas e também dá pra clicar em
  **"Atualizar agora"** na dashboard.
- Pra cada site, ele lê os links da página e filtra os que mencionam
  "Renanzinho"/"Renan Filho" ou "JHC"/"João Henrique Caldas" no texto do link.
- Notícia nova (URL que ainda não está no banco) → abre a matéria, pega um
  trecho do texto, manda pra IA classificar como positiva/negativa/neutra,
  e salva tudo no banco `monitoramento.db` (SQLite, fica junto do app).
- A dashboard mostra tudo isso com filtro por pessoa e por "somente hoje".

## Pontos de atenção
- Sites com paywall ou proteção anti-bot (Cloudflare, etc.) podem bloquear o
  scraper — se algum site específico não retornar nada, me avisa que a gente
  ajusta o header/estratégia pra ele.
- Como o scraper lê o **texto do link** na home pra decidir se é sobre a
  pessoa, se um site nunca põe o nome completo no título do link (só na
  matéria), ele pode passar batido. Nesse caso dá pra evoluir depois pra
  também checar o conteúdo da matéria, não só o título — mas isso deixa a
  varredura mais lenta (abre todas as matérias do dia, não só as que já têm
  o nome no título).
