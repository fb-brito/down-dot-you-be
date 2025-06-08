# app.py
import os
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import yt_dlp

# --- Configuração da Aplicação Flask ---
app = Flask(__name__)
# Chave secreta para usar mensagens flash
app.secret_key = 'supersecretkey' 

# --- Constantes de Diretório ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
VIDEOS_DIR = os.path.join(DOWNLOADS_DIR, 'videos')
AUDIOS_DIR = os.path.join(DOWNLOADS_DIR, 'audios')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
MASTER_LOG_FILE = os.path.join(LOGS_DIR, 'master_log.csv')

# --- Funções de Lógica ---

def create_initial_directories():
    """Garante que a pasta principal de downloads exista."""
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(AUDIOS_DIR, exist_ok=True)

# Chamada da função para garantir que os diretórios sejam criados na inicialização
create_initial_directories()

def log_master_record(video_info, operation_type, status, output_path):
    """
    Registra uma operação no arquivo de log mestre.
    *** CORREÇÃO: Garante que o diretório de log exista antes de escrever. ***
    """
    # Garante que o diretório de logs exista
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    header = [
        "timestamp", "video_id", "video_title", 
        "operation_type", "status", "output_file_path"
    ]
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "video_id": video_info.get('id', 'N/A'),
        "video_title": video_info.get('title', 'N/A'),
        "operation_type": operation_type,
        "status": status,
        "output_file_path": output_path
    }
    
    file_exists = os.path.isfile(MASTER_LOG_FILE)
    with open(MASTER_LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter=';')
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)

def download_content(video_url, download_type):
    """
    Realiza o download de vídeo ou áudio do YouTube.
    Retorna (True, info, path) em caso de sucesso ou (False, error_message, None) em caso de falha.
    """
    operation_type = "Download Inválido" # Valor padrão
    try:
        if download_type == 'video':
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(VIDEOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                'quiet': False,
                'noplaylist': True
            }
            operation_type = "Download de Vídeo"
        elif download_type == 'audio':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(AUDIOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                'quiet': False,
                'noplaylist': True
            }
            operation_type = "Download de Áudio"
        else:
            return False, "Tipo de download inválido.", None

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            if download_type == 'audio':
                 base, _ = os.path.splitext(filename)
                 filename = base + '.mp3'

        log_master_record(info, operation_type, "SUCCESS", filename)
        return True, info, filename

    except Exception as e:
        error_message = f"Erro ao processar o download: {str(e)}"
        log_master_record({'id': 'N/A', 'title': 'Falha no Download'}, operation_type, "FAIL", error_message)
        return False, error_message, None

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """Renderiza a página inicial."""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    """Processa a requisição de download do formulário."""
    video_url = request.form.get('url')
    download_type = request.form.get('type')

    if not video_url:
        flash("Por favor, insira uma URL do YouTube.", "error")
        return redirect(url_for('index'))

    success, result, path = download_content(video_url, download_type)

    if success:
        title = result.get('title', 'desconhecido')
        flash(f"Sucesso! '{title}' foi baixado.", "success")
    else:
        flash(f"Falha no download. Verifique o console para detalhes.", "error")
        print(f"ERRO DETALHADO: {result}")
        
    return redirect(url_for('index'))


# --- Execução da Aplicação ---
if __name__ == '__main__':
    app.run(debug=True)
