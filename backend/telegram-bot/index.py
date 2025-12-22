import json
import os
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Telegram бот-психолог с Gemini 3 Pro
    Обрабатывает сообщения пользователей и генерирует эмпатичные ответы
    """
    method = event.get('httpMethod', 'POST')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    if method == 'POST':
        body_str = event.get('body', '{}')
        update = json.loads(body_str)
        
        # Обработка сообщения от Telegram
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            # Команды бота
            if text == '/start':
                response_text = "🌸 Привет! Я бот-психолог, созданный, чтобы поддерживать вас.\n\n💙 Вы можете:\n• Поделиться своими переживаниями\n• Получить упражнения для релаксации\n• Задать вопросы о саморазвитии\n\nЧто вас беспокоит сегодня?"
                send_telegram_message(chat_id, response_text)
            
            elif text == '/exercises':
                response_text = "🌿 **Практические упражнения:**\n\n1️⃣ **Дыхание 4-7-8**\nВдох 4 сек → Задержка 7 сек → Выдох 8 сек\nПовторить 4 раза\n\n2️⃣ **Заземление 5-4-3-2-1**\n5 вещей, которые видите\n4 вещи, которые слышите\n3 вещи, которые чувствуете\n2 запаха\n1 вкус\n\n3️⃣ **Прогрессивная релаксация**\nНапрягите мышцы на 5 сек, затем расслабьте\nНачните со стоп, двигайтесь вверх\n\nВыберите упражнение и попробуйте! 🌸"
                send_telegram_message(chat_id, response_text)
            
            elif text.startswith('/'):
                response_text = "Доступные команды:\n/start - Начать\n/exercises - Упражнения\n\nИли просто напишите мне о том, что вас волнует 💙"
                send_telegram_message(chat_id, response_text)
            
            else:
                # Отправка запроса к Gemini
                gemini_response = get_gemini_response(text)
                send_telegram_message(chat_id, gemini_response)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'ok': True}),
            'isBase64Encoded': False
        }
    
    return {
        'statusCode': 405,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': 'Method not allowed'}),
        'isBase64Encoded': False
    }


def get_gemini_response(user_message: str) -> str:
    """Получение ответа от Gemini 3 Pro через прокси"""
    api_key = os.environ['GEMINI_API_KEY']
    proxy_url = os.environ.get('PROXY_URL', '')
    
    # Системный промпт психолога
    system_prompt = """Ты — опытный психолог с теплым эмпатичным стилем общения. 

Твои принципы:
• Всегда проявляй эмпатию и понимание
• Задавай уточняющие вопросы
• Давай практические советы
• Используй эмодзи 🌸💙🌿 для создания уюта
• Пиши короткими абзацами
• Не ставь диагнозы, а поддерживай
• Если ситуация серьезная, рекомендуй обратиться к специалисту очно

Стиль: дружеский, поддерживающий, теплый."""
    
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent?key={api_key}'
    
    payload = {
        'contents': [{
            'parts': [{
                'text': f"{system_prompt}\n\nСообщение пользователя: {user_message}"
            }]
        }],
        'generationConfig': {
            'temperature': 0.7,
            'topP': 0.8,
            'maxOutputTokens': 1024
        }
    }
    
    try:
        # Настройка прокси если указан
        if proxy_url:
            proxy_handler = urllib.request.ProxyHandler({
                'http': f'http://{proxy_url}',
                'https': f'https://{proxy_url}'
            })
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            # Обработка разных форматов ответа Gemini
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                
                # Пробуем разные структуры ответа
                if 'content' in candidate:
                    content = candidate['content']
                    if 'parts' in content and len(content['parts']) > 0:
                        text = content['parts'][0].get('text', '')
                        if text:
                            return text
                
                if 'text' in candidate:
                    return candidate['text']
                
                if 'output' in candidate:
                    return candidate['output']
            
            # Если ничего не нашли, возвращаем весь ответ для отладки
            return f"🌸 Получен ответ, но в неожиданном формате:\n{json.dumps(result, ensure_ascii=False, indent=2)[:500]}"
    
    except Exception as e:
        error_msg = str(e)
        return f"💙 Ошибка: {error_msg}\n\nНо я здесь и готов выслушать вас. Попробуйте команду /exercises для практик релаксации 🌿"


def send_telegram_message(chat_id: int, text: str) -> None:
    """Отправка сообщения в Telegram"""
    bot_token = os.environ['TELEGRAM_BOT_TOKEN']
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        pass  # Логирование ошибок в продакшене