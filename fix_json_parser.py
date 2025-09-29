#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔧 Исправление парсера JSON для решения проблемы с лишними пробелами"""

import re
import json

def fix_spaced_json(text: str) -> str:
    """
    🔧 Исправляет JSON с лишними пробелами между символами
    
    Проблема: LLM возвращает " organ izations " вместо "organizations"
    """
    print(f"🔧 Исправляем JSON с лишними пробелами...")
    
    # Сохраняем оригинальный текст для отладки
    original_text = text
    
    # 1. Удаление markdown блоков кода
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    
    # 2. КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Удаление лишних пробелов в ключах JSON
    # Ищем паттерн: "ключ с пробелами": значение
    def fix_spaced_key(match):
        key_with_spaces = match.group(1)
        # Удаляем все пробелы из ключа
        fixed_key = re.sub(r'\s+', '', key_with_spaces)
        return f'"{fixed_key}":'
    
    # Исправляем ключи с пробелами
    text = re.sub(r'"([^"]*\s[^"]*)":', fix_spaced_key, text)
    
    # 3. Исправляем значения строк с лишними пробелами
    def fix_spaced_value(match):
        prefix = match.group(1)  # ": "
        value_with_spaces = match.group(2)
        suffix = match.group(3)  # "
        
        # Если это выглядит как разделенное пробелами слово, склеиваем
        if len(value_with_spaces.split()) > 1:
            # Проверяем, не является ли это нормальным текстом
            words = value_with_spaces.split()
            if len(words) > 3 and all(len(word) <= 3 for word in words[:3]):
                # Это похоже на разделенные символы, склеиваем
                fixed_value = ''.join(words)
            else:
                # Это нормальный текст, оставляем пробелы
                fixed_value = value_with_spaces
        else:
            fixed_value = value_with_spaces
            
        return f'{prefix}"{fixed_value}"{suffix}'
    
    # Исправляем строковые значения с лишними пробелами
    text = re.sub(r'(:\s*)"([^"]*)"([,\s\}\]])', fix_spaced_value, text)
    
    # 4. Исправляем числовые значения с пробелами (например: " 1 . 0 " -> "1.0")
    def fix_spaced_number(match):
        prefix = match.group(1)  # ": "
        number_with_spaces = match.group(2)
        suffix = match.group(3)  # , } ]
        
        # Удаляем все пробелы из числа
        fixed_number = re.sub(r'\s+', '', number_with_spaces)
        return f'{prefix}{fixed_number}{suffix}'
    
    # Исправляем числа с пробелами
    text = re.sub(r'(:\s*)([0-9\s\.]+)([,\s\}\]])', fix_spaced_number, text)
    
    # 5. Удаление лишних запятых перед закрывающими скобками
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # 6. Добавление недостающих запятых между объектами в массивах
    text = re.sub(r'}\s*\n\s*{', r'},\n    {', text)
    
    # 7. Добавление недостающих запятых между полями объекта
    text = re.sub(r'"\s*\n\s*"(?![,\}\]\s])', r'",\n    "', text)
    
    # 8. Исправление булевых значений
    text = re.sub(r'\btrue\b', 'true', text)
    text = re.sub(r'\bfalse\b', 'false', text)
    text = re.sub(r'\bnull\b', 'null', text)
    
    if text != original_text:
        print(f"🔧 JSON был изменен для исправления ошибок")
        print(f"   Длина до: {len(original_text)}, после: {len(text)}")
    
    return text

def test_fix():
    """Тестируем исправление на примере проблемного JSON"""
    
    # Пример проблемного JSON из логов
    broken_json = '''```json 
 {
    " organ izations ":  [
      {
        " organization _id ":   1 ,
        " name ":  " Ц ент р  Ла бора тор ной  Ди аг ности ки ",
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
 ```'''
    
    print("🧪 Тестируем исправление JSON...")
    print(f"📝 Исходный JSON ({len(broken_json)} символов)")
    
    try:
        # Пытаемся распарсить как есть
        json.loads(broken_json)
        print("✅ JSON уже валидный")
    except json.JSONDecodeError as e:
        print(f"❌ JSON невалидный: {e}")
        
        # Исправляем
        fixed_json = fix_spaced_json(broken_json)
        print(f"🔧 Исправленный JSON ({len(fixed_json)} символов):")
        print(fixed_json[:500] + "..." if len(fixed_json) > 500 else fixed_json)
        
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
            
            if result.get('contacts'):
                contact = result['contacts'][0]
                print(f"   - Имя контакта: '{contact.get('name', '')}'")
                print(f"   - Должность: '{contact.get('position', '')}'")
            
            return result
            
        except json.JSONDecodeError as e2:
            print(f"❌ Исправление не помогло: {e2}")
            return None

if __name__ == "__main__":
    test_fix()