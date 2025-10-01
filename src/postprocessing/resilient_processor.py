#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 Устойчивый процессор писем с автоматическим повтором
Обеспечивает надежную обработку писем с механизмом повторных попыток

Author: Contact Parser Team
Created: 2025-09-30
"""

import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessingStrategy(Enum):
    """Стратегии обработки писем"""
    STANDARD = "standard"
    SIMPLIFIED = "simplified"
    FALLBACK = "fallback"


@dataclass
class ProcessingResult:
    """Результат обработки письма"""
    email_file: str
    success: bool
    strategy_used: ProcessingStrategy
    attempt_number: int
    processing_time: float
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


class ResilientEmailProcessor:
    """
    🔧 Устойчивый процессор писем с автоматическим повтором
    
    Обеспечивает:
    - Автоматический повтор обработки проблемных писем
    - Несколько стратегий обработки
    - Перезапись файлов с ошибками
    - Детальное логирование процесса
    """
    
    def __init__(self, original_processor, max_retries: int = 2):
        """
        Инициализация устойчивого процессора
        
        Args:
            original_processor: Оригинальный процессор писем
            max_retries: Максимальное количество повторных попыток
        """
        self.processor = original_processor
        self.max_retries = max_retries
        self.failed_emails: List[str] = []
        self.processing_results: List[ProcessingResult] = []
        self.retry_statistics = {
            'total_emails': 0,
            'successful_first_attempt': 0,
            'successful_after_retry': 0,
            'permanently_failed': 0,
            'strategies_used': {
                ProcessingStrategy.STANDARD: 0,
                ProcessingStrategy.SIMPLIFIED: 0,
                ProcessingStrategy.FALLBACK: 0
            }
        }
    
    def process_emails_with_retry(self, emails: List[str]) -> Dict[str, Any]:
        """
        Обработка писем с автоматическим повтором
        
        Args:
            emails: Список файлов писем для обработки
            
        Returns:
            Dict с результатами обработки и статистикой
        """
        logger.info(f"🔄 Начинаю устойчивую обработку {len(emails)} писем")
        
        self.retry_statistics['total_emails'] = len(emails)
        self.failed_emails = []
        self.processing_results = []
        
        # Первый проход - стандартная обработка
        logger.info("📧 Первый проход: стандартная обработка")
        first_pass_results = self._process_emails_standard(emails)
        
        # Повторная обработка проблемных писем
        if self.failed_emails:
            logger.warning(f"⚠️ Найдено {len(self.failed_emails)} проблемных писем, начинаю повторную обработку")
            self._retry_failed_emails()
        
        # Формируем итоговый результат
        return self._build_final_result(first_pass_results)
    
    def _process_emails_standard(self, emails: List[str]) -> Dict[str, Any]:
        """Стандартная обработка писем (первый проход)"""
        results = []
        
        for i, email_file in enumerate(emails, 1):
            start_time = time.time()
            
            # Четкий разделитель между письмами
            print(f"\n{'='*80}")
            print(f"📧 ПИСЬМО {i}/{len(emails)}: {Path(email_file).name}")
            print(f"{'='*80}")
            
            try:
                logger.info(f"🔄 Начинаю обработку письма {i}/{len(emails)}")
                result = self.processor.process_single_email(email_file)
                processing_time = time.time() - start_time
                
                if self._has_errors(result):
                    logger.warning(f"❌ Ошибка в {email_file}: {self._extract_error_message(result)}")
                    self.failed_emails.append(email_file)
                    
                    self.processing_results.append(ProcessingResult(
                        email_file=email_file,
                        success=False,
                        strategy_used=ProcessingStrategy.STANDARD,
                        attempt_number=1,
                        processing_time=processing_time,
                        error_message=self._extract_error_message(result)
                    ))
                else:
                    logger.debug(f"✅ Успешно обработан {email_file}")
                    results.append(result)
                    self.retry_statistics['successful_first_attempt'] += 1
                    self.retry_statistics['strategies_used'][ProcessingStrategy.STANDARD] += 1
                    
                    self.processing_results.append(ProcessingResult(
                        email_file=email_file,
                        success=True,
                        strategy_used=ProcessingStrategy.STANDARD,
                        attempt_number=1,
                        processing_time=processing_time,
                        result_data=result
                    ))
                    
            except Exception as e:
                processing_time = time.time() - start_time
                error_msg = str(e)
                logger.error(f"💥 Исключение при обработке {email_file}: {error_msg}")
                
                self.failed_emails.append(email_file)
                self.processing_results.append(ProcessingResult(
                    email_file=email_file,
                    success=False,
                    strategy_used=ProcessingStrategy.STANDARD,
                    attempt_number=1,
                    processing_time=processing_time,
                    error_message=error_msg
                ))
        
        return {'results': results}
    
    def _retry_failed_emails(self):
        """Повторная обработка проблемных писем с разными стратегиями"""
        
        for attempt in range(1, self.max_retries + 1):
            if not self.failed_emails:
                break
                
            logger.info(f"🔄 Попытка повтора #{attempt} для {len(self.failed_emails)} писем")
            
            retry_list = self.failed_emails.copy()
            self.failed_emails = []
            
            for email_file in retry_list:
                success = False
                
                # Пробуем разные стратегии
                strategies = [ProcessingStrategy.SIMPLIFIED, ProcessingStrategy.FALLBACK]
                current_error = None
                
                for strategy in strategies:
                    if success:
                        break
                        
                    start_time = time.time()
                    strategy_error = None
                    
                    try:
                        if strategy == ProcessingStrategy.FALLBACK:
                            logger.warning(f"🆘 Используем fallback стратегию для {email_file} из-за ошибки: {current_error or 'неизвестная'}")
                        else:
                            logger.info(f"🔧 Повтор {email_file} со стратегией {strategy.value}")
                        result = self._process_with_strategy(email_file, strategy, original_error=current_error)
                        processing_time = time.time() - start_time
                        
                        if not self._has_errors(result):
                            logger.info(f"✅ Успешный повтор {email_file} со стратегией {strategy.value}")
                            
                            # Перезаписываем файлы с ошибками
                            self._overwrite_error_files(email_file, result)
                            
                            self.retry_statistics['successful_after_retry'] += 1
                            self.retry_statistics['strategies_used'][strategy] += 1
                            
                            self.processing_results.append(ProcessingResult(
                                email_file=email_file,
                                success=True,
                                strategy_used=strategy,
                                attempt_number=attempt + 1,
                                processing_time=processing_time,
                                result_data=result
                            ))
                            
                            success = True
                        else:
                            strategy_error = self._extract_error_message(result)
                            logger.debug(f"❌ Стратегия {strategy.value} не помогла для {email_file}: {strategy_error}")
                            current_error = strategy_error  # Обновляем для следующей стратегии
                            
                    except Exception as e:
                        processing_time = time.time() - start_time
                        strategy_error = str(e)
                        logger.error(f"💥 Ошибка при повторе {email_file} со стратегией {strategy.value}: {strategy_error}")
                        current_error = strategy_error
                
                # Если все стратегии не помогли
                if not success:
                    self.failed_emails.append(email_file)
        
        # Помечаем окончательно проблемные файлы
        for email_file in self.failed_emails:
            logger.error(f"🚫 Окончательно не удалось обработать {email_file}")
            self._mark_as_error(email_file)
            self.retry_statistics['permanently_failed'] += 1
    
    def _process_with_strategy(self, email_file: str, strategy: ProcessingStrategy, original_error: Optional[str] = None) -> Dict[str, Any]:
        """Обработка письма с определенной стратегией"""
        
        if strategy == ProcessingStrategy.SIMPLIFIED:
            return self._process_simplified(email_file)
        elif strategy == ProcessingStrategy.FALLBACK:
            return self._process_fallback(email_file, original_error=original_error)
        else:
            return self.processor.process_single_email(email_file)
    
    def _process_simplified(self, email_file: str) -> Dict[str, Any]:
        """Упрощенная стратегия обработки"""
        logger.debug(f"🔧 Упрощенная обработка {email_file}")
        
        try:
            # Применяем исправления перед обработкой
            fixed_email_data = self._apply_error_fixes(email_file)
            
            # Обрабатываем с упрощенными параметрами
            result = self.processor.process_single_email(email_file, simplified=True)
            
            # Применяем дополнительные исправления к результату
            if result and isinstance(result, dict):
                try:
                    from src.core.safe_math_utils import fix_none_values_in_data, sanitize_json_fields, fix_json_schema_validation_errors
                    result = fix_none_values_in_data(result)
                    result = sanitize_json_fields(result)
                    result = fix_json_schema_validation_errors(result)
                    logger.info(f"✅ Применены исправления валидации для {email_file}")
                except ImportError:
                    logger.warning("⚠️ Модуль safe_math_utils недоступен, пропускаю исправления")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в упрощенной обработке {email_file}: {e}")
            raise
    
    def _process_fallback(self, email_file: str, original_error: Optional[str] = None) -> Dict[str, Any]:
        """Fallback стратегия - минимальная обработка с извлечением базовой информации"""
        logger.warning(f"🆘 Fallback обработка {email_file} - попытка извлечь базовую информацию. Причина: {original_error or 'неизвестная ошибка'}")
        
        try:
            # Пытаемся извлечь базовую информацию из письма
            basic_info = self._extract_basic_email_info(email_file)
            
            # Создаем минимальную структуру результата с базовой информацией
            fallback_result = {
                'source_file': email_file,
                'organizations': basic_info.get('organizations', []),
                'contacts': basic_info.get('contacts', []),
                'business_context': f"Fallback обработка: {basic_info.get('subject', 'Без темы')}",
                'summary': {
                    'topic': basic_info.get('subject', 'Минимальная обработка'),
                    'product_interest': None,
                    'communication_stage': 'other',
                    'request_type': 'other'
                },
                'key_points': basic_info.get('key_points', []),
                'commercial_offers': [],
                'interactions': basic_info.get('interactions', []),
                'success': False,
                'validation_error': True,
                'processing_strategy': 'fallback',
                'fallback_reason': basic_info.get('fallback_reason', 'Неизвестная ошибка'),
                'original_error': original_error,
                'errors': [original_error or 'Fallback processing triggered due to validation failure']
            }
            
            # Применяем исправления к fallback результату
            try:
                from src.core.safe_math_utils import fix_none_values_in_data, sanitize_json_fields, fix_json_schema_validation_errors
                fallback_result = fix_none_values_in_data(fallback_result)
                fallback_result = sanitize_json_fields(fallback_result)
                fallback_result = fix_json_schema_validation_errors(fallback_result)
            except ImportError:
                logger.warning("⚠️ Модуль safe_math_utils недоступен для fallback")
            
            logger.info(f"🆘 Создан fallback результат для {email_file} с сохранением исходной ошибки")
            fallback_result['processing_strategy'] = 'fallback'
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка даже в fallback обработке {email_file}: {e}")
            raise
    
    def _extract_basic_email_info(self, email_file: str) -> Dict[str, Any]:
        """Извлечение базовой информации из письма для fallback обработки"""
        try:
            import json
            from pathlib import Path
            
            # Читаем файл письма
            email_path = Path(email_file)
            if not email_path.exists():
                # Пытаемся найти файл в стандартных директориях
                possible_paths = [
                    Path("data/emails") / email_path.name,
                    Path("data/emails/2025-07-29") / email_path.name,
                ]
                
                for path in possible_paths:
                    if path.exists():
                        email_path = path
                        break
            
            if not email_path.exists():
                logger.error(f"Файл письма не найден: {email_file}")
                return {'fallback_reason': f'Файл не найден: {email_file}'}
            
            with open(email_path, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            
            # Извлекаем базовую информацию
            from_email = email_data.get('from', '')
            subject = email_data.get('subject', 'Без темы')
            body = email_data.get('body', '')
            
            # Создаем минимальную организацию из домена отправителя
            organizations = []
            contacts = []
            interactions = []
            
            if from_email and '@' in from_email:
                domain = from_email.split('@')[1] if '@' in from_email else ''
                name_part = from_email.split('@')[0] if '@' in from_email else from_email
                
                # Создаем организацию
                if domain and not any(pub in domain.lower() for pub in ['mail.ru', 'yandex.ru', 'gmail.com', 'bk.ru']):
                    organizations.append({
                        'organization_id': 1,
                        'name': domain.replace('.', ' ').title(),
                        'inn': None,
                        'website': domain,
                        'city': None,
                        'address': None
                    })
                
                # Создаем контакт
                contacts.append({
                    'contact_id': 1,
                    'organization_id': 1 if organizations else None,
                    'name': name_part.replace('.', ' ').title(),
                    'position': None,
                    'email': from_email,
                    'phone': None
                })
                
                # Создаем взаимодействие
                interactions.append({
                    'organization_id': 1 if organizations else None,
                    'contact_id': 1,
                    'interaction_type': 'other',
                    'summary': f"Письмо: {subject[:100]}",
                    'attachments': [],
                    'confidence': 0.5
                })
            
            # Извлекаем ключевые моменты из темы и тела письма
            key_points = []
            if subject and subject != 'Без темы':
                key_points.append(f"Тема: {subject}")
            
            if body and len(body.strip()) > 10:
                # Берем первые 200 символов тела письма
                body_preview = body.strip()[:200]
                if len(body.strip()) > 200:
                    body_preview += "..."
                key_points.append(f"Содержание: {body_preview}")
            
            return {
                'organizations': organizations,
                'contacts': contacts,
                'interactions': interactions,
                'key_points': key_points,
                'subject': subject,
                'fallback_reason': 'Извлечена базовая информация из письма'
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения базовой информации из {email_file}: {e}")
            return {
                'organizations': [],
                'contacts': [],
                'interactions': [],
                'key_points': [],
                'subject': 'Ошибка обработки',
                'fallback_reason': f'Ошибка извлечения: {str(e)}'
            }
    
    def _apply_error_fixes(self, email_file: str) -> Dict[str, Any]:
        """Применение исправлений для известных ошибок"""
        logger.debug(f"🔧 Применяю исправления для {email_file}")
        
        try:
            # Читаем исходный файл письма
            email_path = Path(email_file)
            if not email_path.exists():
                # Пытаемся найти файл в стандартных директориях
                possible_paths = [
                    Path("data/emails") / email_path.name,
                    Path("data/emails/2025-07-29") / email_path.name,
                ]
                
                for path in possible_paths:
                    if path.exists():
                        email_path = path
                        break
            
            if email_path.exists():
                with open(email_path, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                
                # Применяем исправления
                try:
                    from src.core.safe_math_utils import sanitize_json_fields, fix_none_values_in_data
                    email_data = sanitize_json_fields(email_data)
                    email_data = fix_none_values_in_data(email_data)
                except ImportError:
                    logger.warning("⚠️ Модуль safe_math_utils недоступен, пропускаю исправления")
                
                return email_data
            else:
                logger.warning(f"⚠️ Не найден файл {email_file} для применения исправлений")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка при применении исправлений для {email_file}: {e}")
            return {}
    
    def _has_errors(self, result: Dict[str, Any]) -> bool:
        """Проверка наличия ошибок в результате"""
        if not result:
            return True
        
        # Проверяем флаг success
        if result.get('success') is False:
            return True
        
        # Проверяем наличие validation_error
        if result.get('validation_error') is True:
            return True
        
        # Проверяем наличие поля error
        if 'error' in result:
            return True
        
        # Проверяем вложенные результаты
        if 'processed_result' in result:
            processed = result['processed_result']
            if processed.get('success') is False or processed.get('validation_error') is True:
                return True
        
        return False
    
    def _extract_error_message(self, result: Dict[str, Any]) -> str:
        """Извлечение сообщения об ошибке из результата"""
        if not result:
            return "Пустой результат"
        
        # Проверяем прямое поле error
        if 'error' in result:
            return str(result['error'])
        
        # Проверяем вложенные ошибки
        if 'processed_result' in result:
            processed = result['processed_result']
            if 'original_response' in processed and 'error' in processed['original_response']:
                return str(processed['original_response']['error'])
        
        # Проверяем validation_error
        if result.get('validation_error'):
            return "Ошибка валидации"
        
        return "Неизвестная ошибка"
    
    def _overwrite_error_files(self, email_file: str, result: Dict[str, Any]):
        """Перезапись файлов с ошибками валидными результатами"""
        logger.info(f"📝 Перезаписываю результаты для {email_file}")
        
        try:
            # Находим файлы результатов для данного письма
            email_name = Path(email_file).stem
            results_dir = Path("data/llm_results/2025-07-29")
            
            if not results_dir.exists():
                logger.warning(f"⚠️ Директория результатов не найдена: {results_dir}")
                return
            
            # Ищем файлы с ошибками для данного письма
            error_files = list(results_dir.glob(f"{email_name}*"))
            
            for error_file in error_files:
                if error_file.suffix in ['.md', '.json']:
                    try:
                        # Создаем новый валидный результат
                        if error_file.suffix == '.json':
                            # Обновляем JSON файл
                            with open(error_file, 'w', encoding='utf-8') as f:
                                json.dump(result, f, ensure_ascii=False, indent=2)
                        elif error_file.suffix == '.md':
                            # Создаем новый markdown отчет
                            self._create_success_markdown(error_file, result)
                        
                        logger.debug(f"✅ Перезаписан файл {error_file}")
                        
                    except Exception as e:
                        logger.error(f"❌ Ошибка при перезаписи {error_file}: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Ошибка при перезаписи файлов для {email_file}: {e}")
    
    def _create_success_markdown(self, md_file: Path, result: Dict[str, Any]):
        """Создание успешного markdown отчета"""
        
        markdown_content = f"""# Отчёт по письму — Успешная повторная обработка

