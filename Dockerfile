# Usa uma imagem oficial do Python como base
FROM python:3.11-slim

# Instala o FFmpeg dentro do nosso ambiente
RUN apt-get update && apt-get install -y ffmpeg

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código do seu projeto para dentro do container
COPY . .

# Expõe a porta que o Gunicorn vai usar
EXPOSE 10000

# O comando para iniciar a aplicação quando o container rodar
CMD ["gunicorn", "--workers", "1", "--timeout", "120", "--bind", "0.0.0.0:10000", "app:app"]