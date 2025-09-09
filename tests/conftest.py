#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Конфигурация pytest и общие fixtures
Фаза 7: Тестирование и Надежность
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

# Добавляем src в путь для импортов
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Также добавляем корневую директорию проекта
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_email_data() -> Dict[str, Any]:
    """Фикстура с примером данных email для тестирования"""
    return {
        'thread_id': 'test_thread_123',
        'from': 'test@example.com',
        'to': 'recipient@test.com',
        'subject': 'Тестовое письмо',
        'body': '''
        Добрый день!

        Меня зовут Иван Петров, я менеджер по продажам в ООО "Тестовая Компания".
        Мои контактные данные:
        - Телефон: +7 (999) 123-45-67
        - Email: ivan.petrov@testcompany.ru
        - Рабочий телефон: 8 (495) 111-22-33 доб. 456

        Буду рад обсудить сотрудничество!

        С уважением,
        Иван Петров
        Менеджер по продажам
        ООО "Тестовая Компания"
        Москва, ул. Тестовая, д. 1
        ''',
        'attachments': [],
        'metadata': {
            'file_name': 'test_email.json',
            'date': '2025-07-29',
            'source': 'test'
        }
    }


@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """Фикстура с mock ответом от LLM"""
    return {
        'content': '''{
            "contacts": [
                {
                    "name": "Иван Петров",
                    "phone": "+7 (999) 123-45-67",
                    "email": "ivan.petrov@testcompany.ru",
                    "organization": "ООО \\"Тестовая Компания\\"",
                    "position": "Менеджер по продажам",
                    "confidence": 0.95,
                    "source": "email_body"
                }
            ],
            "business_context": "Запрос на обсуждение сотрудничества от менеджера по продажам",
            "commercial_offers": []
        }''',
        'provider': 'openrouter',
        'response_time': 1.2,
        'tokens_used': 150
    }


@pytest.fixture
def mock_provider():
    """Фикстура с mock LLM провайдером"""
    provider = Mock()
    provider.name = 'mock_provider'
    provider.config.active = True
    provider.config.priority = 1
    provider.is_available.return_value = True
    provider.make_request.return_value = {
        'content': '{"contacts": [], "business_context": "test", "commercial_offers": []}',
        'provider': 'mock',
        'response_time': 0.1
    }
    return provider


@pytest.fixture
def mock_provider_manager(mock_provider):
    """Фикстура с mock менеджером провайдеров"""
    manager = Mock()
    manager.providers = {'mock': mock_provider}
    manager.make_request_with_fallback.return_value = {
        'content': '{"contacts": [], "business_context": "test", "commercial_offers": []}',
        'provider': 'mock',
        'response_time': 0.1
    }
    return manager


@pytest.fixture
def real_email_files():
    """Фикстура с реальными файлами email для тестирования"""
    email_dir = Path('data/emails/2025-07-29')
    if email_dir.exists():
        json_files = list(email_dir.glob('*.json'))
        return json_files[:5]  # Возвращаем первые 5 файлов для быстрого тестирования
    return []


@pytest.fixture
def real_email_data(real_email_files):
    """Фикстура с данными из реальных email файлов"""
    if not real_email_files:
        return []

    email_data_list = []
    for email_file in real_email_files:
        try:
            with open(email_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Ограничиваем размер текста для тестирования
            text = data.get('body', '')
            if len(text) > 3000:
                text = text[:3000] + "..."

            email_data_list.append({
                'file_path': email_file,
                'data': data,
                'text': text,
                'text_length': len(text),
                'attachments_count': len(data.get('attachments', []))
            })
        except Exception as e:
            print(f"Ошибка загрузки {email_file}: {e}")
            continue

    return email_data_list


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Автоматическая настройка тестового окружения"""
    # Здесь можно добавить общую настройку для всех тестов
    # Например, настройку логирования, временных файлов и т.д.
    pass
