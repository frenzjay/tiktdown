import requests
import os
import coloredlogs
import logging
import secrets
from tqdm import tqdm
from urllib.parse import urlparse, urlunparse
from flask import Flask, render_template, request, send_file, redirect, url_for

app = Flask(__name__)

SERVICE = 'TIKTOK'

LOG_FORMAT = "%(asctime)s - [{level[0]}] - {service} - %(message)s".format(level="levelname", service=SERVICE)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
coloredlogs.install(level='INFO', fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logger = logging.getLogger(SERVICE)

stop_signal = False

def check_link(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return False
    url = urlunparse(parsed_url)
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False

def download_video(url, filename):
    global stop_signal
    
    temp_dir = 'temp_downloads'
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = os.path.join(temp_dir, secrets.token_urlsafe(8) + '.mp4')

    response = requests.get(url, stream=True)
    file_size = int(response.headers.get('Content-Length', 0))
    progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f'Downloading {filename}')

    with open(temp_filename, 'wb') as file:
        for data in response.iter_content(chunk_size=1024):
            file.write(data)
            progress_bar.update(len(data))
            if stop_signal:
                break

    progress_bar.close()
    return temp_filename

def sigint_handler(signal, frame):
    global stop_signal
    stop_signal = True

@app.route('/', methods=['GET', 'POST'])
def index():
    global stop_signal

    if request.method == 'POST':
        input_id_normal = request.form['input_id_normal']
        input_url = request.form['input_url']
        option = request.form['option']

        if input_id_normal:
            url = f'https://tikwm.com/video/media/hdplay/{input_id_normal}.mp4'
            filename = f'{input_id_normal}_TikTok.mp4'
            
            try:
                temp_filename = download_video(url, filename)
            except KeyboardInterrupt:
                logger.info('Download interrupted.')
                return render_template('index.html', message='Download interrupted.')
            
            logger.info('Download completed.')
            return redirect(url_for('download', filename=os.path.basename(temp_filename)))

        elif input_url:
            parsed_url = urlparse(input_url)
            filename = parsed_url.path.split('/')[-1]
            id = filename.split('_')[0][7:]

            url_or4 = f'https://pull-flv-l11-va01.tiktokcdn.com/stage/stream-{id}_or4.flv'
            if option == '1':
                url = url_or4
            
            if check_link(url):
                try:
                    temp_filename = download_video(url, filename)
                except KeyboardInterrupt:
                    logger.info('Download interrupted.')
                    return render_template('index.html', message='Download interrupted.')
                
                logger.info('Download completed.')
                return redirect(url_for('download', filename=os.path.basename(temp_filename)))
            else:
                return render_template('index.html', message='Please specify a valid URL.')

    return render_template('index.html', message='')

@app.route('/download/<filename>')
def download(filename):
    temp_dir = 'temp_downloads'
    return send_file(os.path.join(temp_dir, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
