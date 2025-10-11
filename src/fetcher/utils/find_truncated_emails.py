#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Скрипт для поиска обрезанных писем в базе данных
Ищет письма с пометкой "ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ" и создает отчеты
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
import argparse


class TruncatedEmailFinder:
    """🔍 Класс для поиска обрезанных писем"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.emails_dir = self.data_dir / "emails"
        self.reports_dir = self.data_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        
        # Статистика
        self.stats = {
            "total_emails": 0,
            "truncated_emails": 0,
            "truncated_by_date": defaultdict(int),
            "truncated_by_sender": defaultdict(int),
            "total_chars_saved": 0,
            "total_chars_original": 0,
        }
        
        # Список найденных писем
        self.truncated_emails = []
    
    def scan_emails_directory(self) -> None:
        """📂 Сканирование директории с письмами"""
        self.logger.info("🔍 Начинаем сканирование директории с письмами...")
        
        if not self.emails_dir.exists():
            self.logger.error(f"❌ Директория с письмами не найдена: {self.emails_dir}")
            return
        
        # Рекурсивно сканируем все поддиректории (даты)
        for date_dir in sorted(self.emails_dir.iterdir()):
            if not date_dir.is_dir():
                continue
                
            self.logger.info(f"📅 Сканируем директорию: {date_dir.name}")
            self._scan_date_directory(date_dir)
        
        self.logger.info(f"✅ Сканирование завершено. Всего писем: {self.stats['total_emails']}")
    
    def _scan_date_directory(self, date_dir: Path) -> None:
        """📅 Сканирование директории за конкретную дату"""
        json_files = list(date_dir.glob("*.json"))
        
        for json_file in json_files:
            try:
                self._process_email_file(json_file, date_dir.name)
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка обработки файла {json_file}: {e}")
    
    def _process_email_file(self, json_file: Path, date_folder: str) -> None:
        """📧 Обработка одного файла с письмом"""
        self.stats["total_emails"] += 1
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.warning(f"⚠️ Ошибка парсинга JSON в файле {json_file}: {e}")
            return
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка чтения файла {json_file}: {e}")
            return
        
        # Проверяем наличие текста и признаков обрезки
        body_text = email_data.get('body', '')
        from_addr = email_data.get('from', 'unknown')
        subject = email_data.get('subject', 'no subject')
        char_count = email_data.get('char_count', 0)
        
        # Ищем признаки обрезки
        is_truncated = self._check_if_truncated(body_text)
        
        if is_truncated:
            self.stats["truncated_emails"] += 1
            self.stats["truncated_by_date"][date_folder] += 1
            self.stats["truncated_by_sender"][from_addr] += 1
            
            # Сохраняем информацию об обрезанном письме
            truncated_info = {
                "file_path": str(json_file.relative_to(self.data_dir)),
                "date_folder": date_folder,
                "message_id": email_data.get('message_id', ''),
                "from": from_addr,
                "subject": subject,
                "char_count": char_count,
                "truncation_marker": self._find_truncation_marker(body_text),
            }
            
            self.truncated_emails.append(truncated_info)
            
            # Оцениваем сохраненные символы (примерная оценка)
            if char_count < 10000:  # Типичный признак обрезки
                estimated_original = min(80000, char_count * 8)  # Примерная оценка
                self.stats["total_chars_saved"] += estimated_original - char_count
                self.stats["total_chars_original"] += estimated_original
    
    def _check_if_truncated(self, text: str) -> bool:
        """🔍 Проверка, обрезан ли текст"""
        truncation_markers = [
            "ТЕКСТ ОБРЕЗАН ДЛЯ ЭКОНОМИИ ТОКЕНОВ",
            "ТЕКСТ ОБРЕЗАН ДО",
            "TEXT TRUNCATED",
            "[ТЕКСТ ОБРЕЗАН",
            "обрезан для экономии",
        ]
        
        text_upper = text.upper()
        return any(marker in text_upper for marker in truncation_markers)
    
    def _find_truncation_marker(self, text: str) -> str:
        """🏷️ Поиск конкретного маркера обрезки"""
        lines = text.split('\n')
        for line in lines:
            if any(marker in line.upper() for marker in [
                "ТЕКСТ ОБРЕЗАН", "TEXT TRUNCATED", "обрезан для"
            ]):
                return line.strip()
        return "Маркер не найден"
    
    def generate_markdown_report(self) -> str:
        """📝 Генерация Markdown отчета"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Отчет по обрезанным письмам

**Дата создания**: {timestamp}  
**Всего писем**: {self.stats['total_emails']}  
**Обрезанных писем**: {self.stats['truncated_emails']}  
**Процент обрезанных**: {self.stats['truncated_emails']/max(self.stats['total_emails'],1)*100:.1f}%

## 📊 Статистика по датам