## Метаданные
- **Файл:** `{result.get('source_file', 'unknown')}`
- **Статус:** ✅ Успешно обработано после повтора
- **Стратегия:** {result.get('processing_strategy', 'unknown')}

## Резюме
- **Бизнес-контекст:** {result.get('business_context', 'Не определен')}
- **Тема:** {result.get('summary', {}).get('topic', 'Не определена')}

## Организации
Найдено организаций: {len(result.get('organizations', []))}

## Контакты  
Найдено контактов: {len(result.get('contacts', []))}

## Коммерческие предложения
Найдено КП: {len(result.get('commercial_offers', []))}

## Диагностика
- **Статус:** ✅ Успех после повтора
- **Стратегия:** {result.get('processing_strategy', 'unknown')}
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    
    def _mark_as_error(self, email_file: str):
        """Маркировка файлов как окончательно проблемных"""
        logger.error(f"🚫 Маркирую {email_file} как окончательно проблемный")
        
        try:
            email_name = Path(email_file).stem
            results_dir = Path("data/llm_results/2025-07-29")
            
            if not results_dir.exists():
                return
            
            # Ищем файлы результатов
            result_files = list(results_dir.glob(f"{email_name}*"))
            
            for result_file in result_files:
                if result_file.suffix in ['.md', '.json']:
                    # Переименовываем файл с префиксом ERROR_
                    error_file_name = f"ERROR_{result_file.name}"
                    error_file_path = result_file.parent / error_file_name
                    
                    try:
                        result_file.rename(error_file_path)
                        logger.debug(f"🚫 Переименован {result_file} → {error_file_path}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка при переименовании {result_file}: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Ошибка при маркировке {email_file}: {e}")
    
    def _build_final_result(self, first_pass_results: Dict[str, Any]) -> Dict[str, Any]:
        """Формирование итогового результата"""
        
        successful_results = [r for r in self.processing_results if r.success]
        failed_results = [r for r in self.processing_results if not r.success]
        
        # Собираем все успешные результаты
        all_results = first_pass_results.get('results', [])
        for result in successful_results:
            if result.result_data and result.attempt_number > 1:
                all_results.append(result.result_data)
        
        final_result = {
            'results': all_results,
            'statistics': {
                'total_emails': self.retry_statistics['total_emails'],
                'successful_emails': len(successful_results),
                'failed_emails': len(failed_results),
                'successful_first_attempt': self.retry_statistics['successful_first_attempt'],
                'successful_after_retry': self.retry_statistics['successful_after_retry'],
                'permanently_failed': self.retry_statistics['permanently_failed'],
                'strategies_used': {k.value: v for k, v in self.retry_statistics['strategies_used'].items()}
            },
            'retry_details': {
                'processing_results': [
                    {
                        'email_file': r.email_file,
                        'success': r.success,
                        'strategy': r.strategy_used.value,
                        'attempt': r.attempt_number,
                        'processing_time': r.processing_time,
                        'error': r.error_message
                    }
                    for r in self.processing_results
                ]
            }
        }
        
        logger.info(f"📊 Итоговая статистика:")
        logger.info(f"   📧 Всего писем: {final_result['statistics']['total_emails']}")
        logger.info(f"   ✅ Успешно: {final_result['statistics']['successful_emails']}")
        logger.info(f"   ❌ Неудачно: {final_result['statistics']['failed_emails']}")
        logger.info(f"   🎯 Успешно с первой попытки: {final_result['statistics']['successful_first_attempt']}")
        logger.info(f"   🔄 Успешно после повтора: {final_result['statistics']['successful_after_retry']}")
        logger.info(f"   🚫 Окончательно не удалось: {final_result['statistics']['permanently_failed']}")
        
        return final_result
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """Получение статистики повторных обработок"""
        return {
            'retry_statistics': self.retry_statistics,
            'processing_results': self.processing_results,
            'failed_emails': self.failed_emails
        }


