"""
monitor_routes.py
Registra na sua aplicação Flask:
  - GET  /monitoramento                    -> dashboard de Renan Filho / JHC + busca por palavra-chave
  - GET  /noticias                         -> feed geral (aba "News") com todas as notícias coletadas
  - GET  /api/monitoramento/noticias       -> lista de notícias por pessoa (JSON)
  - GET  /api/monitoramento/buscar         -> busca por palavra-chave no título/corpo (JSON)
  - GET  /api/monitoramento/resumo         -> contagem do dia (JSON)
  - GET  /api/monitoramento/status         -> status da varredura em andamento
  - POST /api/monitoramento/atualizar      -> dispara varredura manual
  - GET  /api/noticias/todas               -> feed geral (JSON)

COMO INTEGRAR NO SEU main.py:

    from monitor_routes import init_monitor_module

    init_monitor_module(app, login_required=login_required, intervalo_horas=3)
"""

import logging
import threading
from datetime import datetime

from flask import jsonify, request, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler

import monitor_db as db
import monitor_scraper as scraper
from layout import sidebar_html, SIDEBAR_CSS

logger = logging.getLogger(__name__)

INTERVALO_HORAS_PADRAO = 3

_status_lock = threading.Lock()
_status = {"rodando": False, "ultima_atualizacao": None, "ultimo_resultado": None}


def _executar_varredura_em_thread():
    with _status_lock:
        if _status["rodando"]:
            return False
        _status["rodando"] = True

    def alvo():
        try:
            resultado = scraper.rodar_varredura_completa()
            with _status_lock:
                _status["ultimo_resultado"] = resultado
                _status["ultima_atualizacao"] = datetime.now().isoformat(timespec="seconds")
        except Exception as e:
            logger.error("Erro na varredura: %s", e)
            with _status_lock:
                _status["ultimo_resultado"] = {"erro": str(e)}
        finally:
            with _status_lock:
                _status["rodando"] = False

    threading.Thread(target=alvo, daemon=True).start()
    return True


def init_monitor_module(app, login_required=None, intervalo_horas: int = INTERVALO_HORAS_PADRAO):
    db.init_db()
    protetor = login_required if login_required else (lambda f: f)

    # ---------- páginas ----------
    @app.route("/monitoramento")
    @protetor
    def monitoramento_dashboard():
        return render_template_string(
            MONITORAMENTO_TEMPLATE, sidebar=sidebar_html("monitoramento"), sidebar_css=SIDEBAR_CSS
        )

    @app.route("/noticias")
    @protetor
    def noticias_feed():
        return render_template_string(
            NOTICIAS_TEMPLATE, sidebar=sidebar_html("noticias"), sidebar_css=SIDEBAR_CSS
        )

    # ---------- API: monitoramento (Renan Filho / JHC) ----------
    @app.route("/api/monitoramento/noticias")
    @protetor
    def api_noticias():
        pessoa = request.args.get("pessoa") or None
        apenas_hoje = request.args.get("hoje") == "1"
        return jsonify({"success": True, "noticias": db.listar_noticias(pessoa=pessoa, apenas_hoje=apenas_hoje)})

    @app.route("/api/monitoramento/buscar")
    @protetor
    def api_buscar():
        termo = request.args.get("termo", "").strip()
        if not termo:
            return jsonify({"success": False, "message": "Informe um termo de busca."})
        return jsonify({"success": True, "noticias": db.buscar_por_palavra(termo)})

    @app.route("/api/monitoramento/resumo")
    @protetor
    def api_resumo():
        return jsonify({"success": True, "resumo": db.resumo_do_dia()})

    @app.route("/api/monitoramento/status")
    @protetor
    def api_status():
        with _status_lock:
            return jsonify({"success": True, **_status})

    @app.route("/api/monitoramento/atualizar", methods=["POST"])
    @protetor
    def api_atualizar():
        iniciou = _executar_varredura_em_thread()
        msg = "Varredura iniciada em segundo plano." if iniciou else "Já existe uma varredura em andamento."
        return jsonify({"success": iniciou, "message": msg})

    # ---------- API: News (feed geral) ----------
    @app.route("/api/noticias/todas")
    @protetor
    def api_noticias_todas():
        site = request.args.get("site") or None
        apenas_hoje = request.args.get("hoje") == "1"
        return jsonify({
            "success": True,
            "noticias": db.listar_todas_noticias(site=site, apenas_hoje=apenas_hoje),
            "sites": db.listar_sites_distintos(),
        })

    # ---------- agendador automático ----------
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _executar_varredura_em_thread, "interval", hours=intervalo_horas,
        id="varredura_automatica", replace_existing=True,
    )
    scheduler.start()
    logger.info("🕒 Agendador de monitoramento ligado: a cada %sh", intervalo_horas)


# ==================== TEMPLATES ====================

