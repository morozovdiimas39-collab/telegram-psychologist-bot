"""Вспомогательный модуль для автоматического создания секретов после создания VM"""

def should_create_secrets(vm_ip: str, webhook_url: str) -> dict:
    """Возвращает информацию о секретах которые нужно создать"""
    return {
        'secrets_needed': True,
        'secrets': [
            {
                'name': 'VM_IP_ADDRESS',
                'value': vm_ip,
                'description': 'IP адрес виртуальной машины в Yandex Cloud'
            },
            {
                'name': 'VM_WEBHOOK_URL', 
                'value': webhook_url,
                'description': 'URL webhook для автоматического деплоя'
            }
        ]
    }
