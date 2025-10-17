"""
Тест интеграции системы версионирования промптов

Проверяет, что все модули корректно загружают версионированные промпты.
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

def test_prompt_loader():
    """Тест базового модуля загрузки промптов"""
    print("=" * 60)
    print("ТЕСТ 1: Базовый модуль загрузки промптов")
    print("=" * 60)
    
    from src.utils.prompt_loader import load_prompt, get_prompt_version_info
    
    # Загрузка текущей версии
    prompt = load_prompt()
    print(f"✅ Промпт загружен, длина: {len(prompt)} символов")
    
    # Получение информации о версии
    info = get_prompt_version_info()
    print(f"✅ Текущая версия: {info.get('version')}")
    print(f"✅ Описание: {info.get('description')}")
    print(f"✅ Файл: {info.get('file')}")
    
    # Проверка, что это v1.1
    assert info.get('version') == '1.1', "Должна быть версия 1.1"
    assert 'v1.1' in info.get('file', ''), "Файл должен быть v1.1"
    
    print("✅ Тест базового модуля пройден!\n")
    return True


def test_extractor_load_prompt():
    """Тест загрузки промпта через ContactExtractor"""
    print("=" * 60)
    print("ТЕСТ 2: ContactExtractor.load_prompt()")
    print("=" * 60)
    
    from src.core.extractor import ContactExtractor
    from config.settings import Config
    
    config = Config()
    extractor = ContactExtractor(config)
    
    # Загрузка unified промпта
    prompt = extractor.load_prompt("unified_contact_extraction_structured.txt")
    print(f"✅ Промпт загружен через ContactExtractor, длина: {len(prompt)} символов")
    
    # Проверка, что это v1.1 (должен быть больше 25000 символов)
    assert len(prompt) > 25000, "Промпт должен быть v1.1 (>25000 символов)"
    
    # Проверка наличия новых правил из v1.1
    assert "СТРОГИЕ ПРАВИЛА ДЛЯ ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ" in prompt, "Должны быть строгие правила из v1.1"
    assert "ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ОТПРАВКОЙ" in prompt, "Должна быть финальная проверка из v1.1"
    
    print("✅ Тест ContactExtractor пройден!\n")
    return True


def test_async_extractor_load_prompt():
    """Тест загрузки промпта через AsyncContactExtractor"""
    print("=" * 60)
    print("ТЕСТ 3: AsyncContactExtractor.load_prompt()")
    print("=" * 60)
    
    from src.core.async_extractor import AsyncContactExtractor
    from config.settings import Config
    
    config = Config()
    extractor = AsyncContactExtractor(config)
    
    # Загрузка unified промпта (синхронный метод)
    prompt = extractor.load_prompt("unified_contact_extraction_structured.txt")
    print(f"✅ Промпт загружен через AsyncContactExtractor, длина: {len(prompt)} символов")
    
    # Проверка, что это v1.1
    assert len(prompt) > 25000, "Промпт должен быть v1.1 (>25000 символов)"
    assert "СТРОГИЕ ПРАВИЛА ДЛЯ ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ" in prompt, "Должны быть строгие правила из v1.1"
    
    print("✅ Тест AsyncContactExtractor пройден!\n")
    return True


def test_extractor_factory():
    """Тест проверки промптов через ExtractorFactory"""
    print("=" * 60)
    print("ТЕСТ 4: ExtractorFactory.check_dependencies()")
    print("=" * 60)
    
    from src.core.extractor_factory import ExtractorFactory
    
    issues = ExtractorFactory.check_dependencies()
    
    if issues:
        print("⚠️ Найдены проблемы:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Все зависимости в порядке")
    
    # Проверка, что нет проблем с промптами
    prompt_issues = [i for i in issues if 'промпт' in i.lower() or 'prompt' in i.lower()]
    assert len(prompt_issues) == 0, f"Не должно быть проблем с промптами: {prompt_issues}"
    
    print("✅ Тест ExtractorFactory пройден!\n")
    return True


def test_version_comparison():
    """Тест сравнения v1.0 и v1.1"""
    print("=" * 60)
    print("ТЕСТ 5: Сравнение v1.0 и v1.1")
    print("=" * 60)
    
    from src.utils.prompt_loader import load_prompt
    
    # Загрузка обеих версий
    prompt_v10 = load_prompt("1.0")
    prompt_v11 = load_prompt("1.1")
    
    print(f"✅ v1.0 загружен, длина: {len(prompt_v10)} символов")
    print(f"✅ v1.1 загружен, длина: {len(prompt_v11)} символов")
    
    # Проверка, что v1.1 больше
    assert len(prompt_v11) > len(prompt_v10), "v1.1 должен быть больше v1.0"
    
    # Проверка наличия новых элементов в v1.1
    new_elements = [
        "СТРОГИЕ ПРАВИЛА ДЛЯ ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ",
        "ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ОТПРАВКОЙ",
        "ПРИМЕРЫ ПРАВИЛЬНОГО JSON",
        "ПРИМЕРЫ НЕПРАВИЛЬНОГО JSON"
    ]
    
    for element in new_elements:
        assert element in prompt_v11, f"v1.1 должен содержать: {element}"
        assert element not in prompt_v10, f"v1.0 не должен содержать: {element}"
    
    print(f"✅ v1.1 содержит все новые элементы")
    print(f"✅ Разница в размере: +{len(prompt_v11) - len(prompt_v10)} символов (+{(len(prompt_v11) - len(prompt_v10)) / len(prompt_v10) * 100:.1f}%)")
    print("✅ Тест сравнения версий пройден!\n")
    return True


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ СИСТЕМЫ ВЕРСИОНИРОВАНИЯ ПРОМПТОВ")
    print("=" * 60 + "\n")
    
    tests = [
        ("Базовый модуль загрузки", test_prompt_loader),
        ("ContactExtractor", test_extractor_load_prompt),
        ("AsyncContactExtractor", test_async_extractor_load_prompt),
        ("ExtractorFactory", test_extractor_factory),
        ("Сравнение версий", test_version_comparison),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Тест '{test_name}' провален: {e}\n")
            failed += 1
    
    print("=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"✅ Пройдено: {passed}/{len(tests)}")
    print(f"❌ Провалено: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\n✅ Система версионирования промптов полностью интегрирована:")
        print("   - src/utils/prompt_loader.py - базовый модуль")
        print("   - src/core/extractor.py - обновлен")
        print("   - src/core/async_extractor.py - обновлен")
        print("   - src/core/extractor_factory.py - обновлен")
        print("\n✅ Все модули теперь используют версию v1.1 из version.json")
        return 0
    else:
        print(f"\n❌ Некоторые тесты провалены. Требуется исправление.")
        return 1


if __name__ == "__main__":
    exit(main())
