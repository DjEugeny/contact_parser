#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔧 Продвинутый фиксер JSON для решения проблемы с лишними пробелами от Replicate"""

import re
import json

def advanced_fix_spaced_json(text: str) -> str:
    """
    🔧 Продвинутое исправление JSON с лишними пробелами между символами
    
    Проблема: Replicate возвращает " organ izations " вместо "organizations"
    """
    print(f"🔧 Продвинутое исправление JSON с лишними пробелами...")
    
    # Сохраняем оригинальный текст для отладки
    original_text = text
    
    # 1. Удаление markdown блоков кода
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    
    # 2. АГРЕССИВНОЕ ИСПРАВЛЕНИЕ: Удаляем ВСЕ лишние пробелы внутри кавычек
    def fix_quoted_content(match):
        quote_content = match.group(1)
        # Если это ключ JSON (содержит подчеркивания или выглядит как ключ)
        if '_' in quote_content or quote_content.lower() in [
            'organizations', 'contacts', 'business context', 'summary', 'key points',
            'commercial offers', 'interactions', 'organization id', 'contact id',
            'name', 'inn', 'website', 'city', 'address', 'emails', 'phones',
            'position', 'email', 'role in message', 'confidence', 'type', 'number',
            'topic', 'product interest', 'communication stage', 'request type'
        ]:
            # Это ключ - удаляем все пробелы
            fixed = re.sub(r'\s+', '', quote_content)
        else:
            # Это значение - умное склеивание
            words = quote_content.split()
            if len(words) > 2:
                # Проверяем, не разделенное ли это слово
                total_chars = sum(len(word) for word in words)
                if total_chars / len(words) < 3:  # Средняя длина слова < 3 символов
                    # Это разделенное слово, склеиваем
                    fixed = ''.join(words)
                else:
                    # Это нормальный текст, оставляем пробелы между словами
                    fixed = ' '.join(words)
            else:
                # Короткий текст, склеиваем
                fixed = ''.join(words)
        
        return f'"{fixed}"'
    
    # Исправляем содержимое в кавычках
    text = re.sub(r'"([^"]*)"', fix_quoted_content, text)
    
    # 3. Исправляем числовые значения с пробелами (например: " 1 . 0 " -> "1.0")
    def fix_spaced_number(match):
        prefix = match.group(1)  # ": "
        number_with_spaces = match.group(2)
        suffix = match.group(3)  # , } ]
        
        # Удаляем все пробелы из числа
        fixed_number = re.sub(r'\s+', '', number_with_spaces)
        return f'{prefix}{fixed_number}{suffix}'
    
    # Исправляем числа с пробелами
    text = re.sub(r'(:\s*)([0-9\s\.]+)([,\s\}\]])', fix_spaced_number, text)
    
    # 4. Исправляем булевы значения с пробелами
    text = re.sub(r':\s*t\s*r\s*u\s*e\s*([,\}\]])', r': true\1', text)
    text = re.sub(r':\s*f\s*a\s*l\s*s\s*e\s*([,\}\]])', r': false\1', text)
    text = re.sub(r':\s*n\s*u\s*l\s*l\s*([,\}\]])', r': null\1', text)
    
    # 5. Удаление лишних запятых перед закрывающими скобками
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # 6. Добавление недостающих запятых между объектами в массивах
    text = re.sub(r'}\s*\n\s*{', r'},\n    {', text)
    
    # 7. Добавление недостающих запятых между полями объекта
    text = re.sub(r'"\s*\n\s*"(?![,\}\]\s])', r'",\n    "', text)
    
    # 8. Исправление неэкранированных кавычек в значениях
    text = re.sub(r'(?<!\\)"(?![,\}\]\s:"])', r'\\"', text)
    
    if text != original_text:
        print(f"🔧 JSON был изменен для исправления ошибок")
        print(f"   Длина до: {len(original_text)}, после: {len(text)}")
    
    return text

def test_advanced_fix():
    """Тестируем продвинутое исправление на примере проблемного JSON"""
    
    # Пример проблемного JSON из логов
    broken_json = ''' ```json 
 {
    " organ izations ":  [
      {
        " organization _id ":   1 ,
        " name ":  " Ц ент р  Ла бора тор ной  Ди аг но сти ки ",
        " inn ":  null ,
        " website ":  null ,
        " city ":  " Н ово си бир ск ",
        " address ":  " 630 075 ,  г .  Н ово си бир ск ,  ул .  Н арод ная ,   3 ",
        " emails ":  [],
        " phones ":  [" +7 -913 -399 -32 -72 "]
      }
    ],
    " contacts ":  [
      {
        " contact _id ":   1 ,
        " name ":  " Б аби чен ко  И ван  С ерг ее вич ",
        " organization _id ":   1 ,
        " position ":  " Р уко води тель  О М Т С ",
        " email ":  null ,
        " phones ":  [
          {
            " type ":  " office ",
            " number ":  " +7 -913 -399 -32 -72 "
          }
        ],
        " city ":  " Н ово си бир ск ",
        " address ":  " 630 075 ,  г .  Н ово си бир ск ,  ул .  Н арод ная ,   3 ",
        " role _in _message ":  " sender ",
        " confidence ":   0 . 9 
      }
    ]
 }
 ''' 
    
    print("🧪 Тестируем продвинутое исправление JSON...")
    print(f"📝 Исходный JSON ({len(broken_json)} символов)")
    
    try:
        # Пытаемся распарсить как есть
        json.loads(broken_json)
        print("✅ JSON уже валидный")
    except json.JSONDecodeError as e:
        print(f"❌ JSON невалидный: {e}")
        
        # Исправляем
        fixed_json = advanced_fix_spaced_json(broken_json)
        print(f"🔧 Исправленный JSON ({len(fixed_json)} символов):")
        print(fixed_json[:800] + "..." if len(fixed_json) > 800 else fixed_json)
        
        try:
            # Пытаемся распарсить исправленный
            result = json.loads(fixed_json)
            print("✅ Исправленный JSON валидный!")
            
            # Показываем результат
            print(f"📊 Найдено:")
            print(f"   - Организации: {len(result.get('organizations', []))}")
            print(f"   - Контакты: {len(result.get('contacts', []))}")
            
            if result.get('organizations'):
                org = result['organizations'][0]
                print(f"   - Название организации: '{org.get('name', '')}'")
                print(f"   - Город: '{org.get('city', '')}'")
                print(f"   - Адрес: '{org.get('address', '')}'")
            
            if result.get('contacts'):
                contact = result['contacts'][0]
                print(f"   - Имя контакта: '{contact.get('name', '')}'")
                print(f"   - Должность: '{contact.get('position', '')}'")
                print(f"   - Роль: '{contact.get('role_in_message', '')}'")
            
            return result
            
        except json.JSONDecodeError as e2:
            print(f"❌ Исправление не помогло: {e2}")
            return None

if __name__ == "__main__":
    test_advanced_fix()