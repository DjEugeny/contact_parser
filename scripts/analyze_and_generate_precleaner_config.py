#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Скрипт для анализа писем и автоматического формирования конфигурации PreCleaner.

Проанализирует письма в папке data/emails, найдет паттерны подписей,
дисклеймеров и цитирования, затем создаст оптимальную конфигурацию
config/precleaner.yaml на основе найденных паттернов.
"""

import json
import logging
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetcher.utils.enhanced_text_cleaner import EnhancedTextCleaner

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailPatternAnalyzer:
    """🔍 Анализатор паттернов в письмах"""
    
    def __init__(self, emails_dir: str = "data/emails"):
        self.emails_dir = Path(emails_dir)
        self.patterns = {
            'signatures': Counter(),
            'disclaimers': Counter(),
            'quotes': Counter(),
            'headers': Counter()
        }
        self.email_stats = {
            'total_emails': 0,
            'total_length': 0,
            'avg_length': 0,
            'long_emails': 0,
            'domains': Counter()
        }
        
    def analyze_emails(self, limit_days: int = 7) -> Dict:
        """
        🔍 Анализирует письма за последние N дней
        
        Args:
            limit_days: Количество дней для анализа
            
        Returns:
            Словарь с результатами анализа
        """
        logger.info(f"🔍 Начинаем анализ писем за последние {limit_days} дней...")
        
        # Получаем последние папки с письмами
        date_dirs = sorted(self.emails_dir.iterdir())[-limit_days:]
        
        for date_dir in date_dirs:
            if not date_dir.is_dir():
                continue
                
            logger.info(f"📂 Анализируем папку: {date_dir.name}")
            
            for json_file in date_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        email_data = json.load(f)
                    
                    self._analyze_single_email(email_data)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки файла {json_file}: {e}")
        
        # Рассчитываем статистику
        self._calculate_stats()
        
        return {
            'patterns': dict(self.patterns),
            'stats': self.email_stats
        }
    
    def _analyze_single_email(self, email_data: Dict):
        """🔍 Анализирует одно письмо"""
        body = email_data.get('body_clean', '') or email_data.get('body_raw', '')
        sender = email_data.get('from', '').lower()
        domain = sender.split('@')[-1] if '@' in sender else 'unknown'
        
        # Обновляем статистику
        self.email_stats['total_emails'] += 1
        self.email_stats['total_length'] += len(body)
        self.email_stats['domains'][domain] += 1
        
        if len(body) > 50000:  # Длинные письма
            self.email_stats['long_emails'] += 1
        
        # Анализируем паттерны
        self._extract_patterns(body, sender)
    
    def _extract_patterns(self, body: str, sender: str):
        """🔍 Извлекает паттерны из тела письма"""
        lines = body.split('\n')
        
        # Ищем подписи
        signature_patterns = self._find_signature_patterns(lines)
        for pattern in signature_patterns:
            self.patterns['signatures'][pattern] += 1
        
        # Ищем дисклеймеры
        disclaimer_patterns = self._find_disclaimer_patterns(body)
        for pattern in disclaimer_patterns:
            self.patterns['disclaimers'][pattern] += 1
        
        # Ищем цитаты
        quote_patterns = self._find_quote_patterns(lines)
        for pattern in quote_patterns:
            self.patterns['quotes'][pattern] += 1
    
    def _find_signature_patterns(self, lines: List[str]) -> List[str]:
        """🔍 Ищет паттерны подписей"""
        patterns = []
        
        # Маркеры начала подписи
        sig_markers = [
            r'--\s*$',
            r'—\s*$',
            r'с уважением',
            r'best regards',
            r'kind regards',
            r'с наилучшими пожеланиями',
            r'regards',
            r'сincerely',
            r'cheers'
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip().lower()
            
            # Проверяем маркеры подписи
            for marker in sig_markers:
                if re.search(marker, line_clean, re.IGNORECASE):
                    # Извлекаем следующие 5-7 строк как подпись
                    signature_lines = []
                    for j in range(i + 1, min(i + 8, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        if len(next_line) > 100:  # Слишком длинная строка, скорее всего не подпись
                            break
                        signature_lines.append(next_line)
                    
                    if signature_lines:
                        signature = ' | '.join(signature_lines[:3])  # Берем первые 3 строки
                        patterns.append(signature)
                    break
        
        return patterns
    
    def _find_disclaimer_patterns(self, body: str) -> List[str]:
        """🔍 Ищет паттерны дисклеймеров"""
        patterns = []
        
        # Маркеры дисклеймеров
        disclaimer_markers = [
            r'confidentiality notice',
            r'настоящее сообщение',
            r'this message may contain confidential',
            r'unsubscribe',
            r'privacy policy',
            r'конфиденциальная информация',
            r'отписаться',
            r'отказ от ответственности'
        ]
        
        # Разбиваем на абзацы
        paragraphs = re.split(r'\n\s*\n', body)
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            
            # Проверяем маркеры дисклеймера
            for marker in disclaimer_markers:
                if re.search(marker, paragraph_lower, re.IGNORECASE):
                    # Нормализуем абзац
                    clean_para = re.sub(r'\s+', ' ', paragraph.strip())
                    if 50 < len(clean_para) < 500:  # Разумная длина дисклеймера
                        patterns.append(clean_para[:100])  # Берем первые 100 символов
                    break
        
        return patterns
    
    def _find_quote_patterns(self, lines: List[str]) -> List[str]:
        """🔍 Ищет паттерны цитирования"""
        patterns = []
        
        # Маркеры цитирования
        quote_markers = [
            r'^on .* wrote:$',
            r'^от .* писал\(а\):$',
            r'^в .* wrote:$',
            r'^(от|дата|кому|тема|from|date|to|subject):\s'
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Проверяем маркеры цитирования
            for marker in quote_markers:
                if re.search(marker, line_clean, re.IGNORECASE):
                    # Извлекаем следующие несколько строк как заголовок цитаты
                    quote_header = line_clean
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                        if re.match(r'^[a-zа-я]+:\s', next_line, re.IGNORECASE):
                            quote_header += ' | ' + next_line
                        else:
                            break
                    
                    patterns.append(quote_header)
                    break
        
        # Также ищем строки с >
        quote_lines = [line.strip() for line in lines if line.strip().startswith('>')]
        if quote_lines:
            # Берем образец цитирования
            patterns.append(f"> {quote_lines[0][1:][:50]}")
        
        return patterns
    
    def _calculate_stats(self):
        """📊 Рассчитывает общую статистику"""
        if self.email_stats['total_emails'] > 0:
            self.email_stats['avg_length'] = (
                self.email_stats['total_length'] // self.email_stats['total_emails']
            )
    
    def generate_precleaner_config(self, output_path: str = "config/precleaner.yaml") -> Dict:
        """
        ⚙️ Генерирует конфигурацию PreCleaner на основе анализа
        
        Args:
            output_path: Путь для сохранения конфигурации
            
        Returns:
            Словарь с конфигурацией
        """
        logger.info("⚙️ Генерируем конфигурацию PreCleaner...")
        
        # Получаем топ паттерны
        top_signatures = self.patterns['signatures'].most_common(20)
        top_disclaimers = self.patterns['disclaimers'].most_common(20)
        top_quotes = self.patterns['quotes'].most_common(10)
        
        # Извлекаем уникальные маркеры
        sig_markers = set()
        disclaimer_markers = set()
        
        # Анализируем подписи для извлечения маркеров
        for pattern, count in top_signatures:
            if count >= 2:  # Только паттерны, которые встречаются минимум 2 раза
                # Ищем маркеры в паттерне
                for marker in ['--', '—', 'с уважением', 'best regards', 'kind regards', 'regards']:
                    if marker.lower() in pattern.lower():
                        sig_markers.add(marker)
        
        # Анализируем дисклеймеры для извлечения маркеров
        for pattern, count in top_disclaimers:
            if count >= 2:  # Только паттерны, которые встречаются минимум 2 раза
                # Ищем маркеры в паттерне
                for marker in ['confidentiality', 'настоящее сообщение', 'unsubscribe', 'privacy policy']:
                    if marker.lower() in pattern.lower():
                        disclaimer_markers.add(marker)
        
        # Определяем параметры на основе статистики
        avg_email_length = self.email_stats['avg_length']
        long_email_ratio = self.email_stats['long_emails'] / max(1, self.email_stats['total_emails'])
        
        # Настраиваем параметры
        max_signature_lines = 6 if avg_email_length > 10000 else 4
        fold_quote_over_chars = 800 if long_email_ratio > 0.3 else 1200
        
        # Формируем конфигурацию
        config = {
            'precleaner': {
                'max_signature_lines': max_signature_lines,
                'fold_quote_over_chars': fold_quote_over_chars,
                'fold_on_repeat': True,
                'keep_first_signature_per_sender': True,
                'keep_first_disclaimer_per_thread': True,
                'languages': ['ru', 'en'],
                'sig_markers': sorted(list(sig_markers)),
                'disclaimer_markers': sorted(list(disclaimer_markers))
            },
            '_metadata': {
                'generated_at': datetime.now().isoformat(),
                'analyzed_emails': self.email_stats['total_emails'],
                'avg_email_length': avg_email_length,
                'long_email_ratio': long_email_ratio,
                'top_signatures_count': len(top_signatures),
                'top_disclaimers_count': len(top_disclaimers),
                'top_quotes_count': len(top_quotes)
            }
        }
        
        # Сохраняем конфигурацию
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"✅ Конфигурация сохранена: {output_path}")
        
        return config
    
    def generate_report(self, output_dir: str = "data/reports") -> str:
        """
        📊 Генерирует отчет об анализе паттернов
        
        Args:
            output_dir: Директория для сохранения отчета
            
        Returns:
            Путь к сохраненному отчету
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f"precleaner_analysis_report_{timestamp}.md")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 📊 Отчет об анализе паттернов для PreCleaner\n\n")
            f.write(f"**Дата анализа:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Общая статистика
            f.write("## 📈 Общая статистика\n\n")
            f.write(f"- **Всего писем проанализировано:** {self.email_stats['total_emails']:,}\n")
            f.write(f"- **Средняя длина письма:** {self.email_stats['avg_length']:,} символов\n")
            f.write(f"- **Длинных писем (>50К):** {self.email_stats['long_emails']:,} ({self.email_stats['long_emails']/max(1, self.email_stats['total_emails'])*100:.1f}%)\n\n")
            
            # Топ домены
            f.write("### 🌐 Топ домены отправителей\n\n")
            for domain, count in self.email_stats['domains'].most_common(10):
                f.write(f"- **{domain}:** {count} писем\n")
            f.write("\n")
            
            # Топ подписи
            f.write("## ✍️ Топ паттерны подписей\n\n")
            f.write("| Маркер | Количество | Пример |\n")
            f.write("|--------|------------|--------|\n")
            
            for pattern, count in self.patterns['signatures'].most_common(15):
                if count >= 2:  # Только паттерны, которые встречаются минимум 2 раза
                    # Извлекаем маркер
                    marker = "неизвестно"
                    for m in ['--', '—', 'с уважением', 'best regards', 'kind regards', 'regards']:
                        if m.lower() in pattern.lower():
                            marker = m
                            break
                    
                    # Обрезаем пример
                    example = pattern[:50] + "..." if len(pattern) > 50 else pattern
                    example = example.replace("|", " ").replace("\n", " ")
                    
                    f.write(f"| {marker} | {count} | {example} |\n")
            f.write("\n")
            
            # Топ дисклеймеры
            f.write("## 📄 Топ паттерны дисклеймеров\n\n")
            f.write("| Маркер | Количество | Пример |\n")
            f.write("|--------|------------|--------|\n")
            
            for pattern, count in self.patterns['disclaimers'].most_common(15):
                if count >= 2:  # Только паттерны, которые встречаются минимум 2 раза
                    # Извлекаем маркер
                    marker = "неизвестно"
                    for m in ['confidentiality', 'настоящее сообщение', 'unsubscribe', 'privacy policy']:
                        if m.lower() in pattern.lower():
                            marker = m
                            break
                    
                    # Обрезаем пример
                    example = pattern[:50] + "..." if len(pattern) > 50 else pattern
                    example = example.replace("|", " ").replace("\n", " ")
                    
                    f.write(f"| {marker} | {count} | {example} |\n")
            f.write("\n")
            
            # Топ цитаты
            f.write("## 💬 Топ паттерны цитирования\n\n")
            f.write("| Количество | Пример |\n")
            f.write("|------------|--------|\n")
            
            for pattern, count in self.patterns['quotes'].most_common(10):
                if count >= 2:  # Только паттерны, которые встречаются минимум 2 раза
                    # Обрезаем пример
                    example = pattern[:50] + "..." if len(pattern) > 50 else pattern
                    example = example.replace("|", " ").replace("\n", " ")
                    
                    f.write(f"| {count} | {example} |\n")
            f.write("\n")
            
            # Рекомендации
            f.write("## 💡 Рекомендации по конфигурации\n\n")
            f.write(f"- **Максимальное количество строк подписи:** {6 if self.email_stats['avg_length'] > 10000 else 4}\n")
            f.write(f"- **Порог сворачивания цитат:** {800 if self.email_stats['long_emails']/max(1, self.email_stats['total_emails']) > 0.3 else 1200} символов\n")
            f.write("- **Языки:** ru, en\n")
            f.write(f"- **Найдено уникальных маркеров подписей:** {len(self.patterns['signatures'])}\n")
            f.write(f"- **Найдено уникальных маркеров дисклеймеров:** {len(self.patterns['disclaimers'])}\n")
            f.write(f"- **Найдено уникальных маркеров цитирования:** {len(self.patterns['quotes'])}\n")
        
        logger.info(f"📊 Отчет сохранен: {report_path}")
        return report_path


def main():
    """🚀 Основная функция"""
    logger.info("🚀 Запускаем анализ писем для генерации конфигурации PreCleaner...")
    
    # Создаем анализатор
    analyzer = EmailPatternAnalyzer()
    
    # Анализируем письма
    results = analyzer.analyze_emails(limit_days=7)
    
    # Генерируем конфигурацию
    config = analyzer.generate_precleaner_config()
    
    # Генерируем отчет
    report_path = analyzer.generate_report()
    
    # Выводим результаты
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА ПИСЕМ")
    print("="*60)
    print(f"📧 Проанализировано писем: {results['stats']['total_emails']:,}")
    print(f"📏 Средняя длина письма: {results['stats']['avg_length']:,} символов")
    print(f"📄 Длинных писем (>50К): {results['stats']['long_emails']:,}")
    print(f"🔍 Найдено паттернов подписей: {len(results['patterns']['signatures'])}")
    print(f"📋 Найдено паттернов дисклеймеров: {len(results['patterns']['disclaimers'])}")
    print(f"💬 Найдено паттернов цитирования: {len(results['patterns']['quotes'])}")
    print(f"⚙️ Конфигурация сохранена: config/precleaner.yaml")
    print(f"📊 Отчет сохранен: {report_path}")
    print("="*60)
    
    logger.info("✅ Анализ завершен успешно!")


if __name__ == "__main__":
    main()