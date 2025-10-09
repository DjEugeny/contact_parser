#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер моделей с автоматическим fallback
Загружает конфигурацию из models_config.yaml
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Конфигурация одной модели"""
    name: str
    priority: int
    description: str
    requires_prompt_publication: bool = False
    provider: str = ""
    context_window: int = 32768  # Default context window
    
    def __repr__(self):
        return f"ModelConfig({self.name}, priority={self.priority}, context={self.context_window})"


class ModelsManager:
    """Менеджер моделей с автоматическим fallback"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация менеджера моделей
        
        Args:
            config_path: Путь к файлу конфигурации (по умолчанию config/models_config.yaml)
        """
        if config_path is None:
            # Ищем config/models_config.yaml относительно корня проекта
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "models_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Модели по провайдерам
        self.openrouter_models: List[ModelConfig] = []
        self.replicate_models: List[ModelConfig] = []
        
        # Текущие индексы моделей
        self.current_openrouter_index = 0
        self.current_replicate_index = 0
        
        # Счетчики ошибок для текущих моделей
        self.openrouter_error_count = 0
        self.replicate_error_count = 0
        
        self._parse_models()
        
        logger.info(f"📋 ModelsManager инициализирован")
        logger.info(f"   OpenRouter: {len(self.openrouter_models)} моделей")
        logger.info(f"   Replicate: {len(self.replicate_models)} моделей")
    
    def _load_config(self) -> dict:
        """Загрузка конфигурации из YAML"""
        if not self.config_path.exists():
            logger.warning(f"⚠️ Конфиг не найден: {self.config_path}")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Конфигурация загружена: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфига: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Конфигурация по умолчанию"""
        return {
            'openrouter': {
                'models': [
                    {
                        'name': 'qwen/qwen3-235b-a22b:free',
                        'priority': 1,
                        'description': 'Qwen 235B',
                        'requires_prompt_publication': False
                    }
                ]
            },
            'replicate': {
                'models': [
                    {
                        'name': 'deepseek-ai/deepseek-v3.1',
                        'priority': 1,
                        'description': 'DeepSeek v3.1'
                    }
                ]
            },
            'fallback': {
                'enabled': True,
                'max_retries_per_model': 3
            }
        }
    
    def _parse_models(self):
        """Парсинг моделей из конфигурации"""
        # OpenRouter модели
        openrouter_config = self.config.get('openrouter', {})
        for model_data in openrouter_config.get('models', []):
            model = ModelConfig(
                name=model_data['name'],
                priority=model_data.get('priority', 999),
                description=model_data.get('description', ''),
                requires_prompt_publication=model_data.get('requires_prompt_publication', False),
                provider='openrouter',
                context_window=model_data.get('context_window', 32768)
            )
            self.openrouter_models.append(model)
        
        # Сортируем по приоритету
        self.openrouter_models.sort(key=lambda x: x.priority)
        
        # Replicate модели
        replicate_config = self.config.get('replicate', {})
        for model_data in replicate_config.get('models', []):
            model = ModelConfig(
                name=model_data['name'],
                priority=model_data.get('priority', 999),
                description=model_data.get('description', ''),
                provider='replicate',
                context_window=model_data.get('context_window', 32768)
            )
            self.replicate_models.append(model)
        
        # Сортируем по приоритету
        self.replicate_models.sort(key=lambda x: x.priority)
    
    def estimate_tokens(self, text: str, encoding_name: str = "cl100k_base") -> int:
        """
        Оценить количество токенов в тексте
        
        Args:
            text: Текст для оценки
            encoding_name: Название кодировки tiktoken (по умолчанию cl100k_base для GPT-4)
            
        Returns:
            Примерное количество токенов
        """
        try:
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"⚠️ Ошибка оценки токенов через tiktoken: {e}, используем примерную оценку")
            # Fallback: примерная оценка (1 токен ≈ 4 символа для английского, 2-3 для русского)
            return len(text) // 3
    
    def validate_context_length(self, model: ModelConfig, text: str, max_output_tokens: int = 4000) -> bool:
        """
        Проверить, помещается ли текст в context window модели
        
        Args:
            model: Конфигурация модели
            text: Входной текст
            max_output_tokens: Максимальное количество токенов для ответа
            
        Returns:
            True если текст помещается, False если нет
        """
        estimated_tokens = self.estimate_tokens(text)
        total_tokens_needed = estimated_tokens + max_output_tokens
        
        fits = total_tokens_needed <= model.context_window
        
        if not fits:
            logger.warning(
                f"⚠️ Модель {model.name} пропущена: "
                f"требуется ~{total_tokens_needed} токенов "
                f"(input: {estimated_tokens} + output: {max_output_tokens}), "
                f"доступно: {model.context_window}"
            )
        
        return fits
    
    def get_current_model(self, provider: str, estimated_tokens: Optional[int] = None) -> Optional[ModelConfig]:
        """
        Получить текущую модель для провайдера с учетом context length
        
        Args:
            provider: 'openrouter' или 'replicate'
            estimated_tokens: Примерное количество токенов (input + output), если нужна валидация
            
        Returns:
            ModelConfig или None
        """
        if provider.lower() == 'openrouter':
            # Если указаны estimated_tokens, ищем первую подходящую модель
            if estimated_tokens is not None:
                for i in range(self.current_openrouter_index, len(self.openrouter_models)):
                    model = self.openrouter_models[i]
                    if estimated_tokens <= model.context_window:
                        if i != self.current_openrouter_index:
                            logger.info(
                                f"🔄 ModelsManager: пропущено {i - self.current_openrouter_index} моделей "
                                f"из-за недостаточного context window"
                            )
                            self.current_openrouter_index = i
                        logger.info(
                            f"🎯 ModelsManager: OpenRouter использует модель {model.name} "
                            f"(priority {model.priority}, context: {model.context_window})"
                        )
                        return model
                
                logger.error(
                    f"❌ Ни одна модель OpenRouter не имеет достаточного context window "
                    f"для {estimated_tokens} токенов"
                )
                return None
            
            # Без валидации - возвращаем текущую модель
            if self.current_openrouter_index < len(self.openrouter_models):
                model = self.openrouter_models[self.current_openrouter_index]
                logger.info(f"🎯 ModelsManager: OpenRouter использует модель {model.name} (priority {model.priority})")
                return model
                
        elif provider.lower() == 'replicate':
            # Если указаны estimated_tokens, ищем первую подходящую модель
            if estimated_tokens is not None:
                for i in range(self.current_replicate_index, len(self.replicate_models)):
                    model = self.replicate_models[i]
                    if estimated_tokens <= model.context_window:
                        if i != self.current_replicate_index:
                            logger.info(
                                f"🔄 ModelsManager: пропущено {i - self.current_replicate_index} моделей "
                                f"из-за недостаточного context window"
                            )
                            self.current_replicate_index = i
                        logger.info(
                            f"🎯 ModelsManager: Replicate использует модель {model.name} "
                            f"(priority {model.priority}, context: {model.context_window})"
                        )
                        return model
                
                logger.error(
                    f"❌ Ни одна модель Replicate не имеет достаточного context window "
                    f"для {estimated_tokens} токенов"
                )
                return None
            
            # Без валидации - возвращаем текущую модель
            if self.current_replicate_index < len(self.replicate_models):
                model = self.replicate_models[self.current_replicate_index]
                logger.info(f"🎯 ModelsManager: Replicate использует модель {model.name} (priority {model.priority})")
                return model
        
        return None
    
    def get_all_models(self, provider: str) -> List[ModelConfig]:
        """Получить все модели для провайдера"""
        if provider.lower() == 'openrouter':
            return self.openrouter_models.copy()
        elif provider.lower() == 'replicate':
            return self.replicate_models.copy()
        return []
    
    def report_error(self, provider: str, error_message: str) -> bool:
        """
        Сообщить об ошибке модели
        
        Args:
            provider: Провайдер
            error_message: Сообщение об ошибке
            
        Returns:
            True если произошло переключение на следующую модель
        """
        fallback_config = self.config.get('fallback', {})
        max_retries = fallback_config.get('max_retries_per_model', 3)
        switch_on_errors = fallback_config.get('switch_on_errors', [])
        
        # Классифицируем ошибку
        error_lower = error_message.lower()
        is_rate_limit = '429' in error_message or 'rate limit' in error_lower or 'rate_limit' in error_lower
        is_model_error = any(pattern.lower() in error_lower for pattern in [
            'data policy', 'empty response', 'context length', 'model not found',
            'invalid model', 'model error'
        ])
        
        # Логируем тип ошибки
        if is_rate_limit:
            logger.warning(f"⏳ Rate limit для модели в {provider}: {error_message}")
        elif is_model_error:
            logger.warning(f"⚠️ Ошибка модели в {provider}: {error_message}")
        else:
            logger.error(f"❌ Критическая ошибка провайдера {provider}: {error_message}")
        
        # Проверяем, нужно ли переключаться
        should_switch = False
        
        # Всегда переключаемся при rate limit или ошибках модели
        if is_rate_limit or is_model_error:
            should_switch = True
        else:
            # Для других ошибок проверяем конфигурацию
            for error_pattern in switch_on_errors:
                if error_pattern.lower() in error_lower:
                    should_switch = True
                    break
        
        if not should_switch:
            return False
        
        # Увеличиваем счетчик ошибок
        if provider.lower() == 'openrouter':
            self.openrouter_error_count += 1
            
            if self.openrouter_error_count >= max_retries:
                return self._switch_to_next_model('openrouter')
        
        elif provider.lower() == 'replicate':
            self.replicate_error_count += 1
            
            if self.replicate_error_count >= max_retries:
                return self._switch_to_next_model('replicate')
        
        return False
    
    def _switch_to_next_model(self, provider: str) -> bool:
        """
        Переключиться на следующую модель
        
        Returns:
            True если переключение успешно
        """
        if provider.lower() == 'openrouter':
            current_model = self.get_current_model('openrouter')
            
            if self.current_openrouter_index + 1 < len(self.openrouter_models):
                self.current_openrouter_index += 1
                self.openrouter_error_count = 0
                
                next_model = self.get_current_model('openrouter')
                logger.warning(
                    f"🔄 OpenRouter: переключение модели\n"
                    f"   ❌ Было: {current_model.name}\n"
                    f"   ✅ Стало: {next_model.name}"
                )
                
                # Логируем в файл
                self._log_model_switch('openrouter', current_model, next_model)
                return True
            else:
                logger.error(f"❌ OpenRouter: все модели исчерпаны!")
                return False
        
        elif provider.lower() == 'replicate':
            current_model = self.get_current_model('replicate')
            
            if self.current_replicate_index + 1 < len(self.replicate_models):
                self.current_replicate_index += 1
                self.replicate_error_count = 0
                
                next_model = self.get_current_model('replicate')
                logger.warning(
                    f"🔄 Replicate: переключение модели\n"
                    f"   ❌ Было: {current_model.name}\n"
                    f"   ✅ Стало: {next_model.name}"
                )
                
                # Логируем в файл
                self._log_model_switch('replicate', current_model, next_model)
                return True
            else:
                logger.error(f"❌ Replicate: все модели исчерпаны!")
                return False
        
        return False
    
    def _log_model_switch(self, provider: str, old_model: ModelConfig, new_model: ModelConfig):
        """Логирование переключения модели в файл"""
        logging_config = self.config.get('logging', {})
        
        if not logging_config.get('log_model_switches', True):
            return
        
        log_file = logging_config.get('log_file', 'data/logs/model_fallback.log')
        log_path = Path(log_file)
        
        # Создаем директорию если нужно
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Provider: {provider}\n")
                f.write(f"Old Model: {old_model.name} (priority {old_model.priority})\n")
                f.write(f"New Model: {new_model.name} (priority {new_model.priority})\n")
                f.write(f"Reason: Max retries exceeded\n")
        except Exception as e:
            logger.error(f"❌ Ошибка записи в лог: {e}")
    
    def reset_to_first_model(self, provider: str):
        """Сбросить на первую модель (например, после успешного запроса)"""
        if provider.lower() == 'openrouter':
            if self.current_openrouter_index != 0:
                logger.info(f"🔄 OpenRouter: сброс на первую модель")
                self.current_openrouter_index = 0
                self.openrouter_error_count = 0
        
        elif provider.lower() == 'replicate':
            if self.current_replicate_index != 0:
                logger.info(f"🔄 Replicate: сброс на первую модель")
                self.current_replicate_index = 0
                self.replicate_error_count = 0
    
    def get_status(self) -> dict:
        """Получить статус всех моделей"""
        return {
            'openrouter': {
                'current_model': self.get_current_model('openrouter').name if self.get_current_model('openrouter') else None,
                'current_index': self.current_openrouter_index,
                'total_models': len(self.openrouter_models),
                'error_count': self.openrouter_error_count,
                'all_models': [m.name for m in self.openrouter_models]
            },
            'replicate': {
                'current_model': self.get_current_model('replicate').name if self.get_current_model('replicate') else None,
                'current_index': self.current_replicate_index,
                'total_models': len(self.replicate_models),
                'error_count': self.replicate_error_count,
                'all_models': [m.name for m in self.replicate_models]
            }
        }
    
    def print_status(self):
        """Вывести статус в консоль"""
        status = self.get_status()
        
        print("\n📊 СТАТУС МОДЕЛЕЙ")
        print("=" * 50)
        
        # OpenRouter
        or_status = status['openrouter']
        print(f"\n🔷 OpenRouter:")
        print(f"   Текущая модель: {or_status['current_model']}")
        print(f"   Позиция: {or_status['current_index'] + 1}/{or_status['total_models']}")
        print(f"   Ошибок: {or_status['error_count']}")
        print(f"   Доступные модели:")
        for i, model_name in enumerate(or_status['all_models'], 1):
            marker = "→" if i == or_status['current_index'] + 1 else " "
            print(f"      {marker} {i}. {model_name}")
        
        # Replicate
        rep_status = status['replicate']
        print(f"\n🦎 Replicate:")
        print(f"   Текущая модель: {rep_status['current_model']}")
        print(f"   Позиция: {rep_status['current_index'] + 1}/{rep_status['total_models']}")
        print(f"   Ошибок: {rep_status['error_count']}")
        print(f"   Доступные модели:")
        for i, model_name in enumerate(rep_status['all_models'], 1):
            marker = "→" if i == rep_status['current_index'] + 1 else " "
            print(f"      {marker} {i}. {model_name}")


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создаем менеджер
    manager = ModelsManager()
    
    # Показываем статус
    manager.print_status()
    
    # Симулируем ошибки
    print("\n🧪 ТЕСТ FALLBACK")
    print("=" * 50)
    
    # Симулируем 3 ошибки для OpenRouter
    for i in range(3):
        print(f"\n❌ Ошибка {i+1} для OpenRouter (data policy)")
        switched = manager.report_error('openrouter', 'data policy error')
        if switched:
            print(f"✅ Переключились на следующую модель")
    
    # Показываем новый статус
    manager.print_status()
