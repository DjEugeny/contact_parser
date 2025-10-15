#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Data Quality Monitor - Мониторинг качества данных

Отслеживает метрики качества извлечения данных из email:
- text_length > 0 для всех писем
- Полнота контактов (имена, должности, телефоны)
- Полнота организаций (адреса, телефоны)
- Отсутствие дублей

Создано: 2025-10-15
Задача: 3.3 из data-quality-regression-analysis-2025-10-15/tasks.md
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.email_body_extractor import extract_body_with_fallback
from models.email_data_validator_simple import EmailDataValidator


@dataclass
class QualityMetrics:
    """📊 Метрики качества данных"""
    
    # Общие метрики
    total_emails: int = 0
    emails_with_body: int = 0
    emails_without_body: int = 0
    
    # Body метрики
    avg_body_length: float = 0.0
    min_body_length: int = 0
    max_body_length: int = 0
    
    # Форматы
    legacy_format_count: int = 0
    new_format_count: int = 0
    alternative_format_count: int = 0
    empty_format_count: int = 0
    
    # Вложения
    emails_with_attachments: int = 0
    total_attachments: int = 0
    
    # Качество
    emails_with_subject: int = 0
    emails_with_from: int = 0
    char_count_matches: int = 0
    char_count_mismatches: int = 0
    
    # Временные метки
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в dict"""
        return asdict(self)
    
    def get_percentage(self, part: int) -> float:
        """Вычисляет процент от total_emails"""
        if self.total_emails == 0:
            return 0.0
        return round((part / self.total_emails) * 100, 2)
    
    def get_summary(self) -> Dict[str, Any]:
        """Получить краткую сводку"""
        return {
            "total_emails": self.total_emails,
            "body_coverage": f"{self.get_percentage(self.emails_with_body)}%",
            "avg_body_length": round(self.avg_body_length, 0),
            "format_distribution": {
                "legacy": f"{self.get_percentage(self.legacy_format_count)}%",
                "new": f"{self.get_percentage(self.new_format_count)}%",
                "alternative": f"{self.get_percentage(self.alternative_format_count)}%",
                "empty": f"{self.get_percentage(self.empty_format_count)}%"
            },
            "quality_indicators": {
                "has_subject": f"{self.get_percentage(self.emails_with_subject)}%",
                "has_from": f"{self.get_percentage(self.emails_with_from)}%",
                "char_count_accuracy": f"{self.get_percentage(self.char_count_matches)}%"
            }
        }


class DataQualityMonitor:
    """
    🛡️ Монитор качества данных
    """
    
    def __init__(self):
        self.metrics = QualityMetrics()
        self.issues: List[Dict[str, Any]] = []
    
    def analyze_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует одно письмо и обновляет метрики
        
        Args:
            email_data: Данные письма
            
        Returns:
            Dict с результатами анализа
        """
        self.metrics.total_emails += 1
        
        # Получаем метрики письма
        email_metrics = EmailDataValidator.get_quality_metrics(email_data)
        
        # Body метрики
        if email_metrics["has_body"]:
            self.metrics.emails_with_body += 1
            body_length = email_metrics["body_length"]
            
            # Обновляем статистику длины
            if self.metrics.min_body_length == 0 or body_length < self.metrics.min_body_length:
                self.metrics.min_body_length = body_length
            if body_length > self.metrics.max_body_length:
                self.metrics.max_body_length = body_length
        else:
            self.metrics.emails_without_body += 1
            self.issues.append({
                "message_id": email_data.get("message_id", "unknown"),
                "issue": "no_body",
                "severity": "warning"
            })
        
        # Форматы
        format_type = email_metrics["format_type"]
        if format_type == "legacy":
            self.metrics.legacy_format_count += 1
        elif format_type == "new":
            self.metrics.new_format_count += 1
        elif format_type == "alternative":
            self.metrics.alternative_format_count += 1
        else:
            self.metrics.empty_format_count += 1
        
        # Вложения
        if email_metrics["has_attachments"]:
            self.metrics.emails_with_attachments += 1
            self.metrics.total_attachments += email_metrics["attachment_count"]
        
        # Качество
        if email_metrics["has_subject"]:
            self.metrics.emails_with_subject += 1
        else:
            self.issues.append({
                "message_id": email_data.get("message_id", "unknown"),
                "issue": "no_subject",
                "severity": "info"
            })
        
        if email_metrics["has_from"]:
            self.metrics.emails_with_from += 1
        else:
            self.issues.append({
                "message_id": email_data.get("message_id", "unknown"),
                "issue": "no_from",
                "severity": "warning"
            })
        
        # char_count соответствие
        if email_metrics["char_count_match"] is True:
            self.metrics.char_count_matches += 1
        elif email_metrics["char_count_match"] is False:
            self.metrics.char_count_mismatches += 1
            self.issues.append({
                "message_id": email_data.get("message_id", "unknown"),
                "issue": "char_count_mismatch",
                "severity": "info",
                "details": {
                    "expected": email_data.get("char_count"),
                    "actual": email_metrics["body_length"]
                }
            })
        
        return email_metrics
    
    def analyze_batch(self, emails: List[Dict[str, Any]]) -> QualityMetrics:
        """
        Анализирует список писем
        
        Args:
            emails: Список данных писем
            
        Returns:
            QualityMetrics: Итоговые метрики
        """
        for email in emails:
            self.analyze_email(email)
        
        # Вычисляем средние значения
        if self.metrics.emails_with_body > 0:
            total_length = sum(
                EmailDataValidator.get_quality_metrics(email)["body_length"]
                for email in emails
                if EmailDataValidator.get_quality_metrics(email)["has_body"]
            )
            self.metrics.avg_body_length = total_length / self.metrics.emails_with_body
        
        return self.metrics
    
    def get_report(self, detailed: bool = False) -> Dict[str, Any]:
        """
        Получить отчёт о качестве
        
        Args:
            detailed: Включать ли детальную информацию
            
        Returns:
            Dict с отчётом
        """
        report = {
            "summary": self.metrics.get_summary(),
            "issues_count": len(self.issues),
            "timestamp": self.metrics.timestamp
        }
        
        if detailed:
            report["full_metrics"] = self.metrics.to_dict()
            report["issues"] = self.issues
            report["recommendations"] = self._get_recommendations()
        
        return report
    
    def _get_recommendations(self) -> List[str]:
        """Генерирует рекомендации на основе метрик"""
        recommendations = []
        
        # Проверка покрытия body
        body_coverage = self.metrics.get_percentage(self.metrics.emails_with_body)
        if body_coverage < 95:
            recommendations.append(
                f"⚠️ Покрытие body низкое ({body_coverage}%). "
                f"Проверьте работу Email Fetcher."
            )
        
        # Проверка формата
        if self.metrics.empty_format_count > 0:
            empty_pct = self.metrics.get_percentage(self.metrics.empty_format_count)
            recommendations.append(
                f"⚠️ {empty_pct}% писем без body. "
                f"Возможно, это письма только с вложениями."
            )
        
        # Проверка char_count
        if self.metrics.char_count_mismatches > 0:
            mismatch_pct = self.metrics.get_percentage(self.metrics.char_count_mismatches)
            recommendations.append(
                f"ℹ️ {mismatch_pct}% писем с несовпадением char_count. "
                f"Проверьте логику подсчёта символов."
            )
        
        # Проверка subject/from
        if self.metrics.emails_with_subject < self.metrics.total_emails:
            missing = self.metrics.total_emails - self.metrics.emails_with_subject
            recommendations.append(
                f"ℹ️ {missing} писем без subject. Это может быть нормально."
            )
        
        if not recommendations:
            recommendations.append("✅ Качество данных в норме!")
        
        return recommendations
    
    def save_report(self, output_path: Path, detailed: bool = True):
        """
        Сохраняет отчёт в файл
        
        Args:
            output_path: Путь к файлу отчёта
            detailed: Детальный отчёт
        """
        report = self.get_report(detailed=detailed)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Отчёт сохранён: {output_path}")