| Дата | Количество обрезанных |
|------|---------------------|
"""
        
        # Сортируем даты
        for date in sorted(self.stats["truncated_by_date"].keys()):
            count = self.stats["truncated_by_date"][date]
            report += f"| {date} | {count} |\n"
        
        report += "\n## 📧 Статистика по отправителям\n\n"
        report += "| Отправитель | Количество обрезанных |\n"
        report += "|-------------|---------------------|\n"
        
        # Топ-10 отправителей
        top_senders = sorted(
            self.stats["truncated_by_sender"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        for sender, count in top_senders:
            # Обрезаем длинные email для отображения
            display_sender = sender[:50] + "..." if len(sender) > 50 else sender
            report += f"| {display_sender} | {count} |\n"
        
        report += f"\n## 💾 Оценка сохраненных данных\n\n"
        report += f"- **Сохранено символов**: {self.stats['total_chars_saved']:,}\n"
        report += f"- **Оригинальный размер**: {self.stats['total_chars_original']:,}\n"
        report += f"- **Экономия**: {self.stats['total_chars_saved']/max(self.stats['total_chars_original'],1)*100:.1f}%\n"
        
        if self.stats['total_chars_saved'] > 0:
            # Примерная экономия в токенах (1 токен ~ 4 символа)
            tokens_saved = self.stats['total_chars_saved'] // 4
            report += f"- **Примерная экономия токенов**: {tokens_saved:,}\n"
        
        report += "\n## 📋 Список обрезанных писем\n\n"
        
        for i, email_info in enumerate(self.truncated_emails[:20], 1):  # Первые 20
            report += f"### {i}. {email_info['subject'][:80]}...\n"
            report += f"- **Файл**: `{email_info['file_path']}`\n"
            report += f"- **Дата**: {email_info['date_folder']}\n"
            report += f"- **Отправитель**: {email_info['from']}\n"
            report += f"- **Размер**: {email_info['char_count']:,} символов\n"
            report += f"- **Маркер обрезки**: `{email_info['truncation_marker']}`\n\n"
        
        if len(self.truncated_emails) > 20:
            report += f"... и еще {len(self.truncated_emails) - 20} писем\n\n"
        
        return report
    
    def generate_json_report(self) -> Dict:
        """📄 Генерация JSON отчета"""
        return {
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_emails": self.stats["total_emails"],
                "truncated_emails": self.stats["truncated_emails"],
                "truncation_percentage": self.stats["truncated_emails"]/max(self.stats["total_emails"],1)*100,
                "total_chars_saved": self.stats["total_chars_saved"],
                "total_chars_original": self.stats["total_chars_original"],
                "estimated_tokens_saved": self.stats["total_chars_saved"] // 4,
            },
            "by_date": dict(self.stats["truncated_by_date"]),
            "by_sender": dict(self.stats["truncated_by_sender"]),
            "truncated_emails": self.truncated_emails,
        }
    
    def save_reports(self, prefix: str = "truncated_emails") -> Tuple[str, str]:
        """💾 Сохранение отчетов"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Markdown отчет
        md_filename = f"{prefix}_{timestamp}.md"
        md_path = self.reports_dir / md_filename
        
        md_content = self.generate_markdown_report()
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # JSON отчет
        json_filename = f"{prefix}_{timestamp}.json"
        json_path = self.reports_dir / json_filename
        
        json_content = self.generate_json_report()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📝 Отчеты сохранены:")
        self.logger.info(f"   Markdown: {md_path}")
        self.logger.info(f"   JSON: {json_path}")
        
        return str(md_path), str(json_path)
    
    def print_summary(self):
        """📊 Вывод сводной информации"""
        print("\n" + "="*70)
        print("🔍 СВОДКА ПО ОБРЕЗАННЫМ ПИСЬМАМ")
        print("="*70)
        print(f"📧 Всего писем: {self.stats['total_emails']:,}")
        print(f"✂️ Обрезанных писем: {self.stats['truncated_emails']:,}")
        print(f"📊 Процент обрезанных: {self.stats['truncated_emails']/max(self.stats['total_emails'],1)*100:.1f}%")
        
        if self.stats['truncated_emails'] > 0:
            print(f"📅 Период: {min(self.stats['truncated_by_date'].keys())} - {max(self.stats['truncated_by_date'].keys())}")
            print(f"💾 Оценка сохраненных символов: {self.stats['total_chars_saved']:,}")
            print(f"🪙 Оценка сэкономленных токенов: {self.stats['total_chars_saved']//4:,}")
            print(f"📧 Топ отправителей:")
            
            top_senders = sorted(
                self.stats["truncated_by_sender"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            for sender, count in top_senders:
                display_sender = sender[:40] + "..." if len(sender) > 40 else sender
                print(f"   - {display_sender}: {count} писем")
        
        print("="*70)


def main():
    """🚀 Главная функция"""
    parser = argparse.ArgumentParser(description="Поиск обрезанных писем")
    parser.add_argument(
        "--data-dir", 
        default="data", 
        help="Директория с данными (по умолчанию: data)"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Детальное логирование"
    )
    parser.add_argument(
        "--output-prefix", 
        default="truncated_emails", 
        help="Префикс для файлов отчетов"
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 ЗАПУСК ПОИСКА ОБРЕЗАННЫХ ПИСЕМ")
    logger.info(f"📁 Директория с данными: {args.data_dir}")
    
    # Создаем и запускаем поиск
    finder = TruncatedEmailFinder(args.data_dir)
    finder.scan_emails_directory()
    
    # Выводим сводку
    finder.print_summary()
    
    # Сохраняем отчеты
    if finder.stats["truncated_emails"] > 0:
        md_path, json_path = finder.save_reports(args.output_prefix)
        logger.info(f"✅ Отчеты сохранены в {finder.reports_dir}")
        
        # Дополнительная информация
        print(f"\n📄 Детальный отчет: {md_path}")
        print(f"📊 Данные для анализа: {json_path}")
    else:
        logger.info("✅ Обрезанных писем не найдено!")


if __name__ == "__main__":
    main()