#!/usr/bin/env python3
"""
Простой HTTP-прокси сервер для Gemini API на VM
Использует SOCKS5 прокси для обхода геоблокировки
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех доменов

# Твой SOCKS прокси
SOCKS_PROXY = 'socks5://user341025:64tojn@104.164.25.231:1879'

@app.route('/api/gemini', methods=['POST', 'OPTIONS'])
def proxy_gemini():
    """Проксирует запросы к Gemini API через SOCKS"""
    
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Получаем данные от клиента
        client_data = request.json
        api_key = client_data.get('api_key')
        contents = client_data.get('contents')
        
        if not api_key or not contents:
            return jsonify({'error': 'api_key and contents required'}), 400
        
        # URL Gemini API
        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent?key={api_key}'
        
        # Формируем payload для Gemini
        payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': 0.7,
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 8192,
            }
        }
        
        # Отправляем через SOCKS прокси
        proxies = {
            'http': SOCKS_PROXY,
            'https': SOCKS_PROXY
        }
        
        response = requests.post(
            gemini_url,
            json=payload,
            proxies=proxies,
            timeout=60
        )
        
        # Возвращаем результат клиенту
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'proxy': 'working'})

if __name__ == '__main__':
    print("🚀 Запускаю прокси-сервер на порту 3001...")
    print(f"🔒 SOCKS прокси: {SOCKS_PROXY}")
    app.run(host='0.0.0.0', port=3001, debug=False)
