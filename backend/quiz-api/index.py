import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    dsn = os.environ.get('DATABASE_URL')
    return psycopg2.connect(dsn, cursor_factory=RealDictCursor)

def handler(event: dict, context) -> dict:
    '''API для работы с квизами: загрузка данных, сохранение ответов и лидов'''
    
    method = event.get('httpMethod', 'GET')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    params = event.get('queryStringParameters') or {}
    action = params.get('action', 'list')
    
    try:
        if method == 'GET' and action == 'get':
            slug = params.get('slug')
            if not slug:
                return error_response(400, 'Slug required')
            return get_quiz_by_slug(slug)
        
        elif method == 'POST' and action == 'submit':
            body = json.loads(event.get('body', '{}'))
            return submit_quiz_response(body)
        
        elif method == 'GET' and action == 'list':
            return get_all_quizzes()
        
        else:
            return error_response(404, 'Endpoint not found')
            
    except Exception as e:
        return error_response(500, str(e))

def get_quiz_by_slug(slug: str) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT id, title, slug, description, yandex_metrika_id, is_active
        FROM quizzes 
        WHERE slug = %s AND is_active = true
    ''', (slug,))
    
    quiz = cur.fetchone()
    
    if not quiz:
        cur.close()
        conn.close()
        return error_response(404, 'Quiz not found')
    
    quiz_id = quiz['id']
    
    cur.execute('''
        SELECT id, question_text, question_order, metrika_goal_prefix
        FROM questions 
        WHERE quiz_id = %s
        ORDER BY question_order
    ''', (quiz_id,))
    
    questions = cur.fetchall()
    
    for question in questions:
        cur.execute('''
            SELECT id, answer_text, answer_value, answer_order
            FROM answers 
            WHERE question_id = %s
            ORDER BY answer_order
        ''', (question['id'],))
        
        question['answers'] = cur.fetchall()
    
    quiz['questions'] = questions
    
    cur.close()
    conn.close()
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(dict(quiz)),
        'isBase64Encoded': False
    }

def submit_quiz_response(data: dict) -> dict:
    quiz_id = data.get('quiz_id')
    answers = data.get('answers', {})
    contact_info = data.get('contactInfo', {})
    segment_key = data.get('segment_key', '')
    
    if not quiz_id or not answers or not contact_info.get('name') or not contact_info.get('phone'):
        return error_response(400, 'Missing required fields')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO leads (quiz_id, name, phone, email, segment_key)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    ''', (
        quiz_id,
        contact_info.get('name'),
        contact_info.get('phone'),
        contact_info.get('email', ''),
        segment_key
    ))
    
    lead_id = cur.fetchone()['id']
    
    for question_id, answer_id in answers.items():
        cur.execute('''
            INSERT INTO quiz_responses (lead_id, question_id, answer_id)
            VALUES (%s, %s, %s)
        ''', (lead_id, int(question_id), int(answer_id)))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'success': True, 'lead_id': lead_id}),
        'isBase64Encoded': False
    }

def get_all_quizzes() -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT id, title, slug, description, is_active, created_at
        FROM quizzes 
        ORDER BY created_at DESC
    ''')
    
    quizzes = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps([dict(q) for q in quizzes], default=str),
        'isBase64Encoded': False
    }

def error_response(status_code: int, message: str) -> dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message}),
        'isBase64Encoded': False
    }