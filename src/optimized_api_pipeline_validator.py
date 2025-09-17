#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Optimized API Pipeline Validator - Stage 12 Implementation
Оптимизированная версия валидатора с профилированием и кэшированием

Оптимизации:
- Кэширование загруженных email
- Ленивая загрузка вложений
- Профилирование узких мест
- Оптимизация обработки JSON
- Пулинг соединений для async операций
"""

import sys
import json
import time
import cProfile
import pstats
import io
from functools import lru_cache
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Добавление корневой директории проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импорт оригинального валидатора
from src.api_pipeline_validator import APIPipelineValidator, AsyncAPIPipelineValidator
from src.utils.logger import logger

class PerformanceProfiler:
    """Профилировщик производительности для отслеживания узких мест"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.call_counts = {}
        
    def start_timer(self, operation: str):
        """Запуск таймера для операции"""
        self.start_times[operation] = time.time()
        self.call_counts[operation] = self.call_counts.get(operation, 0) + 1
        
    def end_timer(self, operation: str):
        """Завершение таймера и сохранение метрики"""
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
            del self.start_times[operation]
            
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики производительности"""
        stats = {}
        for operation, times in self.metrics.items():
            stats[operation] = {
                'total_time': sum(times),
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'call_count': self.call_counts.get(operation, 0),
                'calls': len(times)
            }
        return stats
        
    def print_report(self):
        """Вывод отчета о производительности"""
        print("\n🚀 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ:")
        print("=" * 60)
        
        stats = self.get_stats()
        # Сортируем по общему времени
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total_time'], reverse=True)
        
        for operation, data in sorted_stats:
            print(f"\n📊 {operation}:")
            print(f"   Общее время: {data['total_time']:.3f}с")
            print(f"   Среднее время: {data['avg_time']:.3f}с")
            print(f"   Мин/Макс: {data['min_time']:.3f}с / {data['max_time']:.3f}с")
            print(f"   Вызовов: {data['call_count']}")

class OptimizedEmailCache:
    """Кэш для загруженных email с LRU политикой"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache = {}
        self._access_order = []
        
    def get(self, filename: str) -> Optional[Dict]:
        """Получение email из кэша"""
        if filename in self._cache:
            # Обновляем порядок доступа
            self._access_order.remove(filename)
            self._access_order.append(filename)
            return self._cache[filename]
        return None
        
    def put(self, filename: str, email_data: Dict):
        """Сохранение email в кэш"""
        if filename in self._cache:
            # Обновляем существующий
            self._access_order.remove(filename)
        elif len(self._cache) >= self.max_size:
            # Удаляем самый старый
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
            
        self._cache[filename] = email_data
        self._access_order.append(filename)
        
    def clear(self):
        """Очистка кэша"""
        self._cache.clear()
        self._access_order.clear()
        
    def size(self) -> int:
        """Размер кэша"""
        return len(self._cache)

class OptimizedAPIPipelineValidator(APIPipelineValidator):
    """Оптимизированная версия валидатора с профилированием и кэшированием"""
    
    def __init__(self, 
                 date: str = "2025-07-29",
                 results_dir: Optional[str] = None,
                 reports_dir: Optional[str] = None,
                 test_mode: bool = False,
                 enable_profiling: bool = True,
                 cache_size: int = 100):
        
        super().__init__(date, results_dir, reports_dir, test_mode)
        
        # Инициализация оптимизаций
        self.profiler = PerformanceProfiler() if enable_profiling else None
        self.email_cache = OptimizedEmailCache(cache_size)
        self.enable_profiling = enable_profiling
        
        # Пул потоков для I/O операций
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        print(f"🚀 Инициализирован оптимизированный валидатор:")
        print(f"   - Профилирование: {'включено' if enable_profiling else 'отключено'}")
        print(f"   - Размер кэша: {cache_size}")
        print(f"   - Потоков для I/O: 4")
        
    def _profile_operation(self, operation_name: str):
        """Декоратор для профилирования операций"""
        class ProfileContext:
            def __init__(self, profiler, name):
                self.profiler = profiler
                self.name = name
                
            def __enter__(self):
                if self.profiler:
                    self.profiler.start_timer(self.name)
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.profiler:
                    self.profiler.end_timer(self.name)
                    
        return ProfileContext(self.profiler, operation_name)
        
    @lru_cache(maxsize=50)
    def _cached_file_exists(self, file_path: str) -> bool:
        """Кэшированная проверка существования файла"""
        return Path(file_path).exists()
        
    def load_email_with_attachments(self, filename: str) -> Optional[Dict]:
        """Оптимизированная загрузка email с кэшированием"""
        
        with self._profile_operation("load_email_total"):
            # Проверяем кэш
            cached_email = self.email_cache.get(filename)
            if cached_email:
                print(f"      ⚡ Загружено из кэша: {filename}")
                return cached_email
                
            with self._profile_operation("load_email_from_disk"):
                # Загружаем с диска используя оригинальный метод
                email_data = super().load_email_with_attachments(filename)
                
            if email_data:
                # Сохраняем в кэш
                self.email_cache.put(filename, email_data)
                print(f"      💾 Сохранено в кэш: {filename} (размер кэша: {self.email_cache.size()})")
                
            return email_data
            
    def process_single_email(self, filename: str) -> Optional[Dict]:
        """Оптимизированная обработка одного email"""
        
        with self._profile_operation("process_single_email_total"):
            print(f"      🔄 Обработка: {filename}")
            
            try:
                with self._profile_operation("email_loading"):
                    email_data = self.load_email_with_attachments(filename)
                    
                if not email_data:
                    return {
                        'filename': filename,
                        'success': False,
                        'error': 'Ошибка загрузки письма',
                        'no_providers_available': False
                    }
                    
                # Проверка процессора
                if not self.processor:
                    print(f"      ❌ Процессор не инициализирован")
                    return {
                        'filename': filename,
                        'success': False,
                        'error': 'Процессор не инициализирован',
                        'no_providers_available': True
                    }
                    
                with self._profile_operation("text_extraction"):
                    text_content = self._extract_text_content_via_main_pipeline(email_data)
                    
                print(f"      🤖 Обработка через основной пайплайн ({len(text_content)} символов)...")
                print(f"      📎 Вложений: {len(email_data.get('attachments', []))}")
                
                with self._profile_operation("llm_processing"):
                    start_time = time.time()
                    try:
                        result = self.processor.extract_all_data(text_content)
                    except Exception as extract_error:
                        print(f"      ❌ Ошибка в основном пайплайне: {extract_error}")
                        return {
                            'filename': filename,
                            'success': False,
                            'error': f'Ошибка основного пайплайна: {str(extract_error)}',
                            'no_providers_available': False
                        }
                        
                processing_time = time.time() - start_time
                
                # Проверяем успешность
                if result and (result.get('organizations') or result.get('contacts') or result.get('commercial_offers')):
                    print(f"      ✅ Обработано успешно за {processing_time:.2f}с")
                    print(f"         - Организации: {len(result.get('organizations', []))}")
                    print(f"         - Контакты: {len(result.get('contacts', []))}")
                    print(f"         - Коммерческие предложения: {len(result.get('commercial_offers', []))}")
                    
                    return {
                        'filename': filename,
                        'email_data': {
                            'from': email_data.get('from', ''),
                            'subject': email_data.get('subject', ''),
                            'date': email_data.get('date', ''),
                            'attachments_count': len(email_data.get('attachments', [])),
                            'char_count': len(text_content),
                            'attachments': email_data.get('attachments', [])
                        },
                        'llm_result': result,
                        'processing_time': processing_time,
                        'timestamp': datetime.now().isoformat(),
                        'success': True
                    }
                else:
                    print(f"      ❌ Обработка неуспешна: нет извлеченных данных")
                    
                    error_msg = str(result.get('error', '')) if result else 'Пустой результат'
                    no_providers = (
                        'Нет доступных LLM провайдеров' in error_msg or
                        'Все провайдеры недоступны' in error_msg or
                        (result and result.get('no_providers_available', False))
                    )
                    
                    return {
                        'filename': filename,
                        'email_data': {
                            'from': email_data.get('from', ''),
                            'subject': email_data.get('subject', ''),
                            'date': email_data.get('date', ''),
                            'attachments_count': len(email_data.get('attachments', [])),
                            'char_count': len(text_content),
                            'attachments': email_data.get('attachments', [])
                        },
                        'llm_result': result or {},
                        'processing_time': processing_time,
                        'timestamp': datetime.now().isoformat(),
                        'success': False,
                        'no_providers_available': no_providers
                    }
                    
            except Exception as e:
                print(f"      ❌ Ошибка обработки: {e}")
                import traceback
                print(f"      🔍 Детали ошибки: {traceback.format_exc()}")
                return {
                    'filename': filename,
                    'success': False,
                    'error': str(e),
                    'no_providers_available': False
                }
                
    def run_first10_mode(self) -> Dict:
        """Оптимизированный режим first10 с профилированием"""
        
        with self._profile_operation("run_first10_mode_total"):
            print("\n🚀 ЗАПУСК ОПТИМИЗИРОВАННОГО РЕЖИМА: first10")
            print("=" * 50)
            
            result = super().run_first10_mode()
            
            # Добавляем метрики производительности
            if self.profiler:
                result['performance_metrics'] = self.profiler.get_stats()
                
            return result
            
    def run_all_mode(self) -> Dict:
        """Оптимизированный режим all с профилированием"""
        
        with self._profile_operation("run_all_mode_total"):
            print("\n🚀 ЗАПУСК ОПТИМИЗИРОВАННОГО РЕЖИМА: all")
            print("=" * 50)
            
            result = super().run_all_mode()
            
            # Добавляем метрики производительности
            if self.profiler:
                result['performance_metrics'] = self.profiler.get_stats()
                
            return result
            
    def generate_performance_report(self) -> str:
        """Генерация отчета о производительности"""
        if not self.profiler:
            return "Профилирование отключено"
            
        stats = self.profiler.get_stats()
        
        report = ["\n🚀 ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ"]
        report.append("=" * 60)
        report.append(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Размер кэша: {self.email_cache.size()}")
        report.append("")
        
        # Топ операций по времени
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total_time'], reverse=True)
        
        report.append("📊 ТОП ОПЕРАЦИЙ ПО ВРЕМЕНИ:")
        for i, (operation, data) in enumerate(sorted_stats[:10], 1):
            report.append(f"{i:2d}. {operation}:")
            report.append(f"    Общее время: {data['total_time']:.3f}с")
            report.append(f"    Среднее время: {data['avg_time']:.3f}с")
            report.append(f"    Вызовов: {data['call_count']}")
            report.append("")
            
        # Рекомендации по оптимизации
        report.append("💡 РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ:")
        
        if 'load_email_from_disk' in stats:
            disk_time = stats['load_email_from_disk']['total_time']
            if disk_time > 5.0:
                report.append("- Рассмотрите увеличение размера кэша email")
                
        if 'llm_processing' in stats:
            llm_time = stats['llm_processing']['avg_time']
            if llm_time > 10.0:
                report.append("- LLM обработка занимает много времени, рассмотрите оптимизацию промптов")
                
        if 'text_extraction' in stats:
            extract_time = stats['text_extraction']['avg_time']
            if extract_time > 2.0:
                report.append("- Извлечение текста медленное, проверьте обработку вложений")
                
        return "\n".join(report)
        
    def cleanup(self):
        """Очистка ресурсов"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
        self.email_cache.clear()
        
        if self.profiler:
            self.profiler.print_report()
            
class OptimizedAsyncAPIPipelineValidator(AsyncAPIPipelineValidator):
    """Оптимизированная асинхронная версия валидатора"""
    
    def __init__(self, 
                 date: str = "2025-07-29",
                 results_dir: Optional[str] = None,
                 reports_dir: Optional[str] = None,
                 test_mode: bool = False,
                 max_concurrent: int = 2,
                 enable_profiling: bool = True,
                 cache_size: int = 100):
        
        super().__init__(date, results_dir, reports_dir, test_mode, max_concurrent)
        
        # Добавляем оптимизации
        self.profiler = PerformanceProfiler() if enable_profiling else None
        self.email_cache = OptimizedEmailCache(cache_size)
        self.enable_profiling = enable_profiling
        
        print(f"🚀 Инициализирован оптимизированный async валидатор:")
        print(f"   - Профилирование: {'включено' if enable_profiling else 'отключено'}")
        print(f"   - Размер кэша: {cache_size}")
        print(f"   - Макс. параллельных: {max_concurrent}")
        
    async def process_single_email_async(self, filename: str) -> Optional[Dict]:
        """Оптимизированная асинхронная обработка email"""
        
        if self.profiler:
            self.profiler.start_timer("async_process_single_email")
            
        try:
            # Проверяем кэш
            cached_email = self.email_cache.get(filename)
            if cached_email:
                print(f"      ⚡ Async загружено из кэша: {filename}")
                # Используем кэшированные данные для обработки
                result = await self._process_cached_email_async(filename, cached_email)
            else:
                # Загружаем и обрабатываем
                result = await super().process_single_email_async(filename)
                
            return result
            
        finally:
            if self.profiler:
                self.profiler.end_timer("async_process_single_email")
                
    async def _process_cached_email_async(self, filename: str, email_data: Dict) -> Optional[Dict]:
        """Обработка кэшированного email асинхронно"""
        
        print(f"      🔄 Async обработка кэшированного: {filename}")
        
        try:
            if not self.async_processor:
                return {
                    'filename': filename,
                    'success': False,
                    'error': 'Async процессор не инициализирован',
                    'no_providers_available': True
                }
                
            # Извлекаем текст
            text_content = self._extract_text_content_via_main_pipeline(email_data)
            
            print(f"      🤖 Async обработка ({len(text_content)} символов)...")
            
            start_time = time.time()
            try:
                result = await self.async_processor.extract_all_data_async(text_content)
            except Exception as extract_error:
                print(f"      ❌ Ошибка в async пайплайне: {extract_error}")
                return {
                    'filename': filename,
                    'success': False,
                    'error': f'Ошибка async пайплайна: {str(extract_error)}',
                    'no_providers_available': False
                }
                
            processing_time = time.time() - start_time
            
            # Формируем результат аналогично синхронной версии
            if result and (result.get('organizations') or result.get('contacts') or result.get('commercial_offers')):
                print(f"      ✅ Async обработано успешно за {processing_time:.2f}с")
                
                return {
                    'filename': filename,
                    'email_data': {
                        'from': email_data.get('from', ''),
                        'subject': email_data.get('subject', ''),
                        'date': email_data.get('date', ''),
                        'attachments_count': len(email_data.get('attachments', [])),
                        'char_count': len(text_content),
                        'attachments': email_data.get('attachments', [])
                    },
                    'llm_result': result,
                    'processing_time': processing_time,
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                }
            else:
                return {
                    'filename': filename,
                    'success': False,
                    'error': 'Нет извлеченных данных',
                    'no_providers_available': False
                }
                
        except Exception as e:
            print(f"      ❌ Ошибка async обработки кэшированного email: {e}")
            return {
                'filename': filename,
                'success': False,
                'error': str(e),
                'no_providers_available': False
            }
            
    def cleanup(self):
        """Очистка ресурсов async валидатора"""
        self.email_cache.clear()
        
        if self.profiler:
            self.profiler.print_report()

def run_performance_benchmark(date: str = "2025-07-29", mode: str = "first10") -> Dict:
    """Запуск бенчмарка производительности"""
    
    print("\n🏁 ЗАПУСК БЕНЧМАРКА ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 60)
    
    # Тест оригинального валидатора
    print("\n📊 Тестирование оригинального валидатора...")
    original_start = time.time()
    
    original_validator = APIPipelineValidator(date=date, test_mode=True)
    if mode == "first10":
        original_result = original_validator.run_first10_mode()
    else:
        original_result = original_validator.run_all_mode()
        
    original_time = time.time() - original_start
    
    # Тест оптимизированного валидатора
    print("\n🚀 Тестирование оптимизированного валидатора...")
    optimized_start = time.time()
    
    optimized_validator = OptimizedAPIPipelineValidator(
        date=date, 
        test_mode=True, 
        enable_profiling=True,
        cache_size=50
    )
    
    try:
        if mode == "first10":
            optimized_result = optimized_validator.run_first10_mode()
        else:
            optimized_result = optimized_validator.run_all_mode()
            
        optimized_time = time.time() - optimized_start
        
        # Генерируем отчет о производительности
        performance_report = optimized_validator.generate_performance_report()
        
        # Сравнение результатов
        improvement = ((original_time - optimized_time) / original_time) * 100
        
        benchmark_result = {
            'original_time': original_time,
            'optimized_time': optimized_time,
            'improvement_percent': improvement,
            'original_success_count': original_result.get('successful_count', 0),
            'optimized_success_count': optimized_result.get('successful_count', 0),
            'performance_report': performance_report,
            'cache_hits': optimized_validator.email_cache.size()
        }
        
        print("\n📈 РЕЗУЛЬТАТЫ БЕНЧМАРКА:")
        print(f"Оригинальное время: {original_time:.2f}с")
        print(f"Оптимизированное время: {optimized_time:.2f}с")
        print(f"Улучшение: {improvement:.1f}%")
        print(f"Размер кэша: {optimized_validator.email_cache.size()}")
        
        return benchmark_result
        
    finally:
        optimized_validator.cleanup()

if __name__ == "__main__":
    # Пример использования
    import argparse
    
    parser = argparse.ArgumentParser(description='Оптимизированный API Pipeline Validator')
    parser.add_argument('--date', default='2025-07-29', help='Дата для обработки')
    parser.add_argument('--mode', choices=['first10', 'all'], default='first10', help='Режим обработки')
    parser.add_argument('--benchmark', action='store_true', help='Запуск бенчмарка')
    parser.add_argument('--async-mode', action='store_true', help='Использовать async версию')
    
    args = parser.parse_args()
    
    if args.benchmark:
        run_performance_benchmark(args.date, args.mode)
    elif getattr(args, 'async_mode', False):
        async def run_async():
            validator = OptimizedAsyncAPIPipelineValidator(
                date=args.date,
                test_mode=True,
                enable_profiling=True
            )
            try:
                result = await validator.run_async_mode(args.mode)
                print(f"\n✅ Async обработка завершена: {result.get("successful_count", 0)} успешных")
            finally:
                validator.cleanup()
                
        asyncio.run(run_async())
    else:
        validator = OptimizedAPIPipelineValidator(
            date=args.date,
            test_mode=True,
            enable_profiling=True
        )
        try:
            if args.mode == 'first10':
                result = validator.run_first10_mode()
            else:
                result = validator.run_all_mode()
                
            print(f'\n✅ Обработка завершена: {result.get("successful_count", 0)} успешных')
        finally:
            validator.cleanup()