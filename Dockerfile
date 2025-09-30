# Usa a imagem oficial do Python
FROM python:3.10-slim

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expõe a porta (tem que ser a mesma do Flask)
EXPOSE 8000

# Comando para iniciar o Flask
CMD ["python", "main.py"]
