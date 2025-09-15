#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📞 Модуль нормализации телефонов для CONTACT_PARSER
Интегрировано из phone_extractor.py для Фазы 3 мастер-плана
"""

import re
from typing import List, Dict, Optional, Tuple
import phonenumbers

class PhoneNormalizer:
    """🔧 Нормализатор телефонных номеров на основе phone_extractor.py"""

    def __init__(self):
        """Инициализация нормализатора"""

        # Мобильные коды России
        self.mobile_codes = set([
            '910', '912', '913', '914', '915', '916', '917', '918', '919',
            '920', '921', '922', '923', '924', '925', '926', '927', '928', '929',
            '930', '931', '932', '933', '934', '936', '937', '938', '939',
            '950', '951', '952', '953', '954', '955', '956', '957', '958', '959',
            '960', '961', '962', '963', '964', '965', '966', '967', '968', '969',
            '980', '981', '982', '983', '984', '985', '986', '987', '988', '989', '999'
        ])

        print("✅ PhoneNormalizer инициализирован")

    def normalize_contact_phone(self, phone: str) -> Dict[str, str]:
        """
        🔄 Полная нормализация телефона для контакта
        Возвращает словарь с различными вариантами нормализации

        Args:
            phone: Исходная строка телефона из LLM

        Returns:
            dict: {
                'raw_phone': 'оригинал',
                'normalized_phone': 'только цифры для сравнения',
                'formatted_phone': 'форматированный для отображения',
                'phone_type': 'тип номера',
                'phone_extension': 'добавочный номер',
                'confidence': 'уверенность в корректности'
            }
        """

        if not phone or not isinstance(phone, str):
            return {
                'raw_phone': phone or '',
                'normalized_phone': '',
                'formatted_phone': '',
                'phone_type': 'неизвестно',
                'phone_extension': '',
                'confidence': 0.0
            }

        # Сохраняем оригинал
        raw_phone = phone.strip()

        # Извлекаем добавочный номер
        phone_clean, extension = self._extract_extension(raw_phone)

        # Нормализуем основной номер
        normalized, formatted, phone_type = self._normalize_phone_number(phone_clean)

        # Определяем уверенность
        confidence = self._calculate_phone_confidence(raw_phone, normalized)

        return {
            'raw_phone': raw_phone,
            'normalized_phone': normalized,
            'formatted_phone': formatted,
            'phone_type': phone_type,
            'phone_extension': extension,
            'confidence': confidence
        }

    def _extract_extension(self, phone: str) -> Tuple[str, str]:
        """
        📞 Извлечение добавочного номера
        Возвращает (основной_номер, добавочный)
        """

        extension_patterns = [
            r'доб\.?\s*(\d{1,5})',
            r'доп\.?\s*(\d{1,5})',
            r'добавочный\s+(\d{1,5})',
            r'ext\.?\s*(\d{1,5})',
            r'вн\.?\s*(\d{1,5})',
            r'в\.?\s*н\.?\s*(\d{1,5})'
        ]

        phone_clean = phone
        extension = ''

        for pattern in extension_patterns:
            match = re.search(pattern, phone, re.IGNORECASE)
            if match:
                extension = match.group(1)
                # Убираем добавочный из основного номера
                phone_clean = re.sub(pattern, '', phone, flags=re.IGNORECASE).strip()
                # Убираем лишние пробелы и запятые после удаления
                phone_clean = re.sub(r'[,\s]+$', '', phone_clean)
                break

        return phone_clean, extension

    def _normalize_phone_number(self, phone: str) -> Tuple[str, str, str]:
        """
        🔢 Нормализация основного номера телефона
        Возвращает (normalized_digits, formatted_display, phone_type)
        """

        if not phone:
            return '', '', 'неизвестно'

        try:
            # Сначала пробуем распарсить через phonenumbers
            parsed = phonenumbers.parse(phone, "RU")

            if phonenumbers.is_valid_number(parsed):
                # Получаем только цифры для сравнения
                normalized = ''.join(filter(str.isdigit, phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)))

                # Форматируем для отображения
                formatted = self._format_phone_russian(parsed)

                # Определяем тип
                phone_type = self._detect_phone_type(normalized)

                return normalized, formatted, phone_type

        except phonenumbers.NumberParseException:
            # Если phonenumbers не справился, используем fallback
            pass

        # Fallback: ручная обработка
        digits_only = ''.join(filter(str.isdigit, phone))

        if len(digits_only) < 7:
            return digits_only, phone, 'короткий'

        # Для российских номеров
        if digits_only.startswith('8') and len(digits_only) == 11:
            normalized = '7' + digits_only[1:]
        elif digits_only.startswith('7') and len(digits_only) == 11:
            normalized = digits_only
        elif len(digits_only) == 10:
            normalized = '7' + digits_only
        else:
            normalized = digits_only

        formatted = self._format_digits_to_russian(normalized)
        phone_type = self._detect_phone_type(normalized)

        return normalized, formatted, phone_type

    def _format_phone_russian(self, phone_number) -> str:
        """🇷🇺 Форматирование в русский стиль: +7 (XXX) XXX-XX-XX"""

        international = phonenumbers.format_number(
            phone_number,
            phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )

        if international.startswith('+7 '):
            digits = re.sub(r'\D', '', international[3:])
            if len(digits) >= 10:
                code = digits[:3]
                num = digits[3:]
                if len(num) >= 7:
                    return f'+7 ({code}) {num[:3]}-{num[3:5]}-{num[5:7]}'

        return international

    def _format_digits_to_russian(self, digits: str) -> str:
        """📞 Форматирование цифр в русский формат"""

        if len(digits) == 11 and digits.startswith('7'):
            code = digits[1:4]
            num = digits[4:]
            if len(num) >= 7:
                return f'+7 ({code}) {num[:3]}-{num[3:5]}-{num[5:7]}'
        elif len(digits) == 10:
            code = digits[:3]
            num = digits[3:]
            if len(num) >= 7:
                return f'+7 ({code}) {num[:3]}-{num[3:5]}-{num[5:7]}'

        return digits

    def _detect_phone_type(self, normalized_digits: str) -> str:
        """🔍 Определение типа телефона"""

        if len(normalized_digits) < 7:
            return 'короткий'

        if len(normalized_digits) == 11 and normalized_digits.startswith('7'):
            code = normalized_digits[1:4]
            if code in self.mobile_codes:
                return 'мобильный'
            elif code.startswith('8'):  # Код города
                return 'городской'
            else:
                return 'неизвестный'

        return 'неизвестно'

    def _calculate_phone_confidence(self, original: str, normalized: str) -> float:
        """
        📊 Расчет уверенности в корректности нормализации
        """

        if not original or not normalized:
            return 0.0

        # Базовая уверенность
        confidence = 0.5

        # Проверяем наличие кода страны
        if normalized.startswith('7') and len(normalized) == 11:
            confidence += 0.2

        # Проверяем корректный формат
        if re.match(r'^\+7\s*\(\d{3}\)\s*\d{3}[-\s]*\d{2}[-\s]*\d{2}', original):
            confidence += 0.2

        # Проверяем наличие добавочного
        if re.search(r'доб\.?\s*\d+', original, re.IGNORECASE):
            confidence += 0.1

        # Проверяем на наличие лишних символов
        clean_digits = ''.join(filter(str.isdigit, original))
        if len(clean_digits) == len(normalized):
            confidence += 0.1

        return min(confidence, 1.0)

    def normalize_contact_list(self, contacts: List[Dict]) -> List[Dict]:
        """
        🔄 Нормализация телефонов для списка контактов
        Обновляет контакты на месте
        """

        for contact in contacts:
            if 'phone' in contact and contact['phone']:
                normalized_data = self.normalize_contact_phone(contact['phone'])

                # Добавляем нормализованные данные к контакту
                contact.update({
                    'raw_phone': normalized_data['raw_phone'],
                    'normalized_phone': normalized_data['normalized_phone'],
                    'formatted_phone': normalized_data['formatted_phone'],
                    'phone_type': normalized_data['phone_type'],
                    'phone_extension': normalized_data['phone_extension'],
                    'phone_confidence': normalized_data['confidence']
                })

        return contacts

    def get_phone_stats(self, contacts: List[Dict]) -> Dict:
        """📊 Статистика по телефонам в контактах"""

        stats = {
            'total_contacts': len(contacts),
            'with_phones': 0,
            'phone_types': {},
            'extensions': 0,
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }

        for contact in contacts:
            if contact.get('phone'):
                stats['with_phones'] += 1

                phone_type = contact.get('phone_type', 'неизвестно')
                stats['phone_types'][phone_type] = stats['phone_types'].get(phone_type, 0) + 1

                if contact.get('phone_extension'):
                    stats['extensions'] += 1

                confidence = contact.get('phone_confidence', 0.0)
                if confidence >= 0.8:
                    stats['confidence_distribution']['high'] += 1
                elif confidence >= 0.5:
                    stats['confidence_distribution']['medium'] += 1
                else:
                    stats['confidence_distribution']['low'] += 1

        return stats

# Глобальная функция для обратной совместимости
_normalizer_instance = None

def normalize_phone(phone: str) -> Dict[str, str]:
    """🔄 Глобальная функция нормализации телефона для обратной совместимости"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = PhoneNormalizer()
    return _normalizer_instance.normalize_contact_phone(phone)
