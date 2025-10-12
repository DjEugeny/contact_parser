#!/usr/bin/env python3
"""
Упрощенный тестовый скрипт для проверки улучшений PreCleaner
"""

import json
import re
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple

@dataclass
class TextBlock:
    text: str
    kind: str = "body"

@dataclass
class PreCleanResult:
    body_clean: str
    body_clean_llm: str
    char_count: int
    clean_spans: List[Dict[str, Any]]
    stats: Dict[str, Any]

def fingerprint(text: str) -> str:
    """Создание хэша текста"""
    t = re.sub(r'\s+', ' ', text.strip().lower())
    return hashlib.sha1(t.encode('utf-8')).hexdigest()[:12]

def classify_improved(text: str, config: Dict[str, Any]) -> str:
    """Улучшенная классификация блоков текста"""
    t = text.strip().lower()
    
    # Проверка на заголовки цитат (русскоязычные и англоязычные)
    quote_header_patterns = [
        r'^(кому|от|тема|дата|копия|скрытая копия)\s*:\s',
        r'^(from|to|subject|date|cc|bcc)\s*:\s',
        r'^-\s*original\s+message\s*-*$',
        r'^\s*перенаправленное\s+сообщение\s*$',
        r'^\s*begin\s+forwarded\s+message\s*$',
        r'^\s*ответ\s+на\s*:$'
    ]
    
    # Проверка на цитаты с заголовками
    if any(re.search(p, t, re.I | re.M) for p in quote_header_patterns):
        return "quote"
    
    # Проверка на цитаты с классическими маркерами
    if t.startswith('>') or (t.startswith('on ') and 'wrote:' in t):
        return "quote"
    
    # Проверка на цитаты с маркерами пересылки
    quote_markers = [
        r'пишет',
        r'написал',
        r'писал',
        r'wrote:',
        r'writes:',
        r'forwarded message',
        r'перенаправленное сообщение',
        r'ответ на'
    ]
    
    if any(re.search(p, t, re.I) for p in quote_markers):
        return "quote"
    
    # Проверка на подписи с расширенными маркерами
    sig_patterns = [
        r'--\s*$',
        r'—\s*$',
        r'с\s+уважением',
        r'с\s+наилучшими\s+пожеланиями',
        r'best\s+regards',
        r'kind\s+regards',
        r'regards',
        r'уважаем',
        r'sincerely',
        r'yours\s+truly'
    ]
    
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if any(re.search(p, t, re.I | re.M) for p in sig_patterns):
        if 1 <= len(lines) <= config.get('max_signature_lines', 6):
            return "signature"
    
    # Проверка на дисклеймеры
    disclaimer_patterns = [
        r'confidentiality\s+notice',
        r'настоящее\s+сообщение',
        r'данное\s+электронное\s+сообщение',
        r'конфиденциальная\s+информация',
        r'не\s+является\s+договором',
        r'не\s+может\s+служить\s+основанием',
        r'только\s+для\s+адресата',
        r'unsubscribe',
        r'privacy\s+policy'
    ]
    
    if any(re.search(p, t, re.I | re.M) for p in disclaimer_patterns):
        return "disclaimer"
    
    # Проверка на заголовки писем
    header_patterns = [
        r'^-+\s*original\s+message\s*-+$',
        r'^on\s+.+\s+wrote:$',
        r'^(от|дата|кому|тема):\s'
    ]
    
    if any(re.search(p, t, re.I) for p in header_patterns):
        return "header"
    
    return "body"

def segment(text: str) -> List[TextBlock]:
    """Сегментация текста на блоки"""
    lines = text.splitlines()
    blocks, buf = [], []
    
    for line in lines:
        if re.match(r'^\s*-{3,}\s*$', line):
            if buf:
                blocks.append(TextBlock("\n".join(buf).strip()))
                buf = []
            continue
        buf.append(line)
    
    if buf:
        blocks.append(TextBlock("\n".join(buf).strip()))
    
    return blocks

def extract_important_info_from_quote(quote_text: str) -> str:
    """Извлечение важной информации из цитаты"""
    important_patterns = [
        (r'(?:телефон|тел\.|phone|мобильный|mob\.):?\s*([+\d\s\-\(\)]+)', 'Телефон'),
        (r'(?:email|e-mail|почта):?\s*([\w\.-]+@[\w\.-]+\.\w+)', 'Email'),
        (r'(?:адрес|address):?\s*([^,\n]+)', 'Адрес'),
        (r'(?:версия|version):\s*([^\s\n]+)', 'Версия'),
        (r'(?:дата|date):\s*([^\n]+)', 'Дата'),
        (r'(?:заказ|order):\s*([^\s\n]+)', 'Заказ'),
        (r'(?:счет|invoice):\s*([^\s\n]+)', 'Счет'),
        (r'(?:договор|contract):\s*([^\s\n]+)', 'Договор')
    ]
    
    important_info = []
    for pattern, label in important_patterns:
        matches = re.findall(pattern, quote_text, re.I)
        for match in matches:
            important_info.append(f"{label}: {match.strip()}")
    
    return "\n".join(important_info)

