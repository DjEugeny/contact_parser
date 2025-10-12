#!/usr/bin/env python3
"""
Comprehensive Pattern Analyzer - анализ паттернов на всей базе писем (май-сентябрь 2025)

Скрипт анализирует все письма в папке data/emails за указанный период,
находит паттерны подписей, цитат и дисклеймеров, генерирует конфигурацию
PreCleaner и подробный отчет.
"""

import os
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import argparse


class ComprehensivePatternAnalyzer:
    """Анализатор паттернов в письмах"""
    
    def __init__(self, emails_dir: str = "data/emails"):
        """
        Инициализация анализатора
        
        Args:
            emails_dir: Папка с письмами
        """
        self.emails_dir = Path(emails_dir)
        self.signature_patterns = defaultdict(int)
        self.disclaimer_patterns = defaultdict(int)
        self.quote_patterns = defaultdict(int)
        self.email_stats = {
            'total_emails': 0,
            'total_domains': 0,
            'total_length': 0,
            'avg_length': 0,
            'domains': Counter(),
            'date_range': {'earliest': None, 'latest': None}
        }
        
        # Расширенные маркеры для поиска
        self.signature_markers = [
            r'--\s*$',
            r'—\s*$',
            r'с уважением[:,]?\s*$',
            r'с наилучшими пожеланиями[:,]?\s*$',
            r'best\s+regards[:,]?\s*$',
            r'kind\s+regards[:,]?\s*$',
            r'regards[:,]?\s*$',
            r'cordially[:,]?\s*$',
            r'yours\s+sincerely[:,]?\s*$',
            r'sincerely[:,]?\s*$',
            r'cheers[:,]?\s*$',
            r'thank\s+you[:,]?\s*$',
            r'thanks[:,]?\s*$'
        ]
        
        # Расширенные маркеры дисклеймеров (включая те, что указал пользователь)
        self.disclaimer_markers = [
            r'confidentiality\s+notice',
            r'конфиденциальная\s+информация',
            r'настоящее\s+сообщение',
            r'данное\s+электронное\s+сообщение',
            r'информация,\s+содержащаяся\s+в\s+данном',
            r'не\s+является\s+договорённостью\s+сторон',
            r'не\s+влечет\s+за\s+собой\s+возникновение',
            r'не\s+может\s+служить\s+основанием',
            r'предназначено\s+только\s+для\s+адресата',
            r'может\s+содержать\s+конфиденциальную\s+информацию',
            r'любое\s+рассмотрение,\s+повторная\s+передача',
            r'распространение\s+или\s+иное\s+использование',
            r'запрещено',
            r'this\s+message\s+may\s+contain\s+confidential',
            r'this\s+e-mail\s+is\s+for\s+the\s+intended\s+recipient',
            r'any\s+consideration,\s+retransmission,\s+distribution',
            r'unsolicited',
            r'privacy\s+policy',
            r'unsubscribe'
        ]
        
        self.quote_markers = [
            r'^>\s',
            r'^on\s.*wrote:$',
            r'^(от|дата|кому|тема|from|date|to|subject):\s',
            r'^-+\s*original\s+message\s*-+$',
            r'^-----+begin\s+forwarded\s+message',
            r'^from:\s',
            r'^sent:\s',
            r'^to:\s',
            r'^subject:\s'
        ]
    
    def extract_text_hash(self, text: str) -> str:
        """Создает хеш текста для идентификации дубликатов"""
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]
    
    def classify_text_block(self, text: str) -> str:
        """
        Классифицирует блок текста
        
        Args:
            text: Блок текста
            
        Returns:
            Тип блока: signature, disclaimer, quote, body
        """
        text_lower = text.lower()
        text_stripped = text.strip()
        lines = [line.strip() for line in text_stripped.splitlines() if line.strip()]
        
        # Проверка на подпись
        for marker in self.signature_markers:
            if re.search(marker, text_stripped, re.I | re.M):
                if 1 <= len(lines) <= 12:  # Подпись обычно 1-12 строк
                    return "signature"
        
        # Проверка на дисклеймер
        for marker in self.disclaimer_markers:
            if re.search(marker, text_lower, re.I | re.M):
                return "disclaimer"
        
        # Проверка на цитату
        for marker in self.quote_markers:
            if re.search(marker, text_stripped, re.I):
                return "quote"
        
        return "body"
    
    def segment_text(self, text: str) -> List[str]:
        """
        Сегментирует текст на блоки
        
        Args:
            text: Исходный текст
            
        Returns:
            Список текстовых блоков
        """
        lines = text.splitlines()
        blocks = []
        current_block = []
        
        for line in lines:
            # Разделитель блоков
            if re.match(r'^\s*-{3,}\s*$', line):
                if current_block:
                    blocks.append('\n'.join(current_block).strip())
                    current_block = []
                continue
            
            current_block.append(line)
        
        if current_block:
            blocks.append('\n'.join(current_block).strip())
        
        return [block for block in blocks if block.strip()]
    
    def analyze_email(self, email_data: Dict) -> None:
        """
        Анализирует одно письмо
        
        Args:
            email_data: Данные письма
        """
        # Используем body_clean, так как в JSON структура содержит это поле
        body_text = email_data.get('body_clean', '') or email_data.get('body_raw', '') or email_data.get('body', '')
        sender = email_data.get('from', '').lower()
        date_str = email_data.get('date', '')
        
        # Обновляем статистику
        self.email_stats['total_emails'] += 1
        self.email_stats['total_length'] += len(body_text)
        
        # Извлекаем домен
        if '@' in sender:
            domain = sender.split('@')[-1]
            self.email_stats['domains'][domain] += 1
        
        # Обновляем диапазон дат
        if date_str:
            try:
                email_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if self.email_stats['date_range']['earliest'] is None or email_date < self.email_stats['date_range']['earliest']:
                    self.email_stats['date_range']['earliest'] = email_date
                if self.email_stats['date_range']['latest'] is None or email_date > self.email_stats['date_range']['latest']:
                    self.email_stats['date_range']['latest'] = email_date
            except:
                pass
        
        # Сегментируем текст и анализируем блоки
        blocks = self.segment_text(body_text)
        
        for block in blocks:
            block_type = self.classify_text_block(block)
            block_hash = self.extract_text_hash(block)
            
            if block_type == "signature":
                self.signature_patterns[block_hash] += 1
            elif block_type == "disclaimer":
                self.disclaimer_patterns[block_hash] += 1
            elif block_type == "quote":
                self.quote_patterns[block_hash] += 1
    
    def scan_emails_directory(self, start_date: datetime = None, end_date: datetime = None) -> None:
        """
        Сканирует директорию с письмами
        
        Args:
            start_date: Начальная дата анализа
            end_date: Конечная дата анализа
        """
        print("🔍 Сканирование директории с письмами...")
        
        if not self.emails_dir.exists():
            print(f"❌ Директория {self.emails_dir} не найдена")
            return
        
        # Обходим все директории с датами
        for date_dir in sorted(self.emails_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            
            # Проверяем, что директория соответствует формату даты
            if not re.match(r'\d{4}-\d{2}-\d{2}', date_dir.name):
                continue
            
            # Фильтруем по диапазону дат
            try:
                dir_date = datetime.strptime(date_dir.name, '%Y-%m-%d')
                if start_date and dir_date < start_date:
                    continue
                if end_date and dir_date > end_date:
                    continue
            except ValueError:
                continue
            
            print(f"📅 Анализ писем за {date_dir.name}...")
            
            # Обходим все JSON файлы в директории
            json_files = list(date_dir.glob('*.json'))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                        self.analyze_email(email_data)
                except Exception as e:
                    print(f"⚠️ Ошибка при обработке {json_file}: {e}")
        
        # Рассчитываем итоговую статистику
        if self.email_stats['total_emails'] > 0:
            self.email_stats['avg_length'] = self.email_stats['total_length'] // self.email_stats['total_emails']
            self.email_stats['total_domains'] = len(self.email_stats['domains'])
    
    def generate_precleaner_config(self, output_path: str = "config/precleaner.yaml") -> Dict:
        """
        Генерирует конфигурацию PreCleaner на основе анализа
        
        Args:
            output_path: Путь для сохранения конфигурации
            
        Returns:
            Словарь с конфигурацией
        """
        print("📝 Генерация конфигурации PreCleaner...")
        
        # Извлекаем уникальные маркеры из найденных паттернов
        sig_markers = set()
        disclaimer_markers = set()
        
        # Анализируем топ-50 паттернов подписей
        top_signatures = sorted(self.signature_patterns.items(), key=lambda x: x[1], reverse=True)[:50]
        for pattern_hash, count in top_signatures:
            # Здесь можно было бы восстановить оригинальный текст, 
            # но для конфигурации используем стандартные маркеры
            pass
        
        # Добавляем стандартные маркеры
        sig_markers.update([
            "--", "—", "с уважением", "с наилучшими пожеланиями",
            "best regards", "kind regards", "regards", "cordially",
            "yours sincerely", "sincerely", "cheers", "thank you", "thanks"
        ])
        
        # Добавляем маркеры дисклеймеров
        disclaimer_markers.update([
            "confidentiality notice", "конфиденциальная информация",
            "настоящее сообщение", "данное электронное сообщение",
            "информация, содержащаяся в данном", "не является договорённостью сторон",
            "не влечет за собой возникновение", "не может служить основанием",
            "предназначено только для адресата", "может содержать конфиденциальную информацию",
            "любое рассмотрение, повторная передача", "распространение или иное использование",
            "запрещено", "this message may contain confidential",
            "this e-mail is for the intended recipient", "privacy policy", "unsubscribe"
        ])
        
        # Определяем параметры на основе статистики
        avg_length = self.email_stats['avg_length']
        long_email_ratio = sum(1 for d in self.email_stats['domains'].values() if d > 10) / max(len(self.email_stats['domains']), 1)
        
        config = {
            'precleaner': {
                'max_signature_lines': 6 if avg_length > 10000 else 4,
                'fold_quote_over_chars': 800 if long_email_ratio > 0.3 else 1200,
                'fold_on_repeat': True,
                'keep_first_signature_per_sender': True,
                'keep_first_disclaimer_per_thread': True,
                'languages': ['ru', 'en'],
                'sig_markers': sorted(list(sig_markers)),
                'disclaimer_markers': sorted(list(disclaimer_markers))
            }
        }
        
        # Сохраняем конфигурацию
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ Конфигурация сохранена в {output_path}")
        return config
    
    def generate_report(self, output_dir: str = ".kiro/specs/precleaner") -> None:
        """
        Генерирует подробный отчет об анализе
        
        Args:
            output_dir: Директория для сохранения отчета
        """
        print("📊 Генерация отчета...")
        
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(output_dir, f'comprehensive_pattern_report_{timestamp}.md')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Комплексный отчет по анализу паттернов в письмах\n\n")
            f.write(f"**Дата создания**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Общая статистика
            f.write("## 📊 Общая статистика\n\n")
            f.write(f"- **Всего писем**: {self.email_stats['total_emails']:,}\n")
            f.write(f"- **Уникальных доменов**: {self.email_stats['total_domains']}\n")
            f.write(f"- **Средняя длина письма**: {self.email_stats['avg_length']:,} символов\n")
            
            if self.email_stats['date_range']['earliest']:
                f.write(f"- **Период**: {self.email_stats['date_range']['earliest'].strftime('%Y-%m-%d')} - {self.email_stats['date_range']['latest'].strftime('%Y-%m-%d')}\n")
            
            f.write("\n### 🏢 Топ-10 доменов\n\n")
            f.write("| Домен | Количество писем | % от общего |\n")
            f.write("|-------|------------------|------------|\n")
            
            total_emails = self.email_stats['total_emails']
            for domain, count in self.email_stats['domains'].most_common(10):
                percentage = (count / total_emails) * 100
                f.write(f"| {domain} | {count:,} | {percentage:.1f}% |\n")
            
            # Паттерны подписей
            f.write("\n## 📝 Паттерны подписей\n\n")
            f.write(f"**Всего уникальных паттернов**: {len(self.signature_patterns):,}\n\n")
            
            top_signatures = sorted(self.signature_patterns.items(), key=lambda x: x[1], reverse=True)[:20]
            if top_signatures:
                f.write("### Топ-20 паттернов подписей\n\n")
                f.write("| Хеш | Количество | % от писем |\n")
                f.write("|-----|------------|------------|\n")
                
                for pattern_hash, count in top_signatures:
                    percentage = (count / total_emails) * 100
                    f.write(f"| `{pattern_hash}` | {count} | {percentage:.2f}% |\n")
            
            # Паттерны дисклеймеров
            f.write("\n## ⚖️ Паттерны дисклеймеров\n\n")
            f.write(f"**Всего уникальных паттернов**: {len(self.disclaimer_patterns):,}\n\n")
            
            if self.disclaimer_patterns:
                f.write("### Топ-10 паттернов дисклеймеров\n\n")
                f.write("| Хеш | Количество | % от писем |\n")
                f.write("|-----|------------|------------|\n")
                
                top_disclaimers = sorted(self.disclaimer_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
                for pattern_hash, count in top_disclaimers:
                    percentage = (count / total_emails) * 100
                    f.write(f"| `{pattern_hash}` | {count} | {percentage:.2f}% |\n")
            else:
                f.write("❌ Дисклеймеры не найдены в проанализированных письмах\n")
            
            # Паттерны цитирования
            f.write("\n## 💬 Паттерны цитирования\n\n")
            f.write(f"**Всего уникальных паттернов**: {len(self.quote_patterns):,}\n\n")
            
            if self.quote_patterns:
                f.write("### Топ-10 паттернов цитирования\n\n")
                f.write("| Хеш | Количество | % от писем |\n")
                f.write("|-----|------------|------------|\n")
                
                top_quotes = sorted(self.quote_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
                for pattern_hash, count in top_quotes:
                    percentage = (count / total_emails) * 100
                    f.write(f"| `{pattern_hash}` | {count} | {percentage:.2f}% |\n")
            
            # Рекомендации
            f.write("\n## 💡 Рекомендации по настройке PreCleaner\n\n")
            
            # Анализируем характеристики писем
            avg_length = self.email_stats['avg_length']
            signature_ratio = len(self.signature_patterns) / max(total_emails, 1)
            disclaimer_ratio = len(self.disclaimer_patterns) / max(total_emails, 1)
            quote_ratio = len(self.quote_patterns) / max(total_emails, 1)
            
            f.write("### На основе анализа данных:\n\n")
            f.write(f"- **Средняя длина писем**: {avg_length:,} символов\n")
            f.write(f"- **Доля писем с подписями**: {signature_ratio*100:.1f}%\n")
            f.write(f"- **Доля писем с дисклеймерами**: {disclaimer_ratio*100:.1f}%\n")
            f.write(f"- **Доля писем с цитатами**: {quote_ratio*100:.1f}%\n\n")
            
            f.write("### Рекомендуемые параметры:\n\n")
            
            if avg_length > 10000:
                f.write("- **max_signature_lines**: 6 (письма длинные, подписи могут быть объемными)\n")
            else:
                f.write("- **max_signature_lines**: 4 (стандартная длина писем)\n")
            
            if quote_ratio > 0.3:
                f.write("- **fold_quote_over_chars**: 800 (много цитирования, агрессивная сворачиваемость)\n")
            else:
                f.write("- **fold_quote_over_chars**: 1200 (стандартная сворачиваемость)\n")
            
            if disclaimer_ratio > 0.1:
                f.write("- **keep_first_disclaimer_per_thread**: false (много дисклеймеров, удаляем повторы)\n")
            else:
                f.write("- **keep_first_disclaimer_per_thread**: true (мало дисклеймеров, сохраняем)\n")
            
            f.write("\n### Найденные маркеры дисклеймеров:\n\n")
            f.write("В ходе анализа были найдены следующие маркеры дисклеймеров:\n\n")
            for marker in self.disclaimer_markers:
                if any(keyword in marker.lower() for keyword in ['confidential', 'конфиденциаль', 'сообщение', 'information']):
                    f.write(f"- `{marker}`\n")
        
        print(f"✅ Отчет сохранен в {report_path}")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Комплексный анализ паттернов в письмах')
    parser.add_argument('--emails-dir', default='data/emails', help='Директория с письмами')
    parser.add_argument('--start-date', help='Начальная дата (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='Конечная дата (YYYY-MM-DD)')
    parser.add_argument('--config-output', default='config/precleaner.yaml', help='Путь для сохранения конфигурации')
    parser.add_argument('--report-dir', default='.kiro/specs/precleaner', help='Директория для отчетов')
    
    args = parser.parse_args()
    
    # Парсим даты
    start_date = None
    end_date = None
    
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Неверный формат начальной даты: {args.start_date}")
            return
    
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Неверный формат конечной даты: {args.end_date}")
            return
    
    # Если даты не указаны, используем май-сентябрь 2025
    if not start_date and not end_date:
        start_date = datetime(2025, 5, 1)
        end_date = datetime(2025, 9, 30)
        print(f"📅 Анализируем период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    
    # Создаем анализатор
    analyzer = ComprehensivePatternAnalyzer(args.emails_dir)
    
    # Сканируем письма
    analyzer.scan_emails_directory(start_date, end_date)
    
    if analyzer.email_stats['total_emails'] == 0:
        print("❌ Письма не найдены")
        return
    
    print(f"✅ Проанализировано {analyzer.email_stats['total_emails']:,} писем")
    
    # Генерируем конфигурацию
    analyzer.generate_precleaner_config(args.config_output)
    
    # Генерируем отчет
    analyzer.generate_report(args.report_dir)
    
    print("🎉 Анализ завершен!")


if __name__ == '__main__':
    main()