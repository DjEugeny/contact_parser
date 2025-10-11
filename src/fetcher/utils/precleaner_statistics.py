#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Система статистики работы PreCleaner
Собирает, анализирует и визуализирует эффективность пред-очистки текстов
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import argparse


@dataclass
class PreCleanerSessionStats:
    """📊 Статистика одной сессии PreCleaner"""
    session_id: str
    start_time: str
    end_time: str
    total_processed: int
    total_tokens_saved: int
    average_reduction: float
    total_signatures_removed: int
    total_quotes_removed: int
    total_disclaimers_removed: int
    average_processing_time: float
    cache_stats: Dict[str, Any]
    
    @property
    def duration_minutes(self) -> float:
        """⏱️ Длительность сессии в минутах"""
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        return (end - start).total_seconds() / 60
    
    @property
    def tokens_per_minute(self) -> float:
        """🪙 Токенов в минуту"""
        if self.duration_minutes == 0:
            return 0.0
        return self.total_tokens_saved / self.duration_minutes


class PreCleanerStatisticsCollector:
    """📊 Коллектор статистики PreCleaner"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.stats_dir = self.data_dir / "logs" / "precleaner"
        self.reports_dir = self.data_dir / "reports" / "precleaner"
        
        # Создаем директории
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        
        # Сессии
        self.sessions: List[PreCleanerSessionStats] = []
        self.current_session: Optional[str] = None
    
    def load_existing_sessions(self):
        """📂 Загрузить существующие сессии"""
        if not self.stats_dir.exists():
            return
        
        stats_files = list(self.stats_dir.glob("precleaner_stats_*.json"))
        
        for stats_file in sorted(stats_files):
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Извлекаем информацию о сессии
                processing_stats = data.get('processing_stats', {})
                
                if processing_stats.get('total_processed', 0) > 0:
                    session = PreCleanerSessionStats(
                        session_id=stats_file.stem,
                        start_time=data.get('timestamp', ''),
                        end_time=data.get('timestamp', ''),  # В старых файлах только одно время
                        total_processed=processing_stats.get('total_processed', 0),
                        total_tokens_saved=processing_stats.get('total_tokens_saved', 0),
                        average_reduction=processing_stats.get('average_reduction', 0.0),
                        total_signatures_removed=processing_stats.get('total_signatures_removed', 0),
                        total_quotes_removed=processing_stats.get('total_quotes_removed', 0),
                        total_disclaimers_removed=processing_stats.get('total_disclaimers_removed', 0),
                        average_processing_time=processing_stats.get('average_processing_time', 0.0),
                        cache_stats=processing_stats.get('cache_stats', {})
                    )
                    
                    self.sessions.append(session)
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка загрузки сессии из {stats_file}: {e}")
        
        self.logger.info(f"📂 Загружено {len(self.sessions)} сессий")
    
    def analyze_efficiency(self) -> Dict[str, Any]:
        """📈 Анализ эффективности PreCleaner"""
        if not self.sessions:
            return {"error": "Нет данных для анализа"}
        
        # Агрегируем данные по всем сессиям
        total_processed = sum(s.total_processed for s in self.sessions)
        total_tokens_saved = sum(s.total_tokens_saved for s in self.sessions)
        total_signatures_removed = sum(s.total_signatures_removed for s in self.sessions)
        total_quotes_removed = sum(s.total_quotes_removed for s in self.sessions)
        total_disclaimers_removed = sum(s.total_disclaimers_removed for s in self.sessions)
        
        # Средние значения
        avg_reduction = sum(s.average_reduction for s in self.sessions) / len(self.sessions)
        avg_processing_time = sum(s.average_processing_time for s in self.sessions) / len(self.sessions)
        
        # Анализ по времени
        sessions_by_date = defaultdict(list)
        for session in self.sessions:
            date = session.start_time[:10]  # YYYY-MM-DD
            sessions_by_date[date].append(session)
        
        # Находим лучшую и худшую сессии
        best_session = max(self.sessions, key=lambda s: s.total_tokens_saved)
        worst_session = min(self.sessions, key=lambda s: s.total_tokens_saved)
        
        return {
            "summary": {
                "total_sessions": len(self.sessions),
                "total_processed": total_processed,
                "total_tokens_saved": total_tokens_saved,
                "average_reduction_percent": avg_reduction,
                "average_processing_time_ms": avg_processing_time * 1000,
                "total_signatures_removed": total_signatures_removed,
                "total_quotes_removed": total_quotes_removed,
                "total_disclaimers_removed": total_disclaimers_removed,
            },
            "performance": {
                "best_session": {
                    "session_id": best_session.session_id,
                    "tokens_saved": best_session.total_tokens_saved,
                    "reduction_percent": best_session.average_reduction,
                    "date": best_session.start_time[:10]
                },
                "worst_session": {
                    "session_id": worst_session.session_id,
                    "tokens_saved": worst_session.total_tokens_saved,
                    "reduction_percent": worst_session.average_reduction,
                    "date": worst_session.start_time[:10]
                }
            },
            "daily_stats": {
                date: {
                    "sessions": len(sessions),
                    "processed": sum(s.total_processed for s in sessions),
                    "tokens_saved": sum(s.total_tokens_saved for s in sessions),
                    "avg_reduction": sum(s.average_reduction for s in sessions) / len(sessions)
                }
                for date, sessions in sessions_by_date.items()
            },
            "cache_efficiency": self._analyze_cache_efficiency()
        }
    
    def _analyze_cache_efficiency(self) -> Dict[str, Any]:
        """🧠 Анализ эффективности кэширования"""
        if not self.sessions:
            return {}
        
        total_thread_patterns = 0
        total_sender_patterns = 0
        total_thread_entries = 0
        total_sender_entries = 0
        
        for session in self.sessions:
            cache_stats = session.cache_stats
            thread_stats = cache_stats.get('thread', {})
            sender_stats = cache_stats.get('sender', {})
            
            total_thread_patterns += thread_stats.get('total_patterns', 0)
            total_sender_patterns += sender_stats.get('total_patterns', 0)
            total_thread_entries += thread_stats.get('total_entries', 0)
            total_sender_entries += sender_stats.get('total_entries', 0)
        
        return {
            "thread_cache": {
                "total_patterns": total_thread_patterns,
                "total_entries": total_thread_entries,
                "avg_entries_per_pattern": total_thread_entries / max(total_thread_patterns, 1)
            },
            "sender_cache": {
                "total_patterns": total_sender_patterns,
                "total_entries": total_sender_entries,
                "avg_entries_per_pattern": total_sender_entries / max(total_sender_patterns, 1)
            }
        }
    
    def generate_markdown_report(self) -> str:
        """📝 Генерация Markdown отчета"""
        analysis = self.analyze_efficiency()
        
        if "error" in analysis:
            return f"# Отчет по эффективности PreCleaner\n\n❌ {analysis['error']}"
        
        summary = analysis["summary"]
        performance = analysis["performance"]
        daily_stats = analysis["daily_stats"]
        cache_eff = analysis["cache_efficiency"]
        
        report = f"""# Отчет по эффективности PreCleaner