def process_quote_improved(block: TextBlock, config: Dict[str, Any]) -> List[str]:
    """Улучшенная обработка цитат"""
    lines = block.text.splitlines()
    non_empty_lines = [l for l in lines if l.strip()]
    
    # Если цитата короткая, сохраняем полностью
    if len(non_empty_lines) <= config.get('quote_preview_non_empty_lines', 30):
        return [block.text]
    
    # Извлекаем важную информацию из цитаты
    important_info = extract_important_info_from_quote(block.text)
    
    # Создаем превью цитаты
    preview_lines = []
    
    # Добавляем начало цитаты
    start_lines = config.get('quote_preview_non_empty_lines', 30)
    for i, line in enumerate(lines):
        if line.strip() and len(preview_lines) < start_lines:
            preview_lines.append(line)
        elif not line.strip():
            preview_lines.append(line)
        if len(preview_lines) >= start_lines + 5:
            break
    
    # Добавляем конец цитаты
    tail_lines = config.get('quote_preview_tail_non_empty_lines', 5)
    tail_count = 0
    for line in reversed(lines):
        if line.strip() and tail_count < tail_lines:
            preview_lines.append(line)
            tail_count += 1
        elif not line.strip():
            preview_lines.append(line)
        if tail_count >= tail_lines + 3:
            break
    
    # Формируем результат
    preview_text = "\n".join(preview_lines)
    
    # Добавляем важную информацию, если она есть
    if important_info:
        preview_text += f"\n\n[Важная информация из цитаты]\n{important_info}"
    
    # Проверяем длину
    max_chars = config.get('quote_preview_max_chars', 600)
    if len(preview_text) > max_chars:
        preview_text = preview_text[:max_chars] + "\n[цитата обрезана]"
    
    return [preview_text]

def extract_contact_info_from_signature(signature_text: str) -> str:
    """Извлечение контактной информации из подписи"""
    contact_patterns = [
        (r'(?:телефон|тел\.|phone|мобильный|mob\.):?\s*([+\d\s\-\(\)]+)', 'Телефон'),
        (r'(?:email|e-mail|почта):?\s*([\w\.-]+@[\w\.-]+\.\w+)', 'Email'),
        (r'(?:адрес|address):?\s*([^,\n]+)', 'Адрес'),
        (r'(?:сайт|web|site):?\s*([^\s\n]+)', 'Сайт'),
        (r'(?:icq|skype|telegram):?\s*([^\s\n]+)', 'Мессенджер')
    ]
    
    contact_info = []
    for pattern, label in contact_patterns:
        matches = re.findall(pattern, signature_text, re.I)
        for match in matches:
            contact_info.append(f"{label}: {match.strip()}")
    
    # Дополнительный поиск телефонов и email без меток
    phones = re.findall(r'[+]?[\d\s\-\(\)]{7,}', signature_text)
    for phone in phones:
        if len(re.sub(r'[^\d]', '', phone)) >= 7:
            contact_info.append(f"Телефон: {phone.strip()}")
    
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', signature_text)
    for email in emails:
        contact_info.append(f"Email: {email.strip()}")
    
    # Удаляем дубликаты
    unique_info = []
    seen = set()
    for info in contact_info:
        if info not in seen:
            unique_info.append(info)
            seen.add(info)
    
    return "\n".join(unique_info)

def process_signature_improved(block: TextBlock, config: Dict[str, Any]) -> List[str]:
    """Улучшенная обработка подписей"""
    lines = block.text.splitlines()
    max_lines = config.get('max_signature_lines', 6)
    
    # Если подпись короткая, сохраняем полностью
    if len(lines) <= max_lines:
        return [block.text]
    
    # Извлекаем важную контактную информацию
    important_info = extract_contact_info_from_signature(block.text)
    
    # Обрезаем подпись до допустимого размера
    trimmed_lines = []
    line_count = 0
    
    for line in lines:
        if line.strip():
            if line_count < max_lines:
                trimmed_lines.append(line)
                line_count += 1
        else:
            trimmed_lines.append(line)
    
    trimmed = "\n".join(trimmed_lines)
    
    # Добавляем важную контактную информацию
    if important_info:
        trimmed += f"\n\n[Контактная информация]\n{important_info}"
    
    return [trimmed]

