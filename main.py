from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import requests
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    PLACID_API_TOKEN = 'placid-mmv6puv1gvuucitb-hhflfvh5yeru1ijl'
    PLACID_API_URL = 'https://api.placid.app/api/rest/images'
    GROQ_API_KEY = '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'
    GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
    UPLOAD_FOLDER = os.path.abspath('uploads')
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov'}

# Templates configuration
PLACID_TEMPLATES = {
    'stories_2': {
        'uuid': 'plrlpyk5wwjvw',
        'name': 'Stories - Modelo 2',
        'description': 'Template para stories',
        'type': 'story',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'stories_1': {
        'uuid': 'dfgp8e0wosomx',
        'name': 'Stories - Modelo 1',
        'description': 'Template para Stories',
        'type': 'story',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'reels_modelo_2': {
        'uuid': 'wsusffzt492wq',
        'name': 'Reels Feed - Modelo 2',
        'description': 'Template para Reels',
        'type': 'reels',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'reels_modelo_1': {
        'uuid': 'fhymmiu4gzs1l',
        'name': 'Reels Feed - Modelo 1',
        'description': 'Template para Reels',
        'type': 'reels',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'feed_1': {
        'uuid': 'bvxnkfasqpbl9',
        'name': 'Feed - Modelo 1',
        'description': 'Template para Feed',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_2': {
        'uuid': '33moedpfusmbo',
        'name': 'Feed - Modelo 2',
        'description': 'Template para Feed',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'watermark': {
        'uuid': 'kky75obfzathq',
        'name': 'Watermark',
        'description': 'Template para Watermark',
        'type': 'watermark',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'watermark_1': {
        'uuid': 'wnmkfkbcsnsdo',
        'name': 'Watermark1',
        'description': 'Template para Watermark - Segundo Modelo',
        'type': 'watermark',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_3': {
        'uuid': 'efnadlehh2ato',
        'name': 'Feed - Modelo 3',
        'description': 'Template para Feed',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_4': {
        'uuid': 'hmnyoopxig4cm',
        'name': 'Feed - Modelo 4',
        'description': 'Template para Feed',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    }
}

# AI Prompts
AI_PROMPTS = {
    'legendas': """Gerador de Legendas Jornalísticas para Instagram

Você é um jornalista especialista em copy para redes sociais, capaz de transformar descrições de notícias em legendas curtas, chamativas e informativas para posts de Instagram do jornal Tribuna Hoje. Sempre que receber uma descrição de notícia, siga rigorosamente estas instruções:

Análise Completa: Identifique os elementos centrais da notícia (quem, o quê, onde e consequência mais relevante) e INFIRA o assunto/tema principal (ex.: política, polícia, saúde, economia, clima, esporte, cultura, serviço).

Impacto Inicial: Comece a legenda com uma chamada forte e clara, destacando a informação mais importante ou surpreendente da descrição.

Contexto Curto: Acrescente 1 a 2 frases curtas que resumam o contexto de forma simples e acessível.

Tom Jornalístico: Mantenha credibilidade, clareza e objetividade, sem sensacionalismo exagerado.

Palavras-Chave Obrigatórias: Inclua naturalmente termos que reforcem relevância jornalística, como "Alagoas", "Maceió", "Tribuna Hoje", "exclusivo", "urgente" quando fizer sentido.

CTA Estratégico (SEPARADO): Crie um CTA em linha própria, adequado ao assunto inferido. Exemplos por assunto:
- Política/economia: "🔗 Leia a matéria completa no link da bio"
- Polícia/segurança: "⚠️ Compartilhe a informação"
- Saúde/serviço público: "📣 Salve e repasse para quem precisa"
- Clima/transporte: "🌧️ Acompanhe os alertas oficiais"
- Opinião/engajamento: "💬 O que você acha? Comente"

Hashtags por Assunto (SEPARADAS): Gere 5 a 8 hashtags específicas ao tema, seguindo regras:
- Inclua sempre #TribunaHoje e, quando fizer sentido, #Alagoas e #Maceio (sem acento)
- Foque em termos do assunto (ex.: #Saude, #Seguranca, #Politica, #Economia, #Clima, #Cultura, #Esporte)
- Use todas em minúsculas, sem acentos, sem espaços, separadas por espaço; não repita hashtags; evite genéricas demais (#news, #insta)

Formatação Obrigatória da Saída (exatamente 3 blocos, nesta ordem, separados por 1 linha em branco, sem rótulos):
1) Corpo da legenda (2 a 3 frases, 250–400 caracteres)

2) CTA em linha única

3) Hashtags em uma única linha

Padrão de Estilo:
- Primeira letra maiúscula em todas as frases do corpo
- Parágrafos curtos e claros (1 a 3 linhas cada)
- Não copiar literalmente a descrição original; reescreva com nova estrutura e escolha de palavras

Resposta Direta: Retorne SOMENTE o texto final no formato acima, sem comentários, explicações ou qualquer texto adicional.""",

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

# Utility functions
def ensure_upload_directory() -> None:
    """Ensure upload directory exists"""
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER)
        logger.info(f"Created upload directory: {Config.UPLOAD_FOLDER}")

def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed - ACCEPTS ALL FILES"""
    logger.info(f"File accepted: {filename}")
    return True

def generate_filename(prefix: str, extension: str) -> str:
    """Generate unique filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

def call_groq_api(prompt: str, content: str, max_tokens: int = 1000) -> Optional[str]:
    """Call Groq API with error handling and retries"""
    if not Config.GROQ_API_KEY or Config.GROQ_API_KEY == 'your-api-key-here':
        logger.warning("Groq API key not configured")
        return None
    
    # Truncate content to prevent API limits
    if len(content) > 4000:
        content = content[:4000] + "..."
    
    full_prompt = f"{prompt}\n\nConteúdo para processar:\n{content}"
    
    if len(full_prompt) > 8000:
        full_prompt = full_prompt[:8000] + "..."
    
    headers = {
        'Authorization': f'Bearer {Config.GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "messages": [{"role": "user", "content": full_prompt}],
        "model": "llama-3.1-8b-instant",
        "max_tokens": min(max_tokens, 500),
        "temperature": 0.7
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Calling Groq API (attempt {attempt + 1})")
            response = requests.post(
                Config.GROQ_API_URL, 
                json=payload, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    
    return None

def create_placid_image(template_uuid: str, layers: Dict[str, Any], 
                       modifications: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Create image in Placid with error handling"""
    logger.info("=" * 40)
    logger.info("🎨 STARTING create_placid_image")
    logger.info(f"🎯 Template UUID: {template_uuid}")
    logger.info(f"🔧 Layers: {layers}")
    logger.info(f"⚙️ Modifications: {modifications}")
    
    headers = {
        'Authorization': f'Bearer {Config.PLACID_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    logger.info(f"🔑 Headers: {headers}")
    
    payload = {
        'template_uuid': template_uuid,
        'layers': layers,
        'create_now': True
    }
    
    if modifications:
        payload['modifications'] = modifications
        logger.info("✅ Modifications added to payload")
    
    logger.info(f"📦 Full payload: {payload}")
    logger.info(f"🌐 API URL: {Config.PLACID_API_URL}")
    
    try:
        logger.info("🚀 Sending request to Placid API...")
        response = requests.post(
            Config.PLACID_API_URL, 
            json=payload, 
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📡 Response received - Status: {response.status_code}")
        logger.info(f"📡 Response headers: {dict(response.headers)}")
        logger.info(f"📡 Response text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Placid image created successfully!")
            logger.info(f"🆔 Image ID: {result.get('id', 'No ID')}")
            logger.info(f"🔗 Image URL: {result.get('image_url', 'No URL')}")
            logger.info(f"📊 Full result: {result}")
            return result
        else:
            logger.error(f"❌ Placid API error!")
            logger.error(f"❌ Status code: {response.status_code}")
            logger.error(f"❌ Response text: {response.text}")
            logger.error(f"❌ Response headers: {dict(response.headers)}")
            return None
            
    except requests.exceptions.Timeout as e:
        logger.error(f"⏰ Placid API timeout: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Placid API connection error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Placid API request failed: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error in create_placid_image: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

def get_placid_image_status(image_id: str) -> Optional[Dict[str, Any]]:
    """Get Placid image status"""
    logger.info("=" * 30)
    logger.info("🔍 STARTING get_placid_image_status")
    logger.info(f"🆔 Image ID: {image_id}")
    
    headers = {
        'Authorization': f'Bearer {Config.PLACID_API_TOKEN}'
    }
    logger.info(f"🔑 Headers: {headers}")
    
    url = f'{Config.PLACID_API_URL}/{image_id}'
    logger.info(f"🌐 Status URL: {url}")
    
    try:
        logger.info("🚀 Sending status request to Placid...")
        response = requests.get(
            url, 
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📡 Status response - Code: {response.status_code}")
        logger.info(f"📡 Status response - Headers: {dict(response.headers)}")
        logger.info(f"📡 Status response - Text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Status retrieved successfully: {result}")
            return result
        else:
            logger.error(f"❌ Failed to get image status: {response.status_code}")
            logger.error(f"❌ Response text: {response.text}")
            return None
            
    except requests.exceptions.Timeout as e:
        logger.error(f"⏰ Timeout getting image status: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Connection error getting image status: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error getting image status: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error getting image status: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

def save_uploaded_file(file, prefix: str) -> Tuple[bool, str, str]:
    """Save uploaded file and return success, filepath, and public URL"""
    logger.info("=" * 30)
    logger.info("💾 STARTING save_uploaded_file")
    logger.info(f"📁 File object: {file}")
    logger.info(f"🏷️ Prefix: {prefix}")
    
    try:
        if not file or not file.filename:
            logger.error("❌ No file or filename provided")
            return False, "", "No file provided"
        
        logger.info(f"✅ File validation passed: {file.filename}")
        logger.info(f"📄 File content type: {file.content_type if hasattr(file, 'content_type') else 'Unknown'}")
        
        # Accept all file types
        logger.info(f"✅ Accepting file: {file.filename}")
        
        # Check file size
        logger.info("📏 Checking file size...")
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        logger.info(f"📏 File size: {size} bytes")
        logger.info(f"📏 Max allowed size: {Config.MAX_FILE_SIZE} bytes")
        
        if size > Config.MAX_FILE_SIZE:
            logger.error(f"❌ File too large: {size} > {Config.MAX_FILE_SIZE}")
            return False, "", "File too large"
        
        logger.info("✅ File size check passed")
        
        # Generate filename
        logger.info("🏷️ Generating filename...")
        if '.' not in file.filename:
            logger.error("❌ No extension in filename")
            return False, "", "No file extension"
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        logger.info(f"🏷️ File extension: {ext}")
        
        filename = generate_filename(prefix, ext)
        logger.info(f"🏷️ Generated filename: {filename}")
        
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        logger.info(f"📂 Full filepath: {filepath}")
        
        # Ensure directory exists
        logger.info("📁 Ensuring upload directory exists...")
        ensure_upload_directory()
        
        # Save file
        logger.info("💾 Saving file to disk...")
        file.save(filepath)
        logger.info("✅ File saved successfully")
        
        # Generate public URL
        public_url = f"{request.url_root}uploads/{filename}"
        logger.info(f"🌐 Public URL: {public_url}")
        
        # Verify file exists
        if os.path.exists(filepath):
            actual_size = os.path.getsize(filepath)
            logger.info(f"✅ File verification: {filename} ({actual_size} bytes)")
        else:
            logger.error(f"❌ File verification failed: {filepath} not found")
            return False, "", "File save verification failed"
        
        logger.info(f"🎉 File upload completed: {filename} ({size} bytes)")
        return True, filepath, public_url
        
    except Exception as e:
        logger.error(f"❌ Exception in save_uploaded_file: {type(e).__name__}: {e}")
        logger.error(f"❌ Exception details: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False, "", str(e)

def configure_layers_for_template(template_key: str, template_info: Dict[str, Any], 
                                public_file_url: str, title: str = "", 
                                subject: str = "", credits: str = "") -> Dict[str, Any]:
    """Configure layers based on template type"""
    logger.info("=" * 35)
    logger.info("🔧 STARTING configure_layers_for_template")
    logger.info(f"🎯 Template key: {template_key}")
    logger.info(f"📋 Template info: {template_info}")
    logger.info(f"🌐 Public file URL: {public_file_url}")
    logger.info(f"📝 Title: {title}")
    logger.info(f"📝 Subject: {subject}")
    logger.info(f"📝 Credits: {credits}")
    
    template_type = template_info.get('type', 'feed')
    logger.info(f"🎨 Template type: {template_type}")
    
    # Base media layer: usar SEMPRE imagem (mesma lógica dos outros formatos)
    layers = {
        "imgprincipal": {
            "image": public_file_url
        }
    }
    logger.info(f"🖼️ Using image layer for template: {template_key}")
    logger.info(f"🖼️ Base layers: {layers}")
    
    # Add text layers based on template type
    if template_type in ['feed', 'watermark'] and title:
        layers["titulocopy"] = {"text": title}
        logger.info(f"✅ Added title layer for {template_type}: {title}")
    else:
        logger.info(f"⏭️ Skipping title layer - Type: {template_type}, Title: {title}")
        
    if template_type == 'feed':
        logger.info("🔍 Processing feed template layers...")
        if subject:
            layers["assuntext"] = {"text": subject}
            logger.info(f"✅ Added subject layer: {subject}")
        else:
            logger.info("⏭️ No subject provided")
            
        if credits:
            layers["creditfoto"] = {"text": f"FOTO: {credits}"}
            logger.info(f"✅ Added credits layer: FOTO: {credits}")
        else:
            logger.info("⏭️ No credits provided")
            
        layers["credit"] = {"text": "Tribuna Hoje"}
        logger.info("✅ Added credit layer: Tribuna Hoje")
        
    elif template_type == 'story' and title:
        layers["titulocopy"] = {"text": title}
        logger.info(f"✅ Added title layer for story: {title}")
    else:
        logger.info(f"⏭️ Skipping story title - Type: {template_type}, Title: {title}")
        
    if template_type == 'reels':
        logger.info("🔍 Processing reels template layers (only titulocopy + imgprincipal)")
        if title:
            layers["titulocopy"] = {"text": title}
            logger.info(f"✅ Added title layer for reels: {title}")
        else:
            logger.info("⏭️ No title provided for reels")
    
    logger.info(f"🎉 Final layers configured: {layers}")
    return layers

# API Response helpers
def success_response(message: str, **kwargs) -> Dict[str, Any]:
    """Create success response"""
    response = {"success": True, "message": message}
    response.update(kwargs)
    return response

def error_response(message: str, **kwargs) -> Dict[str, Any]:
    """Create error response"""
    response = {"success": False, "message": message}
    response.update(kwargs)
    return response

# Route handlers
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/test-placid')
def test_placid():
    """Test Placid API connection"""
    test_payload = {
        'template_uuid': 'qe0qo74vbrgxe',
        'layers': {
            'imgprincipal': {
                'image': 'https://via.placeholder.com/1200x1200/FF0000/FFFFFF?text=TESTE'
            }
        },
        'create_now': True
    }
    
    result = create_placid_image(
        test_payload['template_uuid'], 
        test_payload['layers']
    )
    
    if result:
        return f"✅ Placid funcionando! ID: {result.get('id', 'N/A')}"
    else:
        return "❌ Erro no Placid!"

@app.route('/api/process', methods=['POST'])
def process_request():
    """Main API endpoint for processing requests"""
    logger.info("=" * 60)
    logger.info("🌐 STARTING process_request")
    logger.info(f"📡 Request method: {request.method}")
    logger.info(f"📡 Request URL: {request.url}")
    logger.info(f"📡 Request headers: {dict(request.headers)}")
    logger.info(f"📡 Request content type: {request.content_type}")
    logger.info(f"📡 Request content length: {request.content_length}")
    
    ensure_upload_directory()
    logger.info("✅ Upload directory ensured")
    
    try:
        # Parse request data
        logger.info("🔍 Parsing request data...")
        logger.info(f"📋 Request form: {request.form}")
        logger.info(f"📋 Request files: {request.files}")
        
        # Check if request has JSON data (only if content-type is application/json)
        if request.content_type == 'application/json':
            logger.info(f"📋 Request JSON: {request.json}")
        else:
            logger.info("📋 Request is not JSON, skipping JSON parsing")
        
        if request.form:
            logger.info("📝 Processing form data")
            action = request.form.get('action')
            data_str = request.form.get('data')
            logger.info(f"🎯 Action from form: {action}")
            logger.info(f"📦 Data string from form: {data_str}")
            payload = json.loads(data_str) if data_str else {}
            logger.info(f"📦 Parsed payload: {payload}")
        elif request.content_type == 'application/json':
            logger.info("📝 Processing JSON data")
            data = request.json or {}
            action = data.get('action')
            payload = data.get('data', {})
            logger.info(f"🎯 Action from JSON: {action}")
            logger.info(f"📦 Payload from JSON: {payload}")
        else:
            logger.error(f"❌ Unsupported content type: {request.content_type}")
            return jsonify(error_response("Unsupported content type")), 400
        
        logger.info(f"🎯 Final action: {action}")
        logger.info(f"📦 Final payload: {payload}")
        
        # Route to appropriate handler
        handlers = {
            'apply_watermark': handle_watermark,
            'generate_post': handle_generate_post,
            'generate_title_ai': handle_generate_title,
            'generate_captions_ai': handle_generate_captions,
            'rewrite_news_ai': handle_rewrite_news,
            'save_manual_caption': handle_save_caption,
            'save_manual_rewrite': handle_save_rewrite,
            'save_manual_title': handle_save_title,
        }
        
        logger.info(f"🔧 Available handlers: {list(handlers.keys())}")
        handler = handlers.get(action)
        logger.info(f"🎯 Selected handler: {handler}")
        
        if not handler:
            logger.error(f"❌ Unknown action: {action}")
            return jsonify(error_response(f"Unknown action: {action}")), 400
        
        logger.info(f"🚀 Calling handler for action: {action}")
        result = handler(payload, request)
        logger.info(f"✅ Handler completed, returning result")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        return jsonify(error_response("Invalid JSON data")), 400
    except Exception as e:
        logger.error(f"❌ Exception in process_request: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify(error_response("Internal server error")), 500

def handle_watermark(payload: Dict[str, Any], request) -> jsonify:
    """Handle watermark application"""
    file = request.files.get('file') if hasattr(request, 'files') else None
    if not file:
        return jsonify(error_response("No file provided"))
    
    success, filepath, public_url = save_uploaded_file(file, "watermark")
    if not success:
        return jsonify(error_response(public_url))  # Error message in public_url
    
    template_key = 'watermark'
    template_info = PLACID_TEMPLATES[template_key]
    
    layers = configure_layers_for_template(
        template_key, template_info, public_url,
        title=payload.get('title', ''),
        subject=payload.get('subject', ''),
        credits=payload.get('credits', '')
    )
    
    modifications = {
        "filename": f"watermark_{int(time.time())}.png",
        "width": template_info['dimensions']['width'],
        "height": template_info['dimensions']['height'],
        "image_format": "png"
    }
    
    result = create_placid_image(template_info['uuid'], layers, modifications)
    
    if result:
        if result.get('image_url'):
            return jsonify(success_response(
                "Watermark applied successfully!",
                imageUrl=result['image_url']
            ))
        else:
            return jsonify(success_response(
                "Watermark processing...",
                imageId=result.get('id')
            ))
    else:
        return jsonify(error_response("Failed to create watermark"))

def handle_generate_post(payload: Dict[str, Any], request) -> jsonify:
    """Handle post generation"""
    logger.info("=" * 50)
    logger.info("🚀 STARTING handle_generate_post")
    logger.info(f"📦 Payload received: {payload}")
    logger.info(f"🔍 Request files: {request.files}")
    logger.info(f"🔍 Request form: {request.form}")
    
    file = request.files.get('file') if hasattr(request, 'files') else None
    logger.info(f"📁 File object: {file}")
    logger.info(f"📁 File filename: {file.filename if file else 'None'}")
    logger.info(f"📁 File content type: {file.content_type if file else 'None'}")
    
    if not file:
        logger.error("❌ No file provided")
        return jsonify(error_response("No file provided"))
    
    logger.info("✅ File validation passed")
    
    # Validate required fields
    template_key = payload.get('template', 'feed_1_red')
    title = payload.get('title', '')
    subject = payload.get('subject', '')
    credits = payload.get('credits', '')
    
    logger.info(f"🎯 Template key: {template_key}")
    logger.info(f"📝 Title: {title}")
    logger.info(f"📝 Subject: {subject}")
    logger.info(f"📝 Credits: {credits}")
    
    if template_key not in PLACID_TEMPLATES:
        logger.warning(f"⚠️ Template {template_key} not found, using fallback")
        template_key = 'feed_1_red'  # Fallback
    
    template_info = PLACID_TEMPLATES[template_key]
    logger.info(f"🎨 Template info: {template_info}")
    
    # Check if feed template requires additional fields
    if template_info['type'] == 'feed':
        logger.info("🔍 Checking feed template requirements")
        if not subject or not credits:
            logger.error(f"❌ Feed template missing fields - Subject: {subject}, Credits: {credits}")
            return jsonify(error_response("Feed templates require subject and credits"))
        logger.info("✅ Feed template requirements met")
    
    logger.info("💾 Starting file upload process")
    success, filepath, public_url = save_uploaded_file(file, "post")
    logger.info(f"💾 Upload result - Success: {success}, Filepath: {filepath}, URL: {public_url}")
    
    if not success:
        logger.error(f"❌ File upload failed: {public_url}")
        return jsonify(error_response(public_url))
    
    logger.info("🔧 Configuring layers for template")
    layers = configure_layers_for_template(
        template_key, template_info, public_url,
        title=title,
        subject=subject,
        credits=credits
    )
    logger.info(f"🔧 Layers configured: {layers}")
    
    modifications = {
        "filename": f"instagram_post_{int(time.time())}.png",
        "width": template_info['dimensions']['width'],
        "height": template_info['dimensions']['height'],
        "image_format": "png"
    }
    logger.info(f"⚙️ Modifications: {modifications}")
    
    logger.info("🎨 Creating Placid image")
    result = create_placid_image(template_info['uuid'], layers, modifications)
    logger.info(f"🎨 Placid result: {result}")
    
    if result:
        if result.get('image_url'):
            logger.info("✅ Image created with direct URL")
            return jsonify(success_response(
                "Post generated successfully!",
                imageUrl=result['image_url']
            ))
        else:
            logger.info("⏳ Image processing in background")
            return jsonify(success_response(
                "Post processing...",
                imageId=result.get('id')
            ))
    else:
        logger.error("❌ Failed to create post in Placid")
        return jsonify(error_response("Failed to create post"))

def handle_generate_title(payload: Dict[str, Any], request) -> jsonify:
    """Handle title generation with AI"""
    content = payload.get('newsContent', '').strip()
    if not content:
        return jsonify(error_response("News content is required"))
    
    suggested_title = call_groq_api(AI_PROMPTS['titulo'], content, max_tokens=200)
    
    if suggested_title:
        return jsonify(success_response(
            "Title generated successfully!",
            suggestedTitle=suggested_title
        ))
    else:
        # Fallback examples
        fallback_titles = [
            "EXCLUSIVO: Casos De Dengue DISPARAM Em Maceió E Hospital Soa Alerta...",
            "URGENTE: MPF Impõe Regras Mais Rígidas Para Construções Na Orla...",
            "CONFIRMADO: Motoristas De Aplicativo Precisam Regularizar MEI...",
        ]
        import random
        return jsonify(success_response(
            "Title generated (fallback mode)!",
            suggestedTitle=random.choice(fallback_titles)
        ))

def handle_generate_captions(payload: Dict[str, Any], request) -> jsonify:
    """Handle caption generation with AI"""
    content = payload.get('content', '').strip()
    if not content:
        return jsonify(error_response("Content is required"))
    
    generated_caption = call_groq_api(AI_PROMPTS['legendas'], content, max_tokens=500)
    
    if generated_caption:
        captions = [generated_caption]
        
        # Generate variations
        for _ in range(2):
            variation = call_groq_api(AI_PROMPTS['legendas'], content, max_tokens=500)
            if variation and variation not in captions:
                captions.append(variation)
        
        return jsonify(success_response(
            "Captions generated successfully!",
            captions=captions
        ))
    else:
        # Fallback examples
        fallback_captions = [
            "🚨 URGENTE: Casos de dengue disparam em Maceió e preocupam autoridades!\n\nO Hospital Universitário registrou aumento de 150% nos atendimentos na última semana.\n\n#TribunaHoje #Alagoas #Maceió #Dengue\n\n📱 Acesse o link na bio!",
            "📊 EXCLUSIVO: MPF impõe regras mais rígidas para construções na orla!\n\nA medida visa proteger o meio ambiente na região.\n\n#TribunaHoje #Alagoas #MeioAmbiente\n\n💬 Comente sua opinião!",
        ]
        
        return jsonify(success_response(
            "Captions generated (fallback mode)!",
            captions=fallback_captions
        ))

def handle_rewrite_news(payload: Dict[str, Any], request) -> jsonify:
    """Handle news rewriting with AI"""
    content = payload.get('newsContent', '').strip()
    if not content:
        return jsonify(error_response("News content is required"))
    
    rewritten_content = call_groq_api(AI_PROMPTS['reescrita'], content, max_tokens=1500)
    
    if rewritten_content:
        lines = rewritten_content.strip().split('\n')
        title = lines[0].strip() if lines else "Notícia Reescrita"
        text = '\n'.join(lines[1:]).strip() if len(lines) > 1 else rewritten_content
        
        if not text:
            text = rewritten_content
        
        return jsonify(success_response(
            "News rewritten successfully!",
            rewrittenNews={"titulo": title, "texto": text}
        ))
    else:
        # Fallback example
        fallback_news = {
            "titulo": "Alfredo Gaspar assume relatoria da CPMI que investiga fraudes no INSS",
            "texto": "O deputado federal Alfredo Gaspar (União Brasil-AL) foi designado relator da Comissão Parlamentar Mista de Inquérito (CPMI) que apura possíveis fraudes no Instituto Nacional do Seguro Social (INSS). O anúncio foi feito pelo presidente da comissão. Gaspar afirmou que atuará com base na Constituição para dar respostas claras à sociedade."
        }
        
        return jsonify(success_response(
            "News rewritten (fallback mode)!",
            rewrittenNews=fallback_news
        ))

def handle_save_caption(payload: Dict[str, Any], request) -> jsonify:
    """Handle manual caption saving"""
    caption = payload.get('manualCaption', '').strip()
    if not caption:
        return jsonify(error_response("Caption is required"))
    
    logger.info(f"Caption saved: {caption[:50]}...")
    return jsonify(success_response("Caption saved successfully!"))

def handle_save_rewrite(payload: Dict[str, Any], request) -> jsonify:
    """Handle manual rewrite saving"""
    title = payload.get('manualTitle', '').strip()
    text = payload.get('manualText', '').strip()
    
    if not title or not text:
        return jsonify(error_response("Both title and text are required"))
    
    logger.info(f"Rewrite saved - Title: {title}")
    return jsonify(success_response("Rewritten news saved successfully!"))

def handle_save_title(payload: Dict[str, Any], request) -> jsonify:
    """Handle manual title saving"""
    title = payload.get('manualTitle', '').strip()
    if not title:
        return jsonify(error_response("Title is required"))
    
    logger.info(f"Title saved: {title}")
    return jsonify(success_response("Title saved successfully!"))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    try:
        return send_from_directory(Config.UPLOAD_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        return "File not found", 404

@app.route('/post/<slug>')
def post_image(slug):
    """Serve most recent image for a post slug"""
    try:
        files = os.listdir(Config.UPLOAD_FOLDER)
        image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        
        if not image_files:
            return "No images found", 404
        
        latest_file = max(image_files, key=lambda x: os.path.getctime(os.path.join(Config.UPLOAD_FOLDER, x)))
        logger.info(f"Serving image for slug '{slug}': {latest_file}")
        
        return send_from_directory(Config.UPLOAD_FOLDER, latest_file)
    except Exception as e:
        logger.error(f"Error serving image for slug '{slug}': {e}")
        return "Error loading image", 500

@app.route('/api/check-image/<image_id>')
def check_image_status(image_id):
    """Check Placid image processing status"""
    try:
        image_data = get_placid_image_status(image_id)
        if not image_data:
            return jsonify(error_response("Image not found")), 404
        
        status = image_data.get('status')
        if status == 'finished' and image_data.get('image_url'):
            return jsonify(success_response(
                "Image processing completed",
                status="finished",
                imageUrl=image_data['image_url']
            ))
        elif status == 'error':
            return jsonify(error_response(
                "Error processing image",
                status="error"
            ))
        else:
            return jsonify(success_response(
                "Image still processing",
                status="processing"
            ))
    except Exception as e:
        logger.error(f"Error checking image status {image_id}: {e}")
        return jsonify(error_response("Error checking image status")), 500

# HTML Template
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

        .success-message, .error-message {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }

        .success-message {
            background: #d4edda;
            color: #155724;
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
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
            
            .template-grid {
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
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
                    <div class="upload-text">Upload de qualquer arquivo</div>
                    <div class="upload-subtext">Todos os formatos são aceitos</div>
                </div>
                <input type="file" id="post-file" class="file-input" onchange="handleFileUpload(this, 'post')">

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

                    <div id="format-preview" style="margin: 10px 0 6px; color: #6c757d;"></div>
                    <h3>Templates Disponíveis</h3>
                    <div class="template-grid" id="template-grid"></div>
                </div>

                <div class="two-column">
                    <div>
                        <div class="controls-section">
                            <div class="control-group">
                                <label class="control-label">Título *</label>
                                <input type="text" class="control-input" id="titulo" placeholder="Digite o título do post" required>
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
                        <button class="btn btn-success" onclick="downloadFile('post')" style="display: none;" id="download-post-btn">📥 Download Post</button>
                        <a href="#" id="open-post-image" class="btn btn-secondary" style="margin-left: 10px; display: none;" target="_blank">🖼️ Abrir Imagem</a>
                    </div>
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
                        <label class="control-label">Cole o texto da notícia ou link</label>
                        <textarea class="control-input" id="legenda-texto" rows="6" placeholder="Cole aqui o texto da notícia ou o link para análise..."></textarea>
                    </div>

                    <div class="loading" id="caption-loading">
                        <div class="spinner"></div>
                        <p>Analisando conteúdo e gerando legendas...</p>
                    </div>

                    <div class="success-message" id="caption-success"></div>
                    <div class="error-message" id="caption-error"></div>

                    <button class="btn btn-primary" onclick="generateCaptions()">🤖 Gerar Legendas</button>
                </div>

                <div class="ai-suggestions" id="caption-suggestions" style="display: none;">
                    <h3>Legenda Sugerida pela IA</h3>
                    <div class="suggestion-item" id="suggested-caption">
                        <p><strong>Legenda sugerida aparecerá aqui</strong></p>
                    </div>
                    <div style="margin-top: 15px;">
                        <button class="btn btn-success" onclick="acceptCaption()">✅ Aceitar Sugestão</button>
                        <button class="btn btn-secondary" onclick="rejectCaption()" style="margin-left: 10px;">❌ Recusar</button>
                    </div>
                </div>

                <div class="controls-section" id="manual-caption" style="display: none;">
                    <div class="control-group">
                        <label class="control-label">Digite a legenda manualmente</label>
                        <textarea class="control-input" id="manual-caption-input" rows="4" placeholder="Digite sua legenda personalizada"></textarea>
                    </div>
                    <button class="btn btn-primary" onclick="saveManualCaption()">💾 Salvar Legenda</button>
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
        // Global state
        let currentTab = 'gerar-posts';
        let selectedFormat = 'reels';
        let selectedTemplate = 'stories_1';
        let uploadedFiles = {};
        let generatedImageUrls = {};

        // Registry of templates by format with preview icon and label
        const TEMPLATE_REGISTRY = {
            watermark: [
                { key: 'watermark', label: "Marca d'Água", icon: '🏷️' },
                { key: 'watermark1', label: 'WaterMark1', icon: '🏷️' }
            ],
            feed: [
                { key: 'feed_1', label: 'Feed - Modelo 1', icon: '🖼️' },
                { key: 'feed_2', label: 'Feed - Modelo 2', icon: '🔴' },
                { key: 'feed_3', label: 'Feed - Modelo 3', icon: '⚪' },
                { key: 'feed_4', label: 'Feed - Modelo 4', icon: '⚫' }
            ],
            stories: [
                { key: 'stories_1', label: 'Stories - Modelo 1', icon: '📱' },
                { key: 'stories_2', label: 'Stories - Modelo 2', icon: '📱' }
            ],
            reels: [
                { key: 'reels_modelo_1', label: 'Reels Feed - Modelo 2', icon: '🎬' },
                { key: 'reels_modelo_2', label: 'Reels Feed - Modelo 2', icon: '🎥' },
                { key: 'reels_modelo_3', label: 'Reels Feed - Modelo 3', icon: '🎥' }
            ]
        };

        const FORMAT_PREVIEW = {
            watermark: "Prévia: aplica apenas a marca d'água sobre a imagem enviada.",
            feed: 'Prévia: post quadrado 1200x1200 com título, assunto e créditos.',
            stories: 'Prévia: vertical 1080x1920 para Stories, otimizado para texto curto.',
            reels: 'Prévia: vertical 1080x1920 para Reels/Feed, foco em vídeo/título.'
        };

        function renderTemplatesForFormat(format) {
            const grid = document.getElementById('template-grid');
            if (!grid) return;
            grid.innerHTML = '';
            const list = TEMPLATE_REGISTRY[format] || [];
            list.forEach((tpl, index) => {
                const div = document.createElement('div');
                div.className = 'template-item' + (index === 0 ? ' selected' : '');
                div.setAttribute('onclick', `selectTemplate('${tpl.key}')`);
                div.innerHTML = `
                    <div class="template-preview">${tpl.icon}</div>
                    <p>${tpl.label}</p>
                `;
                grid.appendChild(div);
                if (index === 0) {
                    selectedTemplate = tpl.key;
                }
            });
            const preview = document.getElementById('format-preview');
            if (preview) preview.textContent = FORMAT_PREVIEW[format] || '';
            updateFieldsForTemplate(selectedTemplate);
        }

        // Tab switching
        function switchTab(tabName) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
            document.getElementById(tabName).classList.add('active');
            
            currentTab = tabName;
        }

        // File upload handling
        function handleFileUpload(input, type) {
            const file = input.files[0];
            if (!file) return;
            
            // Validate file size (16MB limit)
            if (file.size > 16 * 1024 * 1024) {
                showError('Arquivo muito grande. Limite: 16MB', type);
                return;
            }
            
            uploadedFiles[type] = file;
            const reader = new FileReader();
            reader.onload = function(e) {
                const previewElement = document.getElementById(`${type}-preview`);
                if (file.type.startsWith('image/')) {
                    previewElement.innerHTML = `<img src="${e.target.result}" style="max-width: 100%; max-height: 300px; border-radius: 10px; object-fit: contain;">`;
                } else if (file.type.startsWith('video/')) {
                    previewElement.innerHTML = `<video controls style="max-width: 100%; max-height: 300px; border-radius: 10px;"><source src="${URL.createObjectURL(file)}" type="${file.type}"></video>`;
                }
                showSuccess(`Arquivo ${file.name} carregado com sucesso!`, type);
            };
            reader.readAsDataURL(file);
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
            // Initial render of templates for default format
            renderTemplatesForFormat(selectedFormat);
        });

        // Format selection
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
            
            // Render only templates available for the chosen format
            renderTemplatesForFormat(format);
        }

        // Template selection
        function selectTemplate(templateKey) {
            document.querySelectorAll('.template-item').forEach(item => item.classList.remove('selected'));
            
            if (event && event.target) {
                event.target.closest('.template-item').classList.add('selected');
            } else {
                const templateElement = document.querySelector(`[onclick="selectTemplate('${templateKey}')"]`);
                if (templateElement) {
                    templateElement.classList.add('selected');
                }
            }
            
            selectedTemplate = templateKey;
            updateFieldsForTemplate(templateKey);
        }
        
        function updateFieldsForTemplate(templateKey) {
            const assuntoGroup = document.getElementById('assunto-group');
            const creditosGroup = document.getElementById('creditos-group');
            
            if (templateKey.includes('feed')) {
                assuntoGroup.style.display = 'block';
                creditosGroup.style.display = 'block';
            } else {
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            }
        }

        // API call helper
        async function sendToAPI(action, data, file = null) {
            try {
                console.log(`Sending to API: ${action}`);
                
                let formData = new FormData();
                formData.append('action', action);
                formData.append('data', JSON.stringify(data));
                
                if (file) {
                    formData.append('file', file);
                }
                
                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData,
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API error:', error);
                return { success: false, message: 'Error processing request' };
            }
        }

        // Check image status
        async function checkImageStatus(imageId, type) {
            try {
                const response = await fetch(`/api/check-image/${imageId}`);
                const result = await response.json();
                
                if (result.success && result.status === 'finished' && result.imageUrl) {
                    generatedImageUrls[type] = result.imageUrl;
                    const preview = document.getElementById(`${type}-preview`);
                    preview.innerHTML = `<img src="${result.imageUrl}" style="max-width: 100%; max-height: 300px; border-radius: 10px; object-fit: contain;">`;
                    showSuccess(`${type === 'post' ? 'Post' : 'Watermark'} finalizado com sucesso!`, type);
                    
                    // Show download button and open link
                    const downloadBtn = document.getElementById(`download-${type}-btn`);
                    const openBtn = document.getElementById(`open-${type}-image`);
                    
                    if (downloadBtn) downloadBtn.style.display = 'inline-block';
                    if (openBtn) {
                        openBtn.href = result.imageUrl;
                        openBtn.style.display = 'inline-block';
                    }
                } else if (result.success && result.status === 'processing') {
                    setTimeout(() => checkImageStatus(imageId, type), 3000);
                } else {
                    showError(`Erro ao processar ${type}`, type);
                }
            } catch (error) {
                console.error('Error checking status:', error);
                showError(`Erro ao verificar status`, type);
            }
        }

        // Generate post
        async function generatePost() {
            if (!uploadedFiles.post) {
                showError('Por favor, faça upload de um arquivo primeiro.', 'post');
                return;
            }
            
            const titulo = document.getElementById('titulo').value.trim();
            const assunto = document.getElementById('assunto').value.trim();
            const creditos = document.getElementById('creditos').value.trim();
            
            // Validate required fields based on template
            if (selectedTemplate.includes('feed') && (!titulo || !assunto || !creditos)) {
                showError('Para templates de Feed, título, assunto e créditos são obrigatórios.', 'post');
                return;
            }
            
            if (!selectedTemplate.includes('feed') && !selectedTemplate.includes('watermark') && !titulo) {
                showError('O título é obrigatório.', 'post');
                return;
            }
            
            showLoading('post');
            
            const apiResult = await sendToAPI('generate_post', {
                template: selectedTemplate,
                title: titulo,
                subject: assunto,
                credits: creditos
            }, uploadedFiles.post);

            hideLoading('post');
            
            if (apiResult.success) {
                if (apiResult.imageUrl) {
                    generatedImageUrls.post = apiResult.imageUrl;
                    const preview = document.getElementById('post-preview');
                    preview.innerHTML = `<img src="${apiResult.imageUrl}" style="max-width: 100%; max-height: 300px; border-radius: 10px; object-fit: contain;">`;
                    showSuccess('Post gerado com sucesso!', 'post');
                    
                    document.getElementById('download-post-btn').style.display = 'inline-block';
                    document.getElementById('open-post-image').href = apiResult.imageUrl;
                    document.getElementById('open-post-image').style.display = 'inline-block';
                } else if (apiResult.imageId) {
                    showSuccess('Post em processamento. Aguarde...', 'post');
                    checkImageStatus(apiResult.imageId, 'post');
                }
            } else {
                showError(apiResult.message || 'Erro ao gerar post', 'post');
            }
        }

        // Generate title
        async function generateTitle() {
            const texto = document.getElementById('noticia-texto').value.trim();
            if (!texto) {
                showError('Por favor, insira o texto da notícia.', 'title');
                return;
            }
            
            showLoading('title');
            document.getElementById('title-suggestions').style.display = 'none';
            
            const apiResult = await sendToAPI('generate_title_ai', {
                newsContent: texto
            });

            hideLoading('title');
            
            if (apiResult.success && apiResult.suggestedTitle) {
                document.getElementById('suggested-title').innerHTML = `<p><strong>${apiResult.suggestedTitle}</strong></p>`;
                document.getElementById('title-suggestions').style.display = 'block';
                showSuccess('Título gerado com sucesso!', 'title');
            } else {
                showError(apiResult.message || 'Erro ao gerar título', 'title');
            }
        }

        // Accept/reject title
        function acceptTitle() {
            const suggestedTitle = document.getElementById('suggested-title').textContent.trim();
            document.getElementById('manual-title-input').value = suggestedTitle;
            document.getElementById('manual-title').style.display = 'block';
            document.getElementById('title-suggestions').style.display = 'none';
            showSuccess('Título aceito!', 'title');
        }

        function rejectTitle() {
            document.getElementById('manual-title').style.display = 'block';
            document.getElementById('title-suggestions').style.display = 'none';
            document.getElementById('manual-title-input').value = '';
            showError('Título recusado. Digite manualmente.', 'title');
        }

        async function saveManualTitle() {
            const manualTitle = document.getElementById('manual-title-input').value.trim();
            if (!manualTitle) {
                showError('Por favor, digite um título.', 'title');
                return;
            }
            
            showLoading('title');
            const apiResult = await sendToAPI('save_manual_title', {
                manualTitle: manualTitle
            });

            hideLoading('title');
            
            if (apiResult.success) {
                showSuccess('Título salvo com sucesso!', 'title');
            } else {
                showError(apiResult.message || 'Erro ao salvar título', 'title');
            }
        }

        // Generate captions
        async function generateCaptions() {
            const texto = document.getElementById('legenda-texto').value.trim();
            if (!texto) {
                showError('Por favor, insira o texto da notícia.', 'caption');
                return;
            }
            
            showLoading('caption');
            document.getElementById('caption-suggestions').style.display = 'none';

            const apiResult = await sendToAPI('generate_captions_ai', {
                content: texto
            });

            hideLoading('caption');
            
            if (apiResult.success && apiResult.captions && apiResult.captions.length > 0) {
                const firstCaption = apiResult.captions[0];
                document.getElementById('suggested-caption').innerHTML = `<p><strong>${firstCaption}</strong></p>`;
                document.getElementById('caption-suggestions').style.display = 'block';
                showSuccess('Legenda gerada com sucesso!', 'caption');
            } else {
                showError(apiResult.message || 'Erro ao gerar legenda', 'caption');
            }
        }

        // Accept/reject caption
        function acceptCaption() {
            const suggestedCaption = document.getElementById('suggested-caption').textContent.trim();
            document.getElementById('manual-caption-input').value = suggestedCaption;
            document.getElementById('manual-caption').style.display = 'block';
            document.getElementById('caption-suggestions').style.display = 'none';
            showSuccess('Legenda aceita!', 'caption');
        }

        function rejectCaption() {
            document.getElementById('manual-caption').style.display = 'block';
            document.getElementById('caption-suggestions').style.display = 'none';
            document.getElementById('manual-caption-input').value = '';
            showError('Legenda recusada. Digite manualmente.', 'caption');
        }

        async function saveManualCaption() {
            const manualCaption = document.getElementById('manual-caption-input').value.trim();
            if (!manualCaption) {
                showError('Por favor, digite uma legenda.', 'caption');
                return;
            }
            
            showLoading('caption');
            const apiResult = await sendToAPI('save_manual_caption', {
                manualCaption: manualCaption
            });

            hideLoading('caption');
            
            if (apiResult.success) {
                showSuccess('Legenda salva com sucesso!', 'caption');
            } else {
                showError(apiResult.message || 'Erro ao salvar legenda', 'caption');
            }
        }

        // Rewrite news
        async function rewriteNews() {
            const texto = document.getElementById('noticia-original').value.trim();
            if (!texto) {
                showError('Por favor, insira o texto da notícia.', 'rewrite');
                return;
            }
            
            showLoading('rewrite');
            document.getElementById('rewrite-suggestions').style.display = 'none';

            const apiResult = await sendToAPI('rewrite_news_ai', {
                newsContent: texto
            });

            hideLoading('rewrite');
            
            if (apiResult.success && apiResult.rewrittenNews) {
                const rewrittenNews = apiResult.rewrittenNews;
                document.getElementById('rewritten-title').textContent = rewrittenNews.titulo;
                document.getElementById('rewritten-text').textContent = rewrittenNews.texto;
                document.getElementById('rewrite-suggestions').style.display = 'block';
                showSuccess('Notícia reescrita com sucesso!', 'rewrite');
            } else {
                showError(apiResult.message || 'Erro ao reescrever notícia', 'rewrite');
            }
        }

        // Accept/reject rewritten news
        function acceptRewrittenNews() {
            const rewrittenTitle = document.getElementById('rewritten-title').textContent;
            const rewrittenText = document.getElementById('rewritten-text').textContent;
            
            document.getElementById('manual-title-rewrite').value = rewrittenTitle;
            document.getElementById('manual-text-rewrite').value = rewrittenText;
            document.getElementById('manual-rewrite').style.display = 'block';
            document.getElementById('rewrite-suggestions').style.display = 'none';
            showSuccess('Notícia aceita!', 'rewrite');
        }

        function rejectRewrittenNews() {
            document.getElementById('manual-rewrite').style.display = 'block';
            document.getElementById('rewrite-suggestions').style.display = 'none';
            document.getElementById('manual-title-rewrite').value = '';
            document.getElementById('manual-text-rewrite').value = '';
            showError('Notícia recusada. Digite uma versão personalizada.', 'rewrite');
        }

        async function saveManualRewrite() {
            const manualTitle = document.getElementById('manual-title-rewrite').value.trim();
            const manualText = document.getElementById('manual-text-rewrite').value.trim();
            
            if (!manualTitle || !manualText) {
                showError('Por favor, preencha título e texto.', 'rewrite');
                return;
            }
            
            showLoading('rewrite');
            const apiResult = await sendToAPI('save_manual_rewrite', {
                manualTitle: manualTitle,
                manualText: manualText
            });

            hideLoading('rewrite');
            
            if (apiResult.success) {
                showSuccess('Notícia salva com sucesso!', 'rewrite');
            } else {
                showError(apiResult.message || 'Erro ao salvar notícia', 'rewrite');
            }
        }

        // Download file
        function downloadFile(type) {
            const url = generatedImageUrls[type];
            if (!url) {
                showError('Nenhum arquivo gerado para download.', type);
                return;
            }

            if (url.startsWith('data:')) {
                const a = document.createElement('a');
                a.href = url;
                a.download = `${type}_${new Date().getTime()}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                window.open(url, '_blank');
            }
            showSuccess('Download iniciado!', type);
        }

        // UI feedback functions
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
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                successElement.style.display = 'none';
            }, 5000);
        }

        function showError(message, type) {
            const errorElement = document.getElementById(`${type}-error`);
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            document.getElementById(`${type}-success`).style.display = 'none';
            
            // Auto-hide after 10 seconds
            setTimeout(() => {
                errorElement.style.display = 'none';
            }, 10000);
        }
    </script>
</body>
</html>
"""

# Initialize app
if __name__ == '__main__':
    ensure_upload_directory()
    
    logger.info("🚀 Starting SaaS Editor...")
    logger.info(f"🎨 Placid API: {Config.PLACID_API_URL}")
    logger.info(f"📋 Templates available: {len(PLACID_TEMPLATES)}")
    
    for key, template in PLACID_TEMPLATES.items():
        logger.info(f"   - {template['name']}: {template['uuid']}")
    
    logger.info("🌐 Server running on: http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
