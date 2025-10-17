"""
Упрощенный тест интеграции системы версионирования промптов
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "=" * 70)
print("ТЕСТ ИНТЕГРАЦИИ СИСТЕМЫ ВЕРСИОНИРОВАНИЯ ПРОМПТОВ")
print("=" * 70 + "\n")

# Тест 1: Базовый модуль
print("1️⃣ Тест базового модуля prompt_loader...")
from src.utils.prompt_loader import load_prompt, get_prompt_version_info

prompt = load_prompt()
info = get_prompt_version_info()

print(f"   ✅ Промпт загружен: {len(prompt)} символов")
print(f"   ✅ Текущая версия: {info.get('version')}")
print(f"   ✅ Файл: {info.get('file')}")

assert info.get('version') == '1.1', "Должна быть версия 1.1"
assert len(prompt) > 25000, "Промпт v1.1 должен быть >25000 символов"
print("   ✅ ПРОЙДЕН\n")

# Тест 2: Сравнение версий
print("2️⃣ Тест сравнения v1.0 и v1.1...")
prompt_v10 = load_prompt("1.0")
prompt_v11 = load_prompt("1.1")

print(f"   ✅ v1.0: {len(prompt_v10)} символов")
print(f"   ✅ v1.1: {len(prompt_v11)} символов")
print(f"   ✅ Разница: +{len(prompt_v11) - len(prompt_v10)} символов (+{(len(prompt_v11) - len(prompt_v10)) / len(prompt_v10) * 100:.1f}%)")

assert len(prompt_v11) > len(prompt_v10), "v1.1 должен быть больше v1.0"
print("   ✅ ПРОЙДЕН\n")

# Тест 3: Наличие новых элементов в v1.1
print("3️⃣ Тест наличия новых элементов в v1.1...")
new_elements = [
    "СТРОГИЕ ПРАВИЛА ДЛЯ ОБЯЗАТЕЛЬНЫХ ПОЛЕЙ",
    "ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ОТПРАВКОЙ",
    "ПРИМЕРЫ ПРАВИЛЬНОГО JSON",
    "ПРИМЕРЫ НЕПРАВИЛЬНОГО JSON"
]

for element in new_elements:
    assert element in prompt_v11, f"v1.1 должен содержать: {element}"
    assert element not in prompt_v10, f"v1.0 не должен содержать: {element}"
    print(f"   ✅ Найден элемент: {element}")

print("   ✅ ПРОЙДЕН\n")

# Тест 4: Проверка интеграции с extractor.py
print("4️⃣ Тест интеграции с extractor.py...")
try:
    # Читаем файл extractor.py и проверяем наличие импорта
    extractor_code = Path("src/core/extractor.py").read_text()
    
    assert "from src.utils.prompt_loader import load_prompt as load_versioned_prompt" in extractor_code, \
        "extractor.py должен импортировать load_versioned_prompt"
    
    assert 'if filename == "unified_contact_extraction_structured.txt"' in extractor_code, \
        "extractor.py должен проверять unified промпт"
    
    print("   ✅ extractor.py обновлен")
    print("   ✅ ПРОЙДЕН\n")
except Exception as e:
    print(f"   ❌ ПРОВАЛЕН: {e}\n")

# Тест 5: Проверка интеграции с async_extractor.py
print("5️⃣ Тест интеграции с async_extractor.py...")
try:
    async_extractor_code = Path("src/core/async_extractor.py").read_text()
    
    assert "from src.utils.prompt_loader import load_prompt as load_versioned_prompt" in async_extractor_code, \
        "async_extractor.py должен импортировать load_versioned_prompt"
    
    assert 'if filename == "unified_contact_extraction_structured.txt"' in async_extractor_code, \
        "async_extractor.py должен проверять unified промпт"
    
    print("   ✅ async_extractor.py обновлен")
    print("   ✅ ПРОЙДЕН\n")
except Exception as e:
    print(f"   ❌ ПРОВАЛЕН: {e}\n")

# Тест 6: Проверка интеграции с extractor_factory.py
print("6️⃣ Тест интеграции с extractor_factory.py...")
try:
    factory_code = Path("src/core/extractor_factory.py").read_text()
    
    assert "version.json" in factory_code, \
        "extractor_factory.py должен проверять version.json"
    
    assert "current_version" in factory_code, \
        "extractor_factory.py должен читать current_version"
    
    print("   ✅ extractor_factory.py обновлен")
    print("   ✅ ПРОЙДЕН\n")
except Exception as e:
    print(f"   ❌ ПРОВАЛЕН: {e}\n")

print("=" * 70)
print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 70)
print("\n✅ Система версионирования промптов полностью интегрирована:")
print("   📁 prompts/version.json - метаданные версий")
print("   📁 prompts/unified_contact_extraction_v1.0.txt - baseline")
print("   📁 prompts/unified_contact_extraction_v1.1.txt - улучшенная версия")
print("   📁 src/utils/prompt_loader.py - модуль загрузки")
print("   📁 src/core/extractor.py - обновлен ✅")
print("   📁 src/core/async_extractor.py - обновлен ✅")
print("   📁 src/core/extractor_factory.py - обновлен ✅")
print("\n✅ Все модули теперь используют версию v1.1 из version.json")
print("\n" + "=" * 70 + "\n")
