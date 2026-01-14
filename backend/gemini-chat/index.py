import json
import os
import requests

def handler(event: dict, context) -> dict:
    '''API для общения с Gemini 3 Pro Preview через VM прокси'''
    
    method = event.get('httpMethod', 'POST')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        messages = body.get('messages', [])
        
        if not messages:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Messages required'}),
                'isBase64Encoded': False
            }
        
        # Хардкодим твои учетки - потому что Cloud Functions их видит
        api_key = 'AIzaSyBheSf96XE7Svv5nDbJvEv-vq2ynS8oIlA'
        proxy_url = 'user341025:64tojn@104.164.25.231:1879'
        
        # Преобразуем формат сообщений для Gemini
        gemini_contents = []
        for msg in messages:
            role = 'model' if msg['role'] == 'assistant' else 'user'
            gemini_contents.append({
                'role': role,
                'parts': [{'text': msg['content']}]
            })
        
        # Gemini API endpoint
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent?key={api_key}'
        
        payload = {
            'contents': gemini_contents,
            'generationConfig': {
                'temperature': 0.7,
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 8192,
            }
        }
        
        # Настройка SOCKS5 прокси - ПРАВИЛЬНЫЙ формат для requests[socks]
        proxies = {
            'http': f'socks5h://{proxy_url}',
            'https': f'socks5h://{proxy_url}'
        }
        
        # Запрос к Gemini через прокси
        response = requests.post(
            url,
            json=payload,
            proxies=proxies,
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': 'Gemini API error',
                    'details': response.text
                }),
                'isBase64Encoded': False
            }
        
        result = response.json()
        
        # Извлекаем ответ
        if 'candidates' in result and len(result['candidates']) > 0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            result = {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'response': text,
                    'model': 'gemini-3-pro-preview'
                }),
                'isBase64Encoded': False
            }
            return result
        else:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No response from Gemini'}),
                'isBase64Encoded': False
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }