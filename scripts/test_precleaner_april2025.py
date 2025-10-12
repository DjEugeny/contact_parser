#!/usr/bin/env python3
"""
Тестирование PreCleaner на периоде 1-15 апреля 2025

Скрипт загружает письма за указанный период с активным PreCleaner,
анализирует эффективность очистки и обеспечивает совместимость по полю body.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PreCleanerTester:
    """Тестировщик PreCleaner"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.results = {
            'total_emails': 0,
            'original_length': 0,
            'cleaned_length': 0,
            'signatures_removed': 0,
            'disclaimers_removed': 0,
            'quotes_removed': 0,
            'tokens_saved': 0,
            'processing_time': 0,
            'samples': []
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Настройка логгера"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def test_precleaner_integration(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Тестирует интеграцию PreCleaner с LegacyEmailFetcherV2
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Результаты тестирования
        """
        self.logger.info(f"🧪 Тестирование PreCleaner за период {start_date.date()} - {end_date.date()}")
        
        try:
            # Импортируем LegacyEmailFetcherV2
            from src.fetcher import LegacyEmailFetcherV2
            
            # Создаем экземпляр
            fetcher = LegacyEmailFetcherV2(self.logger)
            
            if not fetcher.connect():
                self.logger.error("❌ Не удалось подключиться к IMAP")
                return self.results
            
            # Загружаем письма
            self.logger.info("📥 Загрузка писем...")
            emails = fetcher.fetch_emails_by_date_range(start_date, end_date)
            
            self.results['total_emails'] = len(emails)
            self.logger.info(f"✅ Загружено {len(emails)} писем")
            
            if not emails:
                self.logger.warning("⚠️ Письма не найдены за указанный период")
                return self.results
            
            # Анализируем каждое письмо
            for i, email in enumerate(emails[:10]):  # Ограничиваем первыми 10 для теста
                self._analyze_email(email, i)
            
            # Закрываем соединение
            fetcher.close()
            
            # Генерируем отчет
            self._generate_report()
            
            return self.results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при тестировании: {e}")
            return self.results
    
    def _analyze_email(self, email: Dict, index: int) -> None:
        """
        Анализирует одно письмо
        
        Args:
            email: Данные письма
            index: Индекс письма
        """
        try:
            # Получаем разные версии текста
            body_raw = email.get('body_raw', '')
            body_clean = email.get('body_clean', '')
            
            # Проверяем наличие поля body для совместимости
            body = email.get('body', '')
            
            if not body and body_clean:
                # Если поля body нет, но есть body_clean, используем его
                body = body_clean
                email['body'] = body_clean  # Обеспечиваем совместимость
            
            # Анализируем длины
            original_len = len(body_raw)
            cleaned_len = len(body_clean)
            
            self.results['original_length'] += original_len
            self.results['cleaned_length'] += cleaned_len
            
            # Сохраняем образцы для анализа
            if index < 3:  # Первые 3 письма как образцы
                self.results['samples'].append({
                    'index': index,
                    'subject': email.get('subject', ''),
                    'from': email.get('from', ''),
                    'original_length': original_len,
                    'cleaned_length': cleaned_len,
                    'reduction_percent': ((original_len - cleaned_len) / original_len * 100) if original_len > 0 else 0,
                    'has_body': bool(email.get('body')),
                    'body_equals_clean': body == body_clean
                })
            
            # Логируем прогресс
            if index < 5:
                reduction = ((original_len - cleaned_len) / original_len * 100) if original_len > 0 else 0
                self.logger.info(f"📧 Письмо {index+1}: {original_len} → {cleaned_len} символов ({reduction:.1f}% сокращение)")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при анализе письма {index}: {e}")
    
    def _generate_report(self) -> None:
        """Генерирует отчет о тестировании"""
        self.logger.info("📊 Генерация отчета...")
        
        # Создаем директорию для отчетов
        report_dir = Path(".kiro/specs/precleaner")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = report_dir / f"precleaner_test_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Отчет о тестировании PreCleaner\n\n")
            f.write(f"**Дата тестирования**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Период**: 1-15 апреля 2025\n\n")
            
            # Общая статистика
            f.write("## 📊 Общая статистика\n\n")
            f.write(f"- **Всего писем**: {self.results['total_emails']}\n")
            
            if self.results['total_emails'] > 0:
                avg_original = self.results['original_length'] // self.results['total_emails']
                avg_cleaned = self.results['cleaned_length'] // self.results['total_emails']
                avg_reduction = ((self.results['original_length'] - self.results['cleaned_length']) / self.results['original_length'] * 100) if self.results['original_length'] > 0 else 0
                
                f.write(f"- **Средняя длина (оригинал)**: {avg_original:,} символов\n")
                f.write(f"- **Средняя длина (очищенный)**: {avg_cleaned:,} символов\n")
                f.write(f"- **Среднее сокращение**: {avg_reduction:.1f}%\n")
                f.write(f"- **Всего сэкономлено символов**: {self.results['original_length'] - self.results['cleaned_length']:,}\n")
            
            # Образцы писем
            f.write("\n## 📧 Образцы писем\n\n")
            f.write("| № | Тема | Отправитель | Оригинал | Очищено | Сокращение | Есть body | body == clean |\n")
            f.write("|---|------|------------|----------|---------|-----------|----------|--------------|\n")
            
            for sample in self.results['samples']:
                f.write(f"| {sample['index']+1} | {sample['subject'][:50]}... | {sample['from'][:30]}... | ")
                f.write(f"{sample['original_length']:,} | {sample['cleaned_length']:,} | ")
                f.write(f"{sample['reduction_percent']:.1f}% | {'✅' if sample['has_body'] else '❌'} | {'✅' if sample['body_equals_clean'] else '❌'} |\n")
            
            # Совместимость
            f.write("\n## 🔧 Совместимость\n\n")
            all_have_body = all(sample['has_body'] for sample in self.results['samples'])
            all_body_equals_clean = all(sample['body_equals_clean'] for sample in self.results['samples'])
            
            f.write(f"- **Наличие поля body у всех писем**: {'✅' if all_have_body else '❌'}\n")
            f.write(f"- **Совпадение body с body_clean**: {'✅' if all_body_equals_clean else '❌'}\n")
            
            if not all_have_body:
                f.write("⚠️ **Внимание**: Некоторые письма не имеют поля body - это может вызвать проблемы совместимости!\n")
            
            # Рекомендации
            f.write("\n## 💡 Рекомендации\n\n")
            
            if avg_reduction > 20:
                f.write("✅ **Отличное сокращение**: PreCleaner эффективно сокращает тексты\n")
            elif avg_reduction > 10:
                f.write("⚠️ **Хорошее сокращение**: PreCleaner работает, но можно оптимизировать\n")
            else:
                f.write("❌ **Низкое сокращение**: PreCleaner неэффективен, нужна настройка\n")
            
            if not all_have_body:
                f.write("🔧 **Критично**: Обеспечить наличие поля body для совместимости\n")
            
            f.write("\n## 🎯 Следующие шаги\n\n")
            f.write("1. Проверить совместимость с существующими модулями\n")
            f.write("2. При необходимости добавить поле body в процесс сохранения\n")
            f.write("3. Провести тестирование на большем объеме данных\n")
            f.write("4. Оптимизировать параметры PreCleaner при необходимости\n")
        
        self.logger.info(f"✅ Отчет сохранен: {report_path}")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Тестирование PreCleaner')
    parser.add_argument('--start-date', default='2025-04-01', help='Начальная дата (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2025-04-15', help='Конечная дата (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Парсим даты
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError as e:
        print(f"❌ Ошибка формата даты: {e}")
        return
    
    # Создаем тестировщик
    tester = PreCleanerTester()
    
    # Проводим тестирование
    results = tester.test_precleaner_integration(start_date, end_date)
    
    # Выводим итоги
    print("\n" + "="*50)
    print("🎉 Тестирование завершено!")
    print("="*50)
    print(f"📊 Обработано писем: {results['total_emails']}")
    
    if results['total_emails'] > 0:
        total_reduction = ((results['original_length'] - results['cleaned_length']) / results['original_length'] * 100) if results['original_length'] > 0 else 0
        print(f"📉 Общее сокращение: {total_reduction:.1f}%")
        print(f"💾 Экономия символов: {results['original_length'] - results['cleaned_length']:,}")
    
    print("📄 Подробный отчет сохранен в .kiro/specs/precleaner/")


if __name__ == '__main__':
    main()