#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки исправленной системы с Replicate API
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_replicate_api_integration():
    """Тест интеграции с Replicate API после исправлений"""
    print("\n🔧 Тестирование исправленной системы с Replicate API...")
    
    try:
        # Импорт основных компонентов
        from src.api_pipeline_validator import APIPipelineValidator
        from src.core.extractor_factory import ExtractorFactory
        from src.config.config_manager import UnifiedConfigManager
        
        print("✅ Импорты успешны")
        
        # Создание валидатора
        validator = APIPipelineValidator(test_mode=True)
        print("✅ APIPipelineValidator создан")
        
        # Инициализация компонентов
        if not validator.validate_setup():
            print("❌ Ошибка инициализации валидатора")
            return False
        print("✅ Валидатор инициализирован")
        
        # Проверка что processor имеет метод get_stats
        print(f"🔍 Тип validator.processor: {type(validator.processor)}")
        print(f"🔍 Атрибуты processor: {[attr for attr in dir(validator.processor) if not attr.startswith('_')]}")
        
        if hasattr(validator.processor, 'get_stats'):
            stats = validator.processor.get_stats()
            print(f"✅ Метод get_stats работает: {type(stats)}")
        else:
            print("❌ Метод get_stats отсутствует")
            return False
            
        # Проверка создания экстрактора через фабрику
        extractor = ExtractorFactory.create_extractor()
        print(f"✅ Экстрактор создан: {type(extractor)}")
        
        # Проверка что у экстрактора есть get_stats
        if hasattr(extractor, 'get_stats'):
            extractor_stats = extractor.get_stats()
            print(f"✅ Экстрактор имеет get_stats: {type(extractor_stats)}")
        else:
            print("❌ У экстрактора нет get_stats")
            return False
            
        # Проверка UnifiedConfigManager
        config_manager = UnifiedConfigManager()
        if hasattr(config_manager, 'get_stats'):
            config_stats = config_manager.get_stats()
            print(f"✅ UnifiedConfigManager имеет get_stats: {len(config_stats)} ключей")
        else:
            print("❌ У UnifiedConfigManager нет get_stats")
            return False
            
        print("\n🎉 Все проверки пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_replicate_api_integration()
    sys.exit(0 if success else 1)