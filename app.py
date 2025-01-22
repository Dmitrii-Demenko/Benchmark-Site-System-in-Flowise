from flask import Flask, request, jsonify, send_from_directory, abort, url_for
from parser import parse_website
import os

app = Flask(__name__)

# Директория, где хранятся скриншоты
SCREENSHOTS_DIR = 'screenshots'

@app.route('/parse', methods=['POST'])
def parse_route():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL не предоставлен'}), 400
    try:
        result = parse_website(url)
        
        screenshot_filename = result.get('screenshot_filename')
        if screenshot_filename:
            # Формируем полный URL к скриншоту
            screenshot_url = url_for('serve_screenshot', filename=screenshot_filename, _external=True)
            result['screenshot_url'] = screenshot_url
            # Удаляем имя файла из результата, так как теперь есть URL
            del result['screenshot_filename']
        else:
            result['screenshot_url'] = None

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    # Проверяем существование файла
    if not os.path.exists(os.path.join(SCREENSHOTS_DIR, filename)):
        abort(404)
    return send_from_directory(SCREENSHOTS_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
