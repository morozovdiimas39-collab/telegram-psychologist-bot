#!/usr/bin/env python3
"""
Прокси-сервер на VM для обхода блокировки Gemini API
Запуск: python3 vm-gemini-proxy.py
"""

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Настройки
GEMINI_API_KEY = 'AIzaSyBheSf96XE7Svv5nDbJvEv-vq2ynS8oIlA'
PROXY_URL = 'user341025:64tojn@104.164.25.231:1879'

@app.route('/gemini-proxy', methods=['POST', 'OPTIONS'])
def gemini_proxy():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.json
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({'error': 'Messages required'}), 400
        
        # Формируем запрос для Gemini
        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent?key={GEMINI_API_KEY}'
        
        # Преобразуем сообщения в формат Gemini
        contents = []
        for msg in messages:
            role = 'model' if msg['role'] == 'assistant' else 'user'
            contents.append({
                'role': role,
                'parts': [{'text': msg['content']}]
            })
        
        payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': 0.7,
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 8192,
            }
        }
        
        # Используем SOCKS прокси
        proxies = {
            'http': f'socks5://{PROXY_URL}',
            'https': f'socks5://{PROXY_URL}'
        }
        
        # Отправляем запрос через прокси
        response = requests.post(
            gemini_url,
            json=payload,
            proxies=proxies,
            timeout=60
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Gemini API error',
                'details': response.text
            }), response.status_code
        
        result = response.json()
        
        # Извлекаем ответ
        if 'candidates' in result and len(result['candidates']) > 0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            return jsonify({
                'response': text,
                'model': 'gemini-3-pro-preview'
            })
        else:
            return jsonify({'error': 'No response from Gemini'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'gemini-proxy'})

if __name__ == '__main__':
    # Слушаем на всех интерфейсах порт 8888
    app.run(host='0.0.0.0', port=8888, debug=False)
