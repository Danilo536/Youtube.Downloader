import os
import threading
from flask import Flask, render_template, request, flash, jsonify
import yt_dlp as ydl

app = Flask(__name__)
app.secret_key = 'geheim'

progress_data = {
    'percent': 0,
    'status': '',
    'finished': False,
    'error': None
}

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg):
        progress_data['error'] = msg

def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        downloaded = d.get('downloaded_bytes', 0)
        percent = int(downloaded / total * 100) if total else 0
        progress_data['percent'] = percent
        progress_data['status'] = f"Lade runter: {percent}%"
    elif d['status'] == 'finished':
        progress_data['percent'] = 100
        progress_data['status'] = "Download abgeschlossen"
    elif d['status'] == 'error':
        progress_data['error'] = 'Fehler beim Download'
    elif d['status'] == 'extracting':
        progress_data['status'] = "Extrahiere Informationen..."

def rename_webm_to_mp3(file_path):
    if file_path.endswith('.webm'):
        mp3_path = file_path[:-5] + '.mp3'
        try:
            os.rename(file_path, mp3_path)
            return mp3_path
        except Exception as e:
            progress_data['error'] = f"Fehler beim Umbenennen: {str(e)}"
    return file_path

def download_thread(url, download_path, is_playlist, file_format):
    progress_data['percent'] = 0
    progress_data['status'] = "Starte Download..."
    progress_data['finished'] = False
    progress_data['error'] = None

    if not os.path.exists(download_path):
        os.makedirs(download_path)

    if file_format == 'mp3':
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'logger': MyLogger(),
            'progress_hooks': [progress_hook],
            'noplaylist': not is_playlist,
            'format': 'bestaudio/best',
            'postprocessors': [],
        }
    else:
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'logger': MyLogger(),
            'progress_hooks': [progress_hook],
            'noplaylist': not is_playlist,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'merge_output_format': 'mp4',
        }

    try:
        with ydl.YoutubeDL(ydl_opts) as ydl_object:
            ydl_object.download([url])

        if file_format == 'mp3':
            for file in os.listdir(download_path):
                if file.endswith('.webm'):
                    full_path = os.path.join(download_path, file)
                    rename_webm_to_mp3(full_path)

        progress_data['status'] = "Download abgeschlossen"
    except Exception as e:
        progress_data['error'] = f"Fehler: {str(e)}"
    finally:
        progress_data['finished'] = True

@app.route('/')
def index():
    default_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    return render_template('index.html', default_path=default_path)

@app.route('/start_download', methods=['POST'])
def start_download():
    url = request.form.get('url')
    file_format = request.form.get('format', 'mp3')
    download_type = request.form.get('download_type', 'video')
    path = request.form.get('path', '')
    new_folder = request.form.get('new_folder')
    folder_name = request.form.get('folder_name', '').strip()

    if new_folder == 'yes' and folder_name:
        path = os.path.join(path, folder_name)

    if not url or not path:
        flash('URL und Pfad müssen angegeben werden!')
        return ('', 400)

    is_playlist = download_type == 'playlist'

    thread = threading.Thread(target=download_thread, args=(url, path, is_playlist, file_format))
    thread.start()

    return ('', 202)

@app.route('/get_progress')
def get_progress():
    return jsonify(progress_data)

if __name__ == '__main__':
    app.run(debug=True)