**Дата создания**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Всего сессий**: {summary['total_sessions']}  
**Обработано писем**: {summary['total_processed']:,}  
**Сэкономлено токенов**: {summary['total_tokens_saved']:,}

## 📊 Сводная статистика

| Метрика | Значение |
|---------|----------|
| Среднее сокращение | {summary['average_reduction_percent']:.1f}% |
| Среднее время обработки | {summary['average_processing_time_ms']:.1f} мс |
| Удалено подписей | {summary['total_signatures_removed']:,} |
| Удалено цитат | {summary['total_quotes_removed']:,} |
| Удалено дисклеймеров | {summary['total_disclaimers_removed']:,} |

## 🏆 Производительность

### Лучшая сессия
- **ID**: {performance['best_session']['session_id']}
- **Дата**: {performance['best_session']['date']}
- **Сэкономлено токенов**: {performance['best_session']['tokens_saved']:,}
- **Сокращение**: {performance['best_session']['reduction_percent']:.1f}%

### Худшая сессия
- **ID**: {performance['worst_session']['session_id']}
- **Дата**: {performance['worst_session']['date']}
- **Сэкономлено токенов**: {performance['worst_session']['tokens_saved']:,}
- **Сокращение**: {performance['worst_session']['reduction_percent']:.1f}%

## 📅 Ежедневная статистика

| Дата | Сессий | Писем | Токенов | Сокращение |
|------|--------|-------|---------|------------|
"""
        
        # Сортируем даты
        for date in sorted(daily_stats.keys()):
            stats = daily_stats[date]
            report += f"| {date} | {stats['sessions']} | {stats['processed']:,} | {stats['tokens_saved']:,} | {stats['avg_reduction']:.1f}% |\n"
        
        if cache_eff:
            report += f"""
## 🧠 Эффективность кэширования

### Thread Cache
- **Всего паттернов**: {cache_eff['thread_cache']['total_patterns']:,}
- **Всего записей**: {cache_eff['thread_cache']['total_entries']:,}
- **Средние записи на паттерн**: {cache_eff['thread_cache']['avg_entries_per_pattern']:.1f}