BASE_STYLE = """
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; background:#f4f5f7; color:#333; }
    .page { padding:25px; max-width:1100px; }
    .header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:10px; }
    .header h1 { color:#c3161f; }
    .btn { padding:10px 18px; border:none; border-radius:6px; font-weight:600; cursor:pointer; font-size:0.95rem; }
    .btn-primary { background:#c3161f; color:white; }
    .btn-primary:disabled { background:#e0a0a4; cursor:not-allowed; }
    .filtros { display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap; }
    .filtro-btn { padding:8px 16px; border-radius:20px; border:2px solid #dee2e6; background:white; cursor:pointer; font-weight:600; }
    .filtro-btn.active { background:#c3161f; color:white; border-color:#c3161f; }
    .resumo { display:flex; gap:15px; margin-bottom:20px; flex-wrap:wrap; }
    .resumo-card { background:white; border-radius:10px; padding:15px 20px; box-shadow:0 2px 8px rgba(0,0,0,0.08); min-width:140px; }
    .resumo-card .num { font-size:1.6rem; font-weight:bold; }
    .status-line { font-size:0.85rem; color:#6c757d; margin-bottom:15px; }
    .busca-box { display:flex; gap:10px; margin-bottom:20px; }
    .busca-box input { flex:1; padding:12px; border:2px solid #dee2e6; border-radius:8px; font-size:1rem; }
    .noticia { background:white; border-radius:10px; padding:16px 20px; margin-bottom:12px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
    .noticia a { color:#212529; text-decoration:none; font-weight:600; font-size:1.05rem; }
    .noticia a:hover { color:#c3161f; }
    .noticia .meta { font-size:0.85rem; color:#6c757d; margin-top:6px; }
    .noticia .trecho { font-size:0.9rem; color:#495057; margin-top:8px; }
    .badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:700; color:white; margin-left:8px; }
    .badge.positiva { background:#28a745; }
    .badge.negativa { background:#dc3545; }
    .badge.neutra { background:#6c757d; }
    .vazio { text-align:center; color:#adb5bd; padding:40px; }
    select.control-select { padding:10px; border-radius:6px; border:2px solid #dee2e6; }
"""

MONITORAMENTO_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitoramento - Tribuna Hoje</title>
<style>
{{ sidebar_css | safe }}
""" + BASE_STYLE + """
</style>
</head>
<body>
<div class="app-shell">
{{ sidebar | safe }}
<main class="app-content"><div class="page">
    <div class="header">
        <h1>🔎 Monitoramento — Renan Filho e JHC</h1>
        <button class="btn btn-primary" id="btn-atualizar" onclick="atualizarAgora()">🔄 Atualizar agora</button>
    </div>

    <div class="status-line" id="status-line">Carregando status...</div>
    <div class="resumo" id="resumo"></div>

    <div class="busca-box">
        <input type="text" id="campo-busca" placeholder="Buscar palavra-chave no título e corpo das notícias já coletadas...">
        <button class="btn btn-primary" onclick="buscarPalavra()">Buscar</button>
        <button class="btn" style="background:#6c757d;color:white;" onclick="limparBusca()">Limpar</button>
    </div>

    <div class="filtros">
        <button class="filtro-btn active" onclick="filtrar(this,null)">Todos</button>
        <button class="filtro-btn" onclick="filtrar(this,'renan_filho')">Renanzinho (Renan Filho)</button>
        <button class="filtro-btn" onclick="filtrar(this,'jhc')">JHC (João Henrique Caldas)</button>
        <button class="filtro-btn" onclick="filtrarHoje(this)">Somente hoje</button>
    </div>

    <div id="lista-noticias"></div>
</div></main>
</div>

