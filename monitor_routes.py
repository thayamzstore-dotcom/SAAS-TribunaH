"""
monitor_routes.py
Registra na sua aplicação Flask existente:
  - GET  /monitoramento                    -> dashboard HTML
  - GET  /api/monitoramento/noticias       -> lista de notícias (JSON)
  - GET  /api/monitoramento/resumo         -> contagem do dia (JSON)
  - GET  /api/monitoramento/status         -> status da varredura em andamento
  - POST /api/monitoramento/atualizar      -> dispara varredura manual

Também liga um agendador (APScheduler) que roda a varredura automaticamente
de X em X horas.

COMO INTEGRAR NO SEU main.py (adicione perto do final, antes do app.run):

    from monitor_routes import init_monitor_module

    init_monitor_module(app, login_required=login_required)

Isso já cria a tabela do banco, registra as rotas (protegidas pela mesma
senha do resto do app) e liga o agendador automático.
"""

import logging
import threading
from datetime import datetime

from flask import jsonify, request, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler

import monitor_db as db
import monitor_scraper as scraper

logger = logging.getLogger(__name__)

INTERVALO_HORAS_PADRAO = 3

_status_lock = threading.Lock()
_status = {
    "rodando": False,
    "ultima_atualizacao": None,
    "ultimo_resultado": None,
}


def _executar_varredura_em_thread():
    with _status_lock:
        if _status["rodando"]:
            return False  # já tem uma varredura rodando
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

    @app.route("/monitoramento")
    @protetor
    def monitoramento_dashboard():
        return render_template_string(DASHBOARD_TEMPLATE)

    @app.route("/api/monitoramento/noticias")
    @protetor
    def api_noticias():
        pessoa = request.args.get("pessoa") or None
        apenas_hoje = request.args.get("hoje") == "1"
        noticias = db.listar_noticias(pessoa=pessoa, apenas_hoje=apenas_hoje)
        return jsonify({"success": True, "noticias": noticias})

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
        if not iniciou:
            return jsonify({"success": False, "message": "Já existe uma varredura em andamento."})
        return jsonify({"success": True, "message": "Varredura iniciada em segundo plano."})

    # Agendador automático
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _executar_varredura_em_thread,
        "interval",
        hours=intervalo_horas,
        id="varredura_automatica",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("🕒 Agendador de monitoramento ligado: a cada %sh", intervalo_horas)


DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Monitoramento de Notícias - Tribuna Hoje</title>
<style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; background:#f4f5f7; color:#333; }
    .container { max-width:1100px; margin:0 auto; padding:25px; }
    .header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:10px; }
    .header h1 { color:#c3161f; }
    .header a { color:#6c757d; text-decoration:none; }
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
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🔎 Monitoramento de Notícias</h1>
        <div>
            <button class="btn btn-primary" id="btn-atualizar" onclick="atualizarAgora()">🔄 Atualizar agora</button>
            <a href="/" style="margin-left:15px;">&larr; Voltar ao app</a>
        </div>
    </div>

    <div class="status-line" id="status-line">Carregando status...</div>

    <div class="resumo" id="resumo"></div>

    <div class="filtros">
        <button class="filtro-btn active" onclick="filtrar(this,null)">Todos</button>
        <button class="filtro-btn" onclick="filtrar(this,'renan_filho')">Renanzinho (Renan Filho)</button>
        <button class="filtro-btn" onclick="filtrar(this,'jhc')">JHC (João Henrique Caldas)</button>
        <button class="filtro-btn" onclick="filtrarHoje(this)" id="btn-hoje">Somente hoje</button>
    </div>

    <div id="lista-noticias"></div>
</div>

<script>
    let pessoaAtual = null;
    let apenasHoje = false;

    const SENTIMENTO_LABEL = { positiva: '👍 Positiva', negativa: '👎 Negativa', neutra: '➖ Neutra' };

    async function carregarResumo() {
        const r = await fetch('/api/monitoramento/resumo');
        const data = await r.json();
        const el = document.getElementById('resumo');
        el.innerHTML = '';
        if (!data.resumo || data.resumo.length === 0) {
            el.innerHTML = '<div class="resumo-card"><div class="num">0</div><div>Nenhuma notícia hoje ainda</div></div>';
            return;
        }
        data.resumo.forEach(item => {
            const div = document.createElement('div');
            div.className = 'resumo-card';
            div.innerHTML = '<div class="num">' + item.total + '</div><div>' + item.pessoa + ' — ' + (SENTIMENTO_LABEL[item.sentimento] || item.sentimento) + '</div>';
            el.appendChild(div);
        });
    }

    async function carregarNoticias() {
        let url = '/api/monitoramento/noticias?';
        if (pessoaAtual) url += 'pessoa=' + pessoaAtual + '&';
        if (apenasHoje) url += 'hoje=1';

        const r = await fetch(url);
        const data = await r.json();
        const lista = document.getElementById('lista-noticias');
        lista.innerHTML = '';

        if (!data.noticias || data.noticias.length === 0) {
            lista.innerHTML = '<div class="vazio">Nenhuma notícia encontrada com esse filtro.</div>';
            return;
        }

        data.noticias.forEach(n => {
            const div = document.createElement('div');
            div.className = 'noticia';
            div.innerHTML = `
                <a href="${n.url}" target="_blank">${n.titulo}</a>
                <span class="badge ${n.sentimento}">${SENTIMENTO_LABEL[n.sentimento] || n.sentimento}</span>
                <div class="meta">${n.site} · coletado em ${n.coletado_em}</div>
                ${n.trecho ? '<div class="trecho">' + n.trecho.substring(0, 220) + '...</div>' : ''}
            `;
            lista.appendChild(div);
        });
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
            linha.textContent = data.ultima_atualizacao
                ? 'Última atualização: ' + data.ultima_atualizacao
                : 'Ainda não rodou nenhuma varredura.';
        }
        return data.rodando;
    }

    function filtrar(botao, pessoa) {
        document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('active'));
        botao.classList.add('active');
        pessoaAtual = pessoa;
        carregarNoticias();
    }

    function filtrarHoje(botao) {
        apenasHoje = !apenasHoje;
        botao.classList.toggle('active', apenasHoje);
        carregarNoticias();
    }

    async function atualizarAgora() {
        const btn = document.getElementById('btn-atualizar');
        btn.disabled = true;
        await fetch('/api/monitoramento/atualizar', { method: 'POST' });
        pollAteAcabar();
    }

    function pollAteAcabar() {
        const intervalo = setInterval(async () => {
            const rodando = await carregarStatus();
            if (!rodando) {
                clearInterval(intervalo);
                carregarResumo();
                carregarNoticias();
            }
        }, 4000);
    }

    // carga inicial
    carregarStatus();
    carregarResumo();
    carregarNoticias();
    setInterval(carregarStatus, 10000);
</script>
</body>
</html>
"""
