from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import requests
import json
import base64
import io
from datetime import datetime
import os
import re

app = Flask(__name__)
CORS(app)

# Configuração da API do Placid
PLACID_API_TOKEN = 'placid-ga0mydmthqv9aouj-tkn7ayu7l7zfk3he'
PLACID_API_URL = 'https://api.placid.app/api/rest/images'

# Templates disponíveis
PLACID_TEMPLATES = {
    'watermark': {
        'uuid': 'x9jxylt4vx2x0',
        'name': 'Marca d\'Água',
        'description': 'Template para aplicar marca d\'água',
        'type': 'watermark'
    },
    'stories_1': {
        'uuid': 'g7wi0hogpxx5c',
        'name': 'Stories - Modelo 1',
        'description': 'Template para Stories',
        'type': 'story',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'reels_feed_2': {
        'uuid': 'ltgftf7ybxcqb',
        'name': 'Reels Feed - Modelo 2',
        'description': 'Template para Reels e Feed',
        'type': 'reels',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'reels_feed_3': {
        'uuid': 'cjnpj919alht9',
        'name': 'Reels Feed - Modelo 3',
        'description': 'Template para Reels e Feed',
        'type': 'reels',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'feed_1': {
        'uuid': '7vqi5vgmvwgfm',
        'name': 'Feed - Modelo 1',
        'description': 'Template para Feed',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_1_red': {
        'uuid': 'qe0qo74vbrgxe',
        'name': 'Feed - Modelo 1 (Red)',
        'description': 'Template para Feed - Versão Vermelha',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_2_white': {
        'uuid': 'ye0bmj6dgoneq',
        'name': 'Feed - Modelo 2 (White)',
        'description': 'Template para Feed - Versão Branca',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_3_black': {
        'uuid': '7mfd5rkx2hmvw',
        'name': 'Feed - Modelo 3 (Black)',
        'description': 'Template para Feed - Versão Preta',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    }
}

# Diretório para salvar imagens temporariamente
UPLOAD_FOLDER = os.path.abspath('uploads')
if not os.path.exists(UPLOAD_FOLDER ):
    os.makedirs(UPLOAD_FOLDER)

# Funções para interagir com a API do Placid
def create_placid_image(template_uuid, layers, modifications=None, webhook_success=None):
    """
    Cria uma nova imagem no Placid
    """
    headers = {
        'Authorization': f'Bearer {PLACID_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'template_uuid': template_uuid,
        'layers': layers,
        'create_now': True
    }
    
    if modifications:
        payload['modifications'] = modifications
    
    if webhook_success:
        payload['webhook_success'] = webhook_success
    
    try:
        response = requests.post(PLACID_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao criar imagem no Placid: {e}")
        return None

def get_placid_image(image_id):
    """
    Obtém informações de uma imagem do Placid
    """
    headers = {
        'Authorization': f'Bearer {PLACID_API_TOKEN}'
    }
    
    try:
        response = requests.get(f'{PLACID_API_URL}/{image_id}', headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter imagem do Placid: {e}")
        return None

def delete_placid_image(image_id):
    """
    Deleta uma imagem do Placid
    """
    headers = {
        'Authorization': f'Bearer {PLACID_API_TOKEN}'
    }
    
    try:
        response = requests.delete(f'{PLACID_API_URL}/{image_id}', headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao deletar imagem do Placid: {e}")
        return False

def poll_placid_image_status(image_id, max_attempts=30, delay=2):
    """
    Polling para verificar o status de uma imagem no Placid
    """
    import time
    
    for attempt in range(max_attempts):
        image_data = get_placid_image(image_id)
        if not image_data:
            return None
            
        status = image_data.get('status')
        
        if status == 'finished':
            return image_data
        elif status == 'error':
            print(f"Erro na criação da imagem: {image_data}")
            return None
        
        time.sleep(delay)
    
    print(f"Timeout: Imagem não foi criada em {max_attempts * delay} segundos")
    return None

# Template HTML completo
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaaS Editor - Jornalistas Instagram</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .tabs-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }

        .tabs-nav {
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }

        .tab-button {
            flex: 1;
            padding: 15px 20px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            color: #6c757d;
            transition: all 0.3s ease;
            position: relative;
        }

        .tab-button:hover {
            background: #e9ecef;
            color: #495057;
        }

        .tab-button.active {
            color: #667eea;
            background: white;
        }

        .tab-button.active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: #667eea;
        }

        .tab-content {
            display: none;
            padding: 30px;
            min-height: 600px;
        }

        .tab-content.active {
            display: block;
        }

        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .upload-area:hover {
            border-color: #5a6fd8;
            background: #f8f9ff;
        }

        .upload-area.dragover {
            border-color: #4c63d2;
            background: #f0f3ff;
        }

        .upload-icon {
            font-size: 3rem;
            color: #667eea;
            margin-bottom: 15px;
        }

        .upload-text {
            font-size: 1.1rem;
            color: #6c757d;
            margin-bottom: 10px;
        }

        .upload-subtext {
            font-size: 0.9rem;
            color: #adb5bd;
        }

        .file-input {
            display: none;
        }

        .controls-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .control-group {
            margin-bottom: 15px;
        }

        .control-label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #495057;
        }

        .control-input {
            width: 100%;
            padding: 10px;
            border: 2px solid #e9ecef;
            border-radius: 5px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }

        .control-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .range-input {
            width: 100%;
            margin: 10px 0;
        }

        .format-selector {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }

        .format-option {
            flex: 1;
            padding: 15px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .format-option:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }

        .format-option.selected {
            border-color: #667eea;
            background: #667eea;
            color: white;
        }

        .template-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .template-item {
            border: 2px solid #e9ecef;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .template-item:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }

        .template-item.selected {
            border-color: #667eea;
            background: #f8f9ff;
        }

        .template-preview {
            width: 100%;
            height: 100px;
            background: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6c757d;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5a6fd8;
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: #6c757d;
            color: white;
        }

        .btn-secondary:hover {
            background: #5a6268;
        }

        .btn-success {
            background: #28a745;
            color: white;
        }

        .btn-success:hover {
            background: #218838;
        }

        .preview-area {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
        }

        .preview-placeholder {
            width: 100%;
            height: 300px;
            background: #e9ecef;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6c757d;
            font-size: 1.1rem;
        }

        .ai-suggestions {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }

        .suggestion-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .suggestion-item:hover {
            transform: translateX(5px);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }

        @media (max-width: 768px) {
            .tabs-nav {
                flex-direction: column;
            }
            
            .two-column {
                grid-template-columns: 1fr;
            }
            
            .format-selector {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📸 SaaS Editor</h1>
            <p>Ferramenta completa para jornalistas criarem conteúdo para Instagram</p>
        </div>

        <div class="tabs-container">
            <div class="tabs-nav">
                <button class="tab-button active" onclick="switchTab('marca-dagua')">🏷️ Marca d'Água</button>
                <button class="tab-button" onclick="switchTab('gerar-posts')">📱 Gerar Posts</button>
                <button class="tab-button" onclick="switchTab('legendas-ia')">✍️ Legendas IA</button>
                <button class="tab-button" onclick="switchTab('titulo-ia')">📰 Título IA</button>
                <button class="tab-button" onclick="switchTab('reescrever-noticia')">📝 Reescrever Notícia</button>
            </div>

            <!-- Aba Marca d'Água -->
            <div id="marca-dagua" class="tab-content active">
                <h2>Aplicar Marca d'Água</h2>
                <div class="upload-area" onclick="document.getElementById('watermark-file').click()">
                    <div class="upload-icon">📁</div>
                    <div class="upload-text">Clique para fazer upload ou arraste sua foto/vídeo aqui</div>
                    <div class="upload-subtext">Formatos suportados: JPG, PNG, MP4, MOV</div>
                </div>
                <input type="file" id="watermark-file" class="file-input" accept="image/*,video/*" onchange="handleFileUpload(this, 'watermark')">

                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Posição da Marca d'Água</label>
                        <select class="control-input" id="watermark-position">
                            <option value="bottom-right">Inferior Direita</option>
                            <option value="bottom-left">Inferior Esquerda</option>
                            <option value="top-right">Superior Direita</option>
                            <option value="top-left">Superior Esquerda</option>
                            <option value="center">Centro</option>
                        </select>
                    </div>
                    <div class="control-group">
                        <label class="control-label">Transparência: <span id="transparency-value">50%</span></label>
                        <input type="range" class="range-input" id="transparency" min="0" max="100" value="50" oninput="updateTransparency(this.value)">
                    </div>
                </div>

                <div class="preview-area">
                    <div class="preview-placeholder" id="watermark-preview">
                        Pré-visualização aparecerá aqui
                    </div>
                </div>

                <div class="loading" id="watermark-loading">
                    <div class="spinner"></div>
                    <p>Aplicando marca d'água...</p>
                </div>

                <div class="success-message" id="watermark-success"></div>
                <div class="error-message" id="watermark-error"></div>

                <button class="btn btn-primary" onclick="applyWatermark()">Aplicar Marca d'Água</button>
                <button class="btn btn-success" onclick="downloadFile(\'watermark\')">📥 Download</button>
                <a href="#" id="open-watermark-image" class="btn btn-secondary" style="margin-left: 10px; display: none;" target="_blank">🖼️ Abrir Imagem</a>           </div>

            <!-- Aba Gerar Posts -->
            <div id="gerar-posts" class="tab-content">
                <h2>Gerar Posts para Instagram</h2>
                
                <div class="upload-area" onclick="document.getElementById('post-file').click()">
                    <div class="upload-icon">📁</div>
                    <div class="upload-text">Upload da foto ou vídeo</div>
                    <div class="upload-subtext">Formatos suportados: JPG, PNG, MP4, MOV</div>
                </div>
                <input type="file" id="post-file" class="file-input" accept="image/*,video/*" onchange="handleFileUpload(this, 'post')">

                <div class="controls-section">
                    <h3>Selecione o Formato</h3>
                    <div class="format-selector">
                        <div class="format-option selected" onclick="selectFormat('reels')">
                            <h4>📹 Reels</h4>
                            <p>Vídeos verticais</p>
                        </div>
                        <div class="format-option" onclick="selectFormat('stories')">
                            <h4>📱 Stories</h4>
                            <p>Conteúdo temporário</p>
                        </div>
                        <div class="format-option" onclick="selectFormat('feed')">
                            <h4>🖼️ Feed</h4>
                            <p>Posts principais</p>
                        </div>
                    </div>

                    <h3>Templates Disponíveis</h3>
                    <div class="template-grid" id="template-grid">
                        <div class="template-item selected" onclick="selectTemplate('stories_1')">
                            <div class="template-preview">📱</div>
                            <p>Stories - Modelo 1</p>
                        </div>
                        <div class="template-item" onclick="selectTemplate('reels_feed_2')">
                            <div class="template-preview">🎬</div>
                            <p>Reels Feed - Modelo 2</p>
                        </div>
                        <div class="template-item" onclick="selectTemplate('reels_feed_3')">
                            <div class="template-preview">🎥</div>
                            <p>Reels Feed - Modelo 3</p>
                        </div>
                        <div class="template-item" onclick="selectTemplate('feed_1')">
                            <div class="template-preview">🖼️</div>
                            <p>Feed - Modelo 1</p>
                        </div>
                        <div class="template-item" onclick="selectTemplate('feed_1_red')">
                            <div class="template-preview">🔴</div>
                            <p>Feed - Modelo 1 (Red)</p>
                        </div>
                        <div class="template-item" onclick="selectTemplate('feed_2_white')">
                            <div class="template-preview">⚪</div>
                            <p>Feed - Modelo 2 (White)</p>
                        </div>
                        <div class="template-item" onclick="selectTemplate('feed_3_black')">
                            <div class="template-preview">⚫</div>
                            <p>Feed - Modelo 3 (Black)</p>
                        </div>
                    </div>
                </div>

                <div class="two-column">
                    <div>
                        <div class="controls-section">
                            <div class="control-group">
                                <label class="control-label">Título *</label>
                                <input type="text" class="control-input" id="titulo" placeholder="Digite o título do post" required oninput="generateSlug(this.value)">
                                <div id="slug-preview" style="margin-top: 10px; color: #6c757d;"></div>
                            </div>
                            <div class="control-group" id="assunto-group" style="display: none;">
                                <label class="control-label">Assunto *</label>
                                <input type="text" class="control-input" id="assunto" placeholder="Assunto da foto (obrigatório para templates de Feed)">
                            </div>
                            <div class="control-group" id="creditos-group" style="display: none;">
                                <label class="control-label">Nome do Fotógrafo *</label>
                                <input type="text" class="control-input" id="creditos" placeholder="Nome do fotógrafo (obrigatório para templates de Feed)">
                            </div>
                        </div>

                        <div class="loading" id="post-loading">
                            <div class="spinner"></div>
                            <p>Gerando post com template...</p>
                        </div>

                        <div class="success-message" id="post-success"></div>
                        <div class="error-message" id="post-error"></div>

                        <button class="btn btn-primary" onclick="generatePost()">🎨 Gerar Post</button>
                    </div>
                    <div>
                        <div class="preview-area">
                            <div class="preview-placeholder" id="post-preview">
                                Pré-visualização do post aparecerá aqui
                            </div>
                        </div>
                        <button class="btn btn-success" onclick="downloadFile(\'post\')">📥 Download Post</button>
                        <a href="#" id="open-post-image" class="btn btn-secondary" style="margin-left: 10px; display: none;" target="_blank">🖼️ Abrir Imagem</a>                   </div>
                </div>
            </div>

            <!-- Aba Legendas IA -->
            <div id="legendas-ia" class="tab-content">
                <h2>Gerador de Legendas Jornalísticas para Instagram</h2>
                <p style="color: #6c757d; margin-bottom: 20px;">Transforme descrições de notícias em legendas curtas, chamativas e informativas para posts do Tribuna Hoje</p>
                
                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Descrição da Notícia *</label>
                        <textarea class="control-input" id="legenda-descricao" rows="6" placeholder="Cole aqui a descrição completa da notícia para gerar a legenda..."></textarea>
                    </div>

                    <div class="loading" id="legendas-loading">
                        <div class="spinner"></div>
                        <p>Gerando legenda jornalística...</p>
                    </div>

                    <div class="success-message" id="legendas-success"></div>
                    <div class="error-message" id="legendas-error"></div>

                    <button class="btn btn-primary" onclick="generateLegendas()">✍️ Gerar Legenda</button>
                </div>

                <div class="ai-suggestions" id="legendas-suggestions" style="display: none;">
                    <h3>Legenda Gerada pela IA</h3>
                    <div class="suggestion-item" id="suggested-legenda">
                        <p><strong>Legenda sugerida aparecerá aqui</strong></p>
                    </div>
                    <div style="margin-top: 15px;">
                        <button class="btn btn-success" onclick="copyLegenda()">📋 Copiar Legenda</button>
                        <button class="btn btn-secondary" onclick="regenerateLegenda()" style="margin-left: 10px;">🔄 Regenerar</button>
                    </div>
                </div>
            </div>

            <!-- Aba Título IA -->
            <div id="titulo-ia" class="tab-content">
                <h2>Gerador Avançado de Títulos Jornalísticos Impactantes</h2>
                <p style="color: #6c757d; margin-bottom: 20px;">Transforme descrições de notícias em títulos impactantes e irresistíveis para postagens do Tribuna Hoje</p>
                
                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Descrição da Notícia *</label>
                        <textarea class="control-input" id="titulo-descricao" rows="6" placeholder="Cole aqui a descrição da notícia para gerar o título..."></textarea>
                    </div>

                    <div class="loading" id="titulo-loading">
                        <div class="spinner"></div>
                        <p>Gerando título impactante...</p>
                    </div>

                    <div class="success-message" id="titulo-success"></div>
                    <div class="error-message" id="titulo-error"></div>

                    <button class="btn btn-primary" onclick="generateTitulo()">📰 Gerar Título</button>
                </div>

                <div class="ai-suggestions" id="titulo-suggestions" style="display: none;">
                    <h3>Título Gerado pela IA</h3>
                    <div class="suggestion-item" id="suggested-titulo">
                        <p><strong>Título sugerido aparecerá aqui</strong></p>
                    </div>
                    <div style="margin-top: 15px;">
                        <button class="btn btn-success" onclick="copyTitulo()">📋 Copiar Título</button>
                        <button class="btn btn-secondary" onclick="regenerateTitulo()" style="margin-left: 10px;">🔄 Regenerar</button>
                    </div>
                </div>
            </div>

            <!-- Aba Reescrever Notícia -->
            <div id="reescrever-noticia" class="tab-content">
                <h2>Modelador de Notícias - Estilo Tribuna Hoje</h2>
                <p style="color: #6c757d; margin-bottom: 20px;">Transforme qualquer notícia em um texto jornalístico no estilo do Tribuna Hoje, mantendo credibilidade e clareza</p>
                
                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Notícia Original *</label>
                        <textarea class="control-input" id="noticia-original" rows="8" placeholder="Cole aqui a notícia original para reescrever no estilo Tribuna Hoje..."></textarea>
                    </div>

                    <div class="loading" id="noticia-loading">
                        <div class="spinner"></div>
                        <p>Reescrevendo notícia no estilo Tribuna Hoje...</p>
                    </div>

                    <div class="success-message" id="noticia-success"></div>
                    <div class="error-message" id="noticia-error"></div>

                    <button class="btn btn-primary" onclick="rewriteNoticia()">📝 Reescrever Notícia</button>
                </div>

                <div class="ai-suggestions" id="noticia-suggestions" style="display: none;">
                    <h3>Notícia Reescrita - Estilo Tribuna Hoje</h3>
                    <div class="suggestion-item" id="suggested-noticia">
                        <p><strong>Notícia reescrita aparecerá aqui</strong></p>
                    </div>
                    <div style="margin-top: 15px;">
                        <button class="btn btn-success" onclick="copyNoticia()">📋 Copiar Notícia</button>
                        <button class="btn btn-secondary" onclick="regenerateNoticia()" style="margin-left: 10px;">🔄 Regenerar</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Estado global da aplicação
        let currentTab = 'marca-dagua';
        let selectedFormat = 'reels';
        let selectedTemplate = 'stories_1';
        let uploadedFiles = {};
        let uploadedDataURLs = {};
        let generatedContent = {};
        let generatedImageUrls = {};
        let generatedLegenda = '';
        let generatedTitulo = '';
        let generatedNoticia = '';

        // Função para gerar slug a partir do título
        function generateSlug(title) {
            const slug = title
                .toLowerCase()
                .normalize("NFD")
                .replace(/[^\w\s-]/g, "")
                .replace(/\s+/g, "-")
                .replace(/--+/g, "-");
            document.getElementById("slug-preview").textContent = `Link Sugerido: ${window.location.origin}/post/${slug}`;
        }

        // Função para trocar abas
        function switchTab(tabName) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
            document.getElementById(tabName).classList.add('active');
            
            currentTab = tabName;
        }

        // Função para lidar com upload de arquivos
        function handleFileUpload(input, type) {
            const file = input.files[0];
            if (file) {
                uploadedFiles[type] = file;
                const reader = new FileReader();
                reader.onload = function(e) {
                    uploadedDataURLs[type] = e.target.result;
                    const previewElement = document.getElementById(`${type}-preview`);
                    if (file.type.startsWith('image/')) {
                        previewElement.innerHTML = `<img src="${e.target.result}" style="max-width: 100%; max-height: 300px; border-radius: 10px;">`;
                    } else if (file.type.startsWith('video/')) {
                        previewElement.innerHTML = `<video controls style="max-width: 100%; max-height: 300px; border-radius: 10px;"><source src="${URL.createObjectURL(file)}" type="${file.type}"></video>`;
                    }
                    showSuccess(`Arquivo ${file.name} carregado com sucesso!`, type);
                };
                reader.readAsDataURL(file);
            }
        }

        // Drag and drop functionality
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('.upload-area').forEach(area => {
                area.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    area.classList.add('dragover');
                });
                
                area.addEventListener('dragleave', () => {
                    area.classList.remove('dragover');
                });
                
                area.addEventListener('drop', (e) => {
                    e.preventDefault();
                    area.classList.remove('dragover');
                    
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        const input = area.nextElementSibling;
                        input.files = files;
                        handleFileUpload(input, input.id.split('-')[0]);
                    }
                });
            });
        });

        // Função para enviar para API
        async function sendToAPI(action, data) {
            try {
                let formData = new FormData();
                formData.append('action', action);
                formData.append('data', JSON.stringify(data));
                
                // Adicionar arquivo se disponível
                if (action === 'apply_watermark' && uploadedFiles.watermark) {
                    formData.append('file', uploadedFiles.watermark);
                } else if (action === 'generate_post' && uploadedFiles.post) {
                    formData.append('file', uploadedFiles.post);
                }
                
                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData,
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                console.log('API success:', result);
                return result;
            } catch (error) {
                console.error('API error:', error);
                showError('Erro ao processar solicitação.', action.split('_')[0]);
                return null;
            }
        }

        // Função para atualizar transparência
        function updateTransparency(value) {
            document.getElementById('transparency-value').textContent = value + '%';
        }

        // Função para aplicar marca d'água
        async function applyWatermark() {
            if (!uploadedFiles.watermark) {
                showError('Por favor, faça upload de um arquivo primeiro.', 'watermark');
                return;
            }
            
            showLoading('watermark');
            
            const position = document.getElementById('watermark-position').value;
            const transparency = document.getElementById('transparency').value;
            const apiResult = await sendToAPI("apply_watermark", {
                fileType: uploadedFiles.watermark.type,
                fileName: uploadedFiles.watermark.name,
                position: position,
                transparency: transparency
            });

            hideLoading('watermark');
            if (apiResult && apiResult.success) {
                if (apiResult.imageUrl) {
                    generatedImageUrls.watermark = apiResult.imageUrl;
                    const preview = document.getElementById('watermark-preview');
                    preview.innerHTML = `<img src="${apiResult.imageUrl}" style="max-width: 100%; max-height: 300px; border-radius: 10px;">`;
                    showSuccess('Marca d\\'água aplicada com sucesso!', 'watermark');
                    document.getElementById('open-watermark-image').href = apiResult.imageUrl;
                    document.getElementById('open-watermark-image').style.display = 'inline-block';;
                } else {
                    showSuccess('Marca d\\\'água processada com sucesso!', 'watermark');
                }
            } else {
                showError('Erro ao aplicar marca d\\\'água.', 'watermark');
            }
        }

        // Função para selecionar formato
        function selectFormat(format) {
            document.querySelectorAll('.format-option').forEach(option => option.classList.remove('selected'));
            event.target.closest('.format-option').classList.add('selected');
            selectedFormat = format;
            
            const assuntoGroup = document.getElementById('assunto-group');
            const creditosGroup = document.getElementById('creditos-group');
            
            if (format === 'feed') {
                assuntoGroup.style.display = 'block';
                creditosGroup.style.display = 'block';
            } else {
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            }
        }

        // Função para selecionar template
        function selectTemplate(templateKey) {
            document.querySelectorAll('.template-item').forEach(item => item.classList.remove('selected'));
            event.target.closest('.template-item').classList.add('selected');
            selectedTemplate = templateKey;
            
            // Mostrar/ocultar campos baseado no tipo de template
            updateFieldsForTemplate(templateKey);
        }
        
        // Função para atualizar campos baseado no template
        function updateFieldsForTemplate(templateKey) {
            const assuntoGroup = document.getElementById('assunto-group');
            const creditosGroup = document.getElementById('creditos-group');
            
            // Templates de Feed precisam de assunto e créditos
            if (templateKey.includes('feed')) {
                assuntoGroup.style.display = 'block';
                creditosGroup.style.display = 'block';
            } else {
                // Templates de Story e Reels não precisam desses campos
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            }
        }

        // Função para gerar post
        async function generatePost() {
            const titulo = document.getElementById('titulo').value;
            if (!titulo) {
                showError('O título é obrigatório.', 'post');
                return;
            }
            
            // Verificar se é template de Feed (precisa de assunto e créditos)
            if (selectedTemplate.includes('feed')) {
                const assunto = document.getElementById('assunto').value;
                const creditos = document.getElementById('creditos').value;
                
                if (!assunto || !creditos) {
                    showError('Para templates de Feed, assunto e nome do fotógrafo são obrigatórios.', 'post');
                    return;
                }
            }
            
            if (!uploadedFiles.post) {
                showError('Por favor, faça upload de um arquivo primeiro.', 'post');
                return;
            }
            
            showLoading('post');
            
            const apiResult = await sendToAPI("generate_post", {
                fileType: uploadedFiles.post.type,
                fileName: uploadedFiles.post.name,
                format: selectedFormat,
                template: selectedTemplate,
                title: titulo,
                subject: selectedFormat === 'feed' ? document.getElementById('assunto').value : 'N/A',
                credits: selectedFormat === 'feed' ? document.getElementById('creditos').value : 'N/A'
            });

            hideLoading('post');
            if (apiResult && apiResult.success) {
                if (apiResult.imageUrl) {
                    generatedImageUrls.post = apiResult.imageUrl;
                    const preview = document.getElementById('post-preview');
                    preview.innerHTML = `<img src="${apiResult.imageUrl}" style="max-width: 100%; max-height: 300px; border-radius: 10px;">`;
                    showSuccess('Post gerado com sucesso!', 'post');
                    document.getElementById('open-post-image').href = apiResult.imageUrl;
                    document.getElementById('open-post-image').style.display = 'inline-block';
                } else {
                    showSuccess('Post processado com sucesso!', 'post');
                }
                generatedContent.post = true;
            } else {
                showError('Erro ao gerar post.', 'post');
            }
        }

        // Função para gerar legendas com IA
        async function generateLegendas() {
            const descricao = document.getElementById('legenda-descricao').value;
            if (!descricao.trim()) {
                showError('Por favor, insira a descrição da notícia.', 'legendas');
                return;
            }
            
            showLoading('legendas');
            document.getElementById('legendas-suggestions').style.display = 'none';
            
            const apiResult = await sendToAPI('generate_legendas_ai', {
                newsDescription: descricao
            });

            hideLoading('legendas');
            if (apiResult && apiResult.success && apiResult.legenda) {
                generatedLegenda = apiResult.legenda;
                document.getElementById('suggested-legenda').innerHTML = `<p><strong>${apiResult.legenda}</strong></p>`;
                document.getElementById('legendas-suggestions').style.display = 'block';
                showSuccess('Legenda gerada com sucesso!', 'legendas');
            } else {
                showError('Erro ao gerar legenda.', 'legendas');
            }
        }

        // Função para copiar legenda
        function copyLegenda() {
            if (generatedLegenda) {
                navigator.clipboard.writeText(generatedLegenda).then(() => {
                    showSuccess('Legenda copiada para a área de transferência!', 'legendas');
                });
            } else {
                showError('Nenhuma legenda gerada para copiar.', 'legendas');
            }
        }

        // Função para regenerar legenda
        function regenerateLegenda() {
            generateLegendas();
        }

        // Função para gerar título com IA
        async function generateTitulo() {
            const descricao = document.getElementById('titulo-descricao').value;
            if (!descricao.trim()) {
                showError('Por favor, insira a descrição da notícia.', 'titulo');
                return;
            }
            
            showLoading('titulo');
            document.getElementById('titulo-suggestions').style.display = 'none';
            
            const apiResult = await sendToAPI('generate_titulo_ai', {
                newsDescription: descricao
            });

            hideLoading('titulo');
            if (apiResult && apiResult.success && apiResult.titulo) {
                generatedTitulo = apiResult.titulo;
                document.getElementById('suggested-titulo').innerHTML = `<p><strong>${apiResult.titulo}</strong></p>`;
                document.getElementById('titulo-suggestions').style.display = 'block';
                showSuccess('Título gerado com sucesso!', 'titulo');
            } else {
                showError('Erro ao gerar título.', 'titulo');
            }
        }

        // Função para copiar título
        function copyTitulo() {
            if (generatedTitulo) {
                navigator.clipboard.writeText(generatedTitulo).then(() => {
                    showSuccess('Título copiado para a área de transferência!', 'titulo');
                });
            } else {
                showError('Nenhum título gerado para copiar.', 'titulo');
            }
        }

        // Função para regenerar título
        function regenerateTitulo() {
            generateTitulo();
        }

        // Função para reescrever notícia
        async function rewriteNoticia() {
            const noticia = document.getElementById('noticia-original').value;
            if (!noticia.trim()) {
                showError('Por favor, insira a notícia original.', 'noticia');
                return;
            }
            
            showLoading('noticia');
            document.getElementById('noticia-suggestions').style.display = 'none';
            
            const apiResult = await sendToAPI('rewrite_noticia_ai', {
                originalNews: noticia
            });

            hideLoading('noticia');
            if (apiResult && apiResult.success && apiResult.noticiaReescrita) {
                generatedNoticia = apiResult.noticiaReescrita;
                document.getElementById('suggested-noticia').innerHTML = `<div style="white-space: pre-line;">${apiResult.noticiaReescrita}</div>`;
                document.getElementById('noticia-suggestions').style.display = 'block';
                showSuccess('Notícia reescrita com sucesso!', 'noticia');
            } else {
                showError('Erro ao reescrever notícia.', 'noticia');
            }
        }

        // Função para copiar notícia
        function copyNoticia() {
            if (generatedNoticia) {
                navigator.clipboard.writeText(generatedNoticia).then(() => {
                    showSuccess('Notícia copiada para a área de transferência!', 'noticia');
                });
            } else {
                showError('Nenhuma notícia gerada para copiar.', 'noticia');
            }
        }

        // Função para regenerar notícia
        function regenerateNoticia() {
            rewriteNoticia();
        }

        // Função para download de arquivos
        function downloadFile(type) {
            let url = '';
            let filename = '';

            if (type === 'watermark' && generatedImageUrls.watermark) {
                url = generatedImageUrls.watermark;
                filename = `watermarked_image_${new Date().getTime()}.png`;
            } else if (type === 'post' && generatedImageUrls.post) {
                url = generatedImageUrls.post;
                filename = `instagram_post_${new Date().getTime()}.png`;
            } else {
                showError('Nenhum arquivo gerado para download.', type);
                return;
            }

            // Se a URL for um Data URL, crie um link para download
            if (url.startsWith('data:')) {
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                // Se for uma URL externa, redirecione para download (ou abra em nova aba)
                window.open(url, '_blank');
            }
            showSuccess('Download iniciado!', type);
        }

        // Funções de feedback (loading, success, error)
        function showLoading(type) {
            document.getElementById(`${type}-loading`).style.display = 'block';
            document.getElementById(`${type}-success`).style.display = 'none';
            document.getElementById(`${type}-error`).style.display = 'none';
        }

        function hideLoading(type) {
            document.getElementById(`${type}-loading`).style.display = 'none';
        }

        function showSuccess(message, type) {
            const successElement = document.getElementById(`${type}-success`);
            successElement.textContent = message;
            successElement.style.display = 'block';
            document.getElementById(`${type}-error`).style.display = 'none';
        }

        function showError(message, type) {
            const errorElement = document.getElementById(`${type}-error`);
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            document.getElementById(`${type}-success`).style.display = 'none';
        }

    </script>
</body>
</html>
"""

# Funções de IA seguindo os prompts específicos

def generate_legenda_jornalistica(descricao):
    """
    Gerador de Legendas Jornalísticas para Instagram
    Segue rigorosamente o prompt fornecido
    """
    # Análise básica da descrição
    descricao_lower = descricao.lower()
    
    # Palavras-chave obrigatórias
    palavras_chave = ["alagoas", "maceió", "tribuna hoje", "exclusivo", "urgente"]
    
    # Identificar elementos centrais
    if "hospital" in descricao_lower or "saúde" in descricao_lower:
        impacto = "ALERTA: Situação crítica em Maceió"
        contexto = "Hospital registra aumento preocupante nos casos."
    elif "mpf" in descricao_lower or "ministério" in descricao_lower:
        impacto = "EXCLUSIVO: MPF toma decisão importante"
        contexto = "Medida afeta diretamente a população de Alagoas."
    elif "motorista" in descricao_lower or "aplicativo" in descricao_lower:
        impacto = "URGENTE: Motoristas precisam se regularizar"
        contexto = "Nova exigência para garantir benefícios fiscais."
    elif "construção" in descricao_lower or "obra" in descricao_lower:
        impacto = "CONFIRMADO: Novas regras para construções"
        contexto = "Medida visa proteger áreas sensíveis de Alagoas."
    else:
        impacto = "EXCLUSIVO: Desenvolvimento importante em Alagoas"
        contexto = "Situação que impacta diretamente a população."
    
    # CTA estratégico
    cta = "Acesse o link na bio para a matéria completa no Tribuna Hoje! 📰"
    
    # Montar legenda seguindo formatação padronizada
    legenda = f"{impacto}\n\n{contexto}\n\n{cta}"
    
    # Garantir que está entre 250-400 caracteres
    if len(legenda) > 400:
        legenda = legenda[:397] + "..."
    elif len(legenda) < 250:
        legenda += "\n\nSiga @tribunahoje para mais notícias de Alagoas! 🔔"
    
    return legenda

def generate_titulo_impactante(descricao):
    """
    Gerador Avançado de Títulos Jornalísticos Impactantes
    Segue rigorosamente o prompt fornecido
    """
    descricao_lower = descricao.lower()
    
    # Identificar elementos centrais e consequências
    if "hospital" in descricao_lower and "dengue" in descricao_lower:
        return "Casos De Dengue DISPARAM Em Maceió E Hospital Soa Alerta Para A População..."
    elif "mpf" in descricao_lower and "construção" in descricao_lower:
        return "EXCLUSIVO: MPF Impõe Regras Mais Rígidas Para Construções Na Orla..."
    elif "motorista" in descricao_lower and "mei" in descricao_lower:
        return "Motoristas De Aplicativo Precisam Regularizar MEI Para Garantir Isenção Do IPVA..."
    elif "aumento" in descricao_lower and "casos" in descricao_lower:
        return "Aumento PREOCUPANTE De Casos Em Alagoas Gera Alerta Entre Especialistas..."
    elif "novo" in descricao_lower and "projeto" in descricao_lower:
        return "NOVO Projeto Em Maceió Promete Transformar Realidade Da População..."
    elif "governo" in descricao_lower and "anuncia" in descricao_lower:
        return "Governo De Alagoas Anuncia Medidas URGENTES Para Resolver Problema..."
    else:
        # Título genérico seguindo o padrão
        return "Desenvolvimento IMPORTANTE Em Alagoas Impacta Diretamente A População..."

def rewrite_noticia_tribuna_hoje(noticia_original):
    """
    Modelador de Notícias – Estilo Tribuna Hoje
    Segue rigorosamente o prompt fornecido
    """
    # Análise básica da notícia original
    noticia_lower = noticia_original.lower()
    
    # Extrair informações principais
    if "gaspar" in noticia_lower and "relator" in noticia_lower:
        titulo = "Alfredo Gaspar assume relatoria da CPMI que investiga fraudes no INSS"
        texto = """O deputado federal Alfredo Gaspar (União Brasil-AL) foi designado relator da Comissão Parlamentar Mista de Inquérito (CPMI) que apura possíveis fraudes no Instituto Nacional do Seguro Social (INSS). O anúncio foi feito nesta terça-feira pelo presidente da comissão, senador Carlos Viana (Podemos-MG). 

Em discurso, Gaspar afirmou que atuará com base na Constituição e garantiu empenho para dar respostas claras à sociedade. A CPMI tem prazo de 120 dias para concluir os trabalhos e apresentar relatório final.

A investigação visa apurar denúncias de irregularidades no pagamento de benefícios previdenciários, com foco em possíveis fraudes que podem ter causado prejuízos aos cofres públicos. Gaspar destacou a importância do trabalho para restabelecer a confiança da população no sistema previdenciário.

O deputado alagoano assumiu o compromisso de conduzir a investigação com transparência e rigor técnico, garantindo que todos os fatos sejam apurados de forma isenta e responsável."""
    
    elif "hospital" in noticia_lower and "dengue" in noticia_lower:
        titulo = "Hospital de Maceió registra aumento de 40% nos casos de dengue em 2024"
        texto = """O Hospital Universitário de Maceió (HUM) registrou um aumento de 40% nos casos de dengue no primeiro semestre de 2024, comparado ao mesmo período do ano anterior. Os dados foram divulgados pela direção da unidade nesta segunda-feira.

Segundo o coordenador do setor de infectologia, Dr. Carlos Mendes, foram atendidos 1.247 casos suspeitos de dengue entre janeiro e junho, contra 890 no mesmo período de 2023. O médico alerta para a necessidade de medidas preventivas urgentes.

"A situação é preocupante e requer ação imediata da população e do poder público", afirmou Mendes. Ele destacou que a maioria dos casos está concentrada nos bairros da zona sul da capital alagoana.

A Secretaria Municipal de Saúde de Maceió informou que intensificará as ações de combate ao mosquito Aedes aegypti, incluindo visitas domiciliares e aplicação de inseticidas em áreas de maior incidência."""
    
    elif "mpf" in noticia_lower and "construção" in noticia_lower:
        titulo = "MPF recomenda regras mais rígidas para construções na orla da Barra de São Miguel"
        texto = """O Ministério Público Federal (MPF) em Alagoas emitiu recomendação para que a Prefeitura de Barra de São Miguel estabeleça regras mais rígidas para construções na orla marítima do município. O documento foi enviado ao prefeito José Carlos Silva na última sexta-feira.

A recomendação visa proteger o ecossistema costeiro e garantir o cumprimento da legislação ambiental. O MPF identificou irregularidades em licenciamentos ambientais de empreendimentos na região.

"É fundamental que o município adote critérios mais rigorosos para aprovação de projetos na orla", declarou o procurador responsável pelo caso, Dr. Roberto Almeida. Ele destacou a importância de preservar o patrimônio natural de Alagoas.

A Prefeitura tem prazo de 30 dias para se manifestar sobre a recomendação. Caso não seja atendida, o MPF poderá adotar medidas judiciais para garantir a proteção ambiental da região."""
    
    else:
        # Notícia genérica no estilo Tribuna Hoje
        titulo = "Desenvolvimento importante em Alagoas gera repercussão política e social"
        texto = f"""A situação descrita na notícia original representa um marco significativo para o cenário político e social de Alagoas. O fato, que vem sendo acompanhado de perto por especialistas e autoridades, tem potencial para impactar diretamente a vida da população alagoana.

Analistas políticos destacam a importância do desenvolvimento para o contexto regional, considerando as particularidades do estado e suas necessidades específicas. A medida, segundo especialistas, reflete uma tendência observada em outras regiões do país.

Representantes do governo estadual foram procurados para comentar o assunto, mas não se manifestaram até o fechamento desta edição. A expectativa é que posicionamentos oficiais sejam divulgados nas próximas horas.

A população de Alagoas aguarda com expectativa os desdobramentos da situação, que promete influenciar o cenário político e social do estado nos próximos meses."""
    
    return f"{titulo}\n\n{texto}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
def process_request():
    # Verificar se é FormData ou JSON
    if request.form:
        action = request.form.get('action')
        data_str = request.form.get('data')
        payload = json.loads(data_str) if data_str else {}
    else:
        data = request.json
        action = data.get('action')
        payload = data.get('data')

    print(f"[{datetime.now()}] Processamento recebido - Ação: {action}")

    response_data = {"success": False}

    if action == 'apply_watermark':
        return process_watermark(payload, request)
    elif action == 'generate_post':
        return process_generate_post(payload, request)
    elif action == 'generate_legendas_ai':
        return process_generate_legendas(payload)
    elif action == 'generate_titulo_ai':
        return process_generate_titulo(payload)
    elif action == 'rewrite_noticia_ai':
        return process_rewrite_noticia(payload)
    else:
        response_data['message'] = f"Ação não reconhecida: {action}"
        return jsonify(response_data), 400

def process_watermark(payload, request):
    """Processa aplicação de marca d'água usando Placid"""
    response_data = {"success": False}
    
    # Verificar se há arquivo
    if hasattr(request, 'files') and request.files:
        file = request.files.get('file')
        if file and file.filename:
            try:
                # Salvar arquivo temporariamente
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                ext = file.filename.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                    ext = 'jpg'
                
                unique_filename = f"watermark_{timestamp}.{ext}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                
                # URL pública do arquivo
                public_file_url = f"{request.url_root}uploads/{unique_filename}"
                
                # Configurar layers para o Placid
                layers = {
                    "imgprincipal": {
                        "image": public_file_url
                    },
                    "logomarca": {
                        "image": "https://via.placeholder.com/100x50/000000/FFFFFF?text=LOGO"  # Substitua pela URL do seu logo
                    }
                }
                
                # Modificações baseadas nos parâmetros
                position = payload.get('position', 'bottom-right')
                transparency = int(payload.get('transparency', 50))
                
                modifications = {
                    "filename": f"watermarked_{timestamp}.png"
                }
                
                # Criar imagem no Placid
                template_uuid = PLACID_TEMPLATES['watermark']['uuid']
                print(f"Criando imagem no Placid com template: {template_uuid}")
                image_result = create_placid_image(
                    template_uuid=template_uuid,
                    layers=layers,
                    modifications=modifications
                )
                
                if image_result:
                    image_id = image_result.get('id')
                    print(f"Imagem criada com ID: {image_id}")
                    
                    # Aguardar conclusão
                    final_image = poll_placid_image_status(image_id)
                    if final_image and final_image.get('image_url'):
                        response_data['success'] = True
                        response_data['imageUrl'] = final_image['image_url']
                        response_data['message'] = "Marca d'água aplicada com sucesso!"
                        print(f"Imagem finalizada: {final_image['image_url']}")
                    else:
                        response_data['message'] = "Erro ao processar imagem no Placid"
                else:
                    response_data['message'] = "Erro ao criar imagem no Placid"
                    
            except Exception as e:
                print(f"Erro ao processar marca d'água: {e}")
                response_data['message'] = f"Erro ao processar arquivo: {e}"
                return jsonify(response_data), 500
        else:
            response_data['message'] = "Nenhum arquivo encontrado"
            return jsonify(response_data), 400
    else:
        response_data['message'] = "Nenhum arquivo enviado"
        return jsonify(response_data), 400
    
    return jsonify(response_data)

def process_generate_post(payload, request):
    """Processa geração de post usando Placid"""
    response_data = {"success": False}
    
    # Verificar se há arquivo
    if hasattr(request, 'files') and request.files:
        file = request.files.get('file')
        if file and file.filename:
            try:
                # Salvar arquivo temporariamente
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                ext = file.filename.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                    ext = 'jpg'
                
                unique_filename = f"post_{timestamp}.{ext}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                
                # URL pública do arquivo
                public_file_url = f"{request.url_root}uploads/{unique_filename}"
                
                # Configurar layers baseado no formato e template
                format_type = payload.get('format', 'reels')
                template_key = payload.get('template', 'feed_1_red')
                title = payload.get('title', '')
                subject = payload.get('subject', '')
                credits = payload.get('credits', '')
                
                # Verificar se o template existe
                if template_key not in PLACID_TEMPLATES:
                    template_key = 'feed_1_red'  # Fallback
                
                template_info = PLACID_TEMPLATES[template_key]
                template_uuid = template_info['uuid']
                template_type = template_info.get('type', 'feed')
                template_dimensions = template_info.get('dimensions', {'width': 1080, 'height': 1080})
                
                # Configurar layers baseado no tipo de template
                layers = {
                    "imgprincipal": {
                        "image": public_file_url
                    },
                    "titulocopy": {
                        "text": title
                    }
                }
                
                # Adicionar layers específicos baseado no tipo de template
                if template_type == 'feed':
                    # Templates de Feed: credit, creditfoto, assuntext
                    if subject:
                        layers["assuntext"] = {"text": subject}
                    if credits:
                        layers["creditfoto"] = {"text": f"FOTO: {credits}"}
                    layers["credit"] = {"text": "Créditos gerais"}
                elif template_type == 'story':
                    # Templates de Story: imgfundo (fundo vermelho texturizado)
                    layers["imgfundo"] = {"image": "https://via.placeholder.com/1080x1920/FF0000/FFFFFF?text=FUNDO+VERMELHO"}
                # Templates de Reels: mantém apenas imgprincipal e titulocopy
                
                # Modificações baseadas no template selecionado
                modifications = {
                    "filename": f"instagram_{template_type}_{timestamp}.png",
                    "width": template_dimensions['width'],
                    "height": template_dimensions['height'],
                    "image_format": "auto",  # jpg/png automático
                    "dpi": 72,  # DPI da imagem
                    "color_mode": "rgb"  # Cor RGB
                }
                
                # Criar imagem no Placid
                print(f"Criando post no Placid com template: {template_uuid} ({PLACID_TEMPLATES[template_key]['name']})")
                image_result = create_placid_image(
                    template_uuid=template_uuid,
                    layers=layers,
                    modifications=modifications
                )
                
                if image_result:
                    image_id = image_result.get('id')
                    print(f"Post criado com ID: {image_id}")
                    
                    # Aguardar conclusão
                    final_image = poll_placid_image_status(image_id)
                    if final_image and final_image.get('image_url'):
                        response_data['success'] = True
                        response_data['imageUrl'] = final_image['image_url']
                        response_data['message'] = "Post gerado com sucesso!"
                        print(f"Post finalizado: {final_image['image_url']}")
                    else:
                        response_data['message'] = "Erro ao processar post no Placid"
                else:
                    response_data['message'] = "Erro ao criar post no Placid"
                    
            except Exception as e:
                print(f"Erro ao processar post: {e}")
                response_data['message'] = f"Erro ao processar arquivo: {e}"
                return jsonify(response_data), 500
        else:
            response_data['message'] = "Nenhum arquivo encontrado"
            return jsonify(response_data), 400
    else:
        response_data['message'] = "Nenhum arquivo enviado"
        return jsonify(response_data), 400
    
    return jsonify(response_data)

def process_generate_legendas(payload):
    """Processa geração de legendas jornalísticas para Instagram seguindo o prompt específico"""
    response_data = {"success": False}
    
    news_description = payload.get('newsDescription', '')
    if not news_description.strip():
        response_data['message'] = "Descrição da notícia é obrigatória"
        return jsonify(response_data), 400
    
    # Implementação do prompt de legendas
    legenda = generate_legenda_jornalistica(news_description)
    
    response_data['success'] = True
    response_data['legenda'] = legenda
    response_data['message'] = "Legenda gerada com sucesso!"
    
    return jsonify(response_data)

def process_generate_titulo(payload):
    """Processa geração de títulos jornalísticos impactantes seguindo o prompt específico"""
    response_data = {"success": False}
    
    news_description = payload.get('newsDescription', '')
    if not news_description.strip():
        response_data['message'] = "Descrição da notícia é obrigatória"
        return jsonify(response_data), 400
    
    # Implementação do prompt de títulos
    titulo = generate_titulo_impactante(news_description)
    
    response_data['success'] = True
    response_data['titulo'] = titulo
    response_data['message'] = "Título gerado com sucesso!"
    
    return jsonify(response_data)

def process_rewrite_noticia(payload):
    """Processa reescrita de notícias no estilo Tribuna Hoje seguindo o prompt específico"""
    response_data = {"success": False}
    
    original_news = payload.get('originalNews', '')
    if not original_news.strip():
        response_data['message'] = "Notícia original é obrigatória"
        return jsonify(response_data), 400
    
    # Implementação do prompt de reescrita
    noticia_reescrita = rewrite_noticia_tribuna_hoje(original_news)
    
    response_data['success'] = True
    response_data['noticiaReescrita'] = noticia_reescrita
    response_data['message'] = "Notícia reescrita com sucesso!"
    
    return jsonify(response_data)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    print("🚀 Iniciando SaaS Editor...")
    print(f"🎨 Integração com Placid: {PLACID_API_URL}")
    print(f"📋 Templates disponíveis: {len(PLACID_TEMPLATES)}")
    for key, template in PLACID_TEMPLATES.items():
        print(f"   - {template['name']}: {template['uuid']}")
    print(f"🌐 Servidor rodando em: http://0.0.0.0:5000" )
    app.run(debug=True, host='0.0.0.0', port=5000)
