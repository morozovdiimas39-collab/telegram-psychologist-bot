import json
import os
import requests
from typing import Any
from itertools import product

def handler(event: dict, context: Any) -> dict:
    """API для автоматического создания целей и сегментов в Яндекс.Метрике"""
    
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
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    token = os.environ.get('YANDEX_METRIKA_TOKEN')
    counter_id = os.environ.get('YANDEX_METRIKA_COUNTER_ID')
    
    if not token or not counter_id:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'YANDEX_METRIKA_TOKEN и YANDEX_METRIKA_COUNTER_ID должны быть настроены'})
        }
    
    body = json.loads(event.get('body', '{}'))
    quiz_data = body.get('quiz')
    
    if not quiz_data or not quiz_data.get('questions'):
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Отсутствуют данные квиза'})
        }
    
    created_goals = []
    goal_id_map = {}
    
    for question in quiz_data['questions']:
        for answer in question.get('answers', []):
            goal_name = answer.get('metrika_goal')
            if not goal_name:
                continue
            
            goal_data = {
                'goal': {
                    'name': goal_name,
                    'type': 'action',
                    'conditions': [{
                        'type': 'exact',
                        'url': f'goal_{goal_name}'
                    }]
                }
            }
            
            try:
                response = requests.post(
                    f'https://api-metrika.yandex.net/management/v1/counter/{counter_id}/goals',
                    headers={
                        'Authorization': f'OAuth {token}',
                        'Content-Type': 'application/json'
                    },
                    json=goal_data,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    goal_info = response.json()
                    goal_id = goal_info.get('goal', {}).get('id')
                    goal_id_map[goal_name] = goal_id
                    created_goals.append({
                        'name': goal_name,
                        'id': goal_id,
                        'status': 'created'
                    })
                elif response.status_code == 409:
                    created_goals.append({
                        'name': goal_name,
                        'status': 'already_exists'
                    })
                else:
                    created_goals.append({
                        'name': goal_name,
                        'status': 'error',
                        'error': response.text
                    })
                    
            except Exception as e:
                created_goals.append({
                    'name': goal_name,
                    'status': 'error',
                    'error': str(e)
                })
    
    goal_groups = []
    for question in quiz_data['questions']:
        goals = [answer.get('metrika_goal') for answer in question.get('answers', []) if answer.get('metrika_goal')]
        if goals:
            goal_groups.append(goals)
    
    created_segments = []
    
    if len(goal_groups) >= 2:
        combinations = list(product(*goal_groups))
        
        for combo in combinations:
            segment_name = '_'.join([
                goal.replace('rooms_', '').replace('payment_', '').replace('timing_', '')
                for goal in combo
            ])
            
            conditions = []
            for goal in combo:
                if goal in goal_id_map:
                    conditions.append({
                        'type': 'goal',
                        'goal_id': goal_id_map[goal]
                    })
            
            if not conditions:
                continue
            
            segment_data = {
                'segment': {
                    'name': f'Сегмент: {segment_name}',
                    'expression': {
                        'and': conditions
                    }
                }
            }
            
            try:
                response = requests.post(
                    f'https://api-metrika.yandex.net/management/v1/counter/{counter_id}/segments',
                    headers={
                        'Authorization': f'OAuth {token}',
                        'Content-Type': 'application/json'
                    },
                    json=segment_data,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    segment_info = response.json()
                    created_segments.append({
                        'name': segment_name,
                        'id': segment_info.get('segment', {}).get('segment_id'),
                        'goals': list(combo),
                        'status': 'created'
                    })
                elif response.status_code == 409:
                    created_segments.append({
                        'name': segment_name,
                        'goals': list(combo),
                        'status': 'already_exists'
                    })
                else:
                    created_segments.append({
                        'name': segment_name,
                        'goals': list(combo),
                        'status': 'error',
                        'error': response.text
                    })
                    
            except Exception as e:
                created_segments.append({
                    'name': segment_name,
                    'goals': list(combo),
                    'status': 'error',
                    'error': str(e)
                })
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'success': True,
            'created_goals': created_goals,
            'total_goals': len(created_goals),
            'created_segments': created_segments,
            'total_segments': len(created_segments)
        })
    }
