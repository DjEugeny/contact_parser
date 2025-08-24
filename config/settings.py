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
        'api_key': os.getenv('REPLICATE_API_TOKEN'),
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