def preclean_email_improved(text: str, config: Dict[str, Any]) -> PreCleanResult:
    """Улучшенная функция предочистки писем"""
    
    # Сегментация текста
    blocks = segment(text)
    
    # Классификация блоков
    classified_blocks = []
    for block in blocks:
        block.kind = classify_improved(block.text, config)
        classified_blocks.append(block)
    
    # Обработка блоков
    cleaned_chunks = []
    spans = []
    
    for block in classified_blocks:
        if block.kind == "quote":
            processed = process_quote_improved(block, config)
            cleaned_chunks.extend(processed)
        elif block.kind == "signature":
            processed = process_signature_improved(block, config)
            cleaned_chunks.extend(processed)
        elif block.kind == "disclaimer":
            # Простая обработка дисклеймеров
            lines = block.text.splitlines()
            max_lines = config.get('max_disclaimer_lines', 6)
            if len(lines) > max_lines:
                trimmed = "\n".join(lines[:max_lines])
                cleaned_chunks.append(trimmed)
            else:
                cleaned_chunks.append(block.text)
        else:
            cleaned_chunks.append(block.text)
    
    # Формирование результата
    body_clean = "\n".join(cleaned_chunks)
    
    stats = {
        'original_length': len(text),
        'cleaned_length': len(body_clean),
        'reduction_percent': (1 - len(body_clean) / len(text)) * 100 if len(text) > 0 else 0,
        'blocks_processed': len(classified_blocks),
        'quotes_found': len([b for b in classified_blocks if b.kind == "quote"]),
        'signatures_found': len([b for b in classified_blocks if b.kind == "signature"]),
        'disclaimers_found': len([b for b in classified_blocks if b.kind == "disclaimer"])
    }
    
    return PreCleanResult(
        body_clean=body_clean,
        body_clean_llm=body_clean,
        char_count=len(body_clean),
        clean_spans=spans,
        stats=stats
    )

def load_improved_config():
    """Загрузка улучшенной конфигурации"""
    return {
        'quote_preview_header_markers': [
            "Кому:", "От:", "Тема:", "Дата:", "Копия:", "Скрытая копия:",
            "From:", "To:", "Subject:", "Date:", "Cc:", "Bcc:"
        ],
        'quote_preview_markers': [
            "пишет", "написал", "писал", "wrote:", "writes:", 
            "forwarded message", "перенаправленное сообщение", "ответ на"
        ],
        'sig_markers': [
            "--", "—", "с уважением", "с наилучшими пожеланиями",
            "best regards", "kind regards", "regards", "с уважением,",
            "с наилучшими пожеланиями,", "уважаем,", "уважаемая,", "уважаемый,"
        ],
        'quote_preview_non_empty_lines': 50,
        'quote_preview_tail_non_empty_lines': 10,
        'quote_preview_max_chars': 1200,
        'max_signature_lines': 8,
        'max_disclaimer_lines': 8,
        'keep_first_signature_per_sender': True,
        'keep_first_disclaimer_per_thread': True,
        'fold_quote_over_chars': 2000
    }