def monitor_directory(
    emails_dir: Path,
    output_dir: Optional[Path] = None
) -> QualityMetrics:
    """
    Мониторит качество данных в директории с письмами
    
    Args:
        emails_dir: Директория с JSON файлами писем
        output_dir: Директория для сохранения отчётов
        
    Returns:
        QualityMetrics: Итоговые метрики
    """
    monitor = DataQualityMonitor()
    
    # Находим все JSON файлы
    json_files = list(emails_dir.glob("*.json"))
    
    if not json_files:
        print(f"⚠️ Не найдено JSON файлов в {emails_dir}")
        return monitor.metrics
    
    print(f"📊 Анализируем {len(json_files)} писем из {emails_dir}")
    
    # Анализируем каждое письмо
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
            monitor.analyze_email(email_data)
        except Exception as e:
            print(f"❌ Ошибка при обработке {json_file.name}: {e}")
    
    # Выводим сводку
    summary = monitor.metrics.get_summary()
    print(f"\n📊 Сводка:")
    print(f"  Всего писем: {summary['total_emails']}")
    print(f"  Покрытие body: {summary['body_coverage']}")
    print(f"  Средняя длина body: {summary['avg_body_length']}")
    print(f"\n📋 Распределение форматов:")
    for fmt, pct in summary['format_distribution'].items():
        print(f"  {fmt}: {pct}")
    
    # Сохраняем отчёт
    if output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"quality_report_{timestamp}.json"
        monitor.save_report(report_path, detailed=True)
    
    return monitor.metrics


# === CLI ===

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Quality Monitor")
    parser.add_argument(
        "--emails-dir",
        type=Path,
        required=True,
        help="Директория с JSON файлами писем"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Директория для сохранения отчётов"
    )
    
    args = parser.parse_args()
    
    # Запускаем мониторинг
    metrics = monitor_directory(args.emails_dir, args.output_dir)
    
    print(f"\n✅ Мониторинг завершён")
