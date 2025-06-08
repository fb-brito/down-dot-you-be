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

def create_directories():
    """Garante que todos os diretórios necessários existam."""
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(AUDIOS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

def log_master_record(video_info, operation_type, status, output_path):
    """Registra uma operação no arquivo de log mestre."""
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
    try:
        if download_type == 'video':
            # Opções para baixar o melhor vídeo com áudio combinado
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(VIDEOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                'quiet': False
            }
            operation_type = "Download de Vídeo"
        elif download_type == 'audio':
            # Opções para baixar o melhor áudio e convertê-lo para mp3
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(AUDIOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                'quiet': False
            }
            operation_type = "Download de Áudio"
        else:
            return False, "Tipo de download inválido.", None

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # O caminho do arquivo é determinado pelo 'outtmpl', yt-dlp o gerencia.
            # Precisamos construir o caminho esperado para o log.
            filename = ydl.prepare_filename(info)
            # Se for áudio, a extensão muda para mp3 após o pós-processamento.
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
    download_type = request.form.get('type') # 'video' ou 'audio'

    if not video_url:
        flash("Por favor, insira uma URL do YouTube.", "error")
        return redirect(url_for('index'))

    success, result, path = download_content(video_url, download_type)

    if success:
        title = result.get('title', 'desconhecido')
        flash(f"Sucesso! '{title}' foi baixado para '{os.path.basename(path)}'.", "success")
    else:
        flash(f"Falha no download. Erro: {result}", "error")
        
    return redirect(url_for('index'))


# --- Execução da Aplicação ---
if __name__ == '__main__':
    create_directories()
    app.run(debug=True)
