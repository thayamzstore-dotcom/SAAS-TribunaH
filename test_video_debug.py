#!/usr/bin/env python3
"""
🔍 SCRIPT DE TESTE - DEBUG DE VÍDEOS ANDROID
============================================

Script para testar o endpoint /api/debug-video e identificar problemas
com vídeos do Android que não funcionam no template de reels.

USO:
    python test_video_debug.py <caminho_do_video>

EXEMPLO:
    python test_video_debug.py /path/to/android_video.mp4
    python test_video_debug.py /path/to/android_video.3gp
"""

import sys
import os
import requests
import json
from pathlib import Path


def test_video_debug(video_path: str, server_url: str = "http://localhost:5000"):
    """
    Testa um vídeo usando o endpoint de debug

    Args:
        video_path: Caminho para o arquivo de vídeo
        server_url: URL do servidor (padrão: http://localhost:5000)
    """

    print("=" * 80)
    print("🔍 TESTE DE DEBUG DE VÍDEO ANDROID")
    print("=" * 80)

    # Verifica se o arquivo existe
    if not os.path.exists(video_path):
        print(f"❌ Erro: Arquivo não encontrado: {video_path}")
        return False

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"📁 Arquivo: {os.path.basename(video_path)}")
    print(f"📊 Tamanho: {file_size_mb:.2f}MB")
    print(f"📝 Extensão: {Path(video_path).suffix}")
    print()

    # Faz o upload para o endpoint de debug
    endpoint = f"{server_url}/api/debug-video"
    print(f"🌐 Enviando para: {endpoint}")
    print("⏳ Aguarde...")
    print()

    try:
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f)}
            response = requests.post(endpoint, files=files, timeout=60)

        print(f"📡 Status HTTP: {response.status_code}")
        print()

        # Parse da resposta
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"❌ Erro ao decodificar JSON da resposta")
            print(f"Resposta bruta: {response.text[:500]}")
            return False

        # Exibe resultados
        print("=" * 80)
        print("📋 RESULTADOS DO DEBUG")
        print("=" * 80)

        # Informações do arquivo
        if 'file_info' in data:
            print("\n📁 INFORMAÇÕES DO ARQUIVO:")
            file_info = data['file_info']
            print(f"   Nome: {file_info.get('filename', 'N/A')}")
            print(f"   Extensão: {file_info.get('extension', 'N/A')}")
            print(f"   Tamanho: {file_info.get('size_mb', 0):.2f}MB")

        # Informações do vídeo
        if 'video_info' in data:
            print("\n🎬 INFORMAÇÕES DO VÍDEO:")
            video_info = data['video_info']

            if 'error' in video_info:
                print(f"   ❌ ERRO: {video_info['error']}")
            else:
                print(f"   Resolução: {video_info.get('size', 'N/A')}")
                print(f"   Duração: {video_info.get('duration', 0)}s")
                print(f"   FPS: {video_info.get('fps', 'N/A')}")
                print(f"   Aspect Ratio: {video_info.get('aspect_ratio', 'N/A')}")
                print(f"   Áudio: {'Sim' if video_info.get('has_audio') else 'Não'}")
                print(f"   Codec: {video_info.get('codec', 'N/A')}")
                print(f"   Reader: {video_info.get('reader_type', 'N/A')}")
                print(f"   Extração de frame: {video_info.get('frame_extraction', 'N/A')}")

        # Informações de conversão
        if 'conversion_info' in data:
            print("\n🔄 NECESSIDADE DE CONVERSÃO:")
            conv_info = data['conversion_info']
            needs = conv_info.get('needs_conversion', False)
            print(f"   Precisa conversão: {'✅ SIM' if needs else '❌ NÃO'}")

            if needs and 'reasons' in conv_info:
                print("   Motivos:")
                for reason in conv_info['reasons']:
                    print(f"      - {reason}")

        # Compatibilidade Android
        if 'android_compatibility' in data:
            print("\n📱 COMPATIBILIDADE ANDROID:")
            android = data['android_compatibility']

            checks = [
                ('Formato suportado', android.get('format_supported', False)),
                ('Codec compatível', android.get('codec_compatible', False)),
                ('Tamanho OK (<700MB)', android.get('size_ok', False)),
                ('Duração OK (<10min)', android.get('duration_ok', False))
            ]

            for check_name, check_result in checks:
                icon = '✅' if check_result else '❌'
                print(f"   {icon} {check_name}")

        # Avisos
        if 'warnings' in data and data['warnings']:
            print("\n⚠️ AVISOS:")
            for warning in data['warnings']:
                print(f"   {warning}")

        # Erros
        if 'errors' in data and data['errors']:
            print("\n❌ ERROS:")
            for error in data['errors']:
                print(f"   {error}")

        # Informações do sistema
        if 'system_info' in data:
            print("\n🔧 SISTEMA:")
            sys_info = data['system_info']
            print(f"   MoviePy: {sys_info.get('moviepy_version', 'N/A')}")
            print(f"   Python: {sys_info.get('python_version', 'N/A')}")
            print(f"   Plataforma: {sys_info.get('platform', 'N/A')}")

            ffmpeg_available = sys_info.get('ffmpeg_available', False)
            if ffmpeg_available:
                print(f"   FFmpeg: ✅ {sys_info.get('ffmpeg_version', 'N/A')}")
            else:
                print(f"   FFmpeg: ❌ Não disponível")

        # Status geral
        print("\n" + "=" * 80)
        success = data.get('success', False)
        if success:
            print("✅ VÍDEO COMPATÍVEL - Deve funcionar no template de reels")
        else:
            print("❌ VÍDEO COM PROBLEMAS - Verifique os erros acima")
        print("=" * 80)

        return success

    except requests.exceptions.ConnectionError:
        print(f"❌ Erro: Não foi possível conectar ao servidor em {server_url}")
        print("   Certifique-se que o servidor está rodando: python main.py")
        return False

    except requests.exceptions.Timeout:
        print("❌ Erro: Timeout ao processar o vídeo (>60s)")
        print("   O vídeo pode ser muito grande ou complexo")
        return False

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal"""

    if len(sys.argv) < 2:
        print(__doc__)
        print("\n❌ Erro: Caminho do vídeo não fornecido")
        print("\nUso: python test_video_debug.py <caminho_do_video>")
        sys.exit(1)

    video_path = sys.argv[1]
    server_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"

    success = test_video_debug(video_path, server_url)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
