"""Утилиты для работы с файлами.

Модуль содержит функции для нормализации имен файлов,
обеспечивая единообразие обработки во всех компонентах системы.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_filename(
    filename: str,
    remove_extension: bool = True,
    to_lowercase: bool = True,
    preserve_structure: bool = True
) -> str:
    """
    Единая функция нормализации имен файлов.
    
    Объединяет все лучшие практики из различных модулей системы
    для обеспечения консистентного сопоставления файлов.
    
    Args:
        filename: Исходное имя файла
        remove_extension: Удалять ли расширение файла
        to_lowercase: Приводить ли к нижнему регистру
        preserve_structure: Сохранять ли структуру (заменять спецсимволы на _)
    
    Returns:
        Нормализованное имя файла
    """
    if not filename:
        return ""
    
    original_filename = filename
    result = filename
    
    # Удаляем расширение если требуется
    if remove_extension:
        result = re.sub(r'\.[^.]*$', '', result)
    
    # === СПЕЦИФИЧЕСКИЕ ПРЕФИКСЫ ДЛЯ EMAIL ВЛОЖЕНИЙ ===
    # Удаляем префиксы email вложений в формате: YYYYMMDD_domain_ru_hash_HHMMSS_attach_
    # Примеры: 20250820_bk_ru_cd5b3f75_153636_attach_, 20250825_dna-technology_ru_eb76aa48_194637_attach_
    result = re.sub(r'^\d{8}_[a-zA-Z0-9\-\.]+_ru_[a-fA-F0-9]+_\d{6}_attach_', '', result)
    result = re.sub(r'^\d{8}_[a-zA-Z0-9\-\.]+_ru_[a-fA-F0-9]+_\d{6}_inline_', '', result)
    
    # Более общие паттерны для разных доменов
    result = re.sub(r'^\d{8}_[a-zA-Z0-9\-\.]+_[a-fA-F0-9]+_\d{6}_(attach|inline)_', '', result)
    
    # Удаляем префиксы email_X_ (используется в некоторых случаях)
    result = re.sub(r'^email_\d+_', '', result)
    
    # === СТАНДАРТНЫЕ ВРЕМЕННЫЕ МЕТКИ ===
    # Удаляем временные метки в начале (формат: YYYYMMDD_HHMMSS_)
    result = re.sub(r'^\d{8}_\d{6}_', '', result)
    
    # Удаляем префиксы с временными метками (формат: YYYY-MM-DD_HH-MM-SS_)
    result = re.sub(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_', '', result)
    
    # === УДАЛЕНИЕ СУФФИКСОВ OCR МЕТОДОВ ===
    # Удаляем суффиксы методов OCR (для OCR результатов): ___method_name
    result = re.sub(r'___[a-zA-Z0-9_]+$', '', result)
    
    # Удаляем суффиксы методов обработки
    result = re.sub(r'_(ocr|llm|manual|auto)$', '', result)
    
    # Удаляем старые форматы временных меток в конце
    result = re.sub(r'_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$', '', result)
    result = re.sub(r'_\d{8}_\d{6}$', '', result)
    
    # Удаляем суффиксы копий и дубликатов
    result = re.sub(r'\s*\(\d+\)$', '', result)  # (1), (2), etc.
    result = re.sub(r'_(copy|duplicate|копия)\d*$', '', result, flags=re.IGNORECASE)
    
    # Нормализация спецсимволов
    if preserve_structure:
        # Заменяем спецсимволы на подчеркивания для сохранения структуры
        result = re.sub(r'[^\w\s-]', '_', result)
        # Заменяем пробелы на подчеркивания
        result = re.sub(r'\s+', '_', result)
        # Заменяем дефисы на подчеркивания для единообразия
        result = re.sub(r'-+', '_', result)
    else:
        # Полностью удаляем спецсимволы
        result = re.sub(r'[^\w\s]', '', result)
        result = re.sub(r'\s+', '_', result)
    
    # Обрабатываем множественные подчеркивания
    result = re.sub(r'_+', '_', result)
    
    # Убираем подчеркивания в начале и конце
    result = result.strip('_')
    
    # Приводим к нижнему регистру если требуется
    if to_lowercase:
        result = result.lower()
    
    # Логируем изменения для отладки
    if result != original_filename:
        logger.debug(f"Нормализация файла: '{original_filename}' -> '{result}'")
    
    return result


def get_normalized_filename_variants(filename: str) -> list[str]:
    """
    Получить различные варианты нормализации для улучшения сопоставления.
    
    Args:
        filename: Исходное имя файла
    
    Returns:
        Список вариантов нормализованных имен
    """
    variants = []
    
    # Основной вариант
    variants.append(normalize_filename(filename))
    
    # Вариант с сохранением регистра
    variants.append(normalize_filename(filename, to_lowercase=False))
    
    # Вариант без сохранения структуры
    variants.append(normalize_filename(filename, preserve_structure=False))
    
    # Вариант с расширением
    variants.append(normalize_filename(filename, remove_extension=False))
    
    # Удаляем дубликаты, сохраняя порядок
    seen = set()
    unique_variants = []
    for variant in variants:
        if variant and variant not in seen:
            seen.add(variant)
            unique_variants.append(variant)
    
    return unique_variants


def find_best_filename_match(target: str, candidates: list[str]) -> Optional[str]:
    """
    Найти лучшее совпадение имени файла среди кандидатов.
    
    Args:
        target: Целевое имя файла
        candidates: Список кандидатов для сопоставления
    
    Returns:
        Лучший кандидат или None если совпадений нет
    """
    if not target or not candidates:
        return None
    
    target_variants = get_normalized_filename_variants(target)
    
    # Проверяем точные совпадения
    for target_variant in target_variants:
        for candidate in candidates:
            candidate_variants = get_normalized_filename_variants(candidate)
            if target_variant in candidate_variants:
                logger.debug(f"Найдено точное совпадение: '{target}' -> '{candidate}'")
                return candidate
    
    # Если точных совпадений нет, ищем частичные
    for target_variant in target_variants:
        for candidate in candidates:
            candidate_variants = get_normalized_filename_variants(candidate)
            for candidate_variant in candidate_variants:
                if target_variant in candidate_variant or candidate_variant in target_variant:
                    logger.debug(f"Найдено частичное совпадение: '{target}' -> '{candidate}'")
                    return candidate
    
    return None