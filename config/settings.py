#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ Основные настройки мини-CRM
"""

import os
from pathlib import Path

# 📁 Пути проекта
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"

# 📧 IMAP настройки
IMAP_CONFIG = {
    'server': os.getenv('IMAP_SERVER'),
    'port': int(os.getenv('IMAP_PORT', 143)),
    'user': os.getenv('IMAP_USER'),
    'password': os.getenv('IMAP_PASSWORD'),
    'max_retries': 3,
    'retry_delay': 5,
    'batch_size': 50,
    'request_delay': 0.5
}

# 🤖 LLM настройки
LLM_CONFIG = {
    'extractor': {
        'provider': 'openrouter',
        'model': 'qwen/qwen3-235b-a22b:free',
        'api_key': os.getenv('OPENROUTER_API_KEY'),
        'base_url': 'https://openrouter.ai/api/v1',
        'max_tokens': 4000,
        'temperature': 0.1
    },
    'analyzer': {
        'provider': 'replicate',
        'model': 'openai/gpt-4o-mini',
        'api_key': os.getenv('REPLICATE_API_KEY'),
        'max_tokens': 3000,
        'temperature': 0.2
    }
}

# 📊 Google Sheets
SHEETS_CONFIG = {
    'service_account_path': PROJECT_ROOT / 'config' / 'service_account.json',
    'spreadsheet_name': 'Sveta CRM Contacts',
    'worksheets': {
        'contacts': 'Contacts',
        'interactions': 'Interactions', 
        'review': 'Review'
    }
}

# 🏢 Компания Светы
COMPANY_CONFIG = {
    'domain': 'dna-technology.ru',
    'regions': {
        'high_priority': [
            'Новосибирск', 'Томск', 'Кемерово', 
            'Барнаул', 'Горно-Алтайск', 'Новокузнецк', 
            'Абакан', 'Улан-Удэ'
        ],
        'medium_priority': ['Кызыл'],
        'low_priority': ['Красноярск', 'Иркутск']
    }
}

# 🏛️ ИНН обогащение организаций
INN_ENRICHMENT_CONFIG = {
    'enabled': True,
    'auto_accept_threshold': 0.85,
    'review_threshold': 0.65,
    'providers': {
        'fns_integration': {
            'enabled': False,  # Будет включен когда получим API
            'timeout_ms': 6000
        },
        'fns_public': {
            'enabled': True,
            'timeout_ms': 6000
        },
        'dadata': {
            'enabled': True,
            'api_key': os.getenv('DADATA_API_KEY'),
            'secret_key': os.getenv('DADATA_SECRET_KEY'),
            'timeout_ms': 3000
        },
        'rusprofile': {
            'enabled': False,  # Добавим позже если нужно
            'timeout_ms': 4000
        }
    },
    'cache': {
        'path': PROJECT_ROOT / 'registry' / 'inn_cache.jsonl',
        'ttl_days': 180
    },
    'overrides_path': PROJECT_ROOT / 'registry' / 'inn_overrides.yml',
    'legal': {
        'allow_ip_inn': True,
        'store_personal_data': 'minimal'
    }
}
# 📞 Обогащение телефонов контактов от организаций
CONTACT_PHONE_ENRICHMENT_CONFIG = {
    # ========== ОСНОВНЫЕ НАСТРОЙКИ ==========
    
    # Включение/выключение всего модуля обогащения
    'enabled': True,  # False - полностью отключить обогащение телефонами
    
    # Пороги confidence для обычных телефонов (main, office, fax)
    'min_confidence_threshold': 0.5,  # Минимальный порог для обогащения (0.0-1.0)
    'review_threshold': 0.75,  # Порог для автоматического принятия без проверки
    
    # Разрешенные типы телефонов для обогащения (без mobile по умолчанию)
    'allowed_phone_types': ['main', 'office', 'fax'],
    
    # Режим обогащения (влияет на пороги confidence)
    # - 'conservative': высокие требования (min_threshold >= 0.75)
    # - 'balanced': стандартные пороги (по умолчанию)
    # - 'aggressive': низкие требования (min_threshold <= 0.4)
    'enrichment_mode': 'balanced',
    
    # ========== ОБОГАЩЕНИЕ МОБИЛЬНЫМИ ТЕЛЕФОНАМИ ==========
    
    'mobile_enrichment': {
        # ГЛАВНЫЙ ФЛАГ: разрешить обогащение мобильными телефонами организаций
        # Используйте с осторожностью! Mobile телефоны могут быть персональными.
        'enabled': True,  # True - разрешить добавление mobile телефонов контактам
        
        # Пониженный порог confidence для mobile (т.к. это более рискованно)
        # Рекомендуется держать ниже основного порога, но не слишком низко
        'min_confidence_threshold': 0.3,  # Минимум 0.3 для безопасности
        
        # Требовать упоминание имени контакта во вложении для mobile обогащения
        # True - строже (только если имя найдено в тексте вложения)
        # False - мягче (достаточно других факторов confidence)
        'require_name_in_attachment': False,
        
        # Учитывать близость телефона к имени во вложении (proximity boost)
        # Добавляет +0.2 к confidence если телефон рядом с именем контакта
        'proximity_boost': True,
    },
    
    # ========== ВЕСА ФАКТОРОВ ДЛЯ РАСЧЕТА CONFIDENCE ==========
    
    # Настройка весов для каждого фактора при расчете уверенности обогащения
    # Сумма может быть > 1.0, т.к. не все факторы применяются одновременно
    'scoring_factors': {
        'corporate_email': 0.3,      # Корпоративный email с доменом организации
        'position': 0.2,              # Наличие должности у контакта
        'role_in_message': 0.2,       # Активная роль (sender, recipient)
        'city_match': 0.15,           # Совпадение города контакта и организации
        'high_value_score': 0.15,     # Высокий value_score (≥ 7)
        'name_in_attachment': 0.3,    # Имя контакта найдено во вложении
        'phone_proximity': 0.2,       # Телефон рядом с именем во вложении (2-3 строки)
    }
    
    # ========== ПРИМЕРЫ КОНФИГУРАЦИЙ ==========
    
    # Консервативный режим (только офисные, высокий порог):
    # 'enrichment_mode': 'conservative',
    # 'min_confidence_threshold': 0.75,
    # 'mobile_enrichment': {'enabled': False}
    
    # Сбалансированный режим (офисные + избранные mobile):
    # 'enrichment_mode': 'balanced',
    # 'min_confidence_threshold': 0.5,
    # 'mobile_enrichment': {'enabled': True, 'min_confidence_threshold': 0.4}
    
    # Агрессивный режим (максимум обогащения):
    # 'enrichment_mode': 'aggressive',
    # 'min_confidence_threshold': 0.3,
    # 'mobile_enrichment': {'enabled': True, 'min_confidence_threshold': 0.2}
}
