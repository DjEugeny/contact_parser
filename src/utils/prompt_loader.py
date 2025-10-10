"""
Модуль для загрузки версионированных промптов

Поддерживает:
- Загрузку текущей версии промпта
- Загрузку конкретной версии для A/B тестирования
- Fallback на старый файл если версионирование не настроено
- Получение метаданных версий
"""

import json
from pathlib import Path
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def load_prompt(version: Optional[str] = None) -> str:
    """
    Загрузка промпта с поддержкой версионирования
    
    Args:
        version: Версия промпта (например "1.1"). 
                 Если None - загружается current_version из version.json
    
    Returns:
        Текст промпта
    
    Raises:
        ValueError: Если указанная версия не найдена
        FileNotFoundError: Если файл промпта не существует
    
    Examples:
        # Загрузить текущую версию
        prompt = load_prompt()
        
        # Загрузить конкретную версию для A/B теста
        prompt_v10 = load_prompt("1.0")
        prompt_v11 = load_prompt("1.1")
    """
    version_file = Path("prompts/version.json")
    
    # Fallback на старый файл если версионирование не настроено
    if not version_file.exists():
        logger.warning("⚠️ version.json не найден, используется fallback")
        fallback_path = Path("prompts/unified_contact_extraction_structured.txt")
        
        if not fallback_path.exists():
            raise FileNotFoundError(
                f"Fallback промпт не найден: {fallback_path}"
            )
        
        return fallback_path.read_text(encoding='utf-8')
    
    # Загружаем метаданные версий
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            version_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга version.json: {e}")
        raise ValueError(f"Invalid version.json format: {e}")
    
    # Если версия не указана - берем текущую
    if version is None:
        version = version_data.get('current_version')
        if not version:
            raise ValueError("current_version не указан в version.json")
    
    # Проверяем существование версии
    if version not in version_data.get('versions', {}):
        available_versions = list(version_data.get('versions', {}).keys())
        logger.error(
            f"❌ Версия {version} не найдена в version.json. "
            f"Доступные версии: {available_versions}"
        )
        raise ValueError(
            f"Unknown prompt version: {version}. "
            f"Available: {available_versions}"
        )
    
    # Получаем имя файла для версии
    version_info = version_data['versions'][version]
    prompt_file = version_info.get('file')
    
    if not prompt_file:
        raise ValueError(f"Файл не указан для версии {version}")
    
    prompt_path = Path("prompts") / prompt_file
    
    # Проверяем существование файла
    if not prompt_path.exists():
        logger.error(f"❌ Файл промпта не найден: {prompt_path}")
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    logger.info(f"📝 Загружен промпт версии {version}: {prompt_file}")
    
    # Логируем дополнительную информацию о версии
    if 'description' in version_info:
        logger.info(f"   Описание: {version_info['description']}")
    if 'validation_error_rate' in version_info:
        error_rate = version_info['validation_error_rate']
        if error_rate is not None:
            logger.info(
                f"   Validation error rate: "
                f"{error_rate*100:.1f}%"
            )
        else:
            logger.info("   Validation error rate: не измерен (требуется тестирование)")
    
    return prompt_path.read_text(encoding='utf-8')


def get_prompt_version_info(version: Optional[str] = None) -> Dict[str, Any]:
    """
    Получить метаданные версии промпта
    
    Args:
        version: Версия промпта. Если None - возвращается информация о текущей версии
    
    Returns:
        Словарь с метаданными версии
    
    Examples:
        # Получить информацию о текущей версии
        info = get_prompt_version_info()
        print(f"Версия: {info['version']}")
        print(f"Описание: {info['description']}")
        
        # Получить информацию о конкретной версии
        info_v10 = get_prompt_version_info("1.0")
    """
    version_file = Path("prompts/version.json")
    
    if not version_file.exists():
        return {
            "error": "version.json not found",
            "fallback": True
        }
    
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            version_data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "error": f"Invalid version.json format: {e}"
        }
    
    # Если версия не указана - берем текущую
    if version is None:
        version = version_data.get('current_version')
        if not version:
            return {"error": "current_version not specified in version.json"}
    
    version_info = version_data.get('versions', {}).get(version)
    
    if not version_info:
        available_versions = list(version_data.get('versions', {}).keys())
        return {
            "error": f"Version {version} not found",
            "available_versions": available_versions
        }
    
    # Добавляем номер версии в результат
    result = {"version": version}
    result.update(version_info)
    
    return result


def list_available_versions() -> Dict[str, Any]:
    """
    Получить список всех доступных версий промптов
    
    Returns:
        Словарь с информацией о всех версиях
    
    Examples:
        versions = list_available_versions()
        print(f"Текущая версия: {versions['current_version']}")
        for v, info in versions['versions'].items():
            print(f"v{v}: {info['description']}")
    """
    version_file = Path("prompts/version.json")
    
    if not version_file.exists():
        return {
            "error": "version.json not found",
            "fallback": True
        }
    
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return {
            "error": f"Invalid version.json format: {e}"
        }


def update_version_metrics(
    version: str,
    validation_error_rate: Optional[float] = None,
    **kwargs
) -> bool:
    """
    Обновить метрики версии промпта
    
    Args:
        version: Версия промпта для обновления
        validation_error_rate: Процент ошибок валидации (0.0 - 1.0)
        **kwargs: Дополнительные метрики для обновления
    
    Returns:
        True если обновление успешно, False иначе
    
    Examples:
        # Обновить метрики после тестирования
        update_version_metrics(
            "1.1",
            validation_error_rate=0.05,
            tested_on="2025-10-10",
            test_sample_size=30
        )
    """
    version_file = Path("prompts/version.json")
    
    if not version_file.exists():
        logger.error("❌ version.json не найден")
        return False
    
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            version_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга version.json: {e}")
        return False
    
    if version not in version_data.get('versions', {}):
        logger.error(f"❌ Версия {version} не найдена")
        return False
    
    # Обновляем метрики
    if validation_error_rate is not None:
        version_data['versions'][version]['validation_error_rate'] = \
            validation_error_rate
    
    # Добавляем дополнительные метрики
    for key, value in kwargs.items():
        version_data['versions'][version][key] = value
    
    # Сохраняем обновленные данные
    try:
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Метрики версии {version} обновлены")
        return True
    
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения version.json: {e}")
        return False


if __name__ == "__main__":
    # Пример использования
    logging.basicConfig(level=logging.INFO)
    
    print("=== Тест загрузки промпта ===")
    try:
        prompt = load_prompt()
        print(f"✅ Промпт загружен, длина: {len(prompt)} символов")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n=== Информация о версии ===")
    info = get_prompt_version_info()
    if 'error' not in info:
        print(f"Версия: {info.get('version')}")
        print(f"Описание: {info.get('description')}")
        print(f"Файл: {info.get('file')}")
        print(f"Статус: {info.get('status')}")
    else:
        print(f"Ошибка: {info['error']}")
    
    print("\n=== Список версий ===")
    versions = list_available_versions()
    if 'error' not in versions:
        print(f"Текущая версия: {versions.get('current_version')}")
        for v, v_info in versions.get('versions', {}).items():
            print(f"  v{v}: {v_info.get('description')}")
    else:
        print(f"Ошибка: {versions['error']}")