# Тестирование
if __name__ == "__main__":
    # Настройка логирования для тестов
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔄 Тестирование ResilientEmailProcessor")
    print("=" * 60)
    
    # Мок процессор для тестирования
    class MockProcessor:
        def process_single_email(self, email_file, simplified=False):
            # Симулируем ошибки для определенных файлов
            if 'email_014' in email_file:
                return {
                    'success': False,
                    'validation_error': True,
                    'original_response': {
                        'error': 'unsupported operand type(s) for *: \'NoneType\' and \'float\''
                    }
                }
            elif 'email_022' in email_file:
                return {
                    'success': False,
                    'validation_error': True,
                    'error': 'Invalid field name with Chinese characters'
                }
            else:
                return {
                    'success': True,
                    'organizations': [],
                    'contacts': [],
                    'business_context': 'Test context'
                }
    
    # Тестируем ResilientEmailProcessor
    mock_processor = MockProcessor()
    resilient_processor = ResilientEmailProcessor(mock_processor, max_retries=2)
    
    test_emails = [
        'email_001_test.json',
        'email_014_test.json',  # Проблемный
        'email_022_test.json',  # Проблемный
        'email_003_test.json'
    ]
    
    print(f"🧪 Тестирую обработку {len(test_emails)} писем")
    result = resilient_processor.process_emails_with_retry(test_emails)
    
    print("\n📊 Результаты тестирования:")
    print(f"   Всего писем: {result['statistics']['total_emails']}")
    print(f"   Успешно: {result['statistics']['successful_emails']}")
    print(f"   Неудачно: {result['statistics']['failed_emails']}")
    print(f"   Успешно с первой попытки: {result['statistics']['successful_first_attempt']}")
    print(f"   Успешно после повтора: {result['statistics']['successful_after_retry']}")
    
    print("\n✅ Тестирование завершено")
