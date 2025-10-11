#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 CLI утилита для миграции обрезанных писем
Позволяет находить, просматривать и удалять обрезанные письма с бэкапом
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse
import sys

from find_truncated_emails import TruncatedEmailFinder


class TruncatedEmailMigrator:
    """🔄 Класс для миграции обрезанных писем"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.emails_dir = self.data_dir / "emails"
        self.backups_dir = self.data_dir / "backups"
        self.reports_dir = self.data_dir / "reports"
        
        # Создаем директории
        self.backups_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        
        # Текущие результаты поиска
        self.current_finder = None
        self.truncated_files = []
    
    def show_menu(self):
        """📋 Показать главное меню"""
        print("\n" + "="*70)
        print("🔄 УТИЛИТА МИГРАЦИИ ОБРЕЗАННЫХ ПИСЕМ")
        print("="*70)
        print("1. 🔍 Найти все обрезанные письма и создать отчет")
        print("2. 📋 Показать результаты последнего поиска")
        print("3. 🗑️ Удалить все обрезанные письма (с бэкапом)")
        print("4. 💾 Создать бэкап папки emails")
        print("5. 📊 Показать статистику по текущим данным")
        print("0. 🚪 Выход")
        print("-"*70)
    
    def find_truncated_emails(self):
        """🔍 Найти обрезанные письма"""
        print("\n🔍 ПОИСК ОБРЕЗАННЫХ ПИСЕМ")
        print("-"*40)
        
        # Создаем и запускаем поиск
        self.current_finder = TruncatedEmailFinder(str(self.data_dir))
        self.current_finder.scan_emails_directory()
        
        # Сохраняем список файлов для удаления
        self.truncated_files = [
            Path(self.data_dir) / email_info["file_path"] 
            for email_info in self.current_finder.truncated_emails
        ]
        
        # Выводим результаты
        self.current_finder.print_summary()
        
        if self.current_finder.stats["truncated_emails"] > 0:
            # Сохраняем отчеты
            md_path, json_path = self.current_finder.save_reports("migration_scan")
            print(f"\n📄 Отчеты сохранены:")
            print(f"   Markdown: {md_path}")
            print(f"   JSON: {json_path}")
            
            # Спрашиваем о просмотре деталей
            choice = input("\n🔍 Показать детали обрезанных писем? (д/н): ").lower().strip()
            if choice in ['д', 'да', 'y', 'yes']:
                self.show_truncated_details()
        else:
            print("\n✅ Обрезанных писем не найдено!")
    
    def show_truncated_details(self):
        """📋 Показать детали обрезанных писем"""
        if not self.current_finder or not self.current_finder.truncated_emails:
            print("\n❌ Сначала выполните поиск обрезанных писем (пункт 1)")
            return
        
        print(f"\n📋 ДЕТАЛИ ОБРЕЗАННЫХ ПИСЕМ ({len(self.current_finder.truncated_emails)} шт.)")
        print("="*70)
        
        for i, email_info in enumerate(self.current_finder.truncated_emails, 1):
            print(f"\n{i}. {email_info['subject'][:80]}...")
            print(f"   📁 Файл: {email_info['file_path']}")
            print(f"   📅 Дата: {email_info['date_folder']}")
            print(f"   📧 От: {email_info['from']}")
            print(f"   📏 Размер: {email_info['char_count']:,} символов")
            print(f"   ✂️ Маркер: {email_info['truncation_marker']}")
        
        print("\n" + "="*70)
    
    def create_backup(self):
        """💾 Создать бэкап папки emails"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"emails_backup_{timestamp}"
        backup_path = self.backups_dir / backup_name
        
        print(f"\n💾 СОЗДАНИЕ БЭКАПА")
        print(f"📁 Исходная папка: {self.emails_dir}")
        print(f"📁 Папка бэкапа: {backup_path}")
        
        if not self.emails_dir.exists():
            print(f"❌ Папка {self.emails_dir} не существует!")
            return False
        
        try:
            # Создаем бэкап
            shutil.copytree(self.emails_dir, backup_path)
            
            # Проверяем размер
            original_size = self._get_dir_size(self.emails_dir)
            backup_size = self._get_dir_size(backup_path)
            
            print(f"✅ Бэкап успешно создан!")
            print(f"   📊 Размер оригинала: {original_size / (1024**2):.1f} МБ")
            print(f"   📊 Размер бэкапа: {backup_size / (1024**2):.1f} МБ")
            
            if original_size == backup_size:
                print(f"✅ Размеры совпадают - бэкап корректен!")
            else:
                print(f"⚠️ Внимание: размеры не совпадают!")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания бэкапа: {e}")
            return False
    
    def delete_truncated_emails(self):
        """🗑️ Удалить обрезанные письма"""
        if not self.truncated_files:
            print("\n❌ Сначала выполните поиск обрезанных писем (пункт 1)")
            return
        
        print(f"\n🗑️ УДАЛЕНИЕ ОБРЕЗАННЫХ ПИСЕМ")
        print(f"📁 Найдено файлов для удаления: {len(self.truncated_files)}")
        print("-"*50)
        
        # Показываем примеры файлов
        print("📋 Примеры файлов для удаления:")
        for i, file_path in enumerate(self.truncated_files[:5], 1):
            print(f"   {i}. {file_path.relative_to(self.data_dir)}")
        
        if len(self.truncated_files) > 5:
            print(f"   ... и еще {len(self.truncated_files) - 5} файлов")
        
        print("-"*50)
        
        # Предупреждение
        print("⚠️ ВНИМАНИЕ: ЭТА ОПЕРАЦИЯ НЕОБРАТИМА!")
        print("⚠️ Все обрезанные письма будут безвозвратно удалены!")
        print("💡 Убедитесь, что у вас есть бэкап (пункт 4)")
        
        # Подтверждение
        confirm = input("\n❓ Вы уверены, что хотите удалить эти файлы? (введите 'ДА' для подтверждения): ").strip()
        
        if confirm != "ДА":
            print("❌ Операция отменена")
            return
        
        # Создаем бэкап перед удалением
        print("\n💾 Создаем бэкап перед удалением...")
        if not self.create_backup():
            print("❌ Не удалось создать бэкап, операция отменена")
            return
        
        # Удаляем файлы
        deleted_count = 0
        error_count = 0
        
        print(f"\n🗑️ Удаляем файлы...")
        for i, file_path in enumerate(self.truncated_files, 1):
            try:
                if file_path.exists():
                    file_path.unlink()
                    deleted_count += 1
                    print(f"   ✅ ({i}/{len(self.truncated_files)}) Удален: {file_path.name}")
                else:
                    print(f"   ⚠️ ({i}/{len(self.truncated_files)}) Файл не найден: {file_path}")
            except Exception as e:
                error_count += 1
                print(f"   ❌ ({i}/{len(self.truncated_files)}) Ошибка удаления {file_path}: {e}")
        
        print(f"\n📊 РЕЗУЛЬТАТЫ УДАЛЕНИЯ:")
        print(f"   ✅ Удалено файлов: {deleted_count}")
        print(f"   ❌ Ошибок: {error_count}")
        print(f"   📁 Всего файлов: {len(self.truncated_files)}")
        
        if error_count == 0:
            print(f"\n✅ Все обрезанные письма успешно удалены!")
            print(f"💡 Теперь можно перезагрузить письма с полным текстом")
        else:
            print(f"\n⚠️ При удалении возникли ошибки. Проверьте логи.")
        
        # Сохраняем отчет об удалении
        self._save_deletion_report(deleted_count, error_count)
        
        # Сбрасываем результаты
        self.truncated_files = []
        self.current_finder = None
    
    def show_statistics(self):
        """📊 Показать статистику по текущим данным"""
        print(f"\n📊 СТАТИСТИКА ПО ТЕКУЩИМ ДАННЫМ")
        print("-"*50)
        
        if not self.emails_dir.exists():
            print(f"❌ Папка {self.emails_dir} не существует!")
            return
        
        # Общая статистика
        total_files = 0
        total_size = 0
        by_date = {}
        
        for date_dir in sorted(self.emails_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            
            date_files = list(date_dir.glob("*.json"))
            date_count = len(date_files)
            date_size = sum(f.stat().st_size for f in date_files)
            
            total_files += date_count
            total_size += date_size
            by_date[date_dir.name] = {"count": date_count, "size": date_size}
        
        print(f"📁 Папка: {self.emails_dir}")
        print(f"📧 Всего писем: {total_files:,}")
        print(f"💾 Общий размер: {total_size / (1024**2):.1f} МБ")
        print(f"📅 Период: {min(by_date.keys()) if by_date else 'N/A'} - {max(by_date.keys()) if by_date else 'N/A'}")
        
        if by_date:
            print(f"\n📊 По датам (топ-10):")
            sorted_dates = sorted(by_date.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
            
            for date, info in sorted_dates:
                print(f"   {date}: {info['count']} писем, {info['size'] / 1024:.1f} КБ")
        
        # Статистика бэкапов
        if self.backups_dir.exists():
            backups = list(self.backups_dir.glob("emails_backup_*"))
            if backups:
                print(f"\n💾 Доступные бэкапы: {len(backups)}")
                for backup in sorted(backups)[-3:]:  # Последние 3
                    backup_size = self._get_dir_size(backup)
                    print(f"   📁 {backup.name}: {backup_size / (1024**2):.1f} МБ")
    
    def _get_dir_size(self, path: Path) -> int:
        """📏 Получить размер директории в байтах"""
        total_size = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size
    
    def _save_deletion_report(self, deleted_count: int, error_count: int):
        """💾 Сохранить отчет об удалении"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"deletion_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "operation": "delete_truncated_emails",
            "results": {
                "total_files": len(self.truncated_files),
                "deleted": deleted_count,
                "errors": error_count,
            },
            "deleted_files": [str(f.relative_to(self.data_dir)) for f in self.truncated_files],
        }
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"📄 Отчет об удалении сохранен: {report_path}")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить отчет: {e}")
    
    def run(self):
        """🚀 Запустить CLI"""
        while True:
            self.show_menu()
            
            try:
                choice = input("👉 Ваш выбор (0-5): ").strip()
                
                if choice == "1":
                    self.find_truncated_emails()
                elif choice == "2":
                    self.show_truncated_details()
                elif choice == "3":
                    self.delete_truncated_emails()
                elif choice == "4":
                    self.create_backup()
                elif choice == "5":
                    self.show_statistics()
                elif choice == "0":
                    print("\n👋 До свидания!")
                    break
                else:
                    print("❌ Неверный выбор. Попробуйте снова.")
                
                input("\nНажмите Enter для продолжения...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Работа прервана пользователем")
                break
            except Exception as e:
                print(f"\n❌ Произошла ошибка: {e}")
                input("Нажмите Enter для продолжения...")


def main():
    """🚀 Главная функция"""
    parser = argparse.ArgumentParser(description="Утилита миграции обрезанных писем")
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
    
    args = parser.parse_args()
    
    # Настройка логирования
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Создаем и запускаем мигратор
        migrator = TruncatedEmailMigrator(args.data_dir)
        migrator.run()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()