### Sender Cache
- **Всего паттернов**: {cache_eff['sender_cache']['total_patterns']:,}
- **Всего записей**: {cache_eff['sender_cache']['total_entries']:,}
- **Средние записи на паттерн**: {cache_eff['sender_cache']['avg_entries_per_pattern']:.1f}
"""
        
        # Добавляем рекомендации
        report += self._generate_recommendations(analysis)
        
        return report
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> str:
        """💡 Генерация рекомендаций на основе анализа"""
        summary = analysis["summary"]
        
        recommendations = "\n## 💡 Рекомендации\n\n"
        
        # Анализ эффективности
        if summary['average_reduction_percent'] < 20:
            recommendations += "⚠️ **Низкое сокращение текста** (< 20%). Рассмотрите:\n"
            recommendations += "- Настройку более агрессивных паттернов\n"
            recommendations += "- Увеличение порогов для цитат и подписей\n\n"
        elif summary['average_reduction_percent'] > 60:
            recommendations += "✅ **Высокое сокращение текста** (> 60%). Отличная экономия токенов!\n\n"
        
        # Анализ производительности
        if summary['average_processing_time_ms'] > 100:
            recommendations += "⚠️ **Медленная обработка** (> 100 мс). Рассмотрите:\n"
            recommendations += "- Оптимизацию регулярных выражений\n"
            recommendations += "- Увеличение размера кэша\n\n"
        
        # Анализ удаления элементов
        total_removed = (summary['total_signatures_removed'] + 
                        summary['total_quotes_removed'] + 
                        summary['total_disclaimers_removed'])
        
        if total_removed == 0:
            recommendations += "⚠️ **Элементы не удаляются**. Проверьте:\n"
            recommendations += "- Корректность паттернов в конфигурации\n"
            recommendations += "- Формат входящих текстов\n\n"
        elif summary['total_quotes_removed'] < total_removed * 0.1:
            recommendations += "💡 **Мало цитат удаляется**. Возможно:\n"
            recommendations += "- Цитаты имеют нестандартный формат\n"
            recommendations += "- Нужно добавить новые паттерны для цитат\n\n"
        
        return recommendations
    
    def save_report(self, prefix: str = "precleaner_efficiency") -> Tuple[str, str]:
        """💾 Сохранить отчеты"""
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
        
        json_content = self.analyze_efficiency()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📊 Отчеты сохранены:")
        self.logger.info(f"   Markdown: {md_path}")
        self.logger.info(f"   JSON: {json_path}")
        
        return str(md_path), str(json_path)
    
    def print_summary(self):
        """📋 Вывести сводную информацию"""
        analysis = self.analyze_efficiency()
        
        if "error" in analysis:
            print(f"\n❌ {analysis['error']}")
            return
        
        summary = analysis["summary"]
        performance = analysis["performance"]
        
        print("\n" + "="*70)
        print("📊 СВОДКА ПО ЭФФЕКТИВНОСТИ PRECLEANER")
        print("="*70)
        print(f"📅 Период анализа: {len(self.sessions)} сессий")
        print(f"📧 Обработано писем: {summary['total_processed']:,}")
        print(f"🪙 Сэкономлено токенов: {summary['total_tokens_saved']:,}")
        print(f"📉 Среднее сокращение: {summary['average_reduction_percent']:.1f}%")
        print(f"⏱️ Среднее время обработки: {summary['average_processing_time_ms']:.1f} мс")
        
        print(f"\n🏆 Лучшая сессия:")
        print(f"   📅 {performance['best_session']['date']}")
        print(f"   🪙 {performance['best_session']['tokens_saved']:,} токенов")
        print(f"   📉 {performance['best_session']['reduction_percent']:.1f}% сокращение")
        
        print(f"\n📊 Удалено элементов:")
        print(f"   ✂️ Подписи: {summary['total_signatures_removed']:,}")
        print(f"   💬 Цитаты: {summary['total_quotes_removed']:,}")
        print(f"   📄 Дисклеймеры: {summary['total_disclaimers_removed']:,}")
        
        print("="*70)


def main():
    """🚀 Главная функция"""
    parser = argparse.ArgumentParser(description="Анализ статистики PreCleaner")
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
        default="precleaner_efficiency", 
        help="Префикс для файлов отчетов"
    )
    parser.add_argument(
        "--no-reports", 
        action="store_true", 
        help="Не сохранять отчеты, только вывести сводку"
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
    
    logger.info("📊 ЗАПУСК АНАЛИЗА СТАТИСТИКИ PRECLEANER")
    logger.info(f"📁 Директория с данными: {args.data_dir}")
    
    # Создаем коллектор и загружаем данные
    collector = PreCleanerStatisticsCollector(args.data_dir)
    collector.load_existing_sessions()
    
    # Выводим сводку
    collector.print_summary()
    
    # Сохраняем отчеты
    if not args.no_reports and collector.sessions:
        md_path, json_path = collector.save_report(args.output_prefix)
        logger.info(f"✅ Отчеты сохранены в {collector.reports_dir}")
        
        print(f"\n📄 Детальный отчет: {md_path}")
        print(f"📊 Данные для анализа: {json_path}")
    elif not collector.sessions:
        logger.warning("⚠️ Данные для анализа не найдены!")
        print("\n💡 Убедитесь, что PreCleaner был использован и создал файлы статистики")
        print(f"📁 Ожидаемая директория: {collector.stats_dir}")


if __name__ == "__main__":
    main()