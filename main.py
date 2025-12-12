from concurrent.futures import ThreadPoolExecutor
import uuid
import threading
import gc
import tempfile
import shutil

# Fix para compatibilidade Pillow 10+ com MoviePy
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from flask import Flask, request, jsonify, render_template_string, send_from_directory, session, redirect, url_for, Response, stream_with_context
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
APP_PASSWORD = 'tribunahj2025'

# Decorator para proteger rotas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Configuration
class Config:
    PLACID_API_TOKEN = 'placid-mmv6puv1gvuucitb-hhflfvh5yeru1ijl'
    PLACID_API_URL = 'https://api.placid.app/api/rest/images'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
    UPLOAD_FOLDER = os.path.abspath('uploads')
    MAX_FILE_SIZE = 700 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'webm', '3gp', 'hevc'}

try:
    import moviepy.editor as mpe
    logger.info("MoviePy importado com sucesso!")
except ImportError as e:
    logger.error(f"MoviePy não encontrado: {e}")
    mpe = None
except Exception as e:
    logger.error(f"Erro ao importar MoviePy: {type(e).__name__}: {e}")
    mpe = None

# Templates PLACID
PLACID_TEMPLATES = {
    'stories_2': {
        'uuid': 'plrlpyk5wwjvw',
        'name': 'Stories - Modelo 2',
        'type': 'story',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'stories_1': {
        'uuid': 'dfgp8e0wosomx',
        'name': 'Stories - Modelo 1',
        'type': 'story',
        'dimensions': {'width': 1080, 'height': 1920}
    },
    'feed_1': {
        'uuid': 'bvxnkfasqpbl9',
        'name': 'Feed - Modelo 1',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_2': {
        'uuid': '33moedpfusmbo',
        'name': 'Feed - Modelo 2',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'watermark': {
        'uuid': 'kky75obfzathq',
        'name': 'Watermark',
        'type': 'watermark',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'watermark_1': {
        'uuid': 'wnmkfkbcsnsdo',
        'name': 'Watermark1',
        'type': 'watermark',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_3': {
        'uuid': 'efnadlehh2ato',
        'name': 'Feed - Modelo 3',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    },
    'feed_4': {
        'uuid': 'hmnyoopxig4cm',
        'name': 'Feed - Modelo 4',
        'type': 'feed',
        'dimensions': {'width': 1200, 'height': 1200}
    }
}

# Templates LOCAIS (REELS)
LOCAL_REELS_TEMPLATES = {
    'reels_modelo_1': {
        'name': 'Reels - Modelo 1',
        'description': 'Template Tribuna Hoje com título superior',
        'type': 'reels',
        'dimensions': {'width': 1080, 'height': 1920},
        'style': {
            'title_position': 'top',
            'title_background': True,
            'title_color': (255, 255, 255)
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
            'title_color': (255, 255, 255)
        }
    }
}

# AI PROMPTS
AI_PROMPTS = {
    'legendas': """Gerador de Legendas Jornalísticas para Instagram...""",
    'titulo': """Gerador Avançado de Títulos Jornalísticos Impactantes...""",
    'reescrita': """Modelador de Notícias – Estilo Tribuna Hoje..."""
}

# ✅ VARIÁVEIS GLOBAIS PARA PROGRESSO
reels_progress = {}
reels_progress_lock = threading.Lock()
reels_executor = ThreadPoolExecutor(max_workers=2)
active_tasks = {}
# FUNÇÕES AUXILIARES
def ensure_upload_directory():
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER)

def generate_filename(prefix: str, extension: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

def cleanup_temp_files(*file_paths):
    for filepath in file_paths:
        if filepath and os.path.exists(filepath):
            try:
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        os.remove(filepath)
                        logger.info(f"🗑️ Arquivo removido: {filepath}")
                        break
                    except PermissionError:
                        if attempt < max_attempts - 1:
                            time.sleep(0.5)
                        else:
                            logger.warning(f"⚠️ Não foi possível remover {filepath}")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao remover {filepath}: {e}")
                        break
            except Exception as e:
                logger.warning(f"⚠️ Erro geral ao limpar {filepath}: {e}")

def force_close_clips(*clips):
    for clip in clips:
        if clip is not None:
            try:
                if hasattr(clip, 'audio') and clip.audio is not None:
                    try:
                        clip.audio.close()
                    except Exception:
                        pass
                clip.close()
                del clip
            except Exception as e:
                logger.warning(f"⚠️ Erro ao fechar clip: {e}")
    gc.collect()

def aggressive_cleanup():
    """Limpeza agressiva de memória"""
    for _ in range(3):
        gc.collect()
    logger.info("🧹 Limpeza agressiva executada")

def update_reels_progress(task_id: str, step: str, progress: int, message: str):
    with reels_progress_lock:
        reels_progress[task_id] = {
            'step': step,
            'progress': progress,
            'message': message,
            'status': 'processing',
            'timestamp': time.time()
        }
    logger.info(f"📊 Progress [{task_id[:8]}]: {progress}% - {message}")

def complete_reels_progress(task_id: str, video_url: str):
    with reels_progress_lock:
        reels_progress[task_id] = {
            'step': 'completed',
            'progress': 100,
            'message': 'Reels gerado com sucesso!',
            'status': 'completed',
            'videoUrl': video_url
        }

def error_reels_progress(task_id: str, error_message: str):
    with reels_progress_lock:
        reels_progress[task_id] = {
            'step': 'error',
            'progress': 0,
            'message': error_message,
            'status': 'error'
        }

def verify_template_files() -> list:
    """Verifica se templates existem"""
    missing = []
    template1_path = os.path.join(os.path.dirname(__file__), "template1.jpg")
    template2_path = os.path.join(os.path.dirname(__file__), "template2.jpg")
    
    if not os.path.exists(template1_path):
        missing.append("template1.jpg")
    if not os.path.exists(template2_path):
        missing.append("template2.jpg")
    
    return missing

def convert_video_if_needed(input_path: str) -> tuple:
    """Converte vídeos problemáticos para MP4"""
    if mpe is None:
        return input_path, False
    
    needs_conversion = False
    ext = os.path.splitext(input_path)[1].lower()
    
    if ext in ['.mov', '.hevc', '.3gp', '.avi', '.mkv']:
        needs_conversion = True
    
    if not needs_conversion:
        return input_path, False
    
    logger.info("🔄 Convertendo vídeo...")
    converted_filename = generate_filename("converted", "mp4")
    converted_path = os.path.join(Config.UPLOAD_FOLDER, converted_filename)
    
    clip = None
    try:
        clip = mpe.VideoFileClip(input_path)
        clip.write_videofile(
            converted_path,
            codec='libx264',
            audio_codec='aac',
            preset='fast',
            fps=30,
            bitrate='2000k',
            verbose=False,
            logger=None,
            threads=4
        )
        logger.info(f"✅ Vídeo convertido")
        return converted_path, True
    except Exception as e:
        logger.error(f"❌ Erro conversão: {e}")
        return input_path, False
    finally:
        if clip:
            force_close_clips(clip)

def save_uploaded_file(file, prefix: str) -> Tuple[bool, str, str]:
    """Salva arquivo enviado"""
    try:
        if not file or not file.filename:
            return False, "", "No file"
        
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        
        if size > Config.MAX_FILE_SIZE:
            return False, "", "Too large"
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = generate_filename(prefix, ext)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        
        ensure_upload_directory()
        file.save(filepath)
        
        public_url = f"{{BASE_URL}}uploads/{filename}"
        return True, filepath, public_url
    except Exception as e:
        return False, "", str(e)

def success_response(message: str, **kwargs):
    response = {"success": True, "message": message}
    response.update(kwargs)
    return response

def error_response(message: str, **kwargs):
    response = {"success": False, "message": message}
    response.update(kwargs)
    return response

def generate_local_reels_video(source_media_path: str, title_text: str, template_key: str, task_id: str = None, base_url: str = None) -> Optional[Tuple[str, str]]:    
    """Gera um vídeo de reels com tratamento robusto de erros + BARRA DE PROGRESSO"""
    
    if mpe is None:
        logger.error("❌ MoviePy não está disponível")
        if task_id:
            error_reels_progress(task_id, "MoviePy não está disponível")
        return None
    
    missing_templates = verify_template_files()
    if missing_templates:
        logger.error(f"❌ Templates faltando: {missing_templates}")
        if task_id:
            error_reels_progress(task_id, f"Templates faltando: {missing_templates}")
        return None
    
    if task_id:
        update_reels_progress(task_id, 'init', 5, 'Inicializando...')
    
    converted_path = None
    needs_cleanup_converted = False
    title_overlay_path = None
    clip = None
    resized_clip = None
    bg = None
    title_clip = None
    composed = None
    
    try:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
        
        if template_key not in LOCAL_REELS_TEMPLATES:
            if task_id:
                error_reels_progress(task_id, "Template não encontrado")
            return None
        
        template = LOCAL_REELS_TEMPLATES[template_key]
        width, height = 1080, 1920
        
        if task_id:
            update_reels_progress(task_id, 'convert', 10, 'Verificando formato...')
        
        converted_path, needs_cleanup_converted = convert_video_if_needed(source_media_path)
        source_path = converted_path
        
        if task_id:
            update_reels_progress(task_id, 'load', 25, 'Carregando mídia...')
        
        try:
            clip = mpe.VideoFileClip(source_path)
        except Exception:
            with Image.open(source_path) as img:
                img = img.convert('RGB')
                temp_img = generate_filename("reels_from_image", "png")
                temp_path = os.path.join(Config.UPLOAD_FOLDER, temp_img)
                img.save(temp_path, format='PNG')
            clip = mpe.ImageClip(temp_path).set_duration(5).set_fps(30)
        
        if task_id:
            update_reels_progress(task_id, 'template', 40, 'Carregando template...')
        
        if template_key == 'reels_modelo_2':
            template_bg_path = os.path.join(os.path.dirname(__file__), "template2.jpg")
        else:
            template_bg_path = os.path.join(os.path.dirname(__file__), "template1.jpg")
        
        if not os.path.exists(template_bg_path):
            if task_id:
                error_reels_progress(task_id, "Template de fundo não encontrado")
            return None
        
        bg = mpe.ImageClip(template_bg_path).set_duration(clip.duration).resize((width, height))
        
        if task_id:
            update_reels_progress(task_id, 'resize', 55, 'Redimensionando...')
        
        video_area_top = 400
        video_area_bottom = 1520
        video_area_height = video_area_bottom - video_area_top
        video_target_width = width
        
        original_aspect_ratio = clip.w / clip.h
        video_target_height = int(video_target_width / original_aspect_ratio)
        
        if video_target_height > video_area_height:
            video_target_height = video_area_height
            video_target_width = int(video_target_height * original_aspect_ratio)
        
        resized_clip = clip.resize(newsize=(video_target_width, video_target_height))
        
        video_x = (width - video_target_width) // 2
        video_y = video_area_top + (video_area_height - video_target_height) // 2
        positioned_video = resized_clip.set_position((video_x, video_y))
        
        if task_id:
            update_reels_progress(task_id, 'title', 70, 'Criando título...')
        
        title_clip = None
        if title_text and title_text.strip():
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
                font_attempts = [
                    ("Oswald-Bold.ttf", font_size),
                    ("arialbd.ttf", font_size),
                    ("Arial.ttf", font_size),
                    ("DejaVuSans-Bold.ttf", font_size)
                ]
                
                for font_name, size in font_attempts:
                    try:
                        font = ImageFont.truetype(font_name, size)
                        break
                    except Exception:
                        continue
                
                if font is None:
                    font = ImageFont.load_default()
                
                text = title_text.upper().strip()
                max_width = width - (margin_left * 2)
                
                words = text.split()
                lines = []
                current_line = []
                
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    try:
                        bbox = draw.textbbox((0, 0), test_line, font=font)
                        text_width = bbox[2] - bbox[0]
                    except Exception:
                        text_width = len(test_line) * (font_size * 0.6)
                    
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
                    try:
                        bbox = draw.textbbox((0, 0), line, font=font)
                        text_width = bbox[2] - bbox[0]
                    except Exception:
                        text_width = len(line) * (font_size * 0.6)
                    
                    if text_align == 'left':
                        x = margin_left
                    else:
                        x = (width - text_width) // 2
                    
                    y = start_y + i * line_height
                    draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
                
                title_filename = generate_filename("title_overlay", "png")
                title_overlay_path = os.path.join(Config.UPLOAD_FOLDER, title_filename)
                title_img.save(title_overlay_path, format='PNG')
                
                title_clip = mpe.ImageClip(title_overlay_path).set_duration(clip.duration).set_position((0, title_y_position))
                
            except Exception as e:
                logger.error(f"Erro título: {e}")
        
        if task_id:
            update_reels_progress(task_id, 'compose', 80, 'Compondo vídeo...')
        
        clips_to_compose = [bg, positioned_video]
        if title_clip:
            clips_to_compose.append(title_clip)
        
        composed = mpe.CompositeVideoClip(clips_to_compose)
        
        try:
            if hasattr(clip, 'audio') and clip.audio:
                composed = composed.set_audio(clip.audio)
        except Exception:
            pass
        
        if task_id:
            update_reels_progress(task_id, 'export', 90, 'Exportando...')
        
        out_filename = generate_filename(template_key, "mp4")
        out_path = os.path.join(Config.UPLOAD_FOLDER, out_filename)
        
        fps = 30
        try:
            fps = int(getattr(clip, 'fps', 30) or 30)
            fps = min(max(fps, 24), 60)
        except:
            fps = 30
        
        composed.write_videofile(
            out_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast',
            verbose=False,
            logger=None,
            bitrate='800k',
            audio_bitrate='96k'
        )
        
        if base_url:
            public_url = f"{base_url}uploads/{out_filename}"
        else:
            public_url = f"/uploads/{out_filename}"
        
        if task_id:
            complete_reels_progress(task_id, public_url)
        
        return out_path, public_url
        
    except Exception as e:
        logger.error(f"❌ ERRO: {e}")
        if task_id:
            error_reels_progress(task_id, f"Erro: {str(e)}")
        return None
    
    finally:
        force_close_clips(clip, resized_clip, bg, title_clip, composed)
        cleanup_files = []
        if needs_cleanup_converted and converted_path:
            cleanup_files.append(converted_path)
        if title_overlay_path:
            cleanup_files.append(title_overlay_path)
        if cleanup_files:
            cleanup_temp_files(*cleanup_files)
        aggressive_cleanup()

def generate_local_capa_jornal(source_media_path: str, base_url: str = None) -> Optional[Tuple[str, str]]:
    """Gera capa de jornal"""
    try:
        template_bg = os.path.join(os.path.dirname(__file__), "template_capa_jornal.jpg")
        if not os.path.exists(template_bg):
            return None
        
        background = Image.open(template_bg).convert('RGB')
        
        with Image.open(source_media_path) as user_img:
            user_img = user_img.convert('RGB')
            user_img_resized = user_img.resize((970, 1300), Image.LANCZOS)
            background.paste(user_img_resized, (30, 12))
        
        out_filename = generate_filename("capa_jornal", "png")
        out_path = os.path.join(Config.UPLOAD_FOLDER, out_filename)
        background.save(out_path, format="PNG", quality=95)
        
        if base_url:
            public_url = f"{base_url}uploads/{out_filename}"
        else:
            public_url = f"/uploads/{out_filename}"
        
        return out_path, public_url
    except Exception as e:
        logger.error(f"Erro capa: {e}")
        return None
# ✅ ROTA SSE COM HEARTBEAT
@app.route('/api/reels-progress/<task_id>')
def reels_progress_stream(task_id):
    """Stream de progresso com heartbeat"""
    def generate():
        last_update = time.time()
        start_time = time.time()
        max_duration = 30 * 60
        
        while True:
            current_time = time.time()
            
            if current_time - start_time > max_duration:
                yield f"data: {json.dumps({'status': 'error', 'message': 'Timeout de 15 minutos'})}\n\n"
                break
            
            if current_time - last_update > 15:
                yield f": heartbeat\n\n"
                last_update = current_time
            
            with reels_progress_lock:
                if task_id in reels_progress:
                    progress_data = reels_progress[task_id].copy()
                else:
                    progress_data = None
            
            if progress_data:
                yield f"data: {json.dumps(progress_data)}\n\n"
                last_update = current_time
                
                if progress_data.get('status') in ['completed', 'error']:
                    time.sleep(2)
                    with reels_progress_lock:
                        if task_id in reels_progress:
                            del reels_progress[task_id]
                    break
            
            time.sleep(0.5)
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return "Senha incorreta", 401
    
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
def process_request():
    """Main API endpoint"""
    ensure_upload_directory()
    
    try:
        if request.form:
            action = request.form.get('action')
            data_str = request.form.get('data')
            payload = json.loads(data_str) if data_str else {}
        else:
            return jsonify(error_response("Unsupported content type")), 400
        
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
        
        handler = handlers.get(action)
        if not handler:
            return jsonify(error_response(f"Unknown action: {action}")), 400
        
        return handler(payload, request)
    except Exception as e:
        logger.error(f"Erro: {e}")
        return jsonify(error_response("Internal error")), 500

def handle_generate_post(payload: Dict[str, Any], req) -> jsonify:
    """Handle post generation"""
    file = req.files.get('file')
    if not file:
        return jsonify(error_response("No file"))
    
    template_key = payload.get('template', 'feed_1')
    title = payload.get('title', '')
    subject = payload.get('subject', '')
    credits = payload.get('credentials', '')
    
    # ✅ CAPTURA base_url ANTES de qualquer operação
    base_url = req.url_root
    
    # Capa de Jornal
    if template_key == 'feed_capa_jornal':
        success, filepath, _ = save_uploaded_file(file, "post")
        if not success:
            return jsonify(error_response("Upload failed"))
        
        result = generate_local_capa_jornal(filepath, base_url)
        if not result:
            return jsonify(error_response("Falha"))
        
        return jsonify(success_response("Capa gerada!", imageUrl=result[1]))
    
    # REELS com progresso
    if template_key in LOCAL_REELS_TEMPLATES:
        active_count = len([t for t in active_tasks.values() if not t.done()])
        if active_count >= 2:
            return jsonify(error_response("Muitos vídeos processando"))
        
        success, filepath, _ = save_uploaded_file(file, "post")
        if not success:
            return jsonify(error_response("Upload failed"))
        
        task_id = str(uuid.uuid4())
        
        def generate_with_cleanup():
            try:
                generate_local_reels_video(filepath, title, template_key, task_id, base_url)
            except Exception as e:
                logger.error(f"Erro thread: {e}")
                error_reels_progress(task_id, str(e))
            finally:
                if task_id in active_tasks:
                    del active_tasks[task_id]
                aggressive_cleanup()
        
        future = reels_executor.submit(generate_with_cleanup)
        active_tasks[task_id] = future
        
        return jsonify(success_response(
            "Processamento iniciado!",
            taskId=task_id,
            progressUrl=f"/api/reels-progress/{task_id}"
        ))
    
    # Templates Placid normais (Stories, Feed, Watermark)
    if template_key not in PLACID_TEMPLATES:
        template_key = 'feed_1'
    
    template_info = PLACID_TEMPLATES[template_key]
    
    success, filepath, public_url = save_uploaded_file(file, "post")
    if not success:
        return jsonify(error_response("Upload failed"))
    
    # ✅ CORRIGE public_url com base_url
    public_url = public_url.replace("{BASE_URL}", base_url)
    
    layers = {"imgprincipal": {"image": public_url}}
    
    # ✅ CORRIGIDO: Stories também recebe o título
    if template_info['type'] in ['feed', 'watermark', 'story'] and title:
        layers["titulocopy"] = {"text": title}
        logger.info(f"✅ Título '{title}' adicionado para tipo '{template_info['type']}'")
    
    # Campos específicos do Feed
    if template_info['type'] == 'feed':
        if subject:
            layers["assuntext"] = {"text": subject}
        if credits:
            layers["creditfoto"] = {"text": credits}
    # 🐛 DEBUG: Ver o que está sendo enviado
    logger.info("=" * 60)
    logger.info(f"📤 Enviando para Placid:")
    logger.info(f"   Template: {template_key} ({template_info['type']})")
    logger.info(f"   Layers: {layers}")
    logger.info("=" * 60)
    
    result = create_placid_image(template_info['uuid'], layers)
    
    if result:
        if result.get('image_url'):
            return jsonify(success_response("Post gerado!", imageUrl=result['image_url']))
        else:
            return jsonify(success_response("Processando...", imageId=result.get('id')))
    
    return jsonify(error_response("Falha ao gerar"))

def handle_watermark(payload: Dict[str, Any], req) -> jsonify:
    """Handle watermark"""
    file = req.files.get('file')
    if not file:
        return jsonify(error_response("No file"))
    
    base_url = req.url_root
    
    success, filepath, public_url = save_uploaded_file(file, "watermark")
    if not success:
        return jsonify(error_response("Upload failed"))
    
    public_url = public_url.replace("{BASE_URL}", base_url)
    
    template_key = 'watermark'
    template_info = PLACID_TEMPLATES[template_key]
    
    layers = {"imgprincipal": {"image": public_url}}
    
    result = create_placid_image(template_info['uuid'], layers)
    
    if result and result.get('image_url'):
        return jsonify(success_response("Watermark aplicado!", imageUrl=result['image_url']))
    
    return jsonify(error_response("Falha"))

def handle_generate_title(payload: Dict[str, Any], req) -> jsonify:
    """Handle AI title generation"""
    content = payload.get('newsContent', '').strip()
    if not content:
        return jsonify(error_response("Conteúdo necessário"))
    
    suggested = call_openai_api(AI_PROMPTS['titulo'], content, 200)
    
    if suggested:
        return jsonify(success_response("Título gerado!", suggestedTitle=suggested))
    
    return jsonify(success_response("Título gerado (fallback)", 
                                   suggestedTitle="URGENTE: Notícia Importante..."))

def handle_generate_captions(payload: Dict[str, Any], req) -> jsonify:
    """Handle AI caption generation"""
    content = payload.get('content', '').strip()
    if not content:
        return jsonify(error_response("Conteúdo necessário"))
    
    caption = call_openai_api(AI_PROMPTS['legendas'], content, 500)
    
    if caption:
        return jsonify(success_response("Legenda gerada!", captions=[caption]))
    
    return jsonify(success_response("Legenda gerada (fallback)", 
                                   captions=["📰 Acompanhe no Tribuna Hoje!\n\n#tribunahoje #alagoas"]))

def handle_rewrite_news(payload: Dict[str, Any], req) -> jsonify:
    """Handle AI news rewrite"""
    content = payload.get('newsContent', '').strip()
    if not content:
        return jsonify(error_response("Conteúdo necessário"))
    
    rewritten = call_openai_api(AI_PROMPTS['reescrita'], content, 1500)
    
    if rewritten:
        lines = rewritten.strip().split('\n')
        title = lines[0].strip() if lines else "Notícia Reescrita"
        text = '\n'.join(lines[1:]).strip() if len(lines) > 1 else rewritten
        
        return jsonify(success_response("Notícia reescrita!", 
                                       rewrittenNews={"titulo": title, "texto": text}))
    
    return jsonify(success_response("Notícia reescrita (fallback)",
                                   rewrittenNews={"titulo": "Notícia", "texto": "Conteúdo reescrito"}))

def handle_save_caption(payload: Dict[str, Any], req) -> jsonify:
    caption = payload.get('manualCaption', '').strip()
    if not caption:
        return jsonify(error_response("Legenda necessária"))
    return jsonify(success_response("Legenda salva!"))

def handle_save_rewrite(payload: Dict[str, Any], req) -> jsonify:
    title = payload.get('manualTitle', '').strip()
    text = payload.get('manualText', '').strip()
    if not title or not text:
        return jsonify(error_response("Título e texto necessários"))
    return jsonify(success_response("Notícia salva!"))

def handle_save_title(payload: Dict[str, Any], req) -> jsonify:
    title = payload.get('manualTitle', '').strip()
    if not title:
        return jsonify(error_response("Título necessário"))
    return jsonify(success_response("Título salvo!"))

def call_openai_api(prompt: str, content: str, max_tokens: int = 1000) -> Optional[str]:
    """Call OpenAI API"""
    if not Config.OPENAI_API_KEY:
        return None
    
    if len(content) > 4000:
        content = content[:4000] + "..."
    
    full_prompt = f"{prompt}\n\nConteúdo:\n{content}"
    
    headers = {
        'Authorization': f'Bearer {Config.OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Você é um assistente de jornalismo."},
            {"role": "user", "content": full_prompt}
        ],
        "max_tokens": min(max_tokens, 1000),
        "temperature": 0.7
    }
    
    try:
        response = requests.post(Config.OPENAI_API_URL, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
    
    return None

def create_placid_image(template_uuid: str, layers: Dict[str, Any], 
                       modifications: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Create image in Placid"""
    headers = {
        'Authorization': f'Bearer {Config.PLACID_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'template_uuid': template_uuid,
        'layers': layers,
        'create_now': True
    }
    
    if modifications:
        payload['modifications'] = modifications
    
    try:
        response = requests.post(Config.PLACID_API_URL, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Placid error: {e}")
    
    return None

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    try:
        return send_from_directory(Config.UPLOAD_FOLDER, filename)
    except Exception:
        return "File not found", 404

@app.route('/api/check-image/<image_id>')
def check_image_status(image_id):
    """Check Placid image status"""
    try:
        headers = {'Authorization': f'Bearer {Config.PLACID_API_TOKEN}'}
        response = requests.get(f'{Config.PLACID_API_URL}/{image_id}', headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'finished' and result.get('image_url'):
                return jsonify(success_response("Concluído", status="finished", imageUrl=result['image_url']))
            elif result.get('status') == 'error':
                return jsonify(error_response("Erro", status="error"))
            else:
                return jsonify(success_response("Processando", status="processing"))
    except Exception:
        pass
    
    return jsonify(error_response("Erro ao verificar")), 500
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

# Template HTML Principal
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
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
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
            border-color: #37bdff;
            background: #f8f9ff;
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
            border-color: #46ff2f;
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

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
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

        .btn-success {
            background: #28a745;
            color: white;
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

        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }

        .progress-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            padding: 25px;
            color: white;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }

        .progress-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            font-size: 1.3rem;
            font-weight: bold;
        }

        #progress-emoji {
            font-size: 2rem;
            animation: bounce 1s infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .progress-bar-wrapper {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }

        .progress-bar {
            flex: 1;
            height: 30px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A, #CDDC39);
            border-radius: 15px;
            width: 0%;
            transition: width 0.5s ease;
            position: relative;
            overflow: hidden;
        }

        .progress-bar-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(255, 255, 255, 0.3), 
                transparent
            );
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .progress-percentage {
            font-size: 1.2rem;
            font-weight: bold;
            min-width: 50px;
            text-align: right;
        }

        .progress-message {
            font-size: 1.1rem;
            margin: 15px 0;
            text-align: center;
            font-weight: 500;
        }

        .progress-steps {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            gap: 10px;
        }

        .step {
            flex: 1;
            padding: 10px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            text-align: center;
            font-size: 0.9rem;
            opacity: 0.5;
            transition: all 0.3s ease;
        }

        .step.active {
            opacity: 1;
            background: rgba(255, 255, 255, 0.3);
            transform: scale(1.05);
        }

        .step.completed {
            opacity: 1;
            background: linear-gradient(135deg, #4CAF50, #8BC34A);
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

        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
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

            <div id="gerar-posts" class="tab-content active">
                <h2>Gerar Posts para Instagram</h2>
                
                <div class="upload-area" onclick="document.getElementById('post-file').click()">
                    <div style="font-size: 3rem; margin-bottom: 15px;">📁</div>
                    <div style="font-size: 1.1rem; color: #6c757d; margin-bottom: 10px;">Upload de qualquer arquivo</div>
                    <div style="font-size: 0.9rem; color: #adb5bd;">Todos os formatos são aceitos</div>
                </div>
                <input type="file" id="post-file" style="display: none;" onchange="handleFileUpload(this, 'post')">

                <div class="controls-section">
                    <h3>Selecione o Formato</h3>
                    <div class="format-selector">
                        <div class="format-option" onclick="selectFormat('watermark')">
                            <h4>🏷️ Marca d'Água</h4>
                        </div>
                        <div class="format-option selected" onclick="selectFormat('reels')">
                            <h4>📹 Reels</h4>
                        </div>
                        <div class="format-option" onclick="selectFormat('stories')">
                            <h4>📱 Stories</h4>
                        </div>
                        <div class="format-option" onclick="selectFormat('feed')">
                            <h4>🖼️ Feed</h4>
                        </div>
                    </div>

                    <h3>Templates Disponíveis</h3>
                    <div class="template-grid" id="template-grid"></div>
                </div>

                <div class="two-column">
                    <div class="controls-section">
                        <div class="control-group" id="titulo-group">
                            <label class="control-label">Título *</label>
                            <input type="text" class="control-input" id="titulo" placeholder="Digite o título">
                        </div>
                        <div class="control-group" id="assunto-group" style="display: none;">
                            <label class="control-label">Assunto *</label>
                            <input type="text" class="control-input" id="assunto" placeholder="Assunto da foto">
                        </div>
                        <div class="control-group" id="creditos-group" style="display: none;">
                            <label class="control-label">Créditos *</label>
                            <input type="text" class="control-input" id="creditos" placeholder="Nome do fotógrafo">
                        </div>

                        <div class="loading" id="post-loading">
                            <div class="progress-container">
                                <div class="progress-header">
                                    <span id="progress-emoji">🚀</span>
                                    <span id="progress-title">Processando...</span>
                                </div>
                                <div class="progress-bar-wrapper">
                                    <div class="progress-bar">
                                        <div class="progress-bar-fill" id="progress-bar-fill"></div>
                                    </div>
                                    <span class="progress-percentage" id="progress-percentage">0%</span>
                                </div>
                                <p class="progress-message" id="progress-message">Iniciando processamento...</p>
                                <div class="progress-steps">
                                    <span class="step" id="step-1">📦 Preparar</span>
                                    <span class="step" id="step-2">🎬 Processar</span>
                                    <span class="step" id="step-3">💾 Exportar</span>
                                    <span class="step" id="step-4">✅ Concluir</span>
                                </div>
                            </div>
                        </div>

                        <div class="success-message" id="post-success"></div>
                        <div class="error-message" id="post-error"></div>

                        <button class="btn btn-primary" onclick="generatePost()">Gerar Post</button>
                    </div>
                    <div>
                        <div class="preview-area">
                            <div class="preview-placeholder" id="post-preview">
                                Pré-visualização aparecerá aqui
                            </div>
                        </div>
                        <button class="btn btn-success" onclick="downloadFile('post')" style="display: none;" id="download-post-btn">📥 Download</button>
                        <a href="#" id="open-post-image" class="btn btn-secondary" style="margin-left: 10px; display: none;" target="_blank">🖼️ Abrir</a>
                        <a href="#" id="open-post-video" class="btn btn-secondary" style="margin-left: 10px; display: none;" target="_blank">🎬 Abrir Vídeo</a>
                    </div>
                </div>
            </div>

            <div id="noticia-titulo" class="tab-content">
                <h2>Gerar Título com IA</h2>
                <div class="controls-section">
                    <textarea class="control-input" id="noticia-texto" rows="6" placeholder="Cole a notícia aqui"></textarea>
                    <div class="loading" id="title-loading"><p>Gerando...</p></div>
                    <div class="success-message" id="title-success"></div>
                    <div class="error-message" id="title-error"></div>
                    <button class="btn btn-primary" onclick="generateTitle()">🤖 Gerar Título</button>
                </div>
            </div>

            <div id="legendas" class="tab-content">
                <h2>Gerar Legendas com IA</h2>
                <div class="controls-section">
                    <textarea class="control-input" id="legenda-texto" rows="6" placeholder="Cole a notícia aqui"></textarea>
                    <div class="loading" id="caption-loading"><p>Gerando...</p></div>
                    <div class="success-message" id="caption-success"></div>
                    <div class="error-message" id="caption-error"></div>
                    <button class="btn btn-primary" onclick="generateCaptions()">🤖 Gerar Legendas</button>
                </div>
            </div>

            <div id="reescrever-noticia" class="tab-content">
                <h2>Reescrever Notícia com IA</h2>
                <div class="controls-section">
                    <textarea class="control-input" id="noticia-original" rows="6" placeholder="Cole a notícia aqui"></textarea>
                    <div class="loading" id="rewrite-loading"><p>Reescrevendo...</p></div>
                    <div class="success-message" id="rewrite-success"></div>
                    <div class="error-message" id="rewrite-error"></div>
                    <button class="btn btn-primary" onclick="rewriteNews()">📝 Reescrever</button>
                </div>
            </div>
        </div>
    </div>
"""
# Continuação do HTML_TEMPLATE - JavaScript
HTML_TEMPLATE += """
    <script>
        let currentTab = 'gerar-posts';
        let selectedFormat = 'reels';
        let selectedTemplate = 'reels_modelo_1';
        let uploadedFiles = {};
        let generatedImageUrls = {};
        let currentEventSource = null;

        function startReelsProgress(taskId, progressUrl) {
            console.log('📊 Iniciando monitoramento:', taskId);
            
            if (currentEventSource) {
                currentEventSource.close();
                currentEventSource = null;
            }
            
            document.getElementById('post-loading').style.display = 'block';
            
            let timeoutId = setTimeout(() => {
                if (currentEventSource) {
                    currentEventSource.close();
                    currentEventSource = null;
                }
                handleReelsError('Timeout: processamento demorou mais de 30 minutos');
            }, 30 * 60 * 1000);
            
            currentEventSource = new EventSource(progressUrl);
            
            currentEventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    updateProgressUI(data);
                    
                    if (data.status === 'completed' || data.status === 'error') {
                        clearTimeout(timeoutId);
                        currentEventSource.close();
                        currentEventSource = null;
                        
                        if (data.status === 'completed') {
                            handleReelsSuccess(data.videoUrl);
                        } else {
                            handleReelsError(data.message);
                        }
                    }
                } catch (e) {
                    clearTimeout(timeoutId);
                    currentEventSource.close();
                    currentEventSource = null;
                    handleReelsError('Erro ao processar progresso');
                }
            };
            
            currentEventSource.onerror = function(error) {
                clearTimeout(timeoutId);
                if (currentEventSource) {
                    currentEventSource.close();
                    currentEventSource = null;
                }
                handleReelsError('Erro na conexão de progresso');
            };
        }

        function updateProgressUI(data) {
            const progressBar = document.getElementById('progress-bar-fill');
            const progressPercentage = document.getElementById('progress-percentage');
            const progressMessage = document.getElementById('progress-message');
            const progressEmoji = document.getElementById('progress-emoji');
            const progressTitle = document.getElementById('progress-title');
            
            if (progressBar && progressPercentage && progressMessage) {
                progressBar.style.width = data.progress + '%';
                progressPercentage.textContent = data.progress + '%';
                progressMessage.textContent = data.message;
                
                const emojiMap = {
                    'init': '🚀', 'convert': '🔄', 'load': '📥', 'template': '🎨',
                    'resize': '📐', 'title': '📝', 'compose': '🎬', 'export': '💾', 'completed': '🎉'
                };
                progressEmoji.textContent = emojiMap[data.step] || '⚙️';
                
                const titleMap = {
                    'init': 'Inicializando', 'convert': 'Convertendo', 'load': 'Carregando',
                    'template': 'Aplicando Template', 'resize': 'Ajustando Tamanho',
                    'title': 'Criando Título', 'compose': 'Compondo Vídeo',
                    'export': 'Exportando', 'completed': 'Concluído!'
                };
                progressTitle.textContent = titleMap[data.step] || 'Processando...';
                
                const steps = ['step-1', 'step-2', 'step-3', 'step-4'];
                steps.forEach((stepId, index) => {
                    const stepEl = document.getElementById(stepId);
                    if (stepEl) {
                        stepEl.classList.remove('active', 'completed');
                        if (data.progress < 25 && index === 0) {
                            stepEl.classList.add('active');
                        } else if (data.progress >= 25 && data.progress < 50 && index === 1) {
                            stepEl.classList.add('active');
                            document.getElementById('step-1').classList.add('completed');
                        } else if (data.progress >= 50 && data.progress < 90 && index === 2) {
                            stepEl.classList.add('active');
                            document.getElementById('step-1').classList.add('completed');
                            document.getElementById('step-2').classList.add('completed');
                        } else if (data.progress >= 90 && index === 3) {
                            stepEl.classList.add('active');
                            document.getElementById('step-1').classList.add('completed');
                            document.getElementById('step-2').classList.add('completed');
                            document.getElementById('step-3').classList.add('completed');
                        } else if (data.progress >= (index + 1) * 25) {
                            stepEl.classList.add('completed');
                        }
                    }
                });
            }
        }

        function handleReelsSuccess(videoUrl) {
            document.getElementById('post-loading').style.display = 'none';
            generatedImageUrls.post = videoUrl;
            const preview = document.getElementById('post-preview');
            preview.innerHTML = '<video controls style="max-width: 100%; max-height: 300px; border-radius: 10px;"><source src="' + videoUrl + '" type="video/mp4"></video>';
            showSuccess('Reels gerado com sucesso!', 'post');
            
            document.getElementById('download-post-btn').style.display = 'inline-block';
            document.getElementById('open-post-video').href = videoUrl;
            document.getElementById('open-post-video').style.display = 'inline-block';
            document.getElementById('open-post-image').style.display = 'none';
        }

        function handleReelsError(errorMessage) {
            document.getElementById('post-loading').style.display = 'none';
            showError(errorMessage, 'post');
        }

        const TEMPLATE_REGISTRY = {
            watermark: [
                { key: 'watermark', label: "Logo Grande", icon: '🏷️' },
                { key: 'watermark_1', label: 'Logo Pequeno', icon: '🏷️' }
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
                { key: 'reels_modelo_2', label: 'Reels 2 - Lateral', icon: '🎬'}
            ]
        };

        function renderTemplatesForFormat(format) {
            const grid = document.getElementById('template-grid');
            if (!grid) return;
            grid.innerHTML = '';
            const list = TEMPLATE_REGISTRY[format] || [];
            list.forEach((tpl, index) => {
                const div = document.createElement('div');
                div.className = 'template-item' + (index === 0 ? ' selected' : '');
                div.setAttribute('onclick', "selectTemplate('" + tpl.key + "')");
                div.innerHTML = '<div style="font-size: 2rem; margin: 10px 0;">' + tpl.icon + '</div><p><strong>' + tpl.label + '</strong></p>';
                grid.appendChild(div);
                if (index === 0) {
                    selectedTemplate = tpl.key;
                }
            });
            updateFieldsForTemplate(selectedTemplate);
        }

        function switchTab(tabName) {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            document.querySelector("[onclick=\\"switchTab('" + tabName + "')\\"").classList.add('active');
            document.getElementById(tabName).classList.add('active');
            
            currentTab = tabName;
        }

        function handleFileUpload(input, type) {
            const file = input.files[0];
            if (!file) return;
            
            if (file.size > 700 * 1024 * 1024) {
                showError('Arquivo muito grande. Limite: 700MB', type);
                return;
            }
            
            uploadedFiles[type] = file;
            const reader = new FileReader();
            reader.onload = function(e) {
                const previewElement = document.getElementById(type + '-preview');
                if (file.type.startsWith('image/')) {
                    previewElement.innerHTML = '<img src="' + e.target.result + '" style="max-width: 100%; max-height: 300px; border-radius: 10px; object-fit: contain;">';
                } else if (file.type.startsWith('video/')) {
                    previewElement.innerHTML = '<video controls style="max-width: 100%; max-height: 300px; border-radius: 10px;"><source src="' + URL.createObjectURL(file) + '" type="' + file.type + '"></video>';
                }
                showSuccess('Arquivo ' + file.name + ' carregado!', type);
            };
            reader.readAsDataURL(file);
        }

        function selectFormat(format) {
            document.querySelectorAll('.format-option').forEach(option => option.classList.remove('selected'));
            event.target.closest('.format-option').classList.add('selected');
            selectedFormat = format;
            
            const tituloGroup = document.getElementById('titulo-group');
            const assuntoGroup = document.getElementById('assunto-group');
            const creditosGroup = document.getElementById('creditos-group');
            
            if (format === 'watermark') {
                tituloGroup.style.display = 'none';
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            } else if (format === 'feed') {
                tituloGroup.style.display = 'block';
                assuntoGroup.style.display = 'block';
                creditosGroup.style.display = 'block';
            } else {
                tituloGroup.style.display = 'block';
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            }
            
            renderTemplatesForFormat(format);
        }

        function selectTemplate(templateKey) {
            document.querySelectorAll('.template-item').forEach(item => item.classList.remove('selected'));
            if (event && event.target) {
                event.target.closest('.template-item').classList.add('selected');
            }
            selectedTemplate = templateKey;
            updateFieldsForTemplate(templateKey);
        }

        function updateFieldsForTemplate(templateKey) {
            const tituloGroup = document.getElementById('titulo-group');
            const assuntoGroup = document.getElementById('assunto-group');
            const creditosGroup = document.getElementById('creditos-group');
            
            if (templateKey === 'feed_capa_jornal') {
                tituloGroup.style.display = 'none';
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            } else if (templateKey.includes('feed')) {
                tituloGroup.style.display = 'block';
                assuntoGroup.style.display = 'block';
                creditosGroup.style.display = 'block';
            } else {
                tituloGroup.style.display = 'block';
                assuntoGroup.style.display = 'none';
                creditosGroup.style.display = 'none';
            }
        }

        async function sendToAPI(action, data, file = null) {
            try {
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
                    throw new Error('HTTP error! status: ' + response.status);
                }
                
                return await response.json();
            } catch (error) {
                console.error('API error:', error);
                return { success: false, message: 'Erro na API' };
            }
        }

        async function generatePost() {
            if (!uploadedFiles.post) {
                showError('Por favor, faça upload de um arquivo primeiro.', 'post');
                return;
            }
            
            const titulo = document.getElementById('titulo').value.trim();
            const assunto = document.getElementById('assunto').value.trim();
            const creditos = document.getElementById('creditos').value.trim();
            
            if (selectedTemplate === 'feed_capa_jornal') {
                // Não valida nada
            } else if (selectedTemplate.includes('feed') && (!titulo || !assunto || !creditos)) {
                showError('Para templates de Feed, título, assunto e créditos são obrigatórios.', 'post');
                return;
            } else if (selectedTemplate.includes('reels') && !titulo) {
                showError('Para templates de Reels, o título é obrigatório.', 'post');
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
                if (apiResult.taskId && apiResult.progressUrl) {
                    startReelsProgress(apiResult.taskId, apiResult.progressUrl);
                    return;
                }
                
                if (apiResult.videoUrl) {
                    handleReelsSuccess(apiResult.videoUrl);
                } else if (apiResult.imageUrl) {
                    generatedImageUrls.post = apiResult.imageUrl;
                    const preview = document.getElementById('post-preview');
                    preview.innerHTML = '<img src="' + apiResult.imageUrl + '" style="max-width: 100%; max-height: 300px; border-radius: 10px;">';
                    showSuccess('Post gerado com sucesso!', 'post');
                    document.getElementById('download-post-btn').style.display = 'inline-block';
                    document.getElementById('open-post-image').href = apiResult.imageUrl;
                    document.getElementById('open-post-image').style.display = 'inline-block';
                }
            } else {
                showError(apiResult.message || 'Erro ao gerar post', 'post');
            }
        }

        async function generateTitle() {
            const texto = document.getElementById('noticia-texto').value.trim();
            if (!texto) {
                showError('Por favor, insira o texto da notícia.', 'title');
                return;
            }
            showLoading('title');
            const apiResult = await sendToAPI('generate_title_ai', { newsContent: texto });
            hideLoading('title');
            if (apiResult.success && apiResult.suggestedTitle) {
                showSuccess('Título: ' + apiResult.suggestedTitle, 'title');
            } else {
                showError('Erro ao gerar título', 'title');
            }
        }

        async function generateCaptions() {
            const texto = document.getElementById('legenda-texto').value.trim();
            if (!texto) {
                showError('Por favor, insira o texto da notícia.', 'caption');
                return;
            }
            showLoading('caption');
            const apiResult = await sendToAPI('generate_captions_ai', { content: texto });
            hideLoading('caption');
            if (apiResult.success && apiResult.captions) {
                showSuccess('Legenda: ' + apiResult.captions[0], 'caption');
            } else {
                showError('Erro ao gerar legenda', 'caption');
            }
        }

        async function rewriteNews() {
            const texto = document.getElementById('noticia-original').value.trim();
            if (!texto) {
                showError('Por favor, insira o texto da notícia.', 'rewrite');
                return;
            }
            showLoading('rewrite');
            const apiResult = await sendToAPI('rewrite_news_ai', { newsContent: texto });
            hideLoading('rewrite');
            if (apiResult.success && apiResult.rewrittenNews) {
                showSuccess('Notícia reescrita com sucesso!', 'rewrite');
            } else {
                showError('Erro ao reescrever notícia', 'rewrite');
            }
        }

        function downloadFile(type) {
            const url = generatedImageUrls[type];
            if (!url) return;
            const a = document.createElement('a');
            a.href = url;
            a.download = type + '_' + new Date().getTime() + '.mp4';
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        function showLoading(type) {
            document.getElementById(type + '-loading').style.display = 'block';
            document.getElementById(type + '-success').style.display = 'none';
            document.getElementById(type + '-error').style.display = 'none';
        }

        function hideLoading(type) {
            document.getElementById(type + '-loading').style.display = 'none';
        }

        function showSuccess(message, type) {
            const successElement = document.getElementById(type + '-success');
            successElement.textContent = message;
            successElement.style.display = 'block';
            document.getElementById(type + '-error').style.display = 'none';
            setTimeout(() => { successElement.style.display = 'none'; }, 5000);
        }

        function showError(message, type) {
            const errorElement = document.getElementById(type + '-error');
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            document.getElementById(type + '-success').style.display = 'none';
            setTimeout(() => { errorElement.style.display = 'none'; }, 10000);
        }

        document.addEventListener('DOMContentLoaded', function() {
            renderTemplatesForFormat(selectedFormat);
        });
    </script>
</body>
</html>
"""

# ✅ MAIN
if __name__ == '__main__':
    ensure_upload_directory()
    
    logger.info("🚀 Starting SaaS Editor...")
    logger.info("🌐 http://0.0.0.0:5000")
    
    import socket
    socket.setdefaulttimeout(900)
    
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
