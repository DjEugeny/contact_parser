#!/usr/bin/env python3
"""Тест обработки email_035"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Читаем письмо
email_path = Path("data/emails/2025-07-29/email_035_20250729_20250729_yandex_ru_f37d60ba.json")

with open(email_path, 'r') as f:
    email_data = json.load(f)

print("📧 Email_035:")
print(f"  От: {email_data['from']}")
print(f"  Тема: {email_data['subject']}")
print(f"  Текст: {email_data['body']}")
print(f"  Вложения: {len(email_data['attachments'])}")

# Проверим что происходит когда нет контактов/организаций
test_result = {
    'contacts': [],
    'organizations': [],
    'interactions': []
}

print("\n✅ Тестовый результат (пустой):")
print(json.dumps(test_result, indent=2, ensure_ascii=False))

