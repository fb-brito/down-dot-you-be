# app.py
import os
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import yt_dlp

# --- Configuração da Aplicação Flask ---
app = Flask(__name__)
# Chave secreta para usar mensagens flash e sessões
app.secret_key = 'uma-chave-secreta-muito-forte' 

# --- Constantes de Diretório ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
VIDEOS_DIR = os.path.join(DOWNLOADS_DIR, 'videos')
AUDIOS_DIR = os.path.join(DOWNLOADS_DIR, 'audios')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
MASTER_LOG_FILE = os.path.join(LOGS_DIR, 'master_log.csv')

# --- Funções de Lógica ---
def create_initial_directories():
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(AUDIOS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

create_initial_directories()

# (Função log_master_record permanece a mesma)
def log_master_record(video_info, operation_type, status, output_path):
    os.makedirs(LOGS_DIR, exist_ok=True)
    header = ["timestamp", "video_id", "video_title", "operation_type", "status", "output_file_path"]
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

def get_video_info(video_url):
    """Obtém informações do vídeo sem fazer o download."""
    ydl_opts = {'quiet': True, 'noplaylist': False} # noplaylist=False para detectar playlists
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            return info
        except Exception as e:
            print(f"Erro ao obter informações do vídeo: {e}")
            return None

def download_video_item(video_url, download_type):
    """Função de download para um único item, adaptada da original."""
    # Lógica de download similar à função download_content anterior...
    # (Esta função é uma simplificação para ser chamada pela rota de download da fila)
    operation_type = "Download Inválido"
    try:
        if 'audio' in download_type:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                'outtmpl': os.path.join(AUDIOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                'noplaylist': 'playlist' not in download_type
            }
            operation_type = "Download de Áudio" if 'playlist' not in download_type else "Download de Playlist de Áudio"
        else: # Vídeo
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(VIDEOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                'noplaylist': 'playlist' not in download_type
            }
            operation_type = "Download de Vídeo" if 'playlist' not in download_type else "Download de Playlist de Vídeo"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            log_master_record(info, operation_type, "SUCCESS", "")

    except Exception as e:
        log_master_record({'id': 'N/A', 'title': 'Falha no Download'}, operation_type, "FAIL", str(e))


# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """Renderiza a página inicial e exibe a fila."""
    # A fila agora é armazenada na sessão do usuário
    if 'queue' not in session:
        session['queue'] = []
    return render_template('index.html', queue=session['queue'])

@app.route('/add', methods=['POST'])
def add_to_queue():
    """Adiciona um item à fila de downloads."""
    video_url = request.form.get('url')
    download_type = request.form.get('type') # 'video' ou 'audio'
    
    if not video_url:
        flash("Por favor, insira uma URL.", "error")
        return redirect(url_for('index'))

    # Garante que a fila exista na sessão
    if 'queue' not in session:
        session['queue'] = []
    
    # Impõe o limite de 10 itens
    if len(session['queue']) >= 10:
        flash("A fila de downloads está cheia (máx. 10 itens).", "error")
        return redirect(url_for('index'))

    info = get_video_info(video_url)
    if not info:
        flash("Não foi possível obter informações da URL fornecida.", "error")
        return redirect(url_for('index'))

    is_playlist = info.get('_type') == 'playlist'
    final_download_type = f"playlist_{download_type}" if is_playlist else download_type
    
    # Formata o tamanho do arquivo para exibição
    filesize = info.get('filesize_approx')
    if filesize:
        filesize_mb = f"{filesize / 1024 / 1024:.2f} MB"
    else:
        filesize_mb = "N/A" if not is_playlist else "Playlist"

    queue_item = {
        'url': video_url,
        'title': info.get('title', 'Título desconhecido'),
        'type': final_download_type, # ex: 'video', 'audio', 'playlist_video'
        'quality': f"{info.get('height', 'Áudio')}p" if not 'audio' in final_download_type else 'MP3 192kbps',
        'size': filesize_mb,
    }

    session['queue'].append(queue_item)
    # Marca a sessão como modificada para garantir que seja salva
    session.modified = True
    flash(f"'{queue_item['title']}' adicionado à fila.", "success")
    
    return redirect(url_for('index'))

@app.route('/download_queue', methods=['POST'])
def download_queue():
    """Inicia o processo de download de todos os itens na fila."""
    if 'queue' not in session or not session['queue']:
        flash("A fila está vazia. Nada para baixar.", "error")
        return redirect(url_for('index'))

    # O download real pode demorar. Em uma app real, usaríamos tarefas em background (Celery, etc)
    # Para este exemplo, faremos o download sequencialmente.
    queue_to_download = session['queue']
    
    # Limpa a fila na sessão ANTES de começar a baixar
    session['queue'] = []
    session.modified = True

    for item in queue_to_download:
        print(f"Baixando: {item['title']}")
        download_video_item(item['url'], item['type'])
    
    flash("Downloads da fila concluídos!", "success")
    return redirect(url_for('index'))

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    """Limpa todos os itens da fila."""
    session['queue'] = []
    session.modified = True
    flash("Fila de downloads limpa.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
