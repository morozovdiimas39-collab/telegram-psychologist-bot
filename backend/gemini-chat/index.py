import json
import os
import requests

def handler(event: dict, context) -> dict:
    '''API для общения с Gemini 2.0 Flash Experimental через прокси'''
    
    method = event.get('httpMethod', 'POST')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': ''
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        messages = body.get('messages', [])
        
        if not messages:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Messages required'})
            }
        
        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        
        if not api_key:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'API key not configured'})
            }
        
        # Преобразуем формат сообщений для Gemini
        gemini_contents = []
        for msg in messages:
            role = 'model' if msg['role'] == 'assistant' else 'user'
            gemini_contents.append({
                'role': role,
                'parts': [{'text': msg['content']}]
            })
        
        # Gemini API endpoint
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}'
        
        payload = {
            'contents': gemini_contents,
            'generationConfig': {
                'temperature': 0.7,
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': 8192,
            }
        }
        
        # Настройка прокси для обхода блокировки
        proxies = None
        if proxy_url:
            # Формат: user:pass@host:port - используем HTTP прокси
            proxies = {
                'http': f'http://{proxy_url}',
                'https': f'http://{proxy_url}'
            }
        
        # Запрос к Gemini
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
                })
            }
        
        result = response.json()
        
        # Извлекаем ответ
        if 'candidates' in result and len(result['candidates']) > 0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'response': text,
                    'model': 'gemini-2.0-flash-exp'
                })
            }
        else:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No response from Gemini'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }