#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Продвинутый модуль дедупликации контактов
Обрабатывает сложные случаи дублирования в цепочках пересылок и больших письмах
"""

import re
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher
from collections import defaultdict


class AdvancedContactDeduplicator:
    """🔧 Продвинутый дедупликатор контактов с семантическим анализом"""
    
    def __init__(self):
        self.similarity_threshold = 0.75  # Порог схожести для имен (понижен)
        self.phone_similarity_threshold = 0.9  # Порог для телефонов
        
    def deduplicate_contacts(self, contacts: List[Dict]) -> List[Dict]:
        """🎯 Основной метод дедупликации с многоуровневым анализом"""
        if not contacts:
            return []
            
        print(f"   🔍 Продвинутая дедупликация {len(contacts)} контактов")
        
        # Этап 0: Анализ цепочек пересылок и удаление явных дубликатов
        forward_cleaned = self._clean_forward_chain_duplicates(contacts)
        
        # Этап 1: Точные совпадения по email/телефону
        exact_groups = self._group_by_exact_matches(forward_cleaned)
        
        # Этап 2: Семантические совпадения по именам
        semantic_groups = self._group_by_semantic_similarity(exact_groups)
        
        # Этап 3: Объединение групп и создание финальных контактов
        unique_contacts = self._merge_contact_groups(semantic_groups)
        
        duplicates_removed = len(contacts) - len(unique_contacts)
        if duplicates_removed > 0:
            print(f"   ✅ Удалено {duplicates_removed} дубликатов (продвинутый алгоритм)")
            print(f"   📊 Итого уникальных контактов: {len(unique_contacts)}")
        
        return unique_contacts
    
    def _group_by_exact_matches(self, contacts: List[Dict]) -> List[List[Dict]]:
        """📧 Группировка по точным совпадениям email/телефона"""
        email_groups = defaultdict(list)
        phone_groups = defaultdict(list)
        ungrouped = []
        
        for contact in contacts:
            email = self._normalize_email(contact.get('email', ''))
            phone = self._normalize_phone(contact.get('phone', ''))
            
            grouped = False
            
            # Группируем по email (приоритет 1)
            if email:
                email_groups[email].append(contact)
                grouped = True
            
            # Группируем по телефону (приоритет 2), если нет email
            elif phone and len(phone) > 6:
                phone_groups[phone].append(contact)
                grouped = True
            
            if not grouped:
                ungrouped.append(contact)
        
        # Собираем все группы
        groups = []
        groups.extend([group for group in email_groups.values() if len(group) > 0])
        groups.extend([group for group in phone_groups.values() if len(group) > 0])
        groups.extend([[contact] for contact in ungrouped])  # Одиночные контакты
        
        return groups
    
    def _group_by_semantic_similarity(self, groups: List[List[Dict]]) -> List[List[Dict]]:
        """🧠 Группировка по семантическому сходству имен и организаций"""
        final_groups = []
        
        for group in groups:
            if len(group) == 1:
                final_groups.append(group)
                continue
            
            # Для групп с несколькими контактами ищем семантические дубликаты
            subgroups = self._find_semantic_duplicates(group)
            final_groups.extend(subgroups)
        
        return final_groups
    
    def _find_semantic_duplicates(self, contacts: List[Dict]) -> List[List[Dict]]:
        """🔍 Поиск семантических дубликатов в группе контактов"""
        if len(contacts) <= 1:
            return [contacts]
        
        # Создаем матрицу схожести
        similarity_matrix = []
        for i, contact1 in enumerate(contacts):
            row = []
            for j, contact2 in enumerate(contacts):
                if i == j:
                    row.append(1.0)
                else:
                    similarity = self._calculate_contact_similarity(contact1, contact2)
                    row.append(similarity)
            similarity_matrix.append(row)
        
        # Группируем по схожести
        groups = []
        used_indices = set()
        
        for i in range(len(contacts)):
            if i in used_indices:
                continue
            
            group = [contacts[i]]
            used_indices.add(i)
            
            # Ищем похожие контакты
            for j in range(i + 1, len(contacts)):
                if j in used_indices:
                    continue
                
                if similarity_matrix[i][j] >= self.similarity_threshold:
                    group.append(contacts[j])
                    used_indices.add(j)
            
            groups.append(group)
        
        return groups
    
    def _calculate_contact_similarity(self, contact1: Dict, contact2: Dict) -> float:
        """📊 Расчет схожести между двумя контактами"""
        scores = []
        
        # Схожесть имен (вес 50%) - увеличен вес
        name1 = self._normalize_name(contact1.get('name', ''))
        name2 = self._normalize_name(contact2.get('name', ''))
        if name1 and name2:
            name_similarity = self._calculate_name_similarity(name1, name2)
            scores.append(('name', name_similarity, 0.5))
        
        # Схожесть организаций (вес 25%)
        org1 = self._normalize_name(contact1.get('organization', ''))
        org2 = self._normalize_name(contact2.get('organization', ''))
        if org1 and org2:
            org_similarity = self._calculate_organization_similarity(org1, org2)
            scores.append(('org', org_similarity, 0.25))
        
        # Схожесть должностей (вес 15%)
        pos1 = self._normalize_name(contact1.get('position', ''))
        pos2 = self._normalize_name(contact2.get('position', ''))
        if pos1 and pos2:
            pos_similarity = SequenceMatcher(None, pos1, pos2).ratio()
            scores.append(('position', pos_similarity, 0.15))
        
        # Схожесть городов (вес 10%)
        city1 = self._normalize_name(contact1.get('city', ''))
        city2 = self._normalize_name(contact2.get('city', ''))
        if city1 and city2:
            city_similarity = self._calculate_city_similarity(city1, city2)
            scores.append(('city', city_similarity, 0.1))
        
        # Вычисляем взвешенную схожесть
        if not scores:
            return 0.0
        
        total_weight = sum(weight for _, _, weight in scores)
        weighted_sum = sum(score * weight for _, score, weight in scores)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _merge_contact_groups(self, groups: List[List[Dict]]) -> List[Dict]:
        """🔗 Объединение групп контактов в финальные уникальные записи"""
        unique_contacts = []
        
        for group in groups:
            if len(group) == 1:
                unique_contacts.append(group[0])
            else:
                merged_contact = self._merge_contact_group(group)
                unique_contacts.append(merged_contact)
        
        return unique_contacts
    
    def _merge_contact_group(self, contacts: List[Dict]) -> Dict:
        """🔗 Объединение группы дубликатов в один контакт"""
        if not contacts:
            return {}
        
        if len(contacts) == 1:
            return contacts[0]
        
        print(f"   🔗 Объединяю {len(contacts)} семантически похожих контактов")
        
        # Базовый контакт - выбираем наиболее полный
        base_contact = max(contacts, key=lambda c: self._calculate_contact_completeness(c))
        merged = base_contact.copy()
        
        # Собираем все уникальные значения
        all_emails = set()
        all_phones = set()
        all_names = set()
        all_organizations = set()
        all_positions = set()
        all_cities = set()
        max_confidence = 0
        
        for contact in contacts:
            # Собираем emails
            if contact.get('email'):
                all_emails.add(contact['email'])
            
            # Собираем телефоны
            if contact.get('phone'):
                all_phones.add(contact['phone'])
            
            # Собираем имена
            if contact.get('name'):
                all_names.add(contact['name'])
            
            # Собираем организации
            if contact.get('organization'):
                all_organizations.add(contact['organization'])
            
            # Собираем должности
            if contact.get('position'):
                all_positions.add(contact['position'])
            
            # Собираем города
            if contact.get('city'):
                all_cities.add(contact['city'])
            
            # Максимальный confidence
            contact_conf = contact.get('confidence', 0)
            if contact_conf > max_confidence:
                max_confidence = contact_conf
        
        # Выбираем лучшие значения для каждого поля
        if all_emails:
            merged['email'] = self._select_best_value(list(all_emails), 'email')
            if len(all_emails) > 1:
                merged['other_emails'] = [e for e in all_emails if e != merged['email']]
        
        if all_phones:
            merged['phone'] = self._select_best_value(list(all_phones), 'phone')
            if len(all_phones) > 1:
                merged['other_phones'] = [p for p in all_phones if p != merged['phone']]
        
        if all_names:
            merged['name'] = self._select_best_value(list(all_names), 'name')
        
        if all_organizations:
            merged['organization'] = self._select_best_value(list(all_organizations), 'organization')
        
        if all_positions:
            merged['position'] = self._select_best_value(list(all_positions), 'position')
        
        if all_cities:
            merged['city'] = self._select_best_value(list(all_cities), 'city')
        
        merged['confidence'] = max_confidence
        merged['merged_from_count'] = len(contacts)
        
        return merged
    
    def _calculate_contact_completeness(self, contact: Dict) -> int:
        """📊 Расчет полноты контакта (количество заполненных полей)"""
        fields = ['name', 'email', 'phone', 'organization', 'position', 'city']
        return sum(1 for field in fields if contact.get(field))
    
    def _select_best_value(self, values: List[str], field_type: str) -> str:
        """🎯 Выбор лучшего значения из списка"""
        if not values:
            return ''
        
        if len(values) == 1:
            return values[0]
        
        # Для email выбираем самый короткий (обычно основной)
        if field_type == 'email':
            return min(values, key=len)
        
        # Для телефона выбираем самый длинный (наиболее полный)
        if field_type == 'phone':
            return max(values, key=len)
        
        # Для остальных полей выбираем самое длинное (наиболее информативное)
        return max(values, key=len)
    
    def _normalize_email(self, email: str) -> str:
        """📧 Нормализация email для сравнения"""
        if not email:
            return ''
        return email.lower().strip()
    
    def _normalize_phone(self, phone: str) -> str:
        """📞 Нормализация телефона для сравнения"""
        if not phone:
            return ''
        # Убираем все символы кроме цифр и +
        normalized = re.sub(r'[^\d+]', '', phone)
        # Приводим к единому формату: если начинается с 8, заменяем на +7
        if normalized.startswith('8') and len(normalized) == 11:
            normalized = '+7' + normalized[1:]
        return normalized
    
    def _normalize_name(self, name: str) -> str:
        """👤 Нормализация имени для сравнения"""
        if not name:
            return ''
        # Убираем лишние пробелы и приводим к нижнему регистру
        normalized = ' '.join(name.lower().strip().split())
        # Убираем общие сокращения и титулы
        common_titles = ['г-н', 'г-жа', 'мр', 'мс', 'др', 'проф', 'инж']
        words = normalized.split()
        filtered_words = [w for w in words if w not in common_titles]
        return ' '.join(filtered_words)
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """👤 Улучшенный расчет схожести имен"""
        # Разбиваем имена на части
        parts1 = name1.split()
        parts2 = name2.split()
        
        # Если одно из имен содержит инициалы
        if any(len(part) == 1 or (len(part) == 2 and part.endswith('.')) for part in parts1 + parts2):
            return self._compare_names_with_initials(parts1, parts2)
        
        # Обычное сравнение
        return SequenceMatcher(None, name1, name2).ratio()
    
    def _compare_names_with_initials(self, parts1: List[str], parts2: List[str]) -> float:
        """🔤 Сравнение имен с учетом инициалов"""
        # Нормализуем инициалы
        normalized1 = [self._normalize_name_part(part) for part in parts1]
        normalized2 = [self._normalize_name_part(part) for part in parts2]
        
        matches = 0
        total_parts = max(len(normalized1), len(normalized2))
        
        for i in range(min(len(normalized1), len(normalized2))):
            part1 = normalized1[i]
            part2 = normalized2[i]
            
            # Если одна из частей - инициал
            if len(part1) == 1 or len(part2) == 1:
                if part1[0] == part2[0]:  # Сравниваем первые буквы
                    matches += 1
            else:
                # Обычное сравнение
                if SequenceMatcher(None, part1, part2).ratio() > 0.8:
                    matches += 1
        
        return matches / total_parts if total_parts > 0 else 0.0
    
    def _normalize_name_part(self, part: str) -> str:
        """🔤 Нормализация части имени"""
        # Убираем точки из инициалов
        normalized = part.replace('.', '').lower()
        return normalized
    
    def _calculate_organization_similarity(self, org1: str, org2: str) -> float:
        """🏢 Улучшенный расчет схожести организаций"""
        # Убираем общие сокращения
        org1_clean = self._clean_organization_name(org1)
        org2_clean = self._clean_organization_name(org2)
        
        return SequenceMatcher(None, org1_clean, org2_clean).ratio()
    
    def _clean_organization_name(self, org_name: str) -> str:
        """🏢 Очистка названия организации от сокращений"""
        # Убираем общие сокращения и формы собственности
        common_abbreviations = ['ооо', 'зао', 'оао', 'ип', 'пао', 'ао', 'тоо', 'лтд', 'ltd', 'llc', 'inc']
        words = org_name.lower().split()
        filtered_words = [w for w in words if w not in common_abbreviations]
        return ' '.join(filtered_words)
    
    def _calculate_city_similarity(self, city1: str, city2: str) -> float:
        """🌍 Улучшенный расчет схожести городов"""
        # Словарь сокращений городов
        city_abbreviations = {
            'спб': 'санкт-петербург',
            'питер': 'санкт-петербург',
            'мск': 'москва',
            'екб': 'екатеринбург',
            'нск': 'новосибирск'
        }
        
        # Нормализуем названия городов
        city1_norm = city_abbreviations.get(city1.lower(), city1.lower())
        city2_norm = city_abbreviations.get(city2.lower(), city2.lower())
        
        return SequenceMatcher(None, city1_norm, city2_norm).ratio()
    
    def _clean_forward_chain_duplicates(self, contacts: List[Dict]) -> List[Dict]:
        """📧 Очистка дубликатов из цепочек пересылок"""
        if len(contacts) <= 1:
            return contacts
        
        # Группируем контакты по источнику (если есть информация)
        source_groups = defaultdict(list)
        no_source = []
        
        for contact in contacts:
            source = contact.get('source', '')
            if source:
                source_groups[source].append(contact)
            else:
                no_source.append(contact)
        
        cleaned_contacts = []
        
        # Обрабатываем каждую группу источников
        for source, group_contacts in source_groups.items():
            if len(group_contacts) > 1:
                # Ищем точные дубликаты в рамках одного источника
                unique_in_source = self._remove_exact_duplicates_in_source(group_contacts)
                cleaned_contacts.extend(unique_in_source)
            else:
                cleaned_contacts.extend(group_contacts)
        
        # Добавляем контакты без источника
        cleaned_contacts.extend(no_source)
        
        # Дополнительная очистка: удаляем контакты с идентичными подписями
        signature_cleaned = self._remove_signature_duplicates(cleaned_contacts)
        
        removed_count = len(contacts) - len(signature_cleaned)
        if removed_count > 0:
            print(f"   🧹 Удалено {removed_count} дубликатов из цепочек пересылок")
        
        return signature_cleaned
    
    def _remove_exact_duplicates_in_source(self, contacts: List[Dict]) -> List[Dict]:
        """🔍 Удаление точных дубликатов в рамках одного источника"""
        unique_contacts = []
        seen_signatures = set()
        
        for contact in contacts:
            # Создаем подпись контакта
            signature = self._create_contact_signature(contact)
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_contacts.append(contact)
        
        return unique_contacts
    
    def _remove_signature_duplicates(self, contacts: List[Dict]) -> List[Dict]:
        """✂️ Удаление контактов с идентичными подписями"""
        unique_contacts = []
        seen_signatures = set()
        
        for contact in contacts:
            # Создаем расширенную подпись для межисточникового сравнения
            signature = self._create_extended_contact_signature(contact)
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_contacts.append(contact)
        
        return unique_contacts
    
    def _create_contact_signature(self, contact: Dict) -> str:
        """🔑 Создание подписи контакта для обнаружения дубликатов"""
        email = self._normalize_email(contact.get('email', ''))
        phone = self._normalize_phone(contact.get('phone', ''))
        name = self._normalize_name(contact.get('name', ''))
        
        # Основная подпись: email + телефон + имя
        signature_parts = []
        
        if email:
            signature_parts.append(f"email:{email}")
        if phone and len(phone) > 6:
            signature_parts.append(f"phone:{phone}")
        if name:
            signature_parts.append(f"name:{name}")
        
        return "|".join(signature_parts)
    
    def _create_extended_contact_signature(self, contact: Dict) -> str:
        """🔑 Создание расширенной подписи для межисточникового сравнения"""
        base_signature = self._create_contact_signature(contact)
        
        # Добавляем организацию и должность для более точного сравнения
        org = self._normalize_name(contact.get('organization', ''))
        position = self._normalize_name(contact.get('position', ''))
        
        extended_parts = [base_signature]
        
        if org:
            extended_parts.append(f"org:{org}")
        if position:
            extended_parts.append(f"pos:{position}")
        
        return "|".join(extended_parts)