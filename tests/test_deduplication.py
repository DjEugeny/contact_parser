#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест системы дедупликации контактов
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Создаем минимальную версию процессора только для тестирования дедупликации
class TestProcessor:
    """Минимальная версия процессора для тестирования дедупликации"""
    
    def _normalize_email(self, email: str) -> str:
        """🔧 Нормализация email для сравнения"""
        if not email:
            return ""
        return email.lower().strip()
    
    def _normalize_phone(self, phone: str) -> str:
        """🔧 Нормализация телефона для сравнения"""
        if not phone:
            return ""
        # Убираем все символы кроме цифр
        import re
        digits = re.sub(r'\D', '', phone)
        # Если начинается с 8, заменяем на 7
        if digits.startswith('8') and len(digits) == 11:
            digits = '7' + digits[1:]
        # Если начинается с 7 и длина 11 цифр - это российский номер
        if digits.startswith('7') and len(digits) == 11:
            return digits
        # Если длина 10 цифр, добавляем 7 в начало
        if len(digits) == 10:
            return '7' + digits
        return digits
    
    def _normalize_name(self, name: str) -> str:
        """🔧 Нормализация имени для сравнения"""
        if not name:
            return ""
        return ' '.join(name.lower().strip().split())
    
    def _merge_contact_group(self, contacts: list) -> dict:
        """🔗 Объединение группы дубликатов контактов"""
        if not contacts:
            return {}
        
        if len(contacts) == 1:
            return contacts[0]
        
        print(f"   🔗 Объединяю {len(contacts)} дубликатов контакта")
        
        # Базовый контакт - берем первый
        merged = contacts[0].copy()
        
        # Собираем все телефоны
        all_phones = set()
        max_confidence = 0
        
        for contact in contacts:
            # Обновляем поля, выбирая наиболее полные значения
            for field in ['name', 'organization', 'position', 'city']:
                current_value = merged.get(field, '')
                new_value = contact.get(field, '')
                
                # Берем более длинное непустое значение
                if len(str(new_value)) > len(str(current_value)):
                    merged[field] = new_value
            
            # Email берем первый непустой
            if not merged.get('email') and contact.get('email'):
                merged['email'] = contact['email']
            
            # Собираем все телефоны
            if contact.get('phone'):
                all_phones.add(contact['phone'])
            
            # Максимальный confidence
            contact_conf = contact.get('confidence', 0)
            if contact_conf > max_confidence:
                max_confidence = contact_conf
        
        # Устанавливаем объединенные данные
        if all_phones:
            merged['phone'] = list(all_phones)[0]  # Основной телефон
            if len(all_phones) > 1:
                merged['other_phones'] = list(all_phones)[1:]  # Дополнительные
        
        merged['confidence'] = max_confidence
        
        return merged
    
    def _deduplicate_contacts(self, contacts: list) -> list:
        """🔍 Дедупликация контактов по email, телефону и имени"""
        if not contacts:
            return []
        
        print(f"   🔍 Начинаю дедупликацию {len(contacts)} контактов")
        
        # Создаем граф связей между контактами
        contact_groups = []
        
        for i, contact in enumerate(contacts):
            # Ищем группы, с которыми этот контакт может объединиться
            matching_groups = []
            
            for group_idx, group in enumerate(contact_groups):
                should_merge = False
                
                for existing_contact in group:
                    # Проверяем по email
                    if contact.get('email') and existing_contact.get('email'):
                        if self._normalize_email(contact['email']) == self._normalize_email(existing_contact['email']):
                            should_merge = True
                            break
                    
                    # Проверяем по телефону
                    if contact.get('phone') and existing_contact.get('phone'):
                        if self._normalize_phone(contact['phone']) == self._normalize_phone(existing_contact['phone']):
                            should_merge = True
                            break
                    
                    # Проверяем по имени + организации
                    if (contact.get('name') and contact.get('organization') and 
                        existing_contact.get('name') and existing_contact.get('organization')):
                        contact_key = f"{self._normalize_name(contact['name'])}|{self._normalize_name(contact['organization'])}"
                        existing_key = f"{self._normalize_name(existing_contact['name'])}|{self._normalize_name(existing_contact['organization'])}"
                        if contact_key == existing_key:
                            should_merge = True
                            break
                
                if should_merge:
                    matching_groups.append(group_idx)
            
            if not matching_groups:
                # Создаем новую группу
                contact_groups.append([contact])
            elif len(matching_groups) == 1:
                # Добавляем в существующую группу
                contact_groups[matching_groups[0]].append(contact)
            else:
                # Объединяем несколько групп
                new_group = [contact]
                for group_idx in sorted(matching_groups, reverse=True):
                    new_group.extend(contact_groups[group_idx])
                    del contact_groups[group_idx]
                contact_groups.append(new_group)
        
        # Объединяем контакты в каждой группе
        unique_contacts = []
        duplicates_count = 0
        
        for group in contact_groups:
            if len(group) > 1:
                print(f"   🔗 Объединяю {len(group)} дубликатов контакта")
                duplicates_count += len(group) - 1
            
            merged = self._merge_contact_group(group)
            unique_contacts.append(merged)
        
        if duplicates_count > 0:
            print(f"   ✅ Найдено и объединено {duplicates_count} дубликатов")
            print(f"   📊 Итого уникальных контактов: {len(unique_contacts)}")
        else:
            print(f"   ℹ️ Дубликаты не найдены")
        
        return unique_contacts

def test_contact_deduplication():
    """Тест дедупликации контактов"""
    
    # Создаем процессор
    processor = TestProcessor()
    
    # Тестовые контакты с дубликатами
    test_contacts = [
        {
            'name': 'Иван Петров',
            'email': 'ivan.petrov@company.ru',
            'phone': '+7 (495) 123-45-67',
            'organization': 'ООО "Компания"',
            'position': 'Менеджер',
            'confidence': 0.9
        },
        {
            'name': 'Иван Петров',
            'email': 'ivan.petrov@company.ru',
            'phone': '+7-495-123-45-67',  # Тот же телефон, другой формат
            'organization': 'ООО Компания',
            'position': 'Старший менеджер',  # Более полная должность
            'confidence': 0.8
        },
        {
            'name': 'Мария Сидорова',
            'email': 'maria@test.com',
            'phone': '+7 (916) 555-66-77',
            'organization': 'ТестКомпани',
            'position': 'Директор',
            'confidence': 0.7
        },
        {
            'name': 'Петр Иванов',
            'email': '',
            'phone': '8-916-555-66-77',  # Тот же телефон что у Марии, но в формате 8
            'organization': 'Другая компания',
            'position': 'Сотрудник',
            'confidence': 0.6
        },
        {
            'name': 'Анна Козлова',
            'email': 'anna@example.org',
            'phone': '+7 (903) 777-88-99',
            'organization': 'Пример Орг',
            'position': 'Специалист',
            'confidence': 0.85
        }
    ]
    
    print("🧪 ТЕСТ ДЕДУПЛИКАЦИИ КОНТАКТОВ")
    print("=" * 50)
    print(f"📊 Исходное количество контактов: {len(test_contacts)}")
    print()
    
    # Показываем исходные контакты
    print("📋 ИСХОДНЫЕ КОНТАКТЫ:")
    for i, contact in enumerate(test_contacts, 1):
        print(f"   {i}. {contact['name']} | {contact['email']} | {contact['phone']} | {contact['organization']}")
    print()
    
    # Выполняем дедупликацию
    unique_contacts = processor._deduplicate_contacts(test_contacts)
    
    print(f"📊 Количество уникальных контактов: {len(unique_contacts)}")
    print()
    
    # Показываем результат
    print("✅ УНИКАЛЬНЫЕ КОНТАКТЫ ПОСЛЕ ДЕДУПЛИКАЦИИ:")
    for i, contact in enumerate(unique_contacts, 1):
        print(f"   {i}. {contact['name']} | {contact['email']} | {contact['phone']} | {contact['organization']} | {contact['position']} | conf: {contact['confidence']}")
        if 'other_phones' in contact:
            print(f"      📞 Дополнительные телефоны: {contact['other_phones']}")
    print()
    
    # Проверяем результаты
    expected_unique = 3  # Ожидаем 3 уникальных контакта
    if len(unique_contacts) == expected_unique:
        print(f"✅ ТЕСТ ПРОЙДЕН: Найдено {len(unique_contacts)} уникальных контактов (ожидалось {expected_unique})")
    else:
        print(f"❌ ТЕСТ НЕ ПРОЙДЕН: Найдено {len(unique_contacts)} уникальных контактов (ожидалось {expected_unique})")
    
    # Проверяем конкретные случаи
    print("\n🔍 ДЕТАЛЬНАЯ ПРОВЕРКА:")
    
    # Проверяем объединение по email
    ivan_contacts = [c for c in unique_contacts if 'ivan.petrov@company.ru' in c.get('email', '')]
    if len(ivan_contacts) == 1:
        ivan = ivan_contacts[0]
        print(f"   ✅ Контакты Ивана Петрова объединены: {ivan['position']} (должность взята более полная)")
        print(f"   ✅ Confidence взят максимальный: {ivan['confidence']} (было 0.9 и 0.8)")
    else:
        print(f"   ❌ Контакты Ивана Петрова не объединены: найдено {len(ivan_contacts)} записей")
    
    # Проверяем объединение по телефону
    phone_916_contacts = [c for c in unique_contacts if '916' in c.get('phone', '') or ('other_phones' in c and any('916' in p for p in c['other_phones']))]
    if len(phone_916_contacts) == 1:
        print(f"   ✅ Контакты с телефоном 916-555-66-77 объединены")
    else:
        print(f"   ❌ Контакты с телефоном 916-555-66-77 не объединены: найдено {len(phone_916_contacts)} записей")
    
    return len(unique_contacts) == expected_unique

if __name__ == '__main__':
    success = test_contact_deduplication()
    sys.exit(0 if success else 1)