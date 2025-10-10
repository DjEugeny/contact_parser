#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Тестовый скрипт для проверки регрессии ModelsManager
Загружает 7 писем от 2025-07-28 и обрабатывает через pipeline
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.email_loader import ProcessedEmailLoader
from src.integrated_llm_processor import IntegratedLLMProcessor


class RegressionTestMetrics:
    """Сборщик метрик для регрессионного тестирования"""

    def __init__(self):
        self.total_emails = 0
        self.processed_emails = 0
        self.successful_emails = 0
        self.empty_responses = 0
        self.errors = []
        self.processing_times = []
        self.contacts_found = []
        self.organizations_found = []
        self.model_switches = 0
        self.models_used = {}

    def add_result(self, email_result: Dict):
        """Добавить результат обработки письма"""
        self.processed_emails += 1

        # Проверяем успешность
        llm_analysis = email_result.get("llm_analysis", {})

        # Проверка на пустой ответ
        if not llm_analysis or llm_analysis == {}:
            self.empty_responses += 1
        else:
            self.successful_emails += 1

            # Собираем данные о контактах и организациях
            contacts = llm_analysis.get("contacts", [])
            organizations = llm_analysis.get("organizations", [])

            self.contacts_found.append(len(contacts))
            self.organizations_found.append(len(organizations))

    def add_error(self, error_msg: str, email_info: Dict = None):
        """Добавить ошибку"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
            "email": email_info,
        }
        self.errors.append(error_entry)

    def calculate_success_rate(self) -> float:
        """Рассчитать процент успешности"""
        if self.processed_emails == 0:
            return 0.0
        return (self.successful_emails / self.processed_emails) * 100

    def get_summary(self) -> Dict:
        """Получить сводку метрик"""
        return {
            "total_emails": self.total_emails,
            "processed_emails": self.processed_emails,
            "successful_emails": self.successful_emails,
            "empty_responses": self.empty_responses,
            "success_rate": self.calculate_success_rate(),
            "errors_count": len(self.errors),
            "total_contacts": sum(self.contacts_found),
            "total_organizations": sum(self.organizations_found),
            "avg_contacts_per_email": (
                sum(self.contacts_found) / len(self.contacts_found)
                if self.contacts_found
                else 0
            ),
            "avg_organizations_per_email": (
                sum(self.organizations_found) / len(self.organizations_found)
                if self.organizations_found
                else 0
            ),
        }


def print_header():
    """Вывести заголовок теста"""
    print("=" * 80)
    print("🧪 РЕГРЕССИОННЫЙ ТЕСТ: ModelsManager Fix")
    print("=" * 80)
    print(f"📅 Дата тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📧 Целевая дата писем: 2025-07-28")
    print(f"🎯 Ожидаемое количество писем: 7")
    print("=" * 80)
    print()


def load_test_emails(target_date: str = "2025-07-28") -> List[Dict]:
    """Загрузить тестовые письма"""
    print(f"📧 Загрузка писем за {target_date}...")

    loader = ProcessedEmailLoader()
    emails = loader.load_emails_by_date(target_date)

    if not emails:
        print(f"❌ Письма не найдены за {target_date}")
        return []

    print(f"✅ Загружено писем: {len(emails)}")
    return emails


def process_emails_with_metrics(emails: List[Dict]) -> RegressionTestMetrics:
    """Обработать письма и собрать метрики"""
    metrics = RegressionTestMetrics()
    metrics.total_emails = len(emails)

    print(f"\n🔄 Начало обработки {len(emails)} писем...")
    print("-" * 80)

    # Создаем процессор
    processor = IntegratedLLMProcessor(test_mode=False)

    for idx, email in enumerate(emails, 1):
        email_info = {
            "index": idx,
            "from": email.get("from", "N/A"),
            "subject": email.get("subject", "N/A")[:60],
            "thread_id": email.get("thread_id", "N/A"),
        }

        print(f"\n📧 Письмо {idx}/{len(emails)}")
        print(f"   От: {email_info['from'][:60]}")
        print(f"   Тема: {email_info['subject']}")

        try:
            # Обрабатываем письмо
            result = processor.process_single_email(email)

            if result:
                metrics.add_result(result)

                # Выводим краткую информацию
                llm_analysis = result.get("llm_analysis", {})
                contacts_count = len(llm_analysis.get("contacts", []))
                orgs_count = len(llm_analysis.get("organizations", []))

                if llm_analysis and llm_analysis != {}:
                    print(
                        f"   ✅ Успешно: {contacts_count} контактов, {orgs_count} организаций"
                    )
                else:
                    print(f"   ⚠️ Пустой ответ от LLM")
            else:
                metrics.add_error("Результат обработки = None", email_info)
                print(f"   ❌ Ошибка: результат = None")

        except Exception as e:
            error_msg = str(e)
            metrics.add_error(error_msg, email_info)
            print(f"   ❌ Исключение: {error_msg}")

    print("\n" + "-" * 80)
    print("✅ Обработка завершена")

    return metrics


def print_detailed_report(metrics: RegressionTestMetrics):
    """Вывести детальный отчет"""
    summary = metrics.get_summary()

    print("\n" + "=" * 80)
    print("📊 ДЕТАЛЬНЫЙ ОТЧЕТ")
    print("=" * 80)

    # Основные метрики
    print("\n📈 Основные метрики:")
    print(f"   Всего писем:           {summary['total_emails']}")
    print(f"   Обработано:            {summary['processed_emails']}")
    print(f"   Успешно:               {summary['successful_emails']}")
    print(f"   Пустых ответов:        {summary['empty_responses']}")
    print(f"   Ошибок:                {summary['errors_count']}")
    print(f"   Success Rate:          {summary['success_rate']:.1f}%")

    # Данные о контактах
    print(f"\n👥 Извлеченные данные:")
    print(f"   Всего контактов:       {summary['total_contacts']}")
    print(f"   Всего организаций:     {summary['total_organizations']}")
    print(
        f"   Среднее контактов:     {summary['avg_contacts_per_email']:.1f} на письмо"
    )
    print(
        f"   Среднее организаций:   {summary['avg_organizations_per_email']:.1f} на письмо"
    )

    # Детали ошибок
    if metrics.errors:
        print(f"\n❌ Детали ошибок ({len(metrics.errors)}):")
        for i, error in enumerate(metrics.errors, 1):
            email_info = error.get("email", {})
            print(f"\n   Ошибка {i}:")
            print(
                f"      Письмо: {email_info.get('index', 'N/A')} - {email_info.get('subject', 'N/A')}"
            )
            print(f"      Сообщение: {error['error'][:100]}")

    # Проверка требований
    print("\n" + "=" * 80)
    print("✅ ПРОВЕРКА ТРЕБОВАНИЙ")
    print("=" * 80)

    all_passed = True

    # Требование 7.1: Все письма обработаны
    req_7_1 = summary["processed_emails"] == summary["total_emails"]
    status_7_1 = "✅ PASS" if req_7_1 else "❌ FAIL"
    print(f"\n{status_7_1} Требование 7.1: Все письма обработаны")
    print(
        f"   Ожидалось: {summary['total_emails']}, Обработано: {summary['processed_emails']}"
    )
    all_passed = all_passed and req_7_1

    # Требование 7.2: Success rate > 80%
    req_7_2 = summary["success_rate"] >= 80.0
    status_7_2 = "✅ PASS" if req_7_2 else "❌ FAIL"
    print(f"\n{status_7_2} Требование 7.2: Success rate >= 80%")
    print(f"   Текущий: {summary['success_rate']:.1f}%")
    all_passed = all_passed and req_7_2

    # Требование 7.3: Пустых ответов <= 1
    req_7_3 = summary["empty_responses"] <= 1
    status_7_3 = "✅ PASS" if req_7_3 else "❌ FAIL"
    print(f"\n{status_7_3} Требование 7.3: Пустых ответов <= 1")
    print(f"   Текущее: {summary['empty_responses']}")
    all_passed = all_passed and req_7_3

    # Требование 7.4: Критических ошибок = 0
    req_7_4 = summary["errors_count"] == 0
    status_7_4 = "✅ PASS" if req_7_4 else "❌ FAIL"
    print(f"\n{status_7_4} Требование 7.4: Критических ошибок = 0")
    print(f"   Текущее: {summary['errors_count']}")
    all_passed = all_passed and req_7_4

    # Требование 7.5: Извлечены контакты
    req_7_5 = summary["total_contacts"] > 0
    status_7_5 = "✅ PASS" if req_7_5 else "❌ FAIL"
    print(f"\n{status_7_5} Требование 7.5: Извлечены контакты")
    print(f"   Всего контактов: {summary['total_contacts']}")
    all_passed = all_passed and req_7_5

    # Итоговый результат
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ВСЕ ТРЕБОВАНИЯ ВЫПОЛНЕНЫ!")
        print("✅ Регрессия исправлена успешно")
    else:
        print("⚠️ НЕКОТОРЫЕ ТРЕБОВАНИЯ НЕ ВЫПОЛНЕНЫ")
        print("❌ Требуется дополнительная работа")
    print("=" * 80)

    return all_passed


def save_report(metrics: RegressionTestMetrics, passed: bool):
    """Сохранить отчет в файл"""
    report_dir = Path("data/test_reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"regression_test_{timestamp}.json"

    report_data = {
        "test_date": datetime.now().isoformat(),
        "target_email_date": "2025-07-28",
        "summary": metrics.get_summary(),
        "errors": metrics.errors,
        "all_requirements_passed": passed,
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Отчет сохранен: {report_file}")


def main():
    """Главная функция теста"""
    print_header()

    # Загружаем письма
    emails = load_test_emails("2025-07-28")

    if not emails:
        print("❌ Тест прерван: нет писем для обработки")
        sys.exit(1)

    # Проверяем количество писем
    if len(emails) != 7:
        print(f"⚠️ Предупреждение: ожидалось 7 писем, найдено {len(emails)}")

    # Обрабатываем письма и собираем метрики
    metrics = process_emails_with_metrics(emails)

    # Выводим детальный отчет
    passed = print_detailed_report(metrics)

    # Сохраняем отчет
    save_report(metrics, passed)

    # Возвращаем код выхода
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
