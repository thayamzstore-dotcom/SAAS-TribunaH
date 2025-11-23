# 🔍 Guia de Debug - Vídeos Android no Template de Reels

## 📋 Problema Identificado

Vídeos enviados de **dispositivos Android** não funcionam no template de criação de vídeos do SAAS, enquanto vídeos do computador funcionam normalmente.

## 🎯 Causas Principais Identificadas

### 1. **Formatos de Vídeo Mobile Incompatíveis**
- **3GP** (Android antigo) - codec interno pode não ser H.264
- **HEVC/H.265** (Android moderno) - não suportado em navegadores
- **MOV** (iPhone) - pode usar codecs Apple específicos

### 2. **Codecs Problemáticos**
- HEVC (High Efficiency Video Coding)
- H.265
- VP9
- AV1 (Android muito novo)
- MPEG2

### 3. **Problemas de Processamento**
- Vídeos muito grandes (>700MB)
- Vídeos muito longos (>10 minutos)
- Aspect ratio incompatível
- Problemas na extração de frames

---

## ✅ Melhorias Implementadas

### 1. **Endpoint de Debug** (`/api/debug-video`)
Novo endpoint que analisa vídeos em detalhes e retorna:
- Informações do arquivo (tamanho, extensão)
- Informações do vídeo (codec, resolução, duração, FPS)
- Necessidade de conversão
- Compatibilidade Android
- Avisos e erros específicos

### 2. **Detecção Robusta de Codec**
- Usa **FFprobe** para análise precisa do codec
- Fallback para MoviePy se FFprobe não estiver disponível
- Detecta codecs problemáticos: HEVC, H.265, VP9, AV1, etc.

### 3. **Validação 3GP Específica**
- Verifica o codec interno de arquivos 3GP
- Converte automaticamente se necessário

### 4. **Logs Detalhados**
- Logs específicos para troubleshooting Android
- Informações sobre conversão de vídeo
- Detalhes de carregamento e processamento

---

## 🚀 Como Usar

### **Método 1: Usando o Script de Teste**

```bash
# Instale a dependência
pip install requests

# Execute o teste com um vídeo do Android
python test_video_debug.py /caminho/para/video_android.mp4

# Ou especifique a URL do servidor
python test_video_debug.py /caminho/para/video.3gp http://localhost:5000
```

### **Método 2: Usando cURL**

```bash
curl -X POST http://localhost:5000/api/debug-video \
  -F "file=@/caminho/para/video_android.mp4" \
  | python -m json.tool
```

### **Método 3: Usando Postman/Insomnia**

1. Abra Postman
2. Crie uma requisição **POST** para `http://localhost:5000/api/debug-video`
3. Em **Body**, selecione **form-data**
4. Adicione um campo `file` do tipo **File**
5. Selecione o vídeo do Android
6. Envie a requisição

---

## 📊 Exemplo de Resposta

```json
{
  "success": false,
  "file_info": {
    "filename": "video_android.3gp",
    "extension": ".3gp",
    "size_mb": 45.2,
    "path": "/app/uploads/video_android_123456.3gp"
  },
  "video_info": {
    "duration": 120.5,
    "fps": 30,
    "size": "1920x1080",
    "width": 1920,
    "height": 1080,
    "aspect_ratio": 1.78,
    "has_audio": true,
    "codec": "mpeg4",
    "reader_type": "FFMPEG_VideoReader",
    "frame_extraction": "OK"
  },
  "conversion_info": {
    "needs_conversion": true,
    "reasons": [
      "Extensão .3gp requer conversão (formato mobile/Apple)",
      "3GP com codec mpeg4 precisa conversão para H.264"
    ],
    "will_be_converted": true
  },
  "android_compatibility": {
    "format_supported": true,
    "codec_compatible": false,
    "size_ok": true,
    "duration_ok": true
  },
  "warnings": [
    "⚠️ Extensão .3gp pode não ser compatível",
    "⚠️ Aspect ratio 1.78 diferente do ideal para reels (0.56 ou 9:16)"
  ],
  "errors": [],
  "system_info": {
    "moviepy_version": "1.0.3",
    "python_version": "3.9.2",
    "platform": "linux",
    "ffmpeg_available": true,
    "ffmpeg_version": "ffmpeg version 4.3.1"
  }
}
```

---

## 🛠️ Como Interpretar os Resultados

### ✅ **Vídeo Compatível** (`success: true`)
- O vídeo deve funcionar normalmente no template de reels
- Nenhuma conversão necessária

### ⚠️ **Vídeo com Avisos** (`warnings` não vazio)
- O vídeo pode funcionar, mas com limitações
- Ex: FPS alto será reduzido, aspect ratio não ideal

### ❌ **Vídeo Incompatível** (`success: false`)
- O vídeo precisa de conversão ou tem erros
- Verifique `conversion_info.needs_conversion`
- Leia os `errors` para entender o problema

---

## 🔧 Troubleshooting

### **Problema 1: "MoviePy não disponível"**
```bash
pip install moviepy imageio imageio-ffmpeg
```

### **Problema 2: "FFmpeg não encontrado"**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# MacOS
brew install ffmpeg

# Docker (já incluído na imagem)
```

### **Problema 3: "Erro ao carregar vídeo"**
- Verifique se o arquivo está corrompido
- Tente reproduzir o vídeo em um player local (VLC)
- Converta manualmente para MP4 H.264:
  ```bash
  ffmpeg -i video_android.3gp -c:v libx264 -c:a aac video_convertido.mp4
  ```

### **Problema 4: "Timeout ao processar"**
- Vídeo muito longo (>10 minutos)
- Reduza a duração ou aumente o timeout no código

---

## 📝 Checklist de Compatibilidade Android

Use este checklist para verificar se um vídeo do Android funcionará:

- [ ] **Formato**: MP4, WEBM, ou MOV (3GP requer conversão)
- [ ] **Codec**: H.264 ou MPEG4 (HEVC/H.265 requer conversão)
- [ ] **Tamanho**: Menor que 700MB
- [ ] **Duração**: Menor que 10 minutos
- [ ] **Aspect Ratio**: Preferencialmente 9:16 (vertical) para reels
- [ ] **FPS**: Entre 24-60 FPS
- [ ] **Não corrompido**: Pode ser reproduzido normalmente

---

## 🔄 Fluxo de Processamento

```
1. Upload do vídeo
   ↓
2. Salvar arquivo (máx 700MB)
   ↓
3. Verificar codec com FFprobe
   ↓
4. Conversão automática se necessário
   - HEVC/H.265 → H.264
   - 3GP → MP4 H.264
   - MOV (Apple) → MP4 H.264
   ↓
5. Carregar vídeo com MoviePy
   ↓
6. Gerar template de reels
   ↓
7. Exportar vídeo final
```

---

## 📞 Próximos Passos

### **Para Testar com Vídeo Real do Cliente:**

1. **Peça ao cliente para enviar o vídeo original**
   - Use WeTransfer, Google Drive, ou similar
   - NÃO comprima ou converta antes de enviar

2. **Rode o script de debug**
   ```bash
   python test_video_debug.py video_do_cliente.mp4
   ```

3. **Analise os resultados**
   - Se `needs_conversion: true`, o sistema converterá automaticamente
   - Se houver erros, compartilhe os logs comigo

4. **Teste o template normal**
   - Após confirmar compatibilidade, teste criando um reel normalmente
   - Monitore os logs do servidor para erros

### **Se Ainda Houver Problemas:**

1. **Capture os logs completos**
   ```bash
   # Rode o servidor com logs visíveis
   python main.py 2>&1 | tee debug.log
   ```

2. **Envie as informações:**
   - Logs completos (`debug.log`)
   - Resultado do endpoint de debug (JSON)
   - Informações do dispositivo Android do cliente
   - Se possível, o vídeo original

---

## 📚 Referências Técnicas

### **Formatos de Vídeo Android**
- **3GP**: Formato antigo, usado em Android 2.x-4.x
- **MP4**: Formato padrão moderno
- **WEBM**: Alternativa moderna, menos comum

### **Codecs Comuns em Android**
- **H.264 (AVC)**: ✅ Compatível (mais comum)
- **MPEG4**: ✅ Compatível (antigo)
- **HEVC (H.265)**: ❌ Incompatível (Android 5.0+)
- **VP8/VP9**: ⚠️ Compatível mas requer conversão
- **AV1**: ❌ Muito novo, incompatível

### **Conversão Automática**
- **Input**: HEVC, MOV, 3GP, VP9, AV1
- **Output**: MP4 H.264, AAC audio, 30fps, 2000kbps
- **Preset**: medium (balanceamento velocidade/qualidade)

---

## ⚡ Performance

- **Conversão**: ~1-2x duração do vídeo
  - Vídeo de 2min: ~2-4min para converter
  - Vídeo de 10min: ~10-20min para converter

- **Template de Reels**: ~0.5-1x duração do vídeo
  - Vídeo de 2min: ~1-2min para gerar

- **Total**: Espere ~2-3x a duração do vídeo para processo completo

---

**Criado em**: 2025-11-23
**Última atualização**: 2025-11-23
