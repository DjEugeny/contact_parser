#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тестирование оптимизаций Фазы 6
Комплексное тестирование на реальных данных 2025-07-29
"""

import sys
import json
import time
import psutil
from pathlib import Path
from typing import Dict, List, Any
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.extractor_factory import ExtractorFactory
from core.memory_optimizer import MemoryOptimizer


class Phase6PerformanceTester:
    """
    🧪 Тестер производительности оптимизаций Фазы 6

    Тестирует:
    - HTTP оптимизации (connection pooling)
    - Кэширование (промпты + LLM ответы)
    - Memory оптимизации (streaming + GC)
    - Общую производительность на реальных данных
    """

    def __init__(self, test_date: str = "2025-07-29"):
        self.test_date = test_date
        self.test_data_path = Path("data/emails") / test_date
        self.memory_optimizer = MemoryOptimizer(max_memory_mb=400, gc_threshold_mb=200)

        # Статистика тестирования
        self.test_stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_processing_time': 0,
            'average_file_time': 0,
            'peak_memory_mb': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_optimizations': 0,
            'contacts_extracted': 0,
            'errors': []
        }

        # Измерения производительности
        self.performance_metrics = {
            'baseline': {},      # Без оптимизаций
            'with_cache': {},    # С кэшированием
            'with_memory_opt': {}, # С memory оптимизациями
            'full_optimized': {} # Все оптимизации
        }

        logger.info(f"🧪 Phase6PerformanceTester инициализирован для даты {test_date}")

    def discover_test_files(self) -> List[Path]:
        """📂 Найти все тестовые файлы для заданной даты"""
        if not self.test_data_path.exists():
            raise FileNotFoundError(f"❌ Папка с тестовыми данными не найдена: {self.test_data_path}")

        json_files = list(self.test_data_path.glob("*.json"))
        self.test_stats['total_files'] = len(json_files)

        logger.info(f"📂 Найдено {len(json_files)} JSON файлов для тестирования")

        # Сортируем для воспроизводимости
        return sorted(json_files)

    def load_email_data(self, file_path: Path) -> Dict[str, Any]:
        """📧 Загрузить данные email из JSON файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Извлекаем текст письма для обработки
            text = data.get('body', '')

            # Ограничиваем размер для тестирования (первые 3000 символов)
            if len(text) > 3000:
                text = text[:3000] + "..."

            return {
                'file_path': file_path,
                'file_size': file_path.stat().st_size,
                'text': text,
                'text_length': len(text),
                'metadata': {
                    'file_name': file_path.name,
                    'date': self.test_date,
                    'size_mb': file_path.stat().st_size / 1024 / 1024
                }
            }

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки файла {file_path}: {e}")
            self.test_stats['errors'].append(f"Load error {file_path.name}: {e}")
            return None

    def run_baseline_test(self, test_files: List[Path]) -> Dict[str, Any]:
        """
        🏃 Базовый тест производительности (без оптимизаций)

        Args:
            test_files: Список файлов для тестирования

        Returns:
            Dict со статистикой базового теста
        """
        logger.info("🏃 Запуск базового теста производительности...")

        baseline_stats = {
            'files_processed': 0,
            'total_time': 0,
            'average_time': 0,
            'memory_usage': [],
            'contacts_found': 0,
            'errors': 0
        }

        start_time = time.time()

        for file_path in test_files[:5]:  # Тестируем только первые 5 файлов
            file_start_time = time.time()

            try:
                # Загружаем данные
                email_data = self.load_email_data(file_path)
                if not email_data:
                    baseline_stats['errors'] += 1
                    continue

                # Создаем новый экстрактор для чистого теста
                extractor = ExtractorFactory.create_extractor()

                # Обрабатываем текст
                result = extractor.extract_all_data(email_data['text'], email_data['metadata'])

                processing_time = time.time() - file_start_time
                baseline_stats['total_time'] += processing_time
                baseline_stats['files_processed'] += 1
                baseline_stats['contacts_found'] += len(result.get('contacts', []))

                # Замеряем память
                memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                baseline_stats['memory_usage'].append(memory_mb)

                logger.info(".2f"
            except Exception as e:
                logger.error(f"❌ Ошибка обработки файла {file_path.name}: {e}")
                baseline_stats['errors'] += 1

        baseline_stats['average_time'] = baseline_stats['total_time'] / max(baseline_stats['files_processed'], 1)

        self.performance_metrics['baseline'] = baseline_stats

        logger.info("🏃 Базовый тест завершен"        logger.info(f"   📊 Обработано: {baseline_stats['files_processed']} файлов")
        logger.info(".2f"        logger.info(f"   👥 Контактов найдено: {baseline_stats['contacts_found']}")

        return baseline_stats

    def run_optimized_test(self, test_files: List[Path]) -> Dict[str, Any]:
        """
        ⚡ Тест с полными оптимизациями Фазы 6

        Args:
            test_files: Список файлов для тестирования

        Returns:
            Dict со статистикой оптимизированного теста
        """
        logger.info("⚡ Запуск теста с оптимизациями Фазы 6...")

        optimized_stats = {
            'files_processed': 0,
            'total_time': 0,
            'average_time': 0,
            'memory_usage': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_optimizations': 0,
            'contacts_found': 0,
            'errors': 0
        }

        start_time = time.time()

        # Создаем один экстрактор для всех файлов (чтобы кэш работал)
        extractor = ExtractorFactory.create_extractor()

        for file_path in test_files[:10]:  # Тестируем 10 файлов
            file_start_time = time.time()

            try:
                # Загружаем данные
                email_data = self.load_email_data(file_path)
                if not email_data:
                    optimized_stats['errors'] += 1
                    continue

                # Используем memory оптимизатор для больших текстов
                if email_data['text_length'] > 1000:  # > 1KB
                    with self.memory_optimizer.memory_monitor():
                        result = extractor.extract_all_data(email_data['text'], email_data['metadata'])
                    optimized_stats['memory_optimizations'] += 1
                else:
                    result = extractor.extract_all_data(email_data['text'], email_data['metadata'])

                processing_time = time.time() - file_start_time
                optimized_stats['total_time'] += processing_time
                optimized_stats['files_processed'] += 1
                optimized_stats['contacts_found'] += len(result.get('contacts', []))

                # Статистика кэша
                cache_stats = extractor.cache.get_cache_stats()
                optimized_stats['cache_hits'] = cache_stats.get('overall_hit_rate', 0)
                optimized_stats['cache_misses'] = 100 - optimized_stats['cache_hits']

                # Замеряем память
                memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                optimized_stats['memory_usage'].append(memory_mb)

                logger.info(".2f"
            except Exception as e:
                logger.error(f"❌ Ошибка обработки файла {file_path.name}: {e}")
                optimized_stats['errors'] += 1

        optimized_stats['average_time'] = optimized_stats['total_time'] / max(optimized_stats['files_processed'], 1)

        self.performance_metrics['full_optimized'] = optimized_stats

        logger.info("⚡ Оптимизированный тест завершен"        logger.info(f"   📊 Обработано: {optimized_stats['files_processed']} файлов")
        logger.info(".2f"        logger.info(f"   💾 Кэш hits: {optimized_stats['cache_hits']:.1f}%")
        logger.info(f"   🧠 Memory оптимизаций: {optimized_stats['memory_optimizations']}")
        logger.info(f"   👥 Контактов найдено: {optimized_stats['contacts_found']}")

        return optimized_stats

    def run_cache_effectiveness_test(self, test_files: List[Path]) -> Dict[str, Any]:
        """
        💾 Тест эффективности кэширования

        Args:
            test_files: Список файлов для тестирования

        Returns:
            Dict со статистикой кэширования
        """
        logger.info("💾 Тест эффективности кэширования...")

        cache_stats = {
            'first_run_time': 0,
            'second_run_time': 0,
            'speedup_factor': 0,
            'cache_hit_rate': 0,
            'memory_saved_mb': 0
        }

        # Создаем экстрактор
        extractor = ExtractorFactory.create_extractor()

        # Первый прогон (заполняем кэш)
        logger.info("   🔄 Первый прогон (заполнение кэша)...")
        first_start = time.time()

        for file_path in test_files[:5]:
            email_data = self.load_email_data(file_path)
            if email_data:
                extractor.extract_all_data(email_data['text'], email_data['metadata'])

        cache_stats['first_run_time'] = time.time() - first_start

        # Второй прогон (используем кэш)
        logger.info("   🔄 Второй прогон (использование кэша)...")
        second_start = time.time()

        for file_path in test_files[:5]:
            email_data = self.load_email_data(file_path)
            if email_data:
                extractor.extract_all_data(email_data['text'], email_data['metadata'])

        cache_stats['second_run_time'] = time.time() - second_start

        # Вычисляем ускорение
        if cache_stats['second_run_time'] > 0:
            cache_stats['speedup_factor'] = cache_stats['first_run_time'] / cache_stats['second_run_time']

        # Получаем статистику кэша
        extractor_cache_stats = extractor.cache.get_cache_stats()
        cache_stats['cache_hit_rate'] = extractor_cache_stats.get('overall_hit_rate', 0)

        logger.info("💾 Тест кэширования завершен"        logger.info(".2f"        logger.info(".2f"        logger.info(".1f"        logger.info(".1f"
        return cache_stats

    def generate_report(self) -> Dict[str, Any]:
        """
        📊 Генерировать итоговый отчет по тестированию

        Returns:
            Dict с полным отчетом
        """
        report = {
            'test_date': self.test_date,
            'timestamp': time.time(),
            'phase6_performance_report': {
                'baseline_performance': self.performance_metrics.get('baseline', {}),
                'optimized_performance': self.performance_metrics.get('full_optimized', {}),
                'cache_effectiveness': {},
                'memory_optimization_stats': self.memory_optimizer.get_comprehensive_stats(),
                'overall_improvements': {}
            }
        }

        # Вычисляем улучшения
        baseline = report['phase6_performance_report']['baseline_performance']
        optimized = report['phase6_performance_report']['optimized_performance']

        if baseline and optimized:
            improvements = {
                'speed_improvement': (
                    baseline.get('average_time', 0) / max(optimized.get('average_time', 1), 0.01)
                    if optimized.get('average_time', 0) > 0 else 0
                ),
                'memory_efficiency': (
                    sum(baseline.get('memory_usage', [])) / len(baseline.get('memory_usage', [1]))
                    / (sum(optimized.get('memory_usage', [])) / len(optimized.get('memory_usage', [1])))
                    if optimized.get('memory_usage') else 0
                ),
                'error_reduction': (
                    (baseline.get('errors', 0) - optimized.get('errors', 0))
                    / max(baseline.get('errors', 1), 1) * 100
                )
            }
            report['phase6_performance_report']['overall_improvements'] = improvements

        logger.info("📊 Отчет по тестированию Фазы 6 сгенерирован")
        return report

    def run_complete_test_suite(self) -> Dict[str, Any]:
        """
        🚀 Запустить полный набор тестов Фазы 6

        Returns:
            Dict с результатами всех тестов
        """
        logger.info(f"🚀 Начинаем полный набор тестов Фазы 6 для даты {self.test_date}")

        try:
            # Находим тестовые файлы
            test_files = self.discover_test_files()

            # Тест 1: Базовая производительность
            baseline_results = self.run_baseline_test(test_files)

            # Небольшая пауза между тестами
            time.sleep(2)

            # Тест 2: Эффективность кэширования
            cache_results = self.run_cache_effectiveness_test(test_files)

            # Тест 3: Полные оптимизации
            optimized_results = self.run_optimized_test(test_files)

            # Генерируем отчет
            final_report = self.generate_report()
            final_report['cache_effectiveness'] = cache_results

            logger.info("✅ Полный набор тестов Фазы 6 завершен")

            # Выводим ключевые метрики
            print("\n" + "="*60)
            print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ФАЗЫ 6")
            print("="*60)

            baseline_avg = final_report['phase6_performance_report']['baseline_performance'].get('average_time', 0)
            optimized_avg = final_report['phase6_performance_report']['optimized_performance'].get('average_time', 0)

            if optimized_avg > 0:
                speedup = baseline_avg / optimized_avg
                print(".1f"            else:
                speedup = 0
                print("⚡ Скорость: Не удалось измерить (нет данных)")

            cache_hit_rate = final_report.get('cache_effectiveness', {}).get('cache_hit_rate', 0)
            print(".1f"
            cache_speedup = final_report.get('cache_effectiveness', {}).get('speedup_factor', 0)
            print(".1f"
            memory_opts = final_report['phase6_performance_report']['optimized_performance'].get('memory_optimizations', 0)
            print(f"🧠 Memory оптимизаций: {memory_opts}")

            print("="*60)

            return final_report

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в тестировании: {e}")
            return {'error': str(e)}


def main():
    """🏃 Основная функция для запуска тестирования"""
    print("🚀 ЗАПУСК ТЕСТИРОВАНИЯ ОПТИМИЗАЦИЙ ФАЗЫ 6")
    print("="*60)

    # Создаем тестер
    tester = Phase6PerformanceTester(test_date="2025-07-29")

    # Запускаем полный набор тестов
    results = tester.run_complete_test_suite()

    # Сохраняем результаты
    output_file = Path("phase6_test_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"💾 Результаты сохранены в {output_file}")

    return results


if __name__ == "__main__":
    main()
