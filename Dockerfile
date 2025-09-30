FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Instalar dependências do sistema para MoviePy
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p uploads

EXPOSE 5000

# Aumentar timeout para 10 minutos e adicionar mais workers
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "600", "--worker-class", "gthread", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "main:app"]