<script>
    let pessoaAtual = null;
    let apenasHoje = false;
    let modoBusca = false;
    const SENTIMENTO_LABEL = { positiva: '👍 Positiva', negativa: '👎 Negativa', neutra: '➖ Neutra' };

    async function carregarResumo() {
        const r = await fetch('/api/monitoramento/resumo');
        const data = await r.json();
        const el = document.getElementById('resumo');
        el.innerHTML = '';
        if (!data.resumo || data.resumo.length === 0) {
            el.innerHTML = '<div class="resumo-card"><div class="num">0</div><div>Nenhuma menção hoje ainda</div></div>';
            return;
        }
        data.resumo.forEach(item => {
            const div = document.createElement('div');
            div.className = 'resumo-card';
            div.innerHTML = '<div class="num">' + item.total + '</div><div>' + item.pessoa + ' — ' + (SENTIMENTO_LABEL[item.sentimento] || item.sentimento) + '</div>';
            el.appendChild(div);
        });
    }

    function renderLista(noticias) {
        const lista = document.getElementById('lista-noticias');
        lista.innerHTML = '';
        if (!noticias || noticias.length === 0) {
            lista.innerHTML = '<div class="vazio">Nenhuma notícia encontrada.</div>';
            return;
        }
        noticias.forEach(n => {
            const div = document.createElement('div');
            div.className = 'noticia';
            const badge = n.sentimento ? `<span class="badge ${n.sentimento}">${SENTIMENTO_LABEL[n.sentimento] || n.sentimento}</span>` : '';
            div.innerHTML = `
                <a href="${n.url}" target="_blank">${n.titulo}</a> ${badge}
                <div class="meta">${n.site} · coletado em ${n.coletado_em}</div>
                ${n.trecho ? '<div class="trecho">' + n.trecho.substring(0, 220) + '...</div>' : ''}
            `;
            lista.appendChild(div);
        });
    }

    async function carregarNoticias() {
        let url = '/api/monitoramento/noticias?';
        if (pessoaAtual) url += 'pessoa=' + pessoaAtual + '&';
        if (apenasHoje) url += 'hoje=1';
        const r = await fetch(url);
        const data = await r.json();
        renderLista(data.noticias);
    }

    async function buscarPalavra() {
        const termo = document.getElementById('campo-busca').value.trim();
        if (!termo) return;
        modoBusca = true;
        const r = await fetch('/api/monitoramento/buscar?termo=' + encodeURIComponent(termo));
        const data = await r.json();
        renderLista(data.noticias);
    }

    function limparBusca() {
        document.getElementById('campo-busca').value = '';
        modoBusca = false;
        carregarNoticias();
    }

    async function carregarStatus() {
        const r = await fetch('/api/monitoramento/status');
        const data = await r.json();
        const linha = document.getElementById('status-line');
        const btn = document.getElementById('btn-atualizar');
        if (data.rodando) {
            linha.textContent = '⏳ Varredura em andamento...';
            btn.disabled = true;
        } else {
            btn.disabled = false;
            linha.textContent = data.ultima_atualizacao ? 'Última atualização: ' + data.ultima_atualizacao : 'Ainda não rodou nenhuma varredura.';
        }
        return data.rodando;
    }

    function filtrar(botao, pessoa) {
        document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('active'));
        botao.classList.add('active');
        pessoaAtual = pessoa;
        modoBusca = false;
        carregarNoticias();
    }

    function filtrarHoje(botao) {
        apenasHoje = !apenasHoje;
        botao.classList.toggle('active', apenasHoje);
        modoBusca = false;
        carregarNoticias();
    }

    async function atualizarAgora() {
        document.getElementById('btn-atualizar').disabled = true;
        await fetch('/api/monitoramento/atualizar', { method: 'POST' });
        const intervalo = setInterval(async () => {
            const rodando = await carregarStatus();
            if (!rodando) {
                clearInterval(intervalo);
                carregarResumo();
                if (!modoBusca) carregarNoticias();
            }
        }, 4000);
    }

    document.getElementById('campo-busca').addEventListener('keydown', e => { if (e.key === 'Enter') buscarPalavra(); });

    carregarStatus();
    carregarResumo();
    carregarNoticias();
    setInterval(carregarStatus, 10000);
</script>
</body>
</html>
"""

NOTICIAS_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>News - Tribuna Hoje</title>
<style>
{{ sidebar_css | safe }}
""" + BASE_STYLE + """
</style>
</head>
<body>
<div class="app-shell">
{{ sidebar | safe }}
<main class="app-content"><div class="page">
    <div class="header">
        <h1>📡 News — Política (todos os sites)</h1>
        <select class="control-select" id="filtro-site" onchange="carregarFeed()">
            <option value="">Todos os sites</option>
        </select>
    </div>
    <div class="status-line">Atualiza automaticamente a cada 30 segundos.</div>
    <div id="lista-noticias"></div>
</div></main>
</div>

<script>
    const SENTIMENTO_LABEL = { positiva: '👍 Positiva', negativa: '👎 Negativa', neutra: '➖ Neutra' };
    let sitesCarregados = false;

    async function carregarFeed() {
        const site = document.getElementById('filtro-site').value;
        let url = '/api/noticias/todas?';
        if (site) url += 'site=' + encodeURIComponent(site);
        const r = await fetch(url);
        const data = await r.json();

        if (!sitesCarregados && data.sites) {
            const select = document.getElementById('filtro-site');
            data.sites.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s; opt.textContent = s;
                select.appendChild(opt);
            });
            sitesCarregados = true;
        }

        const lista = document.getElementById('lista-noticias');
        lista.innerHTML = '';
        if (!data.noticias || data.noticias.length === 0) {
            lista.innerHTML = '<div class="vazio">Nenhuma notícia coletada ainda.</div>';
            return;
        }
        data.noticias.forEach(n => {
            const div = document.createElement('div');
            div.className = 'noticia';
            const badge = n.sentimento ? `<span class="badge ${n.sentimento}">${SENTIMENTO_LABEL[n.sentimento] || n.sentimento}</span>` : '';
            div.innerHTML = `
                <a href="${n.url}" target="_blank">${n.titulo}</a> ${badge}
                <div class="meta">${n.site} · coletado em ${n.coletado_em}</div>
            `;
            lista.appendChild(div);
        });
    }

    carregarFeed();
    setInterval(carregarFeed, 30000);
</script>
</body>
</html>
"""
