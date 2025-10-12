#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Скрипт для тестирования интеграции PreCleaner с новым Email Fetcher.

Загружает письма с использованием LegacyEmailFetcherV2 с активным PreCleaner,
сравнивает результаты до и после очистки, сохраняет статистику.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PreCleanerTester:
    """🧪 Тестировщик интеграции PreCleaner"""
    
    def __init__(self):
        self.results = {
            'emails_processed': 0,
            'total_original_length': 0,
            'total_cleaned_length': 0,
            'total_tokens_saved': 0,
            'reduction_percentage': 0,
            'emails_with_signatures': 0,
            'emails_with_quotes': 0,
            'emails_with_disclaimers': 0,
            'processing_errors': 0,
            'samples': []
        }
        
    def test_precleaner_integration(self, test_days: int = 1) -> Dict:
        """
        🧪 Тестирует интеграцию PreCleaner
        
        Args:
            test_days: Количество дней для теста
            
        Returns:
            Результаты тестирования
        """
        logger.info(f"🧪 Начинаем тестирование PreCleaner за последние {test_days} дней...")
        
        try:
            from src.fetcher import LegacyEmailFetcherV2
            
            # Создаем экземпляр LegacyEmailFetcherV2
            fetcher = LegacyEmailFetcherV2(logger)
            
            # Подключаемся к серверу
            if not fetcher.connect():
                logger.error("❌ Не удалось подключиться к серверу")
                return self.results
            
            try:
                # Определяем период для теста
                end_date = datetime.now()
                start_date = end_date - timedelta(days=test_days)
                
                logger.info(f"📅 Период теста: {start_date.date()} - {end_date.date()}")
                
                # Загружаем письма
                emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
                
                logger.info(f"✅ Загружено {len(emails)} писем для тестирования")
                
                # Обрабатываем каждое письмо
                for i, email in enumerate(emails):
                    self._process_email(email, i)
                
                # Рассчитываем итоговую статистику
                self._calculate_final_stats()
                
                # Сохраняем статистику PreCleaner
                if hasattr(fetcher, 'text_cleaner') and hasattr(fetcher.text_cleaner, 'get_processing_stats'):
                    precleaner_stats = fetcher.text_cleaner.get_processing_stats()
                    self._save_precleaner_stats(precleaner_stats)
                
            finally:
                fetcher.close()
                
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта модулей: {e}")
            self.results['processing_errors'] += 1
        except Exception as e:
            logger.error(f"❌ Ошибка при тестировании: {e}")
            self.results['processing_errors'] += 1
        
        return self.results
    
    def _process_email(self, email: Dict, index: int):
        """📧 Обрабатывает одно письмо"""
        try:
            self.results['emails_processed'] += 1
            
            # Получаем исходный и очищенный текст
            original_text = email.get('body_raw', '')
            cleaned_text = email.get('body_clean', '')
            
            if not original_text:
                return
            
            original_length = len(original_text)
            cleaned_length = len(cleaned_text)
            
            self.results['total_original_length'] += original_length
            self.results['total_cleaned_length'] += cleaned_length
            
            # Рассчитываем экономию токенов
            tokens_saved = (original_length - cleaned_length) // 4
            self.results['total_tokens_saved'] += tokens_saved
            
            # Анализируем содержимое для определения типов блоков
            self._analyze_email_content(email)
            
            # Сохраняем образцы для анализа
            if index < 5:  # Первые 5 писем как образцы
                self.results['samples'].append({
                    'index': index,
                    'message_id': email.get('message_id', ''),
                    'subject': email.get('subject', ''),
                    'from': email.get('from', ''),
                    'original_length': original_length,
                    'cleaned_length': cleaned_length,
                    'reduction': original_length - cleaned_length,
                    'reduction_percentage': (original_length - cleaned_length) / original_length * 100 if original_length > 0 else 0,
                    'tokens_saved': tokens_saved
                })
            
            logger.debug(f"📧 Обработано письмо {index + 1}: {original_length} → {cleaned_length} символов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки письма: {e}")
            self.results['processing_errors'] += 1
    
    def _analyze_email_content(self, email: Dict):
        """🔍 Анализирует содержимое письма"""
        body = email.get('body_raw', '').lower()
        
        # Проверяем наличие подписей
        sig_markers = ['--', '—', 'с уважением', 'best regards', 'kind regards', 'regards']
        if any(marker in body for marker in sig_markers):
            self.results['emails_with_signatures'] += 1
        
        # Проверяем наличие цитат
        if '>' in body or 'wrote:' in body:
            self.results['emails_with_quotes'] += 1
        
        # Проверяем наличие дисклеймеров
        disclaimer_markers = ['confidentiality', 'настоящее сообщение', 'unsubscribe', 'privacy policy']
        if any(marker in body for marker in disclaimer_markers):
            self.results['emails_with_disclaimers'] += 1
    
    def _calculate_final_stats(self):
        """📊 Рассчитывает итоговую статистику"""
        if self.results['total_original_length'] > 0:
            self.results['reduction_percentage'] = (
                (self.results['total_original_length'] - self.results['total_cleaned_length']) 
                / self.results['total_original_length'] * 100
            )
    
    def _save_precleaner_stats(self, precleaner_stats: Dict):
        """💾 Сохраняет статистику PreCleaner"""
        try:
            stats_dir = Path("data/logs/precleaner")
            stats_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stats_file = stats_dir / f"test_stats_{timestamp}.json"
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'test_results': self.results,
                    'precleaner_stats': precleaner_stats
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 Статистика PreCleaner сохранена: {stats_file}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статистики: {e}")
    
    def print_results(self):
        """📋 Выводит результаты тестирования"""
        print("\n" + "="*70)
        print("🧪 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ PRECLEANER")
        print("="*70)
        print(f"📧 Обработано писем: {self.results['emails_processed']:,}")
        print(f"📏 Общая длина (оригинал): {self.results['total_original_length']:,} символов")
        print(f"📏 Общая длина (очищено): {self.results['total_cleaned_length']:,} символов")
        print(f"📉 Сокращение текста: {self.results['reduction_percentage']:.1f}%")
        print(f"🪙 Сэкономлено токенов: {self.results['total_tokens_saved']:,}")
        print(f"✉️ Писем с подписями: {self.results['emails_with_signatures']:,}")
        print(f"💬 Писем с цитатами: {self.results['emails_with_quotes']:,}")
        print(f"📄 Писем с дисклеймерами: {self.results['emails_with_disclaimers']:,}")
        print(f"❌ Ошибок обработки: {self.results['processing_errors']:,}")
        
        if self.results['samples']:
            print(f"\n📋 Образцы обработки:")
            print("| № | Тема | Отправитель | Длина | Сокращение | %")
            print("|---|------|------------|-------|------------|---|")
            
            for sample in self.results['samples']:
                subject = sample['subject'][:30] + "..." if len(sample['subject']) > 30 else sample['subject']
                sender = sample['from'].split('@')[0] if '@' in sample['from'] else sample['from'][:20]
                
                print(f"| {sample['index']+1} | {subject} | {sender} | {sample['original_length']:,} | {sample['reduction']:,} | {sample['reduction_percentage']:.1f}% |")
        
        print("="*70)
        
        # Рекомендации
        print("\n💡 РЕКОМЕНДАЦИИ:")
        if self.results['reduction_percentage'] < 20:
            print("⚠️ Низкое сокращение текста. Рассмотрите более агрессивные настройки PreCleaner.")
        elif self.results['reduction_percentage'] > 50:
            print("✅ Отличное сокращение текста! PreCleaner работает эффективно.")
        else:
            print("✅ Хорошее сокращение текста. PreCleaner работает корректно.")
        
        if self.results['emails_with_quotes'] > self.results['emails_processed'] * 0.5:
            print("💬 Много писем с цитатами. Убедитесь, что они корректно обрабатываются.")
        
        if self.results['processing_errors'] > 0:
            print("❌ Есть ошибки обработки. Проверьте логи для детализации.")
    
    def generate_report(self, output_dir: str = "data/reports") -> str:
        """
        📊 Генерирует отчет о тестировании
        
        Args:
            output_dir: Директория для сохранения отчета
            
        Returns:
            Путь к сохраненному отчету
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f"precleaner_test_report_{timestamp}.md")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 🧪 Отчет о тестировании PreCleaner\n\n")
            f.write(f"**Дата теста:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Общая статистика
            f.write("## 📊 Общая статистика\n\n")
            f.write(f"- **Обработано писем:** {self.results['emails_processed']:,}\n")
            f.write(f"- **Общая длина (оригинал):** {self.results['total_original_length']:,} символов\n")
            f.write(f"- **Общая длина (очищено):** {self.results['total_cleaned_length']:,} символов\n")
            f.write(f"- **Сокращение текста:** {self.results['reduction_percentage']:.1f}%\n")
            f.write(f"- **Сэкономлено токенов:** {self.results['total_tokens_saved']:,}\n")
            f.write(f"- **Ошибки обработки:** {self.results['processing_errors']:,}\n\n")
            
            # Статистика по типам контента
            f.write("## 📈 Статистика по типам контента\n\n")
            f.write(f"- **Писем с подписями:** {self.results['emails_with_signatures']:,} ({self.results['emails_with_signatures']/max(1, self.results['emails_processed'])*100:.1f}%)\n")
            f.write(f"- **Писем с цитатами:** {self.results['emails_with_quotes']:,} ({self.results['emails_with_quotes']/max(1, self.results['emails_processed'])*100:.1f}%)\n")
            f.write(f"- **Писем с дисклеймерами:** {self.results['emails_with_disclaimers']:,} ({self.results['emails_with_disclaimers']/max(1, self.results['emails_processed'])*100:.1f}%)\n\n")
            
            # Образцы
            if self.results['samples']:
                f.write("## 📋 Образцы обработки\n\n")
                f.write("| № | Тема | Отправитель | Длина | Сокращение | % |\n")
                f.write("|---|------|------------|-------|------------|---|\n")
                
                for sample in self.results['samples']:
                    subject = sample['subject'][:30] + "..." if len(sample['subject']) > 30 else sample['subject']
                    sender = sample['from'].split('@')[0] if '@' in sample['from'] else sample['from'][:20]
                    
                    f.write(f"| {sample['index']+1} | {subject} | {sender} | {sample['original_length']:,} | {sample['reduction']:,} | {sample['reduction_percentage']:.1f}% |\n")
                f.write("\n")
            
            # Рекомендации
            f.write("## 💡 Рекомендации\n\n")
            if self.results['reduction_percentage'] < 20:
                f.write("⚠️ **Низкое сокращение текста.** Рассмотрите более агрессивные настройки PreCleaner:\n")
                f.write("- Увеличьте `max_signature_lines`\n")
                f.write("- Уменьшите `fold_quote_over_chars`\n")
                f.write("- Добавьте дополнительные маркеры в `sig_markers` и `disclaimer_markers`\n\n")
            elif self.results['reduction_percentage'] > 50:
                f.write("✅ **Отличное сокращение текста!** PreCleaner работает эффективно.\n\n")
            else:
                f.write("✅ **Хорошее сокращение текста.** PreCleaner работает корректно.\n\n")
            
            if self.results['emails_with_quotes'] > self.results['emails_processed'] * 0.5:
                f.write("💬 **Много писем с цитатами.** Убедитесь, что они корректно обрабатываются.\n\n")
            
            if self.results['processing_errors'] > 0:
                f.write("❌ **Есть ошибки обработки.** Проверьте логи для детализации.\n\n")
        
        logger.info(f"📊 Отчет о тестировании сохранен: {report_path}")
        return report_path


def main():
    """🚀 Основная функция"""
    logger.info("🚀 Запускаем тестирование интеграции PreCleaner...")
    
    # Создаем тестировщик
    tester = PreCleanerTester()
    
    # Проводим тестирование
    results = tester.test_precleaner_integration(test_days=1)
    
    # Выводим результаты
    tester.print_results()
    
    # Генерируем отчет
    report_path = tester.generate_report()
    
    logger.info("✅ Тестирование завершено!")
    logger.info(f"📊 Отчет сохранен: {report_path}")


if __name__ == "__main__":
    main()