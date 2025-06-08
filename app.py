# app.py
import os
import csv
import threading
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import yt_dlp

# --- Configuração da Aplicação Flask ---
app = Flask(__name__)
app.secret_key = 'chave-ainda-mais-secreta-para-progresso-inline'

# --- Estrutura de Dados para Progresso ---
# Agora rastreamos o progresso por item
progress_data = {
    "is_running": False,
    "current_item_id": None,
    "items": {} # Ex: { "uuid1": {"status": "pending", "percentage": 0, ...}, "uuid2": ... }
}

# --- Constantes e Configuração de Diretórios ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
VIDEOS_DIR = os.path.join(DOWNLOADS_DIR, 'videos')
AUDIOS_DIR = os.path.join(DOWNLOADS_DIR, 'audios')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
MASTER_LOG_FILE = os.path.join(LOGS_DIR, 'master_log.csv')

def create_initial_directories():
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(AUDIOS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

create_initial_directories()

def log_master_record(video_info, operation_type, status, output_path):
    # (código da função sem alterações)
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

# --- Lógica de Download com Barra de Progresso ---

def my_progress_hook(d):
    global progress_data
    item_id = progress_data.get("current_item_id")
    if not item_id or item_id not in progress_data["items"]:
        return

    if d['status'] == 'downloading':
        percentage_str = d['_percent_str'].strip().replace('\x1b[0;94m', '').replace('\x1b[0m', '')
        try:
            percentage = float(percentage_str.replace('%',''))
            progress_data["items"][item_id]["percentage"] = percentage
            progress_data["items"][item_id]["status"] = "downloading"
        except ValueError:
            pass # Ignora erros de parsing iniciais
        
    elif d['status'] == 'finished':
        progress_data["items"][item_id]["percentage"] = 100
        progress_data["items"][item_id]["status"] = "merging" # Um estado intermediário para pós-processamento

def download_worker(queue_to_download):
    global progress_data
    progress_data["is_running"] = True

    for item in queue_to_download:
        item_id = item["id"]
        progress_data["current_item_id"] = item_id
        progress_data["items"][item_id]["status"] = "downloading"

        operation_type = "Download Inválido"
        try:
            if 'audio' in item['type']:
                operation_type = "Download de Áudio" if 'playlist' not in item['type'] else "Download de Playlist de Áudio"
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    'outtmpl': os.path.join(AUDIOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                    'noplaylist': 'playlist' not in item['type'],
                    'progress_hooks': [my_progress_hook],
                    'quiet': True,
                }
            else: # Vídeo
                operation_type = "Download de Vídeo" if 'playlist' not in item['type'] else "Download de Playlist de Vídeo"
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': os.path.join(VIDEOS_DIR, '%(title)s [%(id)s].%(ext)s'),
                    'noplaylist': 'playlist' not in item['type'],
                    'progress_hooks': [my_progress_hook],
                    'quiet': True,
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(item['url'], download=True)
                log_master_record(info, operation_type, "SUCCESS", "")
            
            progress_data["items"][item_id]["status"] = "completed"
            progress_data["items"][item_id]["percentage"] = 100
        
        except Exception as e:
            log_master_record({'id': 'N/A', 'title': item['title']}, operation_type, "FAIL", str(e))
            progress_data["items"][item_id]["status"] = "error"
            progress_data["is_running"] = False # Para a fila em caso de erro
            return

    progress_data["is_running"] = False
    progress_data["current_item_id"] = None

def get_video_info(video_url):
    ydl_opts = {'quiet': True, 'noplaylist': False}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            return ydl.extract_info(video_url, download=False)
        except Exception:
            return None

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    if 'queue' not in session:
        session['queue'] = []
    return render_template('index.html', queue=session.get('queue', []))

@app.route('/add', methods=['POST'])
def add_to_queue():
    if 'queue' not in session:
        session['queue'] = []
    
    if len(session['queue']) >= 10:
        flash("A fila de downloads está cheia (máx. 10 itens).", "error")
        return redirect(url_for('index'))

    video_url = request.form.get('url')
    download_type = request.form.get('type')
    info = get_video_info(video_url)

    if not info:
        flash("Não foi possível obter informações da URL fornecida.", "error")
        return redirect(url_for('index'))

    is_playlist = info.get('_type') == 'playlist'
    final_download_type = f"playlist_{download_type}" if is_playlist else download_type
    
    filesize = info.get('filesize_approx')
    filesize_mb = f"{filesize / 1024 / 1024:.2f} MB" if filesize else ("Playlist" if is_playlist else "N/A")

    queue_item = {
        'id': str(uuid.uuid4()), # ID Único para cada item
        'url': video_url,
        'title': info.get('title', 'Título desconhecido'),
        'type': final_download_type,
        'quality': f"{info.get('height', 'Áudio')}p" if 'audio' not in final_download_type else 'MP3 192kbps',
        'size': filesize_mb,
    }
    session['queue'].append(queue_item)
    session.modified = True
    flash(f"'{queue_item['title']}' adicionado à fila.", "success")
    return redirect(url_for('index'))

@app.route('/download_queue', methods=['POST'])
def start_download_queue():
    global progress_data
    if progress_data['is_running']:
        return jsonify({'status': 'error', 'message': 'Um download já está em progresso.'}), 400
    
    if not session.get('queue'):
        return jsonify({'status': 'error', 'message': 'A fila está vazia.'}), 400

    queue_to_download = list(session['queue'])
    
    # Prepara a estrutura de progresso
    progress_data["items"] = {item["id"]: {"status": "pending", "percentage": 0} for item in queue_to_download}
    
    session['queue'] = []
    session.modified = True
    
    thread = threading.Thread(target=download_worker, args=(queue_to_download,))
    thread.start()
    
    return jsonify({'status': 'started', 'queue': queue_to_download})

@app.route('/progress')
def get_progress():
    return jsonify(progress_data)

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    global progress_data
    if not progress_data['is_running']:
        session.pop('queue', None)
        flash("Fila limpa.", "info")
    else:
        flash("Não é possível limpar a fila enquanto um download está em andamento.", "error")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
