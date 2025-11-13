    
# Fix para compatibilidade Pillow 10+ com MoviePy
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from flask import Flask, request, jsonify, render_template_string, send_from_directory, session, redirect, url_for
from functools import wraps
from flask_cors import CORS
import requests
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ✅ CONFIGURAÇÃO DE SENHA E SEGURANÇA
app.secret_key = 'tribuna-hoje-secret-key-2025-mudar-isso-em-producao'
APP_PASSWORD = 'tribunahj2025'  # ⚠️ MUDE ESTA SENHA!

# Decorator para proteger rotas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

import os
# Configuration
class Config:
    PLACID_API_TOKEN ='-mmv6puv1gvuucitb-hhflfvh5yeru1ijl'
    PLACID_API_URL = 'https://api.placid.app/api/rest/images'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
    UPLOAD_FOLDER = os.path.abspath('uploads')
    MAX_FILE_SIZE = 700 * 1024 * 1024  # 700MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'webm', '3gp', 'hevc'}

try:
    # MoviePy is optional; used for extracting frames from videos for reels
    import moviepy.editor as mpe
    logger.info("MoviePy importado com sucesso!")
except ImportError as e:
    logger.error(f"MoviePy não encontrado: {e}")
    mpe = None
except Exception as e:
    logger.error(f"Erro ao importar MoviePy: {type(e).__name__}: {e}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    mpe = None

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

# SUBSTITUA esta parte no seu main.py (linha ~100-150):

LOCAL_REELS_TEMPLATES = {
    'reels_modelo_1': {
        'name': 'Reels - Modelo 1',
        'description': 'Template Tribuna Hoje com título superior',
        'type': 'reels',
        'dimensions': {'width': 1080, 'height': 1920},
        'style': {
            'title_position': 'top',
            'title_background': True,
            'title_color': (255, 255, 255),        # branco
            'background_color': (139, 0, 0),        # vermelho Tribuna Hoje
            'background_pattern': 'subtle_waves',   # ondinhas fraquinhas
            'title_font_size': 48,
            'title_padding': 80,
            'brand_text': 'TRIBUNAHOJE.com',
            'brand_font_size': 32,
            'brand_position': 'top_center',
            'footer_text': 'Somos Coop',
            'footer_font_size': 24,
            'footer_position': 'bottom_center',
            'video_area': {
                'top': 400,      # vídeo no meio
                'bottom': 1300,   
                'overlay_pattern': 'diagonal_lines'  # área cinza listrada para vídeo
            }
        }
    },
    'reels_modelo_2': {
        'name': 'Reels - Modelo 2',
        'description': 'Template Tribuna Hoje com título inferior',
        'type': 'reels',
        'dimensions': {'width': 1080, 'height': 1920},
        'style': {
            'title_position': 'bottom',
            'title_background': True,
            'title_color': (255, 255, 255),        # branco
            'background_color': (139, 0, 0),        # vermelho Tribuna Hoje
            'background_pattern': 'subtle_waves',   # ondinhas fraquinhas
            'title_font_size': 48,
            'title_padding': 80,
            'brand_text': 'TRIBUNAHOJE.com',
            'brand_font_size': 32,
            'brand_position': 'top_center',
            'footer_text': 'Somos Coop',
            'footer_font_size': 24,
            'footer_position': 'bottom_center',
            'video_area': {
                'top': 400,      # vídeo no meio
                'bottom': 1300,   
                'overlay_pattern': 'diagonal_lines'  # área cinza listrada para vídeo
            }
        }
    }
}

# AI Prompts
AI_PROMPTS = {
    'legendas': """Gerador de Legendas Jornalísticas para Instagram

Você é um jornalista especialista em copy para redes sociais, responsável por transformar descrições de notícias em legendas para o Instagram do Jornal Tribuna Hoje.

Sempre que receber uma notícia no campo de entrada, você deve gerar exatamente uma legenda no formato abaixo, seguindo todas as instruções:

Regras obrigatórias:

Análise da Notícia

Leia atentamente o texto fornecido.

Identifique os elementos centrais: quem, o quê, onde e a consequência mais relevante.

Construção da Legenda

Impacto Inicial: Comece com a informação mais importante ou surpreendente.

Contexto: Acrescente de 3 a 4 frases curtas que resumam o fato de forma clara e objetiva.

Tom Jornalístico: Mantenha credibilidade, clareza e objetividade, tom 100% jornalístico = sem abstrações da IA (com exceção do CTA e das tags). Tudo do próprio texto original com as devidas correções ortográficas. Nada de sensacionalismo ou comentários fora do texto.

CTA Estratégico (em linha separada):

Use exatamente essa CTA

"🔗 Leia a matéria completa no nosso site, link da bio."

Hashtags por Assunto (em linha separada): Sempre crie entre 2 a 5 hashtags.

Inclua sempre #tribunahoje.

Use também #alagoas e #maceio quando a notícia for local.

As demais devem ser específicas ao tema (ex.: #saude, #seguranca, #politica, #economia, #clima, #cultura, #esporte).

Todas devem estar em minúsculas, sem acento, sem espaços, sem repetição, separadas apenas por espaço.

Formatação obrigatória da saída:

A saída deve conter exatamente 3 blocos (sem rótulos, sem títulos, sem explicações):

CTA: Em linha única, separado por uma quebra de linha.

Hashtags: Em linha única, todas em minúsculas.

Ortografia Obrigatória: Use exclusivamente a ortografia oficial da língua portuguesa do Brasil conforme o Novo Acordo Ortográfico. Não cometa erros de grafia, acentuação, concordância ou pontuação. Revise cuidadosamente antes de enviar.

Resposta Direta: Retorne SOMENTE o texto final no formato esperado, sem comentários, explicações ou qualquer texto adicional.
""",


    'titulo': """Gerador Avançado de Títulos Jornalísticos Impactantes

Você é um jornalista especialista em copy de Instagram para jornalismo, capaz de transformar descrições de notícias em títulos chamativos, irresistíveis e padronizados para postagens no feed da Tribuna Hoje.

Sempre que receber uma descrição de notícia, siga rigorosamente estas instruções:

📌 Regras obrigatórias:

Análise Completa:

Identifique os elementos centrais (quem, o quê, onde, consequência mais relevante).

Foco no Impacto:

O título deve começar pelo dado mais forte ou pela consequência mais grave, mesmo que esteja implícito ou ao final do texto original.

Inversão Dramática:

Traga o clímax da notícia para o início e mantenha fluidez na construção.

Ênfase Visual:

Coloque até DUAS palavras em MAIÚSCULAS para chamar atenção imediata.

Formatação Padronizada:

Escreva todas as palavras com a primeira letra maiúscula.

Limite de Caracteres:

O título deve ter entre 80 e 90 caracteres, contando espaços e pontuação.

Se ultrapassar 90, corte na palavra onde exceder e finalize imediatamente com reticências (...).

Proibição de Repetição Literal:

Nunca copie a descrição original; sempre reescreva com nova estrutura e impacto.

Ortografia Obrigatória: Use exclusivamente a ortografia oficial da língua portuguesa do Brasil conforme o Novo Acordo Ortográfico. Não cometa erros de grafia, acentuação, concordância ou pontuação. Revise cuidadosamente antes de enviar.

Resposta Direta: Retorne SOMENTE o texto final no formato esperado, sem comentários, explicações ou qualquer texto adicional.

Sua tarefa: Gerar apenas o título final com base na notícia completa dada na caixa de texto, seguindo todas as regras acima.""",

    'reescrita': """Modelador de Notícias – Estilo Tribuna Hoje

Você é um jornalista sênior com mais de 10 anos de experiência em redação e jornalismo sério. Sua função é transformar qualquer notícia recebida em um texto jornalístico no estilo do Tribuna Hoje, mantendo credibilidade, clareza e a identidade de um veículo tradicional.
Tonalidade:

Séria, institucional e objetiva.

Imparcial, 100% jornalístico, apenas mude algumas palavras da noticia original, mas sem fugir do contexto.

Nada de sensacionalismo ou clickbait.

Estrutura da Notícia:

Título: Claro e direto, sem exageros.

Subtítulo (opcional): Usar apenas quando agregar contexto.

Lide (1º parágrafo): Traga logo a informação principal (quem, o quê, quando, onde e por quê).

Desenvolvimento: Acrescente contexto político, social e histórico para explicar o impacto da notícia.

Estilo Tribuna Hoje:

Clareza e objetividade acima de tudo.

Linguagem jornalística padrão, sem gírias e 100% de acordo com a língua portuguesa, não cometa erros ortográficos.

Foco no impacto político, social ou econômico.

Tratar a informação com responsabilidade e reforçar credibilidade.

Título no topo.

Subtítulo (quando necessário).

Texto corrido entre 4 e 8 parágrafos.

Instrução Final:

Sempre que receber uma notícia ou descrição, reescreva-a no formato jornalístico da Tribuna Hoje.
Retorne apenas a versão final da notícia modelada (Título + texto), sem comentários, explicações ou marcações adicionais."""
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

def is_video_extension(ext: str) -> bool:
    return ext.lower() in {"mp4", "mov", "mkv", "webm", "avi"}

def extract_image_from_video(video_path: str, prefix: str = "frame") -> Optional[str]:
    """Extract a representative frame from a video and save as PNG. Returns image filepath or None."""
    try:
        if mpe is None:
            logger.error("MoviePy não está disponível - verifique instalação")
            return None
        clip = mpe.VideoFileClip(video_path)
        duration = max(clip.duration or 0, 0)
        # Choose frame at 1s or middle if shorter
        t = 1.0 if duration >= 2.0 else max(duration / 2.0, 0.0)
        frame = clip.get_frame(t)
        image = Image.fromarray(frame)
        filename = generate_filename(prefix, "png")
        out_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        ensure_upload_directory()
        image.save(out_path, format="PNG")
        try:
            clip.close()
        except Exception:
            pass
        return out_path
    except Exception as e:
        logger.error(f"Failed to extract frame from video: {type(e).__name__}: {e}")
        return None

def generate_local_reels_image(source_media_path: str, title_text: str, template_key: str) -> Optional[Tuple[str, str]]:
    """
    Create a vertical 1080x1920 PNG for reels using the provided media (image or video frame) and title.
    Returns (filepath, public_url) or None.
    """
    try:
        # If source is video, extract frame
        ext = os.path.splitext(source_media_path)[1].lower().lstrip('.')
        if is_video_extension(ext):
            frame_path = extract_image_from_video(source_media_path, prefix="reels_frame")
            if not frame_path:
                return None
            base_image_path = frame_path
        else:
            base_image_path = source_media_path

        # Canvas setup
        width, height = 1080, 1920
        canvas = Image.new("RGB", (width, height), color=(0, 0, 0))

        # Load source image
        with Image.open(base_image_path) as src:
            src = src.convert("RGB")
            # Fit source to canvas while maintaining aspect ratio
            src_ratio = src.width / src.height
            canvas_ratio = width / height
            if src_ratio > canvas_ratio:
                # source is wider -> fit width
                new_width = width
                new_height = int(new_width / src_ratio)
            else:
                # source is taller -> fit height
                new_height = height
                new_width = int(new_height * src_ratio)
            resized = src.resize((new_width, new_height), Image.LANCZOS)
            # Paste centered
            x = (width - new_width) // 2
            y = (height - new_height) // 2
            canvas.paste(resized, (x, y))

        # Draw title overlay (simple, top area with semi-transparent band)
        draw = ImageDraw.Draw(canvas, 'RGBA')
        band_height = 180
        overlay_color = (0, 0, 0, 140)
        draw.rectangle([(0, 0), (width, band_height)], fill=overlay_color)

        # Load font (fallback to default if no TTF available)
        font = None
        try:
            # Try a common font if available on system
            font = ImageFont.truetype("arial.ttf", 64)
        except Exception:
            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
            except Exception:
                font = ImageFont.load_default()

        # Title text wrap simple: truncate if too long
        text = title_text or ""
        max_width_px = width - 120
        if hasattr(draw, 'textlength'):
            while text and draw.textlength(text, font=font) > max_width_px:
                text = text[:-1]
        else:
            # Fallback approximate using bbox
            while text:
                bbox = draw.textbbox((0, 0), text, font=font)
                if bbox[2] - bbox[0] <= max_width_px:
                    break
                text = text[:-1]

        # Centered title
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (width - text_w) // 2
        text_y = (band_height - text_h) // 2
        # Outline for readability
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
            draw.text((text_x+dx, text_y+dy), text, font=font, fill=(255,255,255,60))
        draw.text((text_x, text_y), text, font=font, fill=(255,255,255,230))

        # Save result
        out_filename = generate_filename(template_key, "png")
        out_path = os.path.join(Config.UPLOAD_FOLDER, out_filename)
        ensure_upload_directory()
        canvas.save(out_path, format="PNG")
        public_url = f"{request.url_root}uploads/{out_filename}"
        return out_path, public_url
    except Exception as e:
        logger.error(f"Failed to generate local reels image: {type(e).__name__}: {e}")
        return None

def _build_title_overlay_image(width: int, band_height: int, title_text: str) -> Image.Image:
    canvas = Image.new("RGBA", (width, band_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, 'RGBA')
    draw.rectangle([(0, 0), (width, band_height)], fill=(0, 0, 0, 140))
    # Font
    try:
        font = ImageFont.truetype("arial.ttf", 64)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        except Exception:
            font = ImageFont.load_default()
    text = title_text or ""
    max_width_px = width - 120
    if hasattr(draw, 'textlength'):
        while text and draw.textlength(text, font=font) > max_width_px:
            text = text[:-1]
    else:
        while text:
            bbox = draw.textbbox((0, 0), text, font=font)
            if bbox[2] - bbox[0] <= max_width_px:
                break
            text = text[:-1]
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (width - text_w) // 2
    text_y = (band_height - text_h) // 2
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
        draw.text((text_x+dx, text_y+dy), text, font=font, fill=(255,255,255,60))
    draw.text((text_x, text_y), text, font=font, fill=(255,255,255,230))
    return canvas

def _create_title_overlay_for_template(width: int, height: int, title_text: str, style: dict) -> Optional[Image.Image]:
    """
    Cria um overlay de título baseado no estilo do template Tribuna Hoje.
    """
    if not title_text:
        return None
    
    try:
        # Carrega fonte
        font_size = style.get('title_font_size', 48)
        brand_font_size = style.get('brand_font_size', 32)
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
            brand_font = ImageFont.truetype("arial.ttf", brand_font_size)
        except Exception:
            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
                brand_font = ImageFont.truetype("DejaVuSans-Bold.ttf", brand_font_size)
            except Exception:
                font = ImageFont.load_default()
                brand_font = ImageFont.load_default()
        
        # Calcula dimensões
        text = title_text.strip().upper()  # Tribuna Hoje usa maiúsculas
        if not text:
            return None
        
        # Quebra texto em múltiplas linhas se necessário
        max_width = width - (style.get('title_padding', 80) * 2)
        lines = _wrap_text(text, font, max_width)
        
        # Calcula altura da área do título
        line_height = font_size + 15
        text_height = len(lines) * line_height
        brand_height = brand_font_size + 10
        total_content_height = text_height + brand_height + 30  # espaço entre elementos
        
        # Área total da faixa (com padding)
        band_height = total_content_height + (style.get('title_padding', 80) * 2)
        
        # Cria canvas para o overlay
        overlay = Image.new("RGBA", (width, band_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, 'RGBA')
        
        # Fundo vermelho da faixa
        bg_color = style.get('background_color', (139, 0, 0))
        bg_rgba = (*bg_color, 255)  # vermelho sólido
        draw.rectangle([(0, 0), (width, band_height)], fill=bg_rgba)
        
        # Posição inicial do texto
        text_color = style.get('title_color', (255, 255, 255))
        y_offset = style.get('title_padding', 80)
        
        # Desenha o título
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = (width - text_w) // 2  # centralizado
            
            # Texto principal em branco
            draw.text((text_x, y_offset), line, font=font, fill=text_color)
            y_offset += line_height
        
        # Adiciona espaço entre título e marca
        y_offset += 20
        
        # Desenha a marca "TRIBUNAHOJE.com"
        brand_text = style.get('brand_text', 'TRIBUNAHOJE.com')
        bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        brand_w = bbox[2] - bbox[0]
        brand_x = (width - brand_w) // 2
        draw.text((brand_x, y_offset), brand_text, font=brand_font, fill=text_color)
        
        return overlay
        
    except Exception as e:
        logger.error("Erro ao criar overlay Tribuna Hoje: {e}")
        return None

def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list:
    """
    Quebra texto em múltiplas linhas para caber na largura especificada.
    """
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line) if hasattr(font, 'getbbox') else font.getsize(test_line)
        text_width = bbox[2] - bbox[0] if hasattr(font, 'getbbox') else bbox[0]
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Palavra muito longa, adiciona mesmo assim
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines
def convert_video_if_needed(input_path: str) -> str:
    """
    Converte vídeos em formatos problemáticos (HEVC, MOV Apple) para MP4 H.264
    Retorna o caminho do vídeo convertido ou o original se não precisar converter
    """
    if mpe is None:
        logger.warning("MoviePy não disponível, pulando conversão")
        return input_path
    
    try:
        # Detecta se precisa converter
        needs_conversion = False
        
        # Verifica extensão
        ext = os.path.splitext(input_path)[1].lower()
        if ext in ['.mov', '.hevc', '.3gp']:
            needs_conversion = True
            logger.info(f"🔄 Arquivo {ext} detectado, precisa converter")
        
        # Tenta carregar o vídeo
        try:
            test_clip = mpe.VideoFileClip(input_path)
            codec = getattr(test_clip, 'codec', 'unknown')
            if 'hevc' in str(codec).lower() or 'h265' in str(codec).lower():
                needs_conversion = True
                logger.info(f"🔄 Codec {codec} detectado, precisa converter")
            test_clip.close()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar codec: {e}, tentando conversão")
            needs_conversion = True
        
        # Se não precisa converter, retorna o original
        if not needs_conversion:
            logger.info("✅ Vídeo já está em formato compatível")
            return input_path
        
        # Converte o vídeo
        logger.info("🔄 Convertendo vídeo para MP4 H.264...")
        converted_filename = generate_filename("converted", "mp4")
        converted_path = os.path.join(Config.UPLOAD_FOLDER, converted_filename)
        
        clip = mpe.VideoFileClip(input_path)
        
        # Exporta com configurações compatíveis
        clip.write_videofile(
            converted_path,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            fps=30,
            bitrate='2000k',
            verbose=False,
            logger=None
        )
        
        clip.close()
        
        logger.info(f"✅ Vídeo convertido: {converted_path}")
        return converted_path
        
    except Exception as e:
        logger.error(f"❌ Erro ao converter vídeo: {e}")
        # Se falhar, retorna o original e deixa o MoviePy tentar processar
        return input_path
        
def generate_local_reels_video(source_media_path: str, title_text: str, template_key: str) -> Optional[Tuple[str, str]]:
    """
    Gera um vídeo de reels usando template de fundo.
    OTIMIZADO PARA VÍDEOS DE ATÉ 10 MINUTOS E FORMATOS MOBILE
    Returns (filepath, public_url) or None.
    """
    if mpe is None:
        logger.error("MoviePy não está disponível - verifique instalação")
        logger.error("Tente: pip install moviepy imageio imageio-ffmpeg")
        return None
    
    logger.info("Iniciando geração de Reels...")
    logger.info(f"Arquivo de entrada: {source_media_path}")
    
    # NOVO: Converte vídeos mobile se necessário
    source_media_path = convert_video_if_needed(source_media_path)
    
    logger.info("Testando importações do MoviePy...")
    try:
        from moviepy.editor import VideoFileClip, ImageClip, ColorClip, CompositeVideoClip, TextClip
        logger.info("Importações básicas OK")
    except Exception as e:
        logger.error(f"Falha nas importações: {e}")
        return None
    
    # Verifica se o template existe
    if template_key not in LOCAL_REELS_TEMPLATES:
        logger.error(f"Template de reels não encontrado: {template_key}")
        return None
    
    template = LOCAL_REELS_TEMPLATES[template_key]
    
    try:
        width, height = template['dimensions']['width'], template['dimensions']['height']
        logger.info(f"Gerando reels com template: {template['name']}")
        logger.info(f"Dimensões do template final: {width}x{height}")
        
        # Carrega o vídeo ou converte imagem para vídeo
        clip = None
        logger.info(f"Verificando arquivo: {os.path.exists(source_media_path)}")
        logger.info(f"Tamanho do arquivo: {os.path.getsize(source_media_path)} bytes")
        try:
            clip = mpe.VideoFileClip(source_media_path)
            logger.info(f"Vídeo original carregado: {clip.w}x{clip.h}, duração: {clip.duration}s")
            logger.info(f"Proporção do vídeo original: {clip.w/clip.h:.3f}")
        except Exception as e:
            logger.error(f"Erro específico ao carregar vídeo: {type(e).__name__}: {e}")
            logger.info("Convertendo imagem para vídeo")
            try:
                with Image.open(source_media_path) as img:
                    img = img.convert('RGB')
                    temp_img = generate_filename("reels_from_image", "png")
                    temp_path = os.path.join(Config.UPLOAD_FOLDER, temp_img)
                    ensure_upload_directory()
                    img.save(temp_path, format='PNG')
                image_clip = mpe.ImageClip(temp_path).set_duration(5)
                clip = image_clip.set_fps(30)
                logger.info("Imagem convertida para vídeo com sucesso")
            except Exception as e2:
                logger.error(f"Falha ao abrir mídia: {type(e2).__name__}: {e2}")
                return None

        # Carrega a imagem de fundo baseada no template selecionado
        if template_key == 'reels_modelo_2':
            template_bg_path = os.path.join(os.path.dirname(__file__), "template2.jpg")
        else:
            template_bg_path = os.path.join(os.path.dirname(__file__), "template1.jpg")
            
        if not os.path.exists(template_bg_path):
            logger.error(f"Imagem de template não encontrada: {template_bg_path}")
            logger.error(f"Template key: {template_key}")
            return None
        
        logger.info(f"Usando template de fundo: {template_bg_path}")
        
        # Cria o fundo usando a imagem template esticando para ocupar toda a tela
        bg = mpe.ImageClip(template_bg_path).set_duration(clip.duration).resize((width, height))
        logger.info(f"Fundo esticado para ocupar toda a tela: {width}x{height}")
        
        # NOVA LÓGICA: Vídeo preenchendo toda a largura do template
        video_area_top = 400
        video_area_bottom = 1520
        video_area_height = video_area_bottom - video_area_top
        
        video_target_width = width
        
        original_aspect_ratio = clip.w / clip.h
        video_target_height = int(video_target_width / original_aspect_ratio)
        
        logger.info(f"Proporção original do vídeo: {original_aspect_ratio:.3f}")
        logger.info(f"Dimensões calculadas para largura total: {video_target_width}x{video_target_height}")
        
        if video_target_height > video_area_height:
            video_target_height = video_area_height
            video_target_width = int(video_target_height * original_aspect_ratio)
            logger.info(f"Ajustado por altura disponível: {video_target_width}x{video_target_height}")
        
        resized_clip = clip.resize(newsize=(video_target_width, video_target_height))
        
        video_x = (width - video_target_width) // 2
        video_y = video_area_top + (video_area_height - video_target_height) // 2
        positioned_video = resized_clip.set_position((video_x, video_y))
        
        logger.info(f"Vídeo redimensionado para: {video_target_width}x{video_target_height}")
        logger.info(f"Posição do vídeo: ({video_x}, {video_y})")

        title_clip = None
        if title_text:
            try:
                if template_key == 'reels_modelo_2':
                    canvas_height = 250
                    font_size = 51
                    line_height = 70
                    text_align = 'left'
                    margin_left = 90
                    title_y_position = video_area_top - 7
                else:
                    canvas_height = 400
                    font_size = 50
                    line_height = 70
                    text_align = 'center'
                    margin_left = 60
                    title_y_position = video_area_top - 62
                
                title_img = Image.new('RGBA', (width, canvas_height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(title_img)
                
                font = None
                try:
                    font = ImageFont.truetype("Oswald-Bold.ttf", font_size)
                    logger.info(f"Fonte Oswald-Bold.ttf carregada: {font_size}px")
                except Exception:
                    try:
                        font = ImageFont.truetype("arialbd.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()
                
                text = title_text.upper().strip()
                max_width = width - (margin_left * 2)
                
                words = text.split()
                lines = []
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_width <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                total_height = len(lines) * line_height
                start_y = (canvas_height - total_height) // 2
                
                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_align == 'left':
                        x = margin_left
                    else:
                        x = (width - text_width) // 2
                    
                    y = start_y + i * line_height
                    
                    draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
                
                title_filename = generate_filename("title_overlay", "png")
                title_path = os.path.join(Config.UPLOAD_FOLDER, title_filename)
                ensure_upload_directory()
                title_img.save(title_path, format='PNG')
                
                title_clip = mpe.ImageClip(title_path).set_duration(clip.duration).set_position((0, title_y_position))
                logger.info(f"Título criado: {template_key}, align={text_align}, size={font_size}px")
                
            except Exception as e:
                logger.error(f"Falha ao criar título: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

        clips_to_compose = [bg, positioned_video]
        if title_clip:
            clips_to_compose.append(title_clip)
        
        composed = mpe.CompositeVideoClip(clips_to_compose)

        try:
            if hasattr(clip, 'audio') and clip.audio is not None:
                composed = composed.set_audio(clip.audio)
                logger.info("Áudio original preservado")
        except Exception as e:
            logger.warning(f"Não foi possível preservar áudio: {e}")

        out_filename = generate_filename(template_key, "mp4")
        out_path = os.path.join(Config.UPLOAD_FOLDER, out_filename)
        
        fps = None
        try:
            fps = int(getattr(clip, 'fps', 30) or 30)
        except Exception:
            fps = 30

        logger.info(f"Exportando vídeo para: {out_path}")
        try:
            composed.write_videofile(
                out_path,
                fps=min(max(fps, 24), 60),
                codec='libx264',
                audio_codec='aac',
                threads=8,
                preset='veryfast',
                verbose=False,
                logger=None
            )
            logger.info("Exportação concluída!")
        except Exception as e:
            logger.error(f"Erro na exportação: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback exportação: {traceback.format_exc()}")
            return None

        try:
            if clip is not None:
                clip.close()
            if 'resized_clip' in locals():
                resized_clip.close()
            if 'composed' in locals():
                composed.close()
            if title_clip is not None:
                title_clip.close()
        except Exception:
            pass

        public_url = f"{request.url_root}uploads/{out_filename}"
        logger.info(f"Reels gerado com sucesso: {public_url}")
        return out_path, public_url
        
    except Exception as e:
        logger.error(f"Falha ao gerar vídeo local de reels: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None
    
def generate_local_capa_jornal(source_media_path: str) -> Optional[Tuple[str, str]]:
    """
    Gera uma imagem de capa de jornal sobrepondo a foto do usuário no template.
    Returns (filepath, public_url) or None.
    """
    try:
        template_bg_path = os.path.join(os.path.dirname(__file__), "template_capa_jornal.jpg")
        
        if not os.path.exists(template_bg_path):
            logger.error(f"Template de capa não encontrado: {template_bg_path}")
            return None
        
        logger.info(f"Carregando template de capa: {template_bg_path}")
        
        # Carrega o template de fundo
        background = Image.open(template_bg_path).convert('RGB')
        bg_width, bg_height = background.size
        logger.info(f"Template carregado: {bg_width}x{bg_height}")
        
        # Carrega a imagem do usuário
        with Image.open(source_media_path) as user_img:
            user_img = user_img.convert('RGB')
            user_width, user_height = user_img.size
            logger.info(f"Imagem do usuário: {user_width}x{user_height}")
            
            # ✨ ÁREA MAIOR - ajuste estes valores para aumentar/diminuir ✨
            target_x = 30           # Posição horizontal (menor = mais à esquerda)
            target_y = 12           # Posição vertical (menor = mais acima)
            max_width = 970         # Largura máxima (AUMENTE para imagem maior)
            max_height = 1300       # Altura máxima (AUMENTE para imagem maior)
            
            # Calcula a proporção da imagem do usuário
            user_aspect = user_width / user_height
            
            logger.info(f"Proporção da imagem: {user_aspect:.3f}")
            
            # ✅ Redimensiona para CABER na área (FIT, não FILL)
            # Isso garante que NADA seja cortado!
            if user_width / max_width > user_height / max_height:
                # Imagem limitada pela LARGURA
                new_width = max_width
                new_height = int(max_width / user_aspect)
            else:
                # Imagem limitada pela ALTURA
                new_height = max_height
                new_width = int(max_height * user_aspect)
            
            logger.info(f"Redimensionando para: {new_width}x{new_height} (SEM CORTE)")
            user_img_resized = user_img.resize((new_width, new_height), Image.LANCZOS)
            
            # ✅ Centraliza a imagem na área disponível (sem cortar!)
            final_x = target_x + (max_width - new_width) // 2
            final_y = target_y + (max_height - new_height) // 2
            
            # Cola a imagem do usuário no template
            background.paste(user_img_resized, (final_x, final_y))
            logger.info(f"Imagem colada COMPLETA na posição: ({final_x}, {final_y})")
        
        # Salva o resultado
        out_filename = generate_filename("feed_capa_jornal", "png")
        out_path = os.path.join(Config.UPLOAD_FOLDER, out_filename)
        ensure_upload_directory()
        background.save(out_path, format="PNG", quality=95)
        
        public_url = f"{request.url_root}uploads/{out_filename}"
        logger.info(f"Capa de jornal gerada: {public_url}")
        
        return out_path, public_url
        
    except Exception as e:
        logger.error(f"Erro ao gerar capa de jornal: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

    # Teste de componentes MoviePy
    logger.info("Testando importações do MoviePy...")
    try:
        from moviepy.editor import VideoFileClip, ImageClip, ColorClip, CompositeVideoClip, TextClip
        logger.info("Importações básicas OK")
    except Exception as e:
        logger.error(f"Falha nas importações: {e}")
        return None
    
    # Verifica se o template existe
    if template_key not in LOCAL_REELS_TEMPLATES:
        logger.error(f"Template de reels não encontrado: {template_key}")
        return None
    
    template = LOCAL_REELS_TEMPLATES[template_key]
    
    try:
        width, height = template['dimensions']['width'], template['dimensions']['height']
        logger.info(f"Gerando reels com template: {template['name']}")
        logger.info(f"Dimensões do template final: {width}x{height}")
        
        # Carrega o vídeo ou converte imagem para vídeo
        clip = None
        logger.info(f"Verificando arquivo: {os.path.exists(source_media_path)}")
        logger.info(f"Tamanho do arquivo: {os.path.getsize(source_media_path)} bytes")
        try:
            clip = mpe.VideoFileClip(source_media_path)
            logger.info(f"Vídeo original carregado: {clip.w}x{clip.h}, duração: {clip.duration}s")
            logger.info(f"Proporção do vídeo original: {clip.w/clip.h:.3f}")
        except Exception as e:
            logger.error(f"Erro específico ao carregar vídeo: {type(e).__name__}: {e}")
            # Se não for vídeo, criar um vídeo curto a partir de imagem
            logger.info("Convertendo imagem para vídeo")
            try:
                with Image.open(source_media_path) as img:
                    img = img.convert('RGB')
                    temp_img = generate_filename("reels_from_image", "png")
                    temp_path = os.path.join(Config.UPLOAD_FOLDER, temp_img)
                    ensure_upload_directory()
                    img.save(temp_path, format='PNG')
                image_clip = mpe.ImageClip(temp_path).set_duration(5)
                clip = image_clip.set_fps(30)
                logger.info("Imagem convertida para vídeo com sucesso")
            except Exception as e2:
                logger.error(f"Falha ao abrir mídia: {type(e2).__name__}: {e2}")
                return None

        # Carrega a imagem de fundo baseada no template selecionado
        if template_key == 'reels_modelo_2':
            template_bg_path = os.path.join(os.path.dirname(__file__), "template2.jpg")
        else:
            template_bg_path = os.path.join(os.path.dirname(__file__), "template1.jpg")
            
        if not os.path.exists(template_bg_path):
            logger.error(f"Imagem de template não encontrada: {template_bg_path}")
            logger.error(f"Template key: {template_key}")
            return None
        
        logger.info(f"Usando template de fundo: {template_bg_path}")
        
        # Cria o fundo usando a imagem template esticando para ocupar toda a tela
        bg = mpe.ImageClip(template_bg_path).set_duration(clip.duration).resize((width, height))
        logger.info(f"Fundo esticado para ocupar toda a tela: {width}x{height}")
        
        # NOVA LÓGICA: Vídeo preenchendo toda a largura do template
        # Área disponível para vídeo: deixa espaço para título
        video_area_top = 400  # Espaço para título
        video_area_bottom = 1520  # Espaço na parte inferior
        video_area_height = video_area_bottom - video_area_top
        
        # MUDANÇA PRINCIPAL: Vídeo ocupa toda a largura do template
        video_target_width = width  # Largura total do template (1080px)
        
        # Calcula altura proporcional baseada na largura total
        original_aspect_ratio = clip.w / clip.h
        video_target_height = int(video_target_width / original_aspect_ratio)
        
        logger.info(f"Proporção original do vídeo: {original_aspect_ratio:.3f}")
        logger.info(f"Dimensões calculadas para largura total: {video_target_width}x{video_target_height}")
        
        # Verifica se a altura calculada cabe na área disponível
        if video_target_height > video_area_height:
            # Se não couber, ajusta pela altura disponível
            video_target_height = video_area_height
            video_target_width = int(video_target_height * original_aspect_ratio)
            logger.info(f"Ajustado por altura disponível: {video_target_width}x{video_target_height}")
        
        # Redimensiona o vídeo para as dimensões calculadas
        resized_clip = clip.resize(newsize=(video_target_width, video_target_height))
        
        # Centraliza o vídeo na área disponível
        video_x = (width - video_target_width) // 2  # Centralizado horizontalmente
        video_y = video_area_top + (video_area_height - video_target_height) // 2  # Centralizado verticalmente na área
        positioned_video = resized_clip.set_position((video_x, video_y))
        
        logger.info(f"Vídeo redimensionado para: {video_target_width}x{video_target_height}")
        logger.info(f"Posição do vídeo: ({video_x}, {video_y})")
        logger.info(f"Proporção do vídeo final: {video_target_width/video_target_height:.3f}")
        logger.info(f"Proporção do template final: {width/height:.3f}")

# Cria o título usando PIL
        title_clip = None
        if title_text:
            try:
                # Configurações diferentes por template
                if template_key == 'reels_modelo_2':
                    # MODELO 2: Texto menor, alinhado à esquerda
                    canvas_height = 250
                    font_size = 51
                    line_height = 70
                    text_align = 'left'
                    margin_left = 90
                    title_y_position = video_area_top - 7
                else:
                    # MODELO 1: Texto grande, centralizado
                    canvas_height = 400
                    font_size = 50
                    line_height = 70
                    text_align = 'center'
                    margin_left = 60
                    title_y_position = video_area_top - 62
                
                # Cria canvas
                title_img = Image.new('RGBA', (width, canvas_height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(title_img)
                
                # Carrega fonte
                font = None
                try:
                    font = ImageFont.truetype("Oswald-Bold.ttf", font_size)
                    logger.info(f"Fonte Oswald-Bold.ttf carregada: {font_size}px")
                except Exception:
                    try:
                        font = ImageFont.truetype("arialbd.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()
                
                # Texto em CAIXA ALTA
                text = title_text.upper().strip()
                max_width = width - (margin_left * 2)
                
                # Quebra o texto em múltiplas linhas
                words = text.split()
                lines = []
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    text_width = bbox[2] - bbox[0]
                    
                    if text_width <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                            current_line = [word]
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Desenha o texto
                total_height = len(lines) * line_height
                start_y = (canvas_height - total_height) // 2
                
                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    
                    # Alinhamento: esquerda ou centro
                    if text_align == 'left':
                        x = margin_left
                    else:
                        x = (width - text_width) // 2
                    
                    y = start_y + i * line_height
                    
                    # Texto branco apenas
                    draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
                
                # Salva e cria clip
                title_filename = generate_filename("title_overlay", "png")
                title_path = os.path.join(Config.UPLOAD_FOLDER, title_filename)
                ensure_upload_directory()
                title_img.save(title_path, format='PNG')
                
                title_clip = mpe.ImageClip(title_path).set_duration(clip.duration).set_position((0, title_y_position))
                logger.info(f"Título criado: {template_key}, align={text_align}, size={font_size}px")
                
            except Exception as e:
                logger.error(f"Falha ao criar título: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")


        # Composição final: fundo + vídeo + título
        clips_to_compose = [bg, positioned_video]
        if title_clip:
            clips_to_compose.append(title_clip)
        
        composed = mpe.CompositeVideoClip(clips_to_compose)

        # Preserva áudio original se existir
        try:
            if hasattr(clip, 'audio') and clip.audio is not None:
                composed = composed.set_audio(clip.audio)
                logger.info("Áudio original preservado")
        except Exception as e:
            logger.warning(f"Não foi possível preservar áudio: {e}")

        # Exporta o vídeo
        out_filename = generate_filename(template_key, "mp4")
        out_path = os.path.join(Config.UPLOAD_FOLDER, out_filename)
        
        fps = None
        try:
            fps = int(getattr(clip, 'fps', 30) or 30)
        except Exception:
            fps = 30

        logger.info(f"Exportando vídeo para: {out_path}")
        try:
            composed.write_videofile(
                out_path,
                fps=min(max(fps, 24), 60),
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='veryfast',
                verbose=False,
                logger=None
            )
            logger.info("Exportação concluída!")
        except Exception as e:
            logger.error(f"Erro na exportação: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback exportação: {traceback.format_exc()}")
            return None

        # Cleanup
        try:
            if clip is not None:
                clip.close()
            if 'resized_clip' in locals():
                resized_clip.close()
            if 'composed' in locals():
                composed.close()
            if title_clip is not None:
                title_clip.close()
        except Exception:
            pass

        public_url = f"{request.url_root}uploads/{out_filename}"
        logger.info(f"Reels gerado com sucesso: {public_url}")
        return out_path, public_url
        
    except Exception as e:
        logger.error(f"Falha ao gerar vídeo local de reels: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def call_openai_api(prompt: str, content: str, max_tokens: int = 1000) -> Optional[str]:
    """Call OpenAI API with error handling and retries"""
    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY == '':
        logger.warning("OpenAI API key not configured")
        return None
    
    # Truncate content to prevent API limits
    if len(content) > 4000:
        content = content[:4000] + "..."
    
    full_prompt = f"{prompt}\n\nConteúdo para processar:\n{content}"
    
    if len(full_prompt) > 12000:
        full_prompt = full_prompt[:12000] + "..."
    
    headers = {
        'Authorization': f'Bearer {Config.OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Você é um assistente especializado em jornalismo."},
            {"role": "user", "content": full_prompt}
        ],
        "max_tokens": min(max_tokens, 1000),
        "temperature": 0.7
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Calling OpenAI API (attempt {attempt + 1})")
            response = requests.post(
                Config.OPENAI_API_URL, 
                json=payload, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
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
            layers["creditfoto"] = {"text": f" {credits}"}
            logger.info(f"✅ Added credits layer: {credits}")
        else:
            logger.info("⏭️ No credits provided")
            
        
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
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login com senha"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == APP_PASSWORD:
            session['logged_in'] = True
            logger.info("✅ Login bem-sucedido!")
            return redirect(url_for('index'))
        else:
            logger.warning("❌ Tentativa de login falhou!")
            return render_template_string(LOGIN_TEMPLATE, error=True)
    
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    return render_template_string(LOGIN_TEMPLATE, error=False)

@app.route('/logout')
def logout():
    """Logout do sistema"""
    session.pop('logged_in', None)
    logger.info("🔒 Usuário deslogado")
    return redirect(url_for('login'))

@app.route('/')
@login_required  # ← ADICIONE ESTA LINHA
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
    
    file = request.files.get('file') if hasattr(request, 'files') else None
    
    if not file:
        logger.error("❌ No file provided")
        return jsonify(error_response("No file provided"))
    
    logger.info("✅ File validation passed")
    
    # Validate required fields
    template_key = payload.get('template', 'feed_1')
    title = payload.get('title', '')
    subject = payload.get('subject', '')
    credits = payload.get('credits', '')
    
    logger.info(f"🎯 Template key: {template_key}")
    
    # Check if it's the capa de jornal template
    if template_key == 'feed_capa_jornal':
        logger.info("📰 Using local capa de jornal compositor")
        success, filepath, public_url = save_uploaded_file(file, "post")
        
        if not success:
            logger.error(f"File upload failed: {public_url}")
            return jsonify(error_response(public_url))
        
        generated = generate_local_capa_jornal(filepath)
        if not generated:
            return jsonify(error_response("Falha ao gerar capa de jornal"))
        
        _, public_out_url = generated
        return jsonify(success_response(
            "Capa de jornal gerada com sucesso!",
            imageUrl=public_out_url
        ))
    
    # Check if it's a local reels template
    if template_key in LOCAL_REELS_TEMPLATES:
        logger.info("🎬 Using local reels video compositor")
        success, filepath, public_url = save_uploaded_file(file, "post")
        
        if not success:
            return jsonify(error_response(public_url))
        
        generated = generate_local_reels_video(filepath, title, template_key)
        if not generated:
            return jsonify(error_response("Falha ao gerar reels"))
        
        _, public_out_url = generated
        return jsonify(success_response(
            "Reels gerado com sucesso!",
            videoUrl=public_out_url
        ))
    
    # Normal Placid template processing
    if template_key not in PLACID_TEMPLATES:
        template_key = 'feed_1'
    
    template_info = PLACID_TEMPLATES[template_key]
    
    if template_info['type'] == 'feed':
        if not subject or not credits:
            return jsonify(error_response("Feed templates require subject and credits"))
    
    success, filepath, public_url = save_uploaded_file(file, "post")
    if not success:
        return jsonify(error_response(public_url))
    
    layers = configure_layers_for_template(
        template_key, template_info, public_url,
        title=title,
        subject=subject,
        credits=credits
    )
    
    modifications = {
        "filename": f"instagram_post_{int(time.time())}.png",
        "width": template_info['dimensions']['width'],
        "height": template_info['dimensions']['height'],
        "image_format": "png"
    }
    
    result = create_placid_image(template_info['uuid'], layers, modifications)
    
    if result:
        if result.get('image_url'):
            return jsonify(success_response(
                "Post generated successfully!",
                imageUrl=result['image_url']
            ))
        else:
            return jsonify(success_response(
                "Post processing...",
                imageId=result.get('id')
            ))
    else:
        return jsonify(error_response("🚫 ACESSO BLOQUEADO - CRÉDITOS ESGOTADOS!"))

def handle_generate_title(payload: Dict[str, Any], request) -> jsonify:
    """Handle title generation with AI"""
    content = payload.get('newsContent', '').strip()
    if not content:
        return jsonify(error_response("News content is required"))
    
    suggested_title = call_openai_api(AI_PROMPTS['titulo'], content, max_tokens=200)
    
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
    
    generated_caption = call_openai_api(AI_PROMPTS['legendas'], content, max_tokens=500)
    
    if generated_caption:
        captions = [generated_caption]
        
        # Generate variations
        for _ in range(2):
            variation = call_openai_api(AI_PROMPTS['legendas'], content, max_tokens=500)
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
    
    rewritten_content = call_openai_api(AI_PROMPTS['reescrita'], content, max_tokens=1500)
    
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
    
    logger.info("Caption saved: {caption[:50]}...")
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
                "Image processing complted",
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
# Template de Login
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Tribuna Hoje</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #c3161f 0%, #8b0000 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 50px;
            max-width: 400px;
            width: 90%;
            text-align: center;
        }
        
        .logo { font-size: 4rem; margin-bottom: 20px; }
        
        .login-container h1 {
            color: #c3161f;
            margin-bottom: 10px;
            font-size: 2rem;
        }
        
        .login-container p {
            color: #6c757d;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 25px;
            text-align: left;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #2c3e50;
            font-weight: 600;
        }
        
        .form-group input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-size: 1.1rem;
            transition: all 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #c3161f;
        }
        
        .btn-login {
            width: 100%;
            padding: 15px;
            background: #c3161f;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.2rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-login:hover {
            background: #8b0000;
            transform: translateY(-2px);
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .footer {
            margin-top: 30px;
            color: #6c757d;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🔐</div>
        <h1>TRIBUNA HOJE</h1>
        <p>App Automação Instagram</p>
        
        {% if error %}
        <div class="error-message">
            ❌ Senha incorreta! Tente novamente.
        </div>
        {% endif %}
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label for="password">Senha de Acesso</label>
                <input 
                    type="password" 
                    id="password" 
                    name="password" 
                    placeholder="Digite a senha" 
                    required 
                    autofocus
                >
            </div>
            
            <button type="submit" class="btn-login">
                Entrar 🚀
            </button>
        </form>
        
        <div class="footer">
            © 2025 Tribuna Hoje
        </div>
    </div>
</body>
</html>
"""
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App Automação Instagram</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #c3161f 0%, #c3161f 100%);
            min-height: 100vh;
            color: #fffff;
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
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
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
            color: #46ff2f;
            background: white;
        }

        .tab-button.active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: #46ff2f;
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
            border: 3px dashed #46ff2f;
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
            color: #119c00;
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
            color: #2c3e50;
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
            border-color: #8dea8e;
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
            border-color: #119c00;
            background: #f8f9ff;
        }

        .format-option.selected {
            border-color: #119c00;
            background: #119c00;
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
            border-color: #46ff2f;
            transform: translateY(-2px);
        }

        .template-item.selected {
            border-color: #46ff2f;
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
            font-size: 1.5rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }

        .btn-primary {
            background: #46ff2f;
            color: white;
        }

        .btn-primary:hover {
            background: #37bdff;
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
            border-left: 4px solid #119c00;
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
            border-top: 4px solid #119c00;
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
    <div class="header">
    <h1>PosTH APP - TRIBUNA HOJE</h1>
    <p>Ferramenta Completa Criação de Conteúdo no Instagram</p>
    <a href="/logout" style="color: white; text-decoration: none; background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 5px; margin-top: 15px; display: inline-block;">
        🔒 Sair
    </a>
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
                    <div class="controls-section">
    <div class="control-group" id="titulo-group">
        <label class="control-label">Título *</label>
        <input type="text" class="control-input" id="titulo" placeholder="Digite o título do post" required>
    </div>
    <div class="control-group" id="assunto-group" style="display: none;">
        <label class="control-label">Assunto *</label>
        <input type="text" class="control-input" id="assunto" placeholder="Assunto da foto (Obrigatório para template de Feed)">
    </div>
    <div class="control-group" id="creditos-group" style="display: none;">
        <label class="control-label">Créditos *</label>
        <input type="text" class="control-input" id="creditos" placeholder="Nome do fotógrafo">
    </div>
</div>

                        <div class="loading" id="post-loading">
                            <div class="spinner"></div>
                            <p>Gerando post com template...</p>
                        </div>

                        <div class="success-message" id="post-success"></div>
                        <div class="error-message" id="post-error"></div>

                        <button class="btn btn-primary" onclick="generatePost()">Gerar Post</button>
                    </div>
                    <div>
                        <div class="preview-area">
                            <div class="preview-placeholder" id="post-preview">
                                Pré-visualização do post aparecerá aqui
                            </div>
                        </div>
                        <button class="btn btn-success" onclick="downloadFile('post')" style="display: none;" id="download-post-btn">📥 Download Post</button>
                        <a href="#" id="open-post-image" class="btn btn-secondary" style="margin-left: 10px; display: none;" target="_blank">🖼️ Abrir Imagem</a>
                        <a href="#" id="open-post-video" class="btn btn-secondary" style="margin-left: 10px; display: none;" target="_blank">🎬 Abrir Vídeo</a>
                    </div>
                </div>
            </div>

            <!-- Aba Notícia e Título -->
            <div id="noticia-titulo" class="tab-content">
                <h2>Gerar Título com IA</h2>
                
                <div class="controls-section">
                    <div class="control-group">
                        <label class="control-label">Cole o texto da notícia ou link</label>
                        <textarea class="control-input" id="noticia-texto" rows="6" placeholder="Cole aqui o texto completo da notícia"></textarea>
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
                        <textarea class="control-input" id="legenda-texto" rows="6" placeholder="Cole aqui o texto da notícia"></textarea>
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
        let selectedTemplate = 'reels_modelo_1';
        let uploadedFiles = {};
        let generatedImageUrls = {};

        // Registry of templates by format with preview icon and label
        const TEMPLATE_REGISTRY = {
            watermark: [
                { key: 'watermark', label: "Logo Grande", icon: '🏷️' },
                { key: 'watermark1', label: 'Logo Pequeno', icon: '🏷️' }
            ],
            feed: [
                { key: 'feed_1', label: 'Feed - Modelo 1', icon: '🖼️' },
                { key: 'feed_2', label: 'Feed - Modelo 2', icon: '🔴' },
                { key: 'feed_3', label: 'Feed - Modelo 3', icon: '⚪' },
                { key: 'feed_4', label: 'Feed - Modelo 4', icon: '⚫' },
                { key: 'feed_capa_jornal', label: 'Capa de Jornal', icon: '📰' }
            ],
            stories: [
                { key: 'stories_1', label: 'Stories - Modelo 1', icon: '📱' },
                { key: 'stories_2', label: 'Stories - Modelo 2', icon: '📱' }
            ],
            reels: [
                { key: 'reels_modelo_1', label: 'Reels 1 - Centralizado', icon: '🎬'},
                { key: 'reels_modelo_2', label: 'Reels 2 - Lateral', icon: '🎬'},
            ]
        };

        const FORMAT_PREVIEW = {
            watermark: "Prévia: aplica apenas a marca d'água sobre a imagem enviada.",
            feed: 'Prévia: post quadrado 1200x1200 com título, assunto e créditos.',
            stories: 'Prévia: vertical 1080x1920 para Stories, otimizado para texto curto.',
            reels: 'Prévia: vertical 1080x1920 para Reels, templates locais com vídeo + título.'
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
                    <p><strong>${tpl.label}</strong></p>
                    ${tpl.description ? `<small style="color: #6c757d; font-size: 0.8rem;">${tpl.description}</small>` : ''}
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
            
            // Validate file size (700MB limit)
            if (file.size > 700 * 1024 * 1024) {
                showError('Arquivo muito grande. Limite: 700MB', type);
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
    
    const tituloGroup = document.getElementById('titulo-group');
    const assuntoGroup = document.getElementById('assunto-group');
    const creditosGroup = document.getElementById('creditos-group');
    
    if (format === 'watermark') {
        // Watermark: oculta todos os campos
        tituloGroup.style.display = 'none';
        assuntoGroup.style.display = 'none';
        creditosGroup.style.display = 'none';
    } else if (format === 'feed') {
        // Feed: mostra todos
        tituloGroup.style.display = 'block';
        assuntoGroup.style.display = 'block';
        creditosGroup.style.display = 'block';
    } else {
        // Stories e Reels: só título
        tituloGroup.style.display = 'block';
        assuntoGroup.style.display = 'none';
        creditosGroup.style.display = 'none';
    }
    
    renderTemplatesForFormat(format);
}

        // Template selection
        // Template selection - atualizada para Capa de Jornal
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
    const tituloGroup = document.getElementById('titulo-group');
    const assuntoGroup = document.getElementById('assunto-group');
    const creditosGroup = document.getElementById('creditos-group');
    
    // NOVO: Capa de Jornal não precisa de nenhum campo
    if (templateKey === 'feed_capa_jornal') {
        tituloGroup.style.display = 'none';
        assuntoGroup.style.display = 'none';
        creditosGroup.style.display = 'none';
    } else if (templateKey.includes('feed')) {
        // Feed normal: mostra todos
        tituloGroup.style.display = 'block';
        assuntoGroup.style.display = 'block';
        creditosGroup.style.display = 'block';
    } else if (templateKey.includes('reels')) {
        // Reels: só título
        tituloGroup.style.display = 'block';
        assuntoGroup.style.display = 'none';
        creditosGroup.style.display = 'none';
    } else {
        // Stories: só título
        tituloGroup.style.display = 'block';
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
                return { success: false, message: '🚫 ACESSO BLOQUEADO - CRÉDITOS ESGOTADOS!' };
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
    
    // NOVO: Capa de Jornal não precisa de validação
    if (selectedTemplate === 'feed_capa_jornal') {
        // Não valida nada, apenas continua
    } else if (selectedTemplate.includes('feed') && (!titulo || !assunto || !creditos)) {
        // Feed normal: valida todos os campos
        showError('Para templates de Feed, título, assunto e créditos são obrigatórios.', 'post');
        return;
    } else if (selectedTemplate.includes('reels') && !titulo) {
        // Reels: valida só título
        showError('Para templates de Reels, o título é obrigatório.', 'post');
        return;
    }

// Watermark não exige título - permite vazio

            showLoading('post');
            
            const apiResult = await sendToAPI('generate_post', {
                template: selectedTemplate,
                title: titulo,
                subject: assunto,
                credits: creditos
            }, uploadedFiles.post);

            hideLoading('post');
            
            if (apiResult.success) {
                if (apiResult.videoUrl) {
                    generatedImageUrls.post = apiResult.videoUrl;
                    const preview = document.getElementById('post-preview');
                    preview.innerHTML = `<video controls style="max-width: 100%; max-height: 300px; border-radius: 10px;"><source src="${apiResult.videoUrl}" type="video/mp4"></video>`;
                    showSuccess('Reels gerado com sucesso!', 'post');
                    
                    // Mostra botões para vídeo
                    document.getElementById('download-post-btn').style.display = 'inline-block';
                    document.getElementById('open-post-video').href = apiResult.videoUrl;
                    document.getElementById('open-post-video').style.display = 'inline-block';
                    document.getElementById('open-post-image').style.display = 'none';
                } else if (apiResult.imageUrl) {
                    generatedImageUrls.post = apiResult.imageUrl;
                    const preview = document.getElementById('post-preview');
                    preview.innerHTML = `<img src="${apiResult.imageUrl}" style="max-width: 100%; max-height: 300px; border-radius: 10px; object-fit: contain;">`;
                    showSuccess('Post gerado com sucesso!', 'post');
                    
                    // Mostra botões para imagem
                    document.getElementById('download-post-btn').style.display = 'inline-block';
                    document.getElementById('open-post-image').href = apiResult.imageUrl;
                    document.getElementById('open-post-image').style.display = 'inline-block';
                    document.getElementById('open-post-video').style.display = 'none';
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
                // Para URLs externas, cria um link de download
                const a = document.createElement('a');
                a.href = url;
                a.download = `${type}_${new Date().getTime()}.${url.includes('video') ? 'mp4' : 'png'}`;
                a.target = '_blank';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
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
    
    # AUMENTA TIMEOUT PARA VÍDEOS LONGOS (10 MINUTOS)
    import socket
    socket.setdefaulttimeout(900)  # 15 minutos (margem de segurança)
    logger.info("⏱️ Timeout configurado: 900 segundos (15 min)")
    
    # CONFIGURAÇÃO OTIMIZADA PARA PRODUÇÃO
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    
    app.run(
        debug=False,  # ← Desabilita debug em produção
        host='0.0.0.0',
        port=5000,
        threaded=True,
        request_handler=WSGIRequestHandler
    )
