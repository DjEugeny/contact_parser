#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Commercial Proposal Collector - Сервисный скрипт для сбора коммерческих предложений

Этот скрипт предоставляет CLI интерфейс для поиска и сбора коммерческих предложений
из вложений электронной почты за указанный период.

Автор: Contact Parser Team
Версия: 1.1.0
"""

import sys
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Добавляем корневую директорию проекта в путь
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# Импортируем модули коллектора
from scripts.commercial_proposal_collector.scanner import AttachmentScanner
from scripts.commercial_proposal_collector.detector import ProposalDetector
from scripts.commercial_proposal_collector.collector import FileCollector

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/proposal_collector.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class CommercialProposalCollector:
    """Основной класс коллектора коммерческих предложений."""
    
    def __init__(self):
        """Инициализация коллектора."""
        self.scanner = AttachmentScanner()
        self.detector = ProposalDetector()
        self.collector = FileCollector()
        
        # Предустановленные периоды
        self.presets = {
            "1": {
                "name": "Q3 2025",
                "start": date(2025, 7, 1),
                "end": date(2025, 9, 30),
                "description": "1 июля - 30 сентября 2025"
            },
            "2": {
                "name": "Q2 2025",
                "start": date(2025, 4, 1),
                "end": date(2025, 6, 30),
                "description": "1 апреля - 30 июня 2025"
            },
            "3": {
                "name": "Q1 2025",
                "start": date(2025, 1, 1),
                "end": date(2025, 3, 31),
                "description": "1 января - 31 марта 2025"
            },
            "4": {
                "name": "Q4 2025",
                "start": date(2025, 10, 1),
                "end": date(2025, 12, 31),
                "description": "1 октября - 31 декабря 2025"
            },
            "5": {
                "name": "2025 год",
                "start": date(2025, 1, 1),
                "end": date(2025, 12, 31),
                "description": "1 января - 31 декабря 2025"
            },
            "6": {
                "name": "Q1 2026",
                "start": date(2026, 1, 1),
                "end": date(2026, 3, 31),
                "description": "1 января - 31 марта 2026"
            },
            "7": {
                "name": "Q2 2026",
                "start": date(2026, 4, 1),
                "end": date(2026, 6, 30),
                "description": "1 апреля - 30 июня 2026"
            },
            "8": {
                "name": "Q3 2026",
                "start": date(2026, 7, 1),
                "end": date(2026, 9, 30),
                "description": "1 июля - 30 сентября 2026"
            },
            "9": {
                "name": "Q4 2026",
                "start": date(2026, 10, 1),
                "end": date(2026, 12, 31),
                "description": "1 октября - 31 декабря 2026"
            },
            "10": {
                "name": "2026 год",
                "start": date(2026, 1, 1),
                "end": date(2026, 12, 31),
                "description": "1 января - 31 декабря 2026"
            }
        }
    
    def display_header(self):
        """Отображение заголовка приложения."""
        print("\n" + "="*60)
        print("🔍 Коллектор коммерческих предложений")
        print("="*60)
        print()
    
    def display_menu(self) -> str:
        """
        Отображение меню выбора периода.
        
        Returns:
            Выбранная опция
        """
        print("Выберите период обработки:")
        print()
        
        for key, preset in self.presets.items():
            print(f"{key}. {preset['name']} ({preset['description']})")
        
        print("11. Произвольный период")
        print("12. Все доступные даты")
        print("13. Информация о директории с вложениями")
        print("0. Выход")
        print()
        
        choice = input("Введите номер опции: ").strip()
        return choice
    
    def display_organization_menu(self) -> str:
        """
        Отображение меню выбора организации файлов.
        
        Returns:
            Выбранная опция
        """
        print("\nВыберите способ организации файлов:")
        print()
        print("1. Разложить по папкам (по датам)")
        print("2. Сложить все в одну папку")
        print()
        
        choice = input("Введите номер опции: ").strip()
        return choice
    
    def get_custom_period(self) -> Optional[Tuple[date, date]]:
        """
        Получение произвольного периода от пользователя.
        
        Returns:
            Кортеж (начальная_дата, конечная_дата) или None
        """
        print("\n📅 Введите произвольный период:")
        print()
        
        try:
            start_str = input("Начальная дата (ГГГГ-ММ-ДД): ").strip()
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            
            end_str = input("Конечная дата (ГГГГ-ММ-ДД): ").strip()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start_date > end_date:
                print("❌ Начальная дата не может быть позже конечной!")
                return None
                
            return start_date, end_date
            
        except ValueError as e:
            print(f"❌ Некорректный формат даты: {e}")
            return None
    
    def display_directory_info(self):
        """Отображение информации о директории с вложениями."""
        print("\n📂 Информация о директории с вложениями:")
        print("-" * 50)
        
        info = self.scanner.get_directory_info()
        
        if "error" in info:
            print(f"❌ {info['error']}")
            return
            
        print(f"📁 Путь: {info['base_directory']}")
        print(f"📅 Период: {info['date_range']['start']} - {info['date_range']['end']}")
        print(f"📂 Папок с датами: {info['date_directories_count']}")
        print(f"📄 Всего файлов: {info['total_files']}")
        print()
        print("📊 Типы файлов:")
        for ext, count in info['file_types'].items():
            print(f"  {ext}: {count}")
        print()
    
    def scan_and_collect(
        self, 
        start_date: date, 
        end_date: date, 
        period_name: str,
        organize_by_date: bool = True,
        extensions: Optional[List[str]] = None
    ) -> bool:
        """
        Сканирование и сбор файлов за указанный период.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            period_name: Название периода для отчета
            organize_by_date: Организовать ли файлы по датам
            extensions: Список расширений файлов для поиска
            
        Returns:
            True если операция успешна
        """
        if extensions is None:
            extensions = ['.pdf']
        
        print(f"\n🔍 Сканирование периода: {period_name}")
        print(f"📅 Диапазон: {start_date} - {end_date}")
        print(f"📄 Типы файлов: {', '.join(extensions)}")
        print(f"📁 Организация: {'по датам' if organize_by_date else 'в одной папке'}")
        print()
        
        # Шаг 1: Сканирование файловой структуры
        print("📂 Шаг 1: Сканирование файловой структуры...")
        files_by_date = self.scanner.scan_date_range(start_date, end_date, extensions)
        
        if not files_by_date:
            print("❌ Файлы за указанный период не найдены!")
            return False
        
        total_files = sum(len(files) for files in files_by_date.values())
        print(f"✅ Найдено папок: {len(files_by_date)}")
        print(f"✅ Найдено файлов: {total_files}")
        print()
        
        # Шаг 2: Поиск коммерческих предложений
        print("🔍 Шаг 2: Поиск коммерческих предложений...")
        proposals_by_date = {}
        
        for file_date, files in files_by_date.items():
            proposals = self.detector.find_proposals_in_files(files)
            if proposals:
                proposals_by_date[file_date] = proposals
                print(f"  📅 {file_date}: найдено КП {len(proposals)}")
        
        if not proposals_by_date:
            print("❌ Коммерческие предложения не найдены!")
            return False
        
        total_proposals = sum(len(proposals) for proposals in proposals_by_date.values())
        print(f"✅ Всего найдено КП: {total_proposals}")
        print()
        
        # Шаг 3: Статистика по найденным КП
        print("📊 Шаг 3: Анализ найденных предложений...")
        all_proposals = []
        for proposals in proposals_by_date.values():
            all_proposals.extend(proposals)
        
        stats = self.detector.get_proposal_statistics(all_proposals)
        print(f"  📁 Общий размер: {stats['total_size_mb']} МБ")
        print(f"  📄 Типы файлов: {stats['file_types']}")
        print()
        
        # Шаг 4: Копирование файлов
        print("📁 Шаг 4: Копирование файлов...")
        self.collector.clear_statistics()
        
        if organize_by_date:
            copy_stats = self.collector.copy_proposals(
                proposals_by_date, 
                period_name,
                create_date_subfolders=True
            )
        else:
            copy_stats = self.collector.copy_proposals_flat(
                proposals_by_date, 
                period_name
            )
        
        print(f"✅ Скопировано: {copy_stats['success']}/{copy_stats['total']}")
        if copy_stats['failed'] > 0:
            print(f"❌ Ошибок: {copy_stats['failed']}")
        print(f"📊 Размер скопированных файлов: {copy_stats['total_size_mb']} МБ")
        print()
        
        # Шаг 5: Генерация отчета
        print("📄 Шаг 5: Генерация отчета...")
        report_path = self.collector.save_report(period_name)
        
        if report_path:
            print(f"✅ Отчет сохранен: {report_path}")
        else:
            print("❌ Ошибка сохранения отчета!")
        
        print()
        print("🎉 Операция завершена успешно!")
        print(f"📁 Папка с результатами: {self.collector.target_directory / period_name}")
        
        return True
    
    def run_interactive_mode(self):
        """Запуск в интерактивном режиме."""
        while True:
            self.display_header()
            choice = self.display_menu()
            
            if choice == "0":
                print("👋 До свидания!")
                break
            
            elif choice in self.presets:
                preset = self.presets[choice]
                print(f"\nВыбран период: {preset['name']} ({preset['description']})")
                
                # Выбор организации файлов
                org_choice = self.display_organization_menu()
                organize_by_date = org_choice == "1"
                
                if org_choice in ["1", "2"]:
                    confirm = input("Начать обработку? (д/н): ").strip().lower()
                    if confirm in ['д', 'да', 'y', 'yes']:
                        self.scan_and_collect(
                            preset['start'],
                            preset['end'],
                            preset['name'],
                            organize_by_date
                        )
                    else:
                        print("❌ Операция отменена.")
                else:
                    print("❌ Некорректный выбор организации файлов.")
            
            elif choice == "11":
                period = self.get_custom_period()
                if period:
                    start_date, end_date = period
                    period_name = f"{start_date}_to_{end_date}"
                    
                    # Выбор организации файлов
                    org_choice = self.display_organization_menu()
                    organize_by_date = org_choice == "1"
                    
                    if org_choice in ["1", "2"]:
                        confirm = input("Начать обработку? (д/н): ").strip().lower()
                        if confirm in ['д', 'да', 'y', 'yes']:
                            self.scan_and_collect(start_date, end_date, period_name, organize_by_date)
                    else:
                        print("❌ Некорректный выбор организации файлов.")
            
            elif choice == "12":
                print("\nВыбран режим: Все доступные даты")
                
                # Выбор организации файлов
                org_choice = self.display_organization_menu()
                organize_by_date = org_choice == "1"
                
                if org_choice in ["1", "2"]:
                    confirm = input("Начать обработку? (д/н): ").strip().lower()
                    if confirm in ['д', 'да', 'y', 'yes']:
                        # Получаем все доступные даты
                        date_dirs = self.scanner.get_date_directories()
                        if date_dirs:
                            start_date = date_dirs[0][0]
                            end_date = date_dirs[-1][0]
                            period_name = "all_dates"
                            
                            self.scan_and_collect(start_date, end_date, period_name, organize_by_date)
                        else:
                            print("❌ Директории с датами не найдены!")
                else:
                    print("❌ Некорректный выбор организации файлов.")
            
            elif choice == "13":
                self.display_directory_info()
            
            else:
                print("❌ Некорректный выбор. Попробуйте снова.")
            
            if choice != "0":
                input("\nНажмите Enter для продолжения...")
    
    def run_batch_mode(self, start_date: date, end_date: date, period_name: str, organize_by_date: bool = True):
        """
        Запуск в пакетном режиме.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            period_name: Название периода
            organize_by_date: Организовать ли файлы по датам
        """
        self.display_header()
        print(f"🚀 Запуск в пакетном режиме: {period_name}")
        print(f"📅 Период: {start_date} - {end_date}")
        print(f"📁 Организация: {'по датам' if organize_by_date else 'в одной папке'}")
        print()
        
        success = self.scan_and_collect(start_date, end_date, period_name, organize_by_date)
        
        if success:
            print("\n✅ Пакетная обработка завершена успешно!")
            sys.exit(0)
        else:
            print("\n❌ Ошибка при пакетной обработке!")
            sys.exit(1)


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Коллектор коммерческих предложений из вложений электронной почты"
    )
    
    parser.add_argument(
        "--mode",
        choices=["interactive", "batch"],
        default="interactive",
        help="Режим работы"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        help="Начальная дата (ГГГГ-ММ-ДД) для пакетного режима"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        help="Конечная дата (ГГГГ-ММ-ДД) для пакетного режима"
    )
    
    parser.add_argument(
        "--period-name",
        type=str,
        help="Название периода для отчета"
    )
    
    parser.add_argument(
        "--organize-by-date",
        action="store_true",
        default=True,
        help="Организовать файлы по датам (по умолчанию: True)"
    )
    
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Сложить все файлы в одну папку (без подпапок по датам)"
    )
    
    args = parser.parse_args()
    
    # Создаем директорию для логов если нужно
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    
    collector = CommercialProposalCollector()
    
    # Определяем способ организации файлов
    organize_by_date = args.organize_by_date and not args.flat
    
    if args.mode == "interactive":
        collector.run_interactive_mode()
    elif args.mode == "batch":
        if not all([args.start_date, args.end_date, args.period_name]):
            print("❌ Для пакетного режима нужны параметры: --start-date, --end-date, --period-name")
            sys.exit(1)
        
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError as e:
            print(f"❌ Некорректный формат даты: {e}")
            sys.exit(1)
        
        collector.run_batch_mode(start_date, end_date, args.period_name, organize_by_date)


if __name__ == "__main__":
    main()