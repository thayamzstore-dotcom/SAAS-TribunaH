"""
layout.py
Menu lateral (sidebar) compartilhado entre as páginas do app:
Gerar Post, Monitoramento e News. Cada página importa `sidebar_html()`
e `SIDEBAR_CSS` e injeta no seu próprio template.
"""

SIDEBAR_CSS = """
        .app-shell { display:flex; min-height:100vh; }
        .app-sidebar {
            width:230px; background:#111827; color:#e5e7eb; flex-shrink:0;
            padding:20px 0; display:flex; flex-direction:column;
        }
        .app-sidebar .logo { padding:0 20px 20px 20px; font-weight:700; font-size:1.1rem; color:white; border-bottom:1px solid #1f2937; margin-bottom:10px; }
        .app-sidebar a {
            display:block; padding:12px 20px; color:#9ca3af; text-decoration:none;
            font-weight:600; font-size:0.95rem; border-left:3px solid transparent;
        }
        .app-sidebar a:hover { background:#1f2937; color:white; }
        .app-sidebar a.active { background:#1f2937; color:white; border-left-color:#c3161f; }
        .app-sidebar .sair { margin-top:auto; border-top:1px solid #1f2937; padding-top:10px; }
        .app-content { flex:1; min-width:0; overflow-x:auto; }
"""


def sidebar_html(active: str) -> str:
    def item(chave, href, label, emoji):
        classe = "active" if chave == active else ""
        return f'<a class="{classe}" href="{href}">{emoji} {label}</a>'

    return f"""
    <aside class="app-sidebar">
        <div class="logo">📰 TRIBUNA HOJE</div>
        {item('gerar_post', '/', 'Gerar Post', '📱')}
        {item('monitoramento', '/monitoramento', 'Monitoramento', '🔎')}
        {item('noticias', '/noticias', 'News', '📡')}
        <div class="sair">
            <a href="/logout">🔒 Sair</a>
        </div>
    </aside>
    """
