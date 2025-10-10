#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📞 Модуль нормализации телефонов для CONTACT_PARSER
Интегрировано из phone_extractor.py для Фазы 3 мастер-плана
"""

import re
from typing import List, Dict, Optional, Tuple, Any
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

    def normalize_contact_phone(self, phone: str) -> Dict[str, Any]:
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

        # Сначала разделяем на отдельные номера, если их несколько
        phone_list = self._split_multiple_phones(raw_phone)
        
        # Если найдено несколько номеров, обрабатываем первый
        # (можно расширить для обработки всех)
        phone_to_process = phone_list[0]

        # Извлекаем добавочный номер
        phone_clean, extension = self._extract_extension(phone_to_process)

        # Нормализуем основной номер
        normalized, formatted, phone_type = self._normalize_phone_number(phone_clean)

        # Определяем уверенность
        confidence = self._calculate_phone_confidence(raw_phone, normalized)

        # КРИТИЧЕСКИ ВАЖНО: НЕ добавляем extension к formatted номеру!
        # Extension должен быть только в отдельном поле
        # if extension:
        #     formatted = f"{formatted} (доб. {extension})"

        return {
            'raw_phone': raw_phone,
            'normalized_phone': normalized,
            'formatted_phone': formatted,
            'phone_type': phone_type,
            'phone_extension': extension,
            'confidence': confidence
        }

    def _split_multiple_phones(self, phone: str) -> List[str]:
        """
        📞 Разделение строки с несколькими номерами
        Возвращает список отдельных номеров
        """
        # Паттерны для разделения номеров
        # Ищем случаи типа "+7 (495) 933 71 47 (48)" где (48) - это второй номер
        
        # Сначала проверяем на наличие нескольких номеров в скобках
        phone_stripped = phone.strip()
        base_without_extension, extension = self._extract_extension(phone_stripped)
        match = re.search(r'(.*?)(\((\d{2,})\))\s*$', base_without_extension)

        if match:
            base_without_brackets = match.group(1).rstrip(' ,;')
            additional_digits = match.group(3)
            base_without_brackets = re.sub(r'\s{2,}', ' ', base_without_brackets).strip()

            base_digits = re.sub(r'[^\d]', '', base_without_brackets)
            if len(base_digits) >= len(additional_digits):
                second_phone_digits = base_digits[:-len(additional_digits)] + additional_digits
                if len(second_phone_digits) == 11 and second_phone_digits.startswith('7'):
                    second_phone = f"+{second_phone_digits}"
                elif second_phone_digits.startswith('+'):
                    second_phone = second_phone_digits
                else:
                    second_phone = second_phone_digits

                if extension:
                    second_phone = f"{second_phone}, доб.{extension}"

                primary_phone = base_without_brackets
                if extension:
                    primary_phone = f"{primary_phone}, доб.{extension}"

                return [primary_phone, second_phone]

        # Если не найдено несколько номеров, возвращаем исходный
        return [phone]
    
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

    def normalize_multiple_phones(self, phone: str) -> List[Dict[str, Any]]:
        """
        📞 Нормализация строки с несколькими номерами
        Возвращает список словарей с нормализованными данными для каждого номера
        """
        if not phone or not phone.strip():
            return [{
                'original': phone or '',
                'formatted': '',
                'normalized': '',
                'type': 'пустой',
                'extension': '',
                'confidence': 0.0
            }]
        
        # Разделяем на отдельные номера
        phone_list = self._split_multiple_phones(phone.strip())
        
        results = []
        for individual_phone in phone_list:
            # Извлекаем добавочный номер
            phone_clean, extension = self._extract_extension(individual_phone)
            
            # Нормализуем основной номер
            normalized_digits, formatted_display, phone_type = self._normalize_phone_number(phone_clean)
            
            # Рассчитываем уверенность
            confidence = self._calculate_phone_confidence(individual_phone, normalized_digits)
            
            # КРИТИЧЕСКИ ВАЖНО: НЕ добавляем extension к formatted номеру!
            # Extension должен быть только в отдельном поле
            # if extension:
            #     formatted_display = f"{formatted_display} (доб. {extension})"
            
            results.append({
                'original': individual_phone,
                'formatted': formatted_display,
                'normalized': normalized_digits,
                'type': phone_type,
                'extension': extension,
                'confidence': confidence
            })
        
        return results

    def normalize_phone_to_object(self, phone: str, city_context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        📞 Главная функция нормализации телефона в объект
        Возвращает список объектов с полями: number, normalized, original, type, extension
        
        КРИТИЧЕСКИ ВАЖНО: 
        - number НЕ содержит добавочный номер
        - extension всегда в отдельном поле
        - normalized в формате E.164 БЕЗ добавочного
        
        Args:
            phone: Телефонный номер для нормализации
            city_context: Опциональный контекст города для коротких номеров
        
        Returns:
            List[Dict]: Список нормализованных телефонных объектов
        """
        if not phone or not phone.strip():
            return []
        
        # Разделяем на отдельные номера (поддержка множественных)
        phone_list = self._split_multiple_phones(phone.strip())
        
        results = []
        for individual_phone in phone_list:
            # Извлекаем добавочный номер
            phone_clean, extension = self._extract_extension(individual_phone)
            
            # Проверяем, является ли номер коротким (неполным)
            digits_only = ''.join(filter(str.isdigit, phone_clean))
            
            # Если номер короткий (< 7 цифр) и есть контекст города
            if len(digits_only) < 7 and city_context:
                # Пытаемся обогатить номер кодом города
                enriched_phone = self._enrich_short_phone_with_city(phone_clean, city_context)
                if enriched_phone:
                    phone_clean = enriched_phone
                    digits_only = ''.join(filter(str.isdigit, phone_clean))
            
            # Нормализуем основной номер
            normalized_digits, formatted_display, phone_type = self._normalize_phone_number(phone_clean)
            
            # Рассчитываем уверенность
            confidence = self._calculate_phone_confidence(individual_phone, normalized_digits)
            
            # Для коротких номеров без успешной нормализации
            if len(digits_only) < 7:
                phone_obj = {
                    'type': 'incomplete',
                    'number': individual_phone,
                    'normalized': None,  # Не можем нормализовать
                    'original': individual_phone,
                    'confidence': 0.0,
                    'needs_manual_review': True,
                    'incomplete_reason': f'Неполный номер ({len(digits_only)} цифр, требуется минимум 7)'
                }
                
                if extension:
                    phone_obj['extension'] = extension
                else:
                    phone_obj['extension'] = None
                    
                results.append(phone_obj)
                continue
            
            # Создаем объект телефона согласно целевой структуре
            phone_obj = {
                'type': self._map_phone_type(phone_type),
                'number': formatted_display,  # БЕЗ добавочного!
                'normalized': self._normalize_to_e164(normalized_digits),  # E.164 формат
                'original': individual_phone,
                'confidence': confidence
            }
            
            # Добавляем extension только если он есть
            if extension:
                phone_obj['extension'] = extension
            else:
                phone_obj['extension'] = None
                
            results.append(phone_obj)
        
        return results
    
    def _enrich_short_phone_with_city(self, phone: str, city: str) -> Optional[str]:
        """
        🏙️ Обогащение короткого номера кодом города
        
        Пытается добавить код города к короткому номеру на основе контекста.
        Например: "28-54-83" + "Новосибирск" → "8(383)28-54-83"
        
        Args:
            phone: Короткий телефонный номер
            city: Название города для определения кода
            
        Returns:
            Optional[str]: Обогащенный номер или None если не удалось
        """
        # Словарь кодов городов России (основные города)
        city_codes = {
            'москва': '495',
            'санкт-петербург': '812',
            'спб': '812',
            'новосибирск': '383',
            'екатеринбург': '343',
            'нижний новгород': '831',
            'казань': '843',
            'челябинск': '351',
            'омск': '381',
            'самара': '846',
            'ростов-на-дону': '863',
            'уфа': '347',
            'красноярск': '391',
            'воронеж': '473',
            'пермь': '342',
            'волгоград': '844',
            'краснодар': '861',
            'саратов': '845',
            'тюмень': '345',
            'тольятти': '8482',
            'ижевск': '3412',
            'барнаул': '3852',
            'ульяновск': '8422',
            'иркутск': '3952',
            'хабаровск': '4212',
            'ярославль': '4852',
            'владивосток': '423',
            'махачкала': '8722',
            'томск': '3822',
            'оренбург': '3532',
            'кемерово': '3842',
            'новокузнецк': '3843',
            'рязань': '4912',
            'астрахань': '8512',
            'набережные челны': '8552',
            'пенза': '8412',
            'липецк': '4742',
            'киров': '8332',
            'чебоксары': '8352',
            'калининград': '4012',
            'тула': '4872',
            'курск': '4712',
            'сочи': '8622',
            'ставрополь': '8652',
            'улан-удэ': '3012',
            'тверь': '4822',
            'магнитогорск': '3519',
            'иваново': '4932',
            'брянск': '4832',
            'белгород': '4722',
            'сургут': '3462',
            'владимир': '4922',
            'нижний тагил': '3435',
            'архангельск': '8182',
            'чита': '3022',
            'калуга': '4842',
            'смоленск': '4812',
            'волжский': '8443',
            'курган': '3522',
            'орел': '4862',
            'череповец': '8202',
            'вологда': '8172',
            'владикавказ': '8672',
            'мурманск': '8152',
            'саранск': '8342',
            'тамбов': '4752',
            'стерлитамак': '3473',
            'грозный': '8712',
            'якутск': '4112',
            'кострома': '4942',
            'петрозаводск': '8142',
            'нижневартовск': '3466',
            'новороссийск': '8617',
            'йошкар-ола': '8362',
        }
        
        if not city:
            return None
        
        # Нормализуем название города
        city_normalized = city.lower().strip()
        
        # Ищем код города
        area_code = city_codes.get(city_normalized)
        
        if not area_code:
            # Не нашли код города
            return None
        
        # Извлекаем только цифры из короткого номера
        digits = ''.join(filter(str.isdigit, phone))
        
        # Формируем полный номер: +7 (код_города) номер
        # Важно: добавляем код города ПЕРЕД цифрами номера
        enriched = f"+7{area_code}{digits}"
        
        return enriched
    
    def _normalize_to_e164(self, digits: str) -> str:
        """
        🌍 Нормализация в E.164 формат без добавочного
        """
        if not digits:
            return ''
        
        # Убираем все нецифровые символы
        clean_digits = ''.join(filter(str.isdigit, digits))
        
        if not clean_digits:
            return ''
        
        # Для российских номеров
        if len(clean_digits) == 11 and clean_digits.startswith('7'):
            return f'+{clean_digits}'
        elif len(clean_digits) == 11 and clean_digits.startswith('8'):
            return f'+7{clean_digits[1:]}'
        elif len(clean_digits) == 10:
            return f'+7{clean_digits}'
        elif clean_digits.startswith('7'):
            return f'+{clean_digits}'
        else:
            return f'+{clean_digits}'
    
    def _map_phone_type(self, internal_type: str) -> str:
        """
        🔄 Маппинг внутренних типов на стандартные
        """
        type_mapping = {
            'мобильный': 'mobile',
            'городской': 'office', 
            'неизвестный': 'office',
            'неизвестно': 'main',
            'короткий': 'other'
        }
        return type_mapping.get(internal_type, 'main')

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