def test_email(email_path, config):
    """Тестирование обработки письма"""
    print(f"\n{'='*80}")
    print(f"ТЕСТИРОВАНИЕ: {email_path}")
    print(f"{'='*80}")
    
    # Загрузка письма
    with open(email_path, 'r', encoding='utf-8') as f:
        email_data = json.load(f)
    
    original_text = email_data.get('body_raw', email_data.get('body', ''))
    original_length = len(original_text)
    
    print(f"Исходная длина: {original_length:,} символов")
    print(f"Отправитель: {email_data.get('from', '未知')}")
    print(f"Тема: {email_data.get('subject', '未知')}")
    print(f"Дата: {email_data.get('date', '未知')}")
    
    # Обработка с улучшенным PreCleaner
    try:
        result = preclean_email_improved(original_text, config)
        
        print(f"\nРЕЗУЛЬТАТЫ:")
        print(f"Обработанная длина: {result.char_count:,} символов")
        print(f"Сокращение: {result.stats['reduction_percent']:.1f}%")
        print(f"Экономия символов: {original_length - result.char_count:,}")
        
        print(f"\nСТАТИСТИКА ОБРАБОТКИ:")
        print(f"Всего блоков: {result.stats['blocks_processed']}")
        print(f"Найдено цитат: {result.stats['quotes_found']}")
        print(f"Найдено подписей: {result.stats['signatures_found']}")
        print(f"Найдено дисклеймеров: {result.stats['disclaimers_found']}")
        
        print(f"\nПРЕВЬЮ ОБРАБОТАННОГО ТЕКСТА:")
        print("-" * 60)
        preview = result.body_clean_llm[:500]
        print(preview)
        if len(result.body_clean_llm) > 500:
            print("...\n[текст обрезан для previews]")
        print("-" * 60)
        
        # Анализ содержимого
        print(f"\nАНАЛИЗ СОДЕРЖИМОГО:")
        print(f"Содержит '[quote': {'Да' if '[quote' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит '[signature': {'Да' if '[signature' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит '[disclaimer': {'Да' if '[disclaimer' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит 'Контактная информация': {'Да' if 'Контактная информация' in result.body_clean_llm else 'Нет'}")
        print(f"Содержит 'Важная информация': {'Да' if 'Важная информация' in result.body_clean_llm else 'Нет'}")
        
        # Проверка сохранения важной информации
        important_info = {
            'Телефон': bool(re.search(r'(?:телефон|тел\.|phone):?\s*[+\d\s\-\(\)]+', result.body_clean_llm, re.I)),
            'Email': bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', result.body_clean_llm)),
            'Адрес': bool(re.search(r'(?:адрес|address):?\s*[^,\n]+', result.body_clean_llm, re.I)),
            'Версия': bool(re.search(r'(?:версия|version):\s*[^\s\n]+', result.body_clean_llm, re.I))
        }
        
        print(f"\nСОХРАНЕНИЕ ВАЖНОЙ ИНФОРМАЦИИ:")
        for info_type, preserved in important_info.items():
            print(f"{info_type}: {'✅ Сохранено' if preserved else '❌ Утеряно'}")
        
        return {
            'original_length': original_length,
            'cleaned_length': result.char_count,
            'reduction': result.stats['reduction_percent'],
            'important_info_preserved': sum(important_info.values()),
            'stats': result.stats,
            'result': result
        }
        
    except Exception as e:
        print(f"\n❌ ОШИБКА ОБРАБОТКИ: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО PRECLEANER")
    print("=" * 80)
    
    # Загрузка конфигурации
    config = load_improved_config()
    print("✅ Конфигурация загружена")
    
    # Пути к тестовым письмам
    email_paths = [
        Path(__file__).parent.parent / 'data' / 'emails' / '2025-04-01' / 'email_016_20250401_20250401_himlabservice_ru_06d4360a.json',
        Path(__file__).parent.parent / 'data' / 'emails' / '2025-04-02' / 'email_023_20250402_20250402_invitro_ru_b972f810.json'
    ]
    
    results = []
    
    for email_path in email_paths:
        if email_path.exists():
            result = test_email(email_path, config)
            if result:
                results.append({
                    'email': email_path.name,
                    'result': result
                })
        else:
            print(f"\n❌ Файл не найден: {email_path}")
    
    # Сводные результаты
    print(f"\n{'='*80}")
    print("СВОДНЫЕ РЕЗУЛЬТАТЫ")
    print(f"{'='*80}")
    
    if results:
        total_original = sum(r['result']['original_length'] for r in results)
        total_cleaned = sum(r['result']['cleaned_length'] for r in results)
        total_reduction = (1 - total_cleaned / total_original) * 100 if total_original > 0 else 0
        
        print(f"Всего писем обработано: {len(results)}")
        print(f"Общий исходный размер: {total_original:,} символов")
        print(f"Общий обработанный размер: {total_cleaned:,} символов")
        print(f"Общее сокращение: {total_reduction:.1f}%")
        print(f"Общая экономия: {total_original - total_cleaned:,} символов")
        
        print(f"\nРЕЗУЛЬТАТЫ ПО ПИСЬМАМ:")
        for r in results:
            print(f"{r['email']}: {r['result']['reduction']:.1f}% сокращения, "
                  f"{r['result']['important_info_preserved']}/4 важной информации сохранено")
        
        # Оценка качества
        avg_reduction = sum(r['result']['reduction'] for r in results) / len(results)
        avg_preserved = sum(r['result']['important_info_preserved'] for r in results) / len(results)
        
        print(f"\nОЦЕНКА КАЧЕСТВА:")
        print(f"Среднее сокращение: {avg_reduction:.1f}%")
        print(f"Среднее сохранение важной информации: {avg_preserved:.1f}/4")
        
        if avg_reduction > 30 and avg_preserved > 2:
            print("✅ РЕЗУЛЬТАТ ХОРОШИЙ: эффективное сокращение с сохранением важной информации")
        elif avg_reduction > 30:
            print("⚠️ РЕЗУЛЬТАТ УДОВЛЕТВОРИТЕЛЬНЫЙ: хорошее сокращение, но теряется важная информация")
        elif avg_preserved > 2:
            print("⚠️ РЕЗУЛЬТАТ УДОВЛЕТВОРИТЕЛЬНЫЙ: важная информация сохранена, но сокращение недостаточно")
        else:
            print("❌ РЕЗУЛЬТАТ ПЛОХОЙ: требуется доработка алгоритма")
    else:
        print("❌ Ни одно письмо не было обработано")

if __name__ == "__main__":
    main()