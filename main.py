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

# Configuração da API Groq
GROQ_API_KEY = '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'
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Verificar se a chave da API está configurada
if not GROQ_API_KEY or GROQ_API_KEY == 'your-api-key-here':
    print("⚠️ AVISO: Chave da API Groq não configurada. Usando modo fallback.")
    GROQ_API_AVAILABLE = False
else:
    GROQ_API_AVAILABLE = True

# Templates disponíveis
PLACID_TEMPLATES = {
    'watermark': {
        'uuid': 'x9jxylt4vx2x0',  # UUID específico para watermark
        'name': 'Marca d\'Água',
        'description': 'Template para aplicar marca d\'água',
        'type': 'watermark',
        'dimensions': {'width': 1200, 'height': 1200}
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
    'watermark1': {
        'uuid': '1wubmwdwwturf',
        'name': 'Watermark1',
        'description': 'Template para Watermark',
        'type': 'watermark',
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

# Prompts das IAs
AI_PROMPTS = {
    'legendas': """Gerador de Legendas Jornalísticas para Instagram

Você é um jornalista especialista em copy para redes sociais, capaz de transformar descrições de notícias em legendas curtas, chamativas e informativas para posts de Instagram do jornal Tribuna Hoje. Sempre que receber uma descrição de notícia, siga rigorosamente estas instruções:

Análise Completa: Identifique os elementos centrais da notícia (quem, o quê, onde e consequência mais relevante).

Impacto Inicial: Comece a legenda com uma chamada forte e clara, destacando a informação mais importante ou surpreendente da descrição.

Contexto Curto: Acrescente em seguida 1 a 2 frases curtas que resumam o contexto, de forma simples e acessível.

Tom Jornalístico: Mantenha a credibilidade, clareza e objetividade, sem sensacionalismo exagerado.

Palavras-Chave Obrigatórias: Inclua naturalmente termos que reforcem relevância jornalística, como "Alagoas", "Maceió", "Tribuna Hoje", "exclusivo", "urgente".

CTA Estratégico: Finalize sempre com um convite à ação (CTA), incentivando o público a seguir o perfil, comentar ou acessar o link na bio para a matéria completa.

Formatação Padronizada:

Primeira letra maiúscula em todas as frases.

Parágrafos curtos e claros (1 a 3 linhas cada).

Extensão Ideal: A legenda deve ter entre 250 e 400 caracteres, curta o bastante para leitura rápida, mas informativa.

Evite Repetições: Nunca copie literalmente a descrição original; sempre reescreva com nova estrutura e escolha de palavras.

Resposta Direta: Retorne SOMENTE a legenda pronta para a foto, sem comentários, explicações ou qualquer texto adicional.""",

    'titulo': """Gerador Avançado de Títulos Jornalísticos Impactantes

Você é um jornalista especialista em copy de Instagram para jornalismo, capaz de transformar descrições de notícias em títulos impactantes e irresistíveis para postagens no feed da Tribuna Hoje. Sempre que receber uma descrição, siga rigorosamente estas instruções:

Análise Completa: Identifique claramente os elementos centrais da descrição (quem, o quê, onde e consequência mais relevante).

Alteração de Foco: Comece pelo dado mais impactante ou pela consequência mais forte da notícia, ainda que isso esteja apenas implícito ou no final da descrição original.

Inversão Dramática: Traga o clímax ou a informação mais chamativa para o início do título e só depois apresente o contexto, mantendo fluidez e clareza.

Palavras Obrigatórias: Sempre inclua naturalmente termos que reforcem credibilidade e alcance jornalístico, como: "Tribuna Hoje", "Alagoas", "Capital", "Interior", "Urgente", "Exclusivo", "Confirmado".

Detalhe Exclusivo: Acrescente obrigatoriamente uma reviravolta ou um dado intrigante não explicitado literalmente na descrição.

Ênfase Visual: Destaque até DUAS palavras de impacto em MAIÚSCULAS para chamar atenção imediata.

Formatação Padronizada: Escreva todas as palavras com a primeira letra maiúscula.

Limite Rigoroso: O título deve ter obrigatoriamente entre 80 e 90 caracteres, contando espaços e pontuação. Se ultrapassar 90, corte exatamente na palavra onde exceder e finalize imediatamente com reticências (...).

Suspense Garantido: Termine sempre com reticências (...) para maximizar curiosidade e engajamento.

Evite Repetições: NUNCA copie literalmente a descrição original; sempre reescreva com nova estrutura.

Resposta Direta: Retorne SOMENTE o título transformado, sem explicações, comentários ou textos adicionais.

Exemplo de Referência:

Descrição original: "Hospital de Maceió registra aumento nos casos de dengue."
Título revisado: "Casos De Dengue DISPARAM Em Maceió E Hospital Soa Alerta Para A População..."

Descrição original: "MPF recomenda regras mais rígidas para construções na orla da Barra de São Miguel."
Título revisado: "EXCLUSIVO: MPF Impõe Regras Mais Rígidas Para Construções Na Orla Da Barra..."

Descrição original: "Motoristas de aplicativo devem manter MEI regular para garantir isenção do IPVA."
Título revisado: "Motoristas De Aplicativo Precisam Regularizar MEI Para Garantir Isenção Do IPVA...""",

    'reescrita': """Modelador de Notícias – Estilo Tribuna Hoje

Você é um jornalista sênior com mais de 10 anos de experiência em redação política e jornalismo sério. Sua função é transformar qualquer notícia recebida em um texto jornalístico no estilo do Tribuna Hoje, mantendo credibilidade, clareza e a identidade de um veículo tradicional.

Regras:

Tonalidade:

Séria, institucional e objetiva.

Imparcial, mas crítica quando necessário.

Nada de sensacionalismo ou clickbait.

Estrutura da Notícia:

Lide (primeiro parágrafo): traga logo a informação principal (quem, o quê, quando, onde e por quê).

Desenvolvimento: acrescente contexto político, social e histórico que ajude o leitor a entender o impacto da notícia.

Citações: sempre que possível, mantenha falas de autoridades ou dados oficiais.

Conclusão: indique próximos passos, desdobramentos ou relevância para Alagoas, o Brasil ou o cenário político.

Estilo Tribuna Hoje:

Clareza e objetividade acima de tudo.

Uso de linguagem jornalística padrão, sem gírias.

Dar foco ao impacto político, social ou econômico da notícia.

Tratar a informação com responsabilidade, reforçando credibilidade.

Formatação:

Título claro e direto, sem exageros.

Subtítulo opcional para complementar contexto.

Texto corrido, entre 3 e 6 parágrafos.

Exemplo de Transformação:

Notícia bruta: "Gaspar foi escolhido relator da comissão que vai investigar fraudes no INSS."

Modelada para Tribuna Hoje:
Título: Alfredo Gaspar assume relatoria da CPMI que investiga fraudes no INSS
Texto: O deputado federal Alfredo Gaspar (União Brasil-AL) foi designado relator da Comissão Parlamentar Mista de Inquérito (CPMI) que apura possíveis fraudes no Instituto Nacional do Seguro Social (INSS). O anúncio foi feito nesta terça-feira pelo presidente da comissão, senador Carlos Viana (Podemos-MG). Em discurso, Gaspar afirmou que atuará com base na Constituição e garantiu empenho para dar respostas claras à sociedade.

Instrução Final

Sempre que receber uma notícia ou descrição, reescreva-a no formato da Tribuna Hoje, mantendo credibilidade, clareza e impacto jornalístico.
Retorne apenas a versão final da notícia modelada (título + texto)."""
}

# Função auxiliar para chamar a API Groq
def call_groq_api(prompt, content, max_tokens=1000):
    """
    Chama a API Groq com o prompt e conteúdo fornecidos usando requests
    """
    # Verificar se a API está disponível
    if not GROQ_API_AVAILABLE:
        print("API Groq não disponível, usando fallback")
        return None
    
    try:
        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Truncar conteúdo se muito longo (limite de ~8000 caracteres)
        if len(content) > 4000:
            content = content[:4000] + "..."
        
        full_prompt = f"{prompt}\n\nConteúdo para processar:\n{content}"
        
        # Truncar prompt se muito longo
        if len(full_prompt) > 8000:
            full_prompt = full_prompt[:8000] + "..."
        
        # Payload simplificado para evitar erros
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "model": "llama-3.1-8b-instant",  # Modelo menor e mais rápido
            "max_tokens": min(max_tokens, 500),  # Limitar max_tokens
            "temperature": 0.7
        }
        
        print(f"DEBUG - Enviando para Groq (tamanho: {len(full_prompt)} chars)")
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)
        
        print(f"DEBUG - Status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ERRO - Status não é 200: {response.status_code}")
            print(f"ERRO - Response: {response.text}")
            return None
            
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
        
    except Exception as e:
        print(f"Erro ao chamar API Groq: {e}")
        return None

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
        'create_now': True  # Criar imediatamente
    }
    
    if modifications:
        payload['modifications'] = modifications
    
    if webhook_success:
        payload['webhook_success'] = webhook_success
    
    try:
        print(f"DEBUG - Enviando para Placid: {PLACID_API_URL}")
        print(f"DEBUG - Template UUID: {payload.get('template_uuid', 'N/A')}")
        print(f"DEBUG - Layers: {payload.get('layers', {})}")
        
        response = requests.post(PLACID_API_URL, json=payload, headers=headers)
        print(f"DEBUG - Status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ERRO - Status não é 200: {response.status_code}")
            print(f"ERRO - Response: {response.text}")
            return None
            
        response.raise_for_status()
        result = response.json()
        print(f"DEBUG - Resposta JSON: {result}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao criar imagem no Placid: {e}")
        if 'response' in locals():
            print(f"ERRO - Status: {response.status_code}")
            print(f"ERRO - Response: {response.text}")
        return None
    except Exception as e:
        print(f"ERRO inesperado: {e}")
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
                <button class="tab-button active" onclick="switchTab('gerar-posts')">📱 Gerar Posts</button>
                <button class="tab-button" onclick="switchTab('noticia-titulo')">🤖 Notícia e Título</button>
                <button class="tab-button" onclick="switchTab('legendas')">✍️ Legendas IA</button>
                <button class="tab-button" onclick="switchTab('reescrever-noticia')">📝 Reescrever Notícia</button>
            </div>


            <!-- Aba Gerar Posts -->
            <div id="gerar-posts" class="tab-content active">
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
                        <div class="format-option" onclick="selectFormat('watermark')">
                            <h4>🏷️ Marca d'Água</h4>
                            <p>Aplicar marca d'água</p>
                        </div>
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
                        <div class="template-item" onclick="selectTemplate('watermark1')">
                            <div class="template-preview">🔴</div>
                            <p>WaterMark1</p>
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

            <!-- Aba Notícia e Título -->
            <div id="noticia-titulo" class="tab-content">
                <h2>Gerar Título com IA</h2>
                
                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Cole o texto da notícia ou link</label>
                        <textarea class="control-input" id="noticia-texto" rows="6" placeholder="Cole aqui o texto da notícia ou o link para análise..."></textarea>
                    </div>

                    <div class="loading" id="title-loading">
                        <div class="spinner"></div>
                        <p>Analisando conteúdo e gerando título...</p>
                    </div>

                    <div class="success-message" id="title-success"></div>
                    <div class="error-message" id="title-error"></div>

                    <button class="btn btn-primary" onclick="generateTitle()">🤖 Gerar Título</button>
                </div>

                <div class="ai-suggestions" id="title-suggestions" style="display: none;">
                    <h3>Título Sugerido pela IA</h3>
                    <div class="suggestion-item" id="suggested-title">
                        <p><strong>Título sugerido aparecerá aqui</strong></p>
                    </div>
                    <div style="margin-top: 15px;">
                        <button class="btn btn-success" onclick="acceptTitle()">✅ Aceitar Sugestão</button>
                        <button class="btn btn-secondary" onclick="rejectTitle()" style="margin-left: 10px;">❌ Recusar</button>
                    </div>
                </div>

                <div class="controls-section" id="manual-title" style="display: none;">
                    <div class="control-group">
                        <label class="control-label">Digite o título manualmente</label>
                        <input type="text" class="control-input" id="manual-title-input" placeholder="Digite seu título personalizado">
                    </div>
                    <button class="btn btn-primary" onclick="saveManualTitle()">💾 Salvar Título</button>
                </div>
            </div>

            <!-- Aba Legendas -->
            <div id="legendas" class="tab-content">
                <h2>Gerar Legendas com IA</h2>
                
                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Notícia, resumo ou link</label>
                        <textarea class="control-input" id="legenda-texto" rows="4" placeholder="Cole o conteúdo para gerar legendas..."></textarea>
                    </div>
                    <div class="control-group">
                        <label class="control-label">Prompt personalizado (opcional)</label>
                        <input type="text" class="control-input" id="custom-prompt" placeholder="Ex: Gere legendas informais e engajantes">
                    </div>

                    <div class="loading" id="captions-loading">
                        <div class="spinner"></div>
                        <p>Gerando legendas personalizadas...</p>
                    </div>

                    <div class="success-message" id="caption-success"></div>
                    <div class="error-message" id="caption-error"></div>

                    <button class="btn btn-primary" onclick="generateCaptions()">🤖 Gerar Legendas</button>
                </div>

                <div class="ai-suggestions" id="captions-suggestions" style="display: none;">
                    <h3>Legendas Sugeridas (clique para copiar)</h3>
                    <div id="captions-list">
                        <!-- Legendas serão inseridas aqui dinamicamente -->
                    </div>
                </div>
            </div>

            <!-- Aba Reescrever Notícia -->
            <div id="reescrever-noticia" class="tab-content">
                <h2>Reescrever Notícia com IA</h2>
                
                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Cole o texto da notícia original</label>
                        <textarea class="control-input" id="noticia-original" rows="6" placeholder="Cole aqui o texto da notícia que deseja reescrever no estilo Tribuna Hoje..."></textarea>
                    </div>

                    <div class="loading" id="rewrite-loading">
                        <div class="spinner"></div>
                        <p>Reescrevendo notícia no estilo Tribuna Hoje...</p>
                    </div>

                    <div class="success-message" id="rewrite-success"></div>
                    <div class="error-message" id="rewrite-error"></div>

                    <button class="btn btn-primary" onclick="rewriteNews()">📝 Reescrever Notícia</button>
                </div>

                <div class="ai-suggestions" id="rewrite-suggestions" style="display: none;">
                    <h3>Notícia Reescrita no Estilo Tribuna Hoje</h3>
                    <div class="suggestion-item" id="rewritten-news">
                        <h4 id="rewritten-title">Título aparecerá aqui</h4>
                        <p id="rewritten-text">Texto reescrito aparecerá aqui</p>
                    </div>
                    <div style="margin-top: 15px;">
                        <button class="btn btn-success" onclick="acceptRewrittenNews()">✅ Aceitar Versão</button>
                        <button class="btn btn-secondary" onclick="rejectRewrittenNews()" style="margin-left: 10px;">❌ Recusar</button>
                    </div>
                </div>

                <div class="controls-section" id="manual-rewrite" style="display: none;">
                    <div class="control-group">
                        <label class="control-label">Título personalizado</label>
                        <input type="text" class="control-input" id="manual-title-rewrite" placeholder="Digite o título personalizado">
                    </div>
                    <div class="control-group">
                        <label class="control-label">Texto personalizado</label>
                        <textarea class="control-input" id="manual-text-rewrite" rows="6" placeholder="Digite o texto personalizado"></textarea>
                    </div>
                    <button class="btn btn-primary" onclick="saveManualRewrite()">💾 Salvar Versão Personalizada</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Estado global da aplicação
        let currentTab = 'gerar-posts';
        let selectedFormat = 'reels';
        let selectedTemplate = 'stories_1';
        let uploadedFiles = {};
        let uploadedDataURLs = {};
        let generatedContent = {};
        let generatedImageUrls = {};

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

        // Função para verificar status da imagem no Placid
        async function checkImageStatus(imageId, type) {
            try {
                const response = await fetch(`/api/check-image/${imageId}`);
                const result = await response.json();
                
                if (result.success && result.status === 'finished' && result.imageUrl) {
                    generatedImageUrls[type] = result.imageUrl;
                    const preview = document.getElementById(`${type}-preview`);
                    preview.innerHTML = `<img src="${result.imageUrl}" style="max-width: 100%; max-height: 300px; border-radius: 10px;">`;
                    showSuccess(`${type === 'watermark' ? 'Marca d\\'água' : 'Post'} finalizado com sucesso!`, type);
                    const openButton = document.getElementById(`open-${type}-image`);
                    if (openButton) {
                        openButton.href = result.imageUrl;
                        openButton.style.display = 'inline-block';
                    }
                } else if (result.success && result.status === 'processing') {
                    // Continuar verificando a cada 3 segundos
                    setTimeout(() => checkImageStatus(imageId, type), 3000);
                } else {
                    showError(`Erro ao processar ${type === 'watermark' ? 'marca d\\'água' : 'post'}.`, type);
                }
            } catch (error) {
                console.error('Erro ao verificar status:', error);
                showError(`Erro ao verificar status do ${type === 'watermark' ? 'watermark' : 'post'}.`, type);
            }
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
                console.log(`DEBUG - Enviando para API: ${action}`, data);
                
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
                
                console.log(`DEBUG - Response status: ${response.status}`);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error(`DEBUG - HTTP error: ${response.status} - ${errorText}`);
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();
                console.log('DEBUG - API success:', result);
                return result;
            } catch (error) {
                console.error('DEBUG - API error:', error);
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
            
            // Watermark só precisa da imagem
            
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
                    document.getElementById('open-watermark-image').style.display = 'inline-block';
                } else if (apiResult.imageId) {
                    showSuccess('Marca d\\'água em processamento. Aguarde...', 'watermark');
                    // Verificar status periodicamente
                    checkImageStatus(apiResult.imageId, 'watermark');
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
            } else if (format === 'watermark') {
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
                // Para watermark, selecionar automaticamente o template de watermark
                selectTemplate('watermark');
            } else {
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            }
        }

        // Função para selecionar template
        function selectTemplate(templateKey) {
            document.querySelectorAll('.template-item').forEach(item => item.classList.remove('selected'));
            
            // Se chamada programaticamente, selecionar pelo templateKey
            if (event && event.target) {
                event.target.closest('.template-item').classList.add('selected');
            } else {
                // Buscar o elemento pelo templateKey
                const templateElement = document.querySelector(`[onclick="selectTemplate('${templateKey}')"]`);
                if (templateElement) {
                    templateElement.classList.add('selected');
                }
            }
            
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
            } else if (templateKey === 'watermark') {
                // Template de watermark só precisa da imagem
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            } else {
                // Templates de Story e Reels não precisam desses campos
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            }
        }

        // Função para gerar post
        async function generatePost() {
            // Para watermark, não precisa de título
            if (selectedTemplate !== 'watermark') {
                const titulo = document.getElementById('titulo').value;
                if (!titulo) {
                    showError('O título é obrigatório.', 'post');
                    return;
                }
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
            
            // Usar sempre a mesma API para todos os templates
            const apiAction = 'generate_post';
            
            const apiResult = await sendToAPI(apiAction, {
                fileType: uploadedFiles.post.type,
                fileName: uploadedFiles.post.name,
                format: selectedFormat,
                template: selectedTemplate,
                title: selectedTemplate === 'watermark' ? '' : document.getElementById('titulo').value,
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
                } else if (apiResult.imageId) {
                    showSuccess('Post em processamento. Aguarde...', 'post');
                    // Verificar status periodicamente
                    checkImageStatus(apiResult.imageId, 'post');
                } else {
                    showSuccess('Post processado com sucesso!', 'post');
                }
                generatedContent.post = true;
            } else {
                showError('Erro ao gerar post.', 'post');
            }
        }

        // Função para gerar título com IA
        async function generateTitle() {
            const texto = document.getElementById('noticia-texto').value;
            if (!texto.trim()) {
                showError('Por favor, insira o texto da notícia ou link.', 'title');
                return;
            }
            
            showLoading('title');
            document.getElementById('title-suggestions').style.display = 'none';
            
            const apiResult = await sendToAPI('generate_title_ai', {
                newsContent: texto
            });

            hideLoading('title');
            if (apiResult && apiResult.success && apiResult.suggestedTitle) {
                document.getElementById('suggested-title').innerHTML = `<p><strong>${apiResult.suggestedTitle}</strong></p>`;
                document.getElementById('title-suggestions').style.display = 'block';
                showSuccess('Título gerado com sucesso!', 'title');
            } else {
                showError('Erro ao gerar título.', 'title');
            }
        }

        // Função para aceitar título sugerido
        function acceptTitle() {
            const suggestedTitle = document.getElementById('suggested-title').textContent.replace('Título sugerido aparecerá aqui', '').trim();
            document.getElementById('manual-title-input').value = suggestedTitle;
            document.getElementById('manual-title').style.display = 'block';
            document.getElementById('title-suggestions').style.display = 'none';
            showSuccess('Título aceito e pronto para salvar!', 'title');
        }

        // Função para recusar título sugerido
        function rejectTitle() {
            document.getElementById('manual-title').style.display = 'block';
            document.getElementById('title-suggestions').style.display = 'none';
            document.getElementById('manual-title-input').value = '';
            showError('Título recusado. Digite um título manualmente.', 'title');
        }

        // Função para salvar título manual
        async function saveManualTitle() {
            const manualTitle = document.getElementById('manual-title-input').value;
            if (!manualTitle.trim()) {
                showError('Por favor, digite um título.', 'title');
                return;
            }
            
            showLoading('title');
            const apiResult = await sendToAPI('save_manual_title', {
                manualTitle: manualTitle
            });

            hideLoading('title');
            if (apiResult && apiResult.success) {
                showSuccess('Título salvo com sucesso!', 'title');
                generatedContent.title = manualTitle;
            } else {
                showError('Erro ao salvar título.', 'title');
            }
        }

        // Função para gerar legendas com IA
        async function generateCaptions() {
            const texto = document.getElementById('legenda-texto').value;
            const customPrompt = document.getElementById('custom-prompt').value;
            if (!texto.trim()) {
                showError('Por favor, insira o conteúdo para gerar legendas.', 'caption');
                return;
            }
            
            console.log('DEBUG - Iniciando geração de legendas para:', texto.substring(0, 100));
            
            showLoading('caption');
            document.getElementById('captions-suggestions').style.display = 'none';

            const apiResult = await sendToAPI('generate_captions_ai', {
                content: texto,
                customPrompt: customPrompt
            });

            console.log('DEBUG - Resultado da API:', apiResult);

            hideLoading('caption');
            if (apiResult && apiResult.success && apiResult.captions) {
                console.log('DEBUG - Legendas recebidas:', apiResult.captions.length);
                const captionsList = document.getElementById('captions-list');
                captionsList.innerHTML = '';
                apiResult.captions.forEach((caption, index) => {
                    console.log(`DEBUG - Processando legenda ${index + 1}:`, caption.substring(0, 50));
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    div.textContent = caption;
                    div.onclick = () => navigator.clipboard.writeText(caption).then(() => alert('Legenda copiada!'));
                    captionsList.appendChild(div);
                });
                document.getElementById('captions-suggestions').style.display = 'block';
                showSuccess('Legendas geradas com sucesso!', 'caption');
            } else {
                console.log('DEBUG - Erro na geração de legendas:', apiResult);
                showError('Erro ao gerar legendas.', 'caption');
            }
        }

        // Função para reescrever notícia com IA
        async function rewriteNews() {
            const texto = document.getElementById('noticia-original').value;
            if (!texto.trim()) {
                showError('Por favor, insira o texto da notícia original.', 'rewrite');
                return;
            }
            
            showLoading('rewrite');
            document.getElementById('rewrite-suggestions').style.display = 'none';

            const apiResult = await sendToAPI('rewrite_news_ai', {
                newsContent: texto
            });

            hideLoading('rewrite');
            if (apiResult && apiResult.success && apiResult.rewrittenNews) {
                const rewrittenNews = apiResult.rewrittenNews;
                document.getElementById('rewritten-title').textContent = rewrittenNews.titulo;
                document.getElementById('rewritten-text').textContent = rewrittenNews.texto;
                document.getElementById('rewrite-suggestions').style.display = 'block';
                showSuccess('Notícia reescrita com sucesso!', 'rewrite');
            } else {
                showError('Erro ao reescrever notícia.', 'rewrite');
            }
        }

        // Função para aceitar notícia reescrita
        function acceptRewrittenNews() {
            const rewrittenTitle = document.getElementById('rewritten-title').textContent;
            const rewrittenText = document.getElementById('rewritten-text').textContent;
            
            document.getElementById('manual-title-rewrite').value = rewrittenTitle;
            document.getElementById('manual-text-rewrite').value = rewrittenText;
            document.getElementById('manual-rewrite').style.display = 'block';
            document.getElementById('rewrite-suggestions').style.display = 'none';
            showSuccess('Notícia aceita e pronta para salvar!', 'rewrite');
        }

        // Função para recusar notícia reescrita
        function rejectRewrittenNews() {
            document.getElementById('manual-rewrite').style.display = 'block';
            document.getElementById('rewrite-suggestions').style.display = 'none';
            document.getElementById('manual-title-rewrite').value = '';
            document.getElementById('manual-text-rewrite').value = '';
            showError('Notícia recusada. Digite uma versão personalizada.', 'rewrite');
        }

        // Função para salvar notícia reescrita manual
        async function saveManualRewrite() {
            const manualTitle = document.getElementById('manual-title-rewrite').value;
            const manualText = document.getElementById('manual-text-rewrite').value;
            
            if (!manualTitle.trim() || !manualText.trim()) {
                showError('Por favor, preencha título e texto.', 'rewrite');
                return;
            }
            
            showLoading('rewrite');
            const apiResult = await sendToAPI('save_manual_rewrite', {
                manualTitle: manualTitle,
                manualText: manualText
            });

            hideLoading('rewrite');
            if (apiResult && apiResult.success) {
                showSuccess('Notícia reescrita salva com sucesso!', 'rewrite');
                generatedContent.rewrite = { title: manualTitle, text: manualText };
            } else {
                showError('Erro ao salvar notícia reescrita.', 'rewrite');
            }
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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/test-placid')
def test_placid():
    """Testa a conexão com a API do Placid"""
    try:
        # Teste simples com template conhecido
        test_payload = {
            'template_uuid': 'qe0qo74vbrgxe',  # feed_1_red
            'layers': {
                'imgprincipal': {
                    'image': 'https://via.placeholder.com/1200x1200/FF0000/FFFFFF?text=TESTE'
                }
            },
            'create_now': True
        }
        
        headers = {
            'Authorization': f'Bearer {PLACID_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        print(f"TESTE - Enviando para Placid: {test_payload}")
        response = requests.post(PLACID_API_URL, json=test_payload, headers=headers)
        print(f"TESTE - Status: {response.status_code}")
        print(f"TESTE - Response: {response.text}")
        
        if response.status_code == 200:
            return f"✅ Placid funcionando! Status: {response.status_code}<br>Response: {response.text}"
        else:
            return f"❌ Erro no Placid! Status: {response.status_code}<br>Response: {response.text}"
            
    except Exception as e:
        return f"❌ Erro na conexão: {e}"

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
    elif action == 'generate_title_ai':
        return process_generate_title(payload)
    elif action == 'generate_captions_ai':
        return process_generate_captions(payload)
    elif action == 'rewrite_news_ai':
        return process_rewrite_news(payload)
    elif action == 'save_manual_rewrite':
        return process_save_rewrite(payload)
    elif action == 'save_manual_title':
        return process_save_title(payload)
    else:
        response_data['message'] = f"Ação não reconhecida: {action}"
        return jsonify(response_data), 400

def process_watermark(payload, request):
    """Processa aplicação de marca d'água usando Placid - usando a mesma lógica dos outros templates"""
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
                
                # Usar a mesma lógica dos outros templates
                template_key = 'watermark'
                template_info = PLACID_TEMPLATES[template_key]
                template_uuid = template_info['uuid']
                template_type = template_info.get('type', 'watermark')
                template_dimensions = template_info.get('dimensions', {'width': 1080, 'height': 1080})
                
                # Configurar layers - apenas imgprincipal para watermark
                layers = {
                    "imgprincipal": {
                        "image": public_file_url
                    }
                }
                
                # Modificações baseadas no template selecionado (mesma lógica dos outros templates)
                modifications = {
                    "filename": f"watermark_{timestamp}.png",
                    "width": template_dimensions['width'],
                    "height": template_dimensions['height'],
                    "image_format": "auto",  # jpg/png automático
                    "dpi": 72,  # DPI da imagem
                    "color_mode": "rgb"  # Cor RGB
                }
                
                # Criar imagem no Placid (mesma lógica dos outros templates)
                print(f"Criando watermark no Placid com template: {template_uuid} ({PLACID_TEMPLATES[template_key]['name']})")
                image_result = create_placid_image(
                    template_uuid=template_uuid,
                    layers=layers,
                    modifications=modifications
                )
                
                if image_result:
                    image_id = image_result.get('id')
                    print(f"Watermark criado com ID: {image_id}")
                    
                    # Verificar se a imagem já está pronta (create_now: True)
                    if image_result.get('image_url'):
                        response_data['success'] = True
                        response_data['imageUrl'] = image_result['image_url']
                        response_data['message'] = "Marca d'água aplicada com sucesso!"
                        print(f"Watermark finalizado: {image_result['image_url']}")
                    else:
                        # Se não estiver pronta, retornar o ID para verificação posterior
                        response_data['success'] = True
                        response_data['imageId'] = image_id
                        response_data['message'] = "Watermark em processamento. Use o ID para verificar status."
                        print(f"Watermark em processamento: {image_id}")
                else:
                    response_data['message'] = "Erro ao criar watermark no Placid"
                    
            except Exception as e:
                print(f"Erro ao processar watermark: {e}")
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
                # Configurar layers baseado no formato e template (definir variáveis primeiro)
                format_type = payload.get('format', 'reels')
                template_key = payload.get('template', 'feed_1_red')
                title = payload.get('title', '')
                subject = payload.get('subject', '')
                credits = payload.get('credits', '')
                
                # Salvar arquivo temporariamente
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                ext = file.filename.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                    ext = 'jpg'
                
                unique_filename = f"post_{timestamp}.{ext}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                
                # URL pública do arquivo - usar uploads direto
                public_file_url = f"{request.url_root}uploads/{unique_filename}"
                print(f"DEBUG - Link público gerado: {public_file_url}")
                
                # DEBUG: Logs para debugar
                print(f"DEBUG - Arquivo salvo: {unique_filename}")
                print(f"DEBUG - URL pública: {public_file_url}")
                print(f"DEBUG - Template selecionado: {payload.get('template', 'N/A')}")
                print(f"DEBUG - Formato: {payload.get('format', 'N/A')}")
                
                # Verificar se o template existe
                if template_key not in PLACID_TEMPLATES:
                    print(f"ERRO - Template '{template_key}' não encontrado!")
                    print(f"Templates disponíveis: {list(PLACID_TEMPLATES.keys())}")
                    template_key = 'feed_1_red'  # Fallback
                    print(f"DEBUG - Usando fallback: {template_key}")
                
                template_info = PLACID_TEMPLATES[template_key]
                template_uuid = template_info['uuid']
                template_type = template_info.get('type', 'feed')
                template_dimensions = template_info.get('dimensions', {'width': 1080, 'height': 1080})
                
                print(f"DEBUG - Template info: {template_info}")
                print(f"DEBUG - Template UUID: {template_uuid}")
                print(f"DEBUG - Template type: {template_type}")
                
                # Configurar layers baseado no tipo de template
                layers = {
                    "imgprincipal": {
                        "image": public_file_url
                    }
                }
                
                # Debug: verificar template_type
                print(f"Template selecionado: {template_key}, Tipo: {template_type}")
                
                # Usar o mesmo sistema do feed - modelo 1 (red) para todos os templates
                # Apenas mudando os layers específicos de cada template
                
                if template_type == 'watermark':
                    # Template de watermark: usar EXATAMENTE a mesma forma do feed - modelo 1 (red)
                    print("Configurando layers para watermark: usando sistema IDÊNTICO ao feed")
                    layers["titulocopy"] = {"text": title}
                    if subject:
                        layers["assuntext"] = {"text": subject}
                    if credits:
                        layers["creditfoto"] = {"text": f"FOTO: {credits}"}
                    layers["credit"] = {"text": "Créditos gerais"}
                elif template_type == 'feed':
                    # Templates de Feed: usar sistema completo do feed - modelo 1 (red)
                    print("Configurando layers para feed")
                    layers["titulocopy"] = {"text": title}
                    if subject:
                        layers["assuntext"] = {"text": subject}
                    if credits:
                        layers["creditfoto"] = {"text": f"FOTO: {credits}"}
                    layers["credit"] = {"text": "Créditos gerais"}
                elif template_type == 'story':
                    # Templates de Story: usar sistema do feed + layers específicos
                    print("Configurando layers para story")
                    layers["titulocopy"] = {"text": title}
                    layers["imgfundo"] = {"image": "https://via.placeholder.com/1080x1920/FF0000/FFFFFF?text=FUNDO+VERMELHO"}
                else:
                    # Templates de Reels: usar sistema do feed + layers específicos
                    print("Configurando layers para reels")
                    layers["titulocopy"] = {"text": title}
                
                print(f"DEBUG - Layers finais: {layers}")
                print(f"DEBUG - URL da imagem no layer imgprincipal: {layers.get('imgprincipal', {}).get('image', 'NÃO ENCONTRADA')}")
                
                # Verificar se o arquivo local existe
                if os.path.exists(file_path):
                    print(f"DEBUG - ✅ Arquivo local existe: {file_path}")
                    print(f"DEBUG - ✅ Tamanho do arquivo: {os.path.getsize(file_path)} bytes")
                else:
                    print(f"DEBUG - ❌ Arquivo local NÃO existe: {file_path}")
                
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
                print(f"DEBUG - Criando post no Placid com template: {template_uuid} ({PLACID_TEMPLATES[template_key]['name']})")
                print(f"DEBUG - Enviando para Placid - Layers: {layers}")
                print(f"DEBUG - Enviando para Placid - Modifications: {modifications}")
                image_result = create_placid_image(
                    template_uuid=template_uuid,
                    layers=layers,
                    modifications=modifications
                )
                
                if image_result:
                    image_id = image_result.get('id')
                    print(f"Post criado com ID: {image_id}")
                    
                    # Verificar se a imagem já está pronta (create_now: True)
                    if image_result.get('image_url'):
                        response_data['success'] = True
                        response_data['imageUrl'] = image_result['image_url']
                        response_data['message'] = "Post gerado com sucesso!"
                        print(f"Post finalizado: {image_result['image_url']}")
                    else:
                        # Se não estiver pronta, retornar o ID para verificação posterior
                        response_data['success'] = True
                        response_data['imageId'] = image_id
                        response_data['message'] = "Post em processamento. Use o ID para verificar status."
                        print(f"Post em processamento: {image_id}")
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

def process_generate_title(payload):
    """Processa geração de título com IA usando prompt específico e API Groq"""
    response_data = {"success": False}
    
    news_content = payload.get('newsContent', '')
    if not news_content.strip():
        response_data['message'] = "Conteúdo da notícia é obrigatório"
        return jsonify(response_data), 400
    
    # Usar o prompt específico para títulos
    prompt = AI_PROMPTS['titulo']
    
    # Chamar API Groq para gerar título
    suggested_title = call_groq_api(prompt, news_content, max_tokens=200)
    
    if suggested_title:
        response_data['success'] = True
        response_data['suggestedTitle'] = suggested_title
        response_data['message'] = "Título gerado com sucesso usando IA Groq!"
    else:
        # Fallback para exemplos pré-definidos em caso de erro
        import random
        sample_titles = [
            "EXCLUSIVO: Casos De Dengue DISPARAM Em Maceió E Hospital Soa Alerta...",
            "URGENTE: MPF Impõe Regras Mais Rígidas Para Construções Na Orla...",
            "CONFIRMADO: Motoristas De Aplicativo Precisam Regularizar MEI...",
            "Tribuna Hoje: Nova Descoberta REVOLUCIONA Tratamento De Doenças...",
            "Alagoas: Especialistas Alertam Para Impacto Das Mudanças Climáticas..."
        ]
        suggested_title = random.choice(sample_titles)
        response_data['success'] = True
        response_data['suggestedTitle'] = suggested_title
        response_data['message'] = "Título gerado com sucesso (modo fallback)!"
    
    return jsonify(response_data)

def process_generate_captions(payload):
    """Processa geração de legendas com IA usando prompt específico e API Groq"""
    response_data = {"success": False}
    
    content = payload.get('content', '')
    if not content.strip():
        response_data['message'] = "Conteúdo é obrigatório"
        return jsonify(response_data), 400
    
    print(f"DEBUG - Gerando legendas para conteúdo: {content[:100]}...")
    
    # Usar o prompt específico para legendas
    prompt = AI_PROMPTS['legendas']
    
    # Chamar API Groq para gerar legendas
    generated_caption = call_groq_api(prompt, content, max_tokens=500)
    
    if generated_caption:
        print(f"DEBUG - Legenda gerada pela IA: {generated_caption[:100]}...")
        # Gerar múltiplas variações
        captions = [generated_caption]
        
        # Gerar mais 2 variações
        for i in range(2):
            variation = call_groq_api(prompt, content, max_tokens=500)
            if variation and variation not in captions:
                captions.append(variation)
                print(f"DEBUG - Variação {i+1} gerada")
        
        response_data['success'] = True
        response_data['captions'] = captions
        response_data['message'] = "Legendas geradas com sucesso usando IA Groq!"
    else:
        print("DEBUG - Usando fallback para legendas")
        # Fallback para exemplos pré-definidos em caso de erro
        sample_captions = [
            "🚨 URGENTE: Casos de dengue disparam em Maceió e preocupam autoridades!\n\nO Hospital Universitário registrou aumento de 150% nos atendimentos na última semana. A situação preocupa especialistas que alertam para possível epidemia.\n\n#TribunaHoje #Alagoas #Maceió #Dengue #Saúde\n\n📱 Acesse o link na bio para a matéria completa!",
            
            "📊 EXCLUSIVO: MPF impõe regras mais rígidas para construções na orla!\n\nA medida visa proteger o meio ambiente e garantir desenvolvimento sustentável na região. Empresários terão 90 dias para se adequar.\n\n#TribunaHoje #Alagoas #BarraDeSãoMiguel #MeioAmbiente\n\n💬 O que você acha dessa decisão? Comente abaixo!",
            
            "⚡ CONFIRMADO: Motoristas de aplicativo precisam regularizar MEI!\n\nNova legislação exige documentação em dia para garantir isenção do IPVA. Prazo limite é 31 de dezembro.\n\n#TribunaHoje #Alagoas #MEI #IPVA #Motoristas\n\n🔗 Saiba mais no link da bio!",
            
            "🏥 Tribuna Hoje: Hospital de Maceió investe em equipamentos de última geração!\n\nInvestimento de R$ 2 milhões vai melhorar atendimento para mais de 50 mil pacientes por mês. Expectativa é reduzir filas em 40%.\n\n#TribunaHoje #Alagoas #Maceió #Saúde #Investimento\n\n📱 Compartilhe essa notícia!",
            
            "🌊 Alagoas: Chuvas intensas causam alagamentos em 15 bairros de Maceió!\n\nDefesa Civil emite alerta para população. Previsão é de mais chuvas nos próximos dias. Evite áreas de risco.\n\n#TribunaHoje #Alagoas #Maceió #Chuvas #Alagamentos\n\n⚠️ Fique atento aos alertas oficiais!"
        ]
        
        response_data['success'] = True
        response_data['captions'] = sample_captions
        response_data['message'] = "Legendas geradas com sucesso (modo fallback)!"
    
    print(f"DEBUG - Retornando {len(response_data.get('captions', []))} legendas")
    return jsonify(response_data)

def process_rewrite_news(payload):
    """Processa reescrita de notícias com IA usando prompt específico e API Groq"""
    response_data = {"success": False}
    
    news_content = payload.get('newsContent', '')
    if not news_content.strip():
        response_data['message'] = "Conteúdo da notícia é obrigatório"
        return jsonify(response_data), 400
    
    # Usar o prompt específico para reescrita
    prompt = AI_PROMPTS['reescrita']
    
    # Chamar API Groq para reescrever notícia
    rewritten_content = call_groq_api(prompt, news_content, max_tokens=1500)
    
    if rewritten_content:
        # Separar título e texto (assumindo que o primeiro parágrafo é o título)
        lines = rewritten_content.strip().split('\n')
        title = lines[0].strip()
        text = '\n'.join(lines[1:]).strip()
        
        # Se não conseguir separar, usar o conteúdo completo como texto
        if not text:
            text = rewritten_content
            title = "Notícia Reescrita"
        
        rewritten_news = {
            "titulo": title,
            "texto": text
        }
        
        response_data['success'] = True
        response_data['rewrittenNews'] = rewritten_news
        response_data['message'] = "Notícia reescrita com sucesso usando IA Groq!"
    else:
        # Fallback para exemplos pré-definidos em caso de erro
        import random
        sample_news = [
            {
                "titulo": "Alfredo Gaspar assume relatoria da CPMI que investiga fraudes no INSS",
                "texto": "O deputado federal Alfredo Gaspar (União Brasil-AL) foi designado relator da Comissão Parlamentar Mista de Inquérito (CPMI) que apura possíveis fraudes no Instituto Nacional do Seguro Social (INSS). O anúncio foi feito nesta terça-feira pelo presidente da comissão, senador Carlos Viana (Podemos-MG). Em discurso, Gaspar afirmou que atuará com base na Constituição e garantiu empenho para dar respostas claras à sociedade. A CPMI foi instalada após denúncias de irregularidades em benefícios previdenciários que podem ter causado prejuízos de bilhões aos cofres públicos. O relatório final deve ser apresentado em 120 dias, com possibilidade de prorrogação por mais 60 dias."
            },
            {
                "titulo": "Hospital de Maceió registra aumento de 150% nos casos de dengue",
                "texto": "O Hospital Universitário Professor Alberto Antunes (Hupaa) registrou aumento de 150% nos atendimentos de casos suspeitos de dengue na última semana, segundo dados divulgados pela Secretaria de Estado da Saúde (Sesau). O crescimento preocupa autoridades sanitárias que alertam para possível epidemia na capital alagoana. A diretora do hospital, Dra. Maria Silva, informou que foram atendidos 45 casos suspeitos nos últimos sete dias, contra 18 na semana anterior. A Sesau orienta a população a eliminar criadouros do mosquito Aedes aegypti e procurar atendimento médico aos primeiros sintomas da doença."
            }
        ]
        
        selected_news = random.choice(sample_news)
        response_data['success'] = True
        response_data['rewrittenNews'] = selected_news
        response_data['message'] = "Notícia reescrita com sucesso (modo fallback)!"
    
    return jsonify(response_data)

def process_save_rewrite(payload):
    """Processa salvamento de reescrita manual"""
    response_data = {"success": False}
    
    manual_title = payload.get('manualTitle', '')
    manual_text = payload.get('manualText', '')
    
    if not manual_title.strip() or not manual_text.strip():
        response_data['message'] = "Título e texto são obrigatórios"
        return jsonify(response_data), 400
    
    # Aqui você pode salvar a reescrita em um banco de dados
    print(f"Reescrita salva - Título: {manual_title}")
    print(f"Reescrita salva - Texto: {manual_text[:100]}...")
    
    response_data['success'] = True
    response_data['message'] = "Notícia reescrita salva com sucesso!"
    
    return jsonify(response_data)

def process_save_title(payload):
    """Processa salvamento de título manual"""
    response_data = {"success": False}
    
    manual_title = payload.get('manualTitle', '')
    if not manual_title.strip():
        response_data['message'] = "Título é obrigatório"
        return jsonify(response_data), 400
    
    # Aqui você pode salvar o título em um banco de dados
    print(f"Título salvo: {manual_title}")
    
    response_data['success'] = True
    response_data['message'] = "Título salvo com sucesso!"
    
    return jsonify(response_data)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/post/<slug>')
def post_image(slug):
    """Serve a imagem mais recente para o slug do post"""
    try:
        # Buscar o arquivo mais recente na pasta uploads
        files = os.listdir(UPLOAD_FOLDER)
        if not files:
            return "Nenhuma imagem encontrada", 404
        
        # Filtrar apenas arquivos de imagem
        image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        if not image_files:
            return "Nenhuma imagem encontrada", 404
        
        # Pegar o arquivo mais recente
        latest_file = max(image_files, key=lambda x: os.path.getctime(os.path.join(UPLOAD_FOLDER, x)))
        
        print(f"DEBUG - Servindo imagem para slug '{slug}': {latest_file}")
        return send_from_directory(UPLOAD_FOLDER, latest_file)
    except Exception as e:
        print(f"Erro ao servir imagem para slug '{slug}': {e}")
        return "Erro ao carregar imagem", 500

@app.route('/api/check-image/<image_id>')
def check_image_status(image_id):
    """Verifica o status de uma imagem no Placid"""
    try:
        image_data = get_placid_image(image_id)
        if not image_data:
            return jsonify({"success": False, "message": "Imagem não encontrada"}), 404
        
        status = image_data.get('status')
        if status == 'finished' and image_data.get('image_url'):
            return jsonify({
                "success": True,
                "status": "finished",
                "imageUrl": image_data['image_url']
            })
        elif status == 'error':
            return jsonify({
                "success": False,
                "status": "error",
                "message": "Erro ao processar imagem"
            })
        else:
            return jsonify({
                "success": True,
                "status": "processing",
                "message": "Imagem ainda em processamento"
            })
    except Exception as e:
        print(f"Erro ao verificar status da imagem {image_id}: {e}")
        return jsonify({"success": False, "message": f"Erro: {e}"}), 500

if __name__ == '__main__':
    print("🚀 Iniciando SaaS Editor...")
    print(f"🎨 Integração com Placid: {PLACID_API_URL}")
    print(f"📋 Templates disponíveis: {len(PLACID_TEMPLATES)}")
    for key, template in PLACID_TEMPLATES.items():
        print(f"   - {template['name']}: {template['uuid']}")
    print(f"🌐 Servidor rodando em: http://0.0.0.0:5000" )
    app.run(debug=True, host='0.0.0.0', port=5000)
