#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Инспектор качества обработки вложений
Детальный анализ результатов извлечения текста из различных типов файлов
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import mimetypes

from email_loader import ProcessedEmailLoader
from attachment_processor import AttachmentProcessor


class AttachmentQualityInspector:
    """🔍 Инспектор для детального анализа качества обработки вложений"""
    
    def __init__(self):
        self.email_loader = ProcessedEmailLoader()
        self.attachment_processor = AttachmentProcessor()
        
        # Папки для результатов анализа
        self.data_dir = Path("data")
        self.quality_dir = self.data_dir / "attachment_quality"
        self.extracted_texts_dir = self.quality_dir / "extracted_texts"
        self.reports_dir = self.quality_dir / "reports"
        
        for dir_path in [self.quality_dir, self.extracted_texts_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        print("🔍 Инициализация инспектора качества вложений")
        print(f"   📁 Извлеченные тексты: {self.extracted_texts_dir}")
        print(f"   📊 Отчеты: {self.reports_dir}")

    def inspect_attachments_by_date(self, target_date: str) -> Dict:
        """📅 Детальная инспекция всех вложений за дату"""
        
        print(f"\n🔍 ИНСПЕКЦИЯ КАЧЕСТВА ВЛОЖЕНИЙ ЗА {target_date}")
        print("="*70)
        
        # Загружаем письма
        emails = self.email_loader.load_emails_by_date(target_date)
        emails_with_attachments = self.email_loader.get_emails_with_attachments(emails)
        
        if not emails_with_attachments:
            print("❌ Нет писем с вложениями для анализа")
            return {}
        
        print(f"📎 Найдено писем с вложениями: {len(emails_with_attachments)}")
        
        # Результаты инспекции
        inspection_results = {
            'inspection_date': target_date,
            'inspected_at': datetime.now().isoformat(),
            'emails_inspected': len(emails_with_attachments),
            'attachments_details': [],
            'statistics': {
                'total_attachments': 0,
                'successful_extractions': 0,
                'failed_extractions': 0,
                'by_file_type': {},
                'by_processing_method': {}
            }
        }
        
        # Обрабатываем каждое письмо
        for email_idx, email in enumerate(emails_with_attachments, 1):
            print(f"\n{'─'*50}")
            print(f"📧 ПИСЬМО {email_idx}/{len(emails_with_attachments)}")
            print(f"   От: {email.get('from', 'N/A')[:50]}...")
            print(f"   Тема: {email.get('subject', 'N/A')[:60]}...")
            
            # Детальная обработка вложений
            email_inspection = self.inspect_email_attachments(email, email_idx)
            inspection_results['attachments_details'].extend(email_inspection['attachments'])
            
            # Обновляем статистику
            self._update_statistics(inspection_results['statistics'], email_inspection['attachments'])
        
        # Сохраняем полный отчет
        self._save_inspection_report(target_date, inspection_results)
        
        # Печатаем итоговую статистику
        self._print_quality_statistics(inspection_results['statistics'])
        
        return inspection_results

    def inspect_email_attachments(self, email: Dict, email_idx: int) -> Dict:
        """📎 Детальная инспекция вложений одного письма"""
        
        attachments = email.get('attachments', [])
        email_results = {'attachments': []}
        
        print(f"   📎 Вложений для анализа: {len(attachments)}")
        
        for att_idx, attachment in enumerate(attachments, 1):
            print(f"\n   🔍 Вложение {att_idx}/{len(attachments)}: {attachment.get('original_filename', 'N/A')}")
            
            # Получаем путь к файлу
            file_path = self.email_loader.get_attachment_file_path(email, attachment)
            
            if not file_path or not file_path.exists():
                print(f"      ❌ Файл не найден")
                continue
            
            # Детальный анализ файла
            detailed_analysis = self._analyze_single_attachment(
                email, attachment, file_path, email_idx, att_idx
            )
            
            email_results['attachments'].append(detailed_analysis)
        
        return email_results

    def _analyze_single_attachment(self, email: Dict, attachment: Dict, file_path: Path, 
                                  email_idx: int, att_idx: int) -> Dict:
        """🔍 Детальный анализ одного вложения"""
        
        original_filename = attachment.get('original_filename', 'unknown')
        file_type = attachment.get('file_type', 'unknown')
        file_size = attachment.get('file_size', 0)
        
        print(f"      📁 Файл: {original_filename}")
        print(f"      📊 Тип: {file_type}")
        print(f"      📏 Размер: {file_size} байт")
        
        # Обрабатываем вложение
        try:
            processed_attachment = self.attachment_processor.process_single_attachment(
                email, attachment, self.email_loader
            )
            
            if not processed_attachment:
                return self._create_failed_analysis(attachment, file_path, "Обработка вернула None")
            
            extracted_text = processed_attachment.get('extracted_text', '')
            processing_method = processed_attachment.get('method', 'unknown')
            
            print(f"      🔧 Метод обработки: {processing_method}")
            print(f"      📝 Извлечено символов: {len(extracted_text)}")
            
            # Сохраняем извлеченный текст для детального просмотра
            text_filename = f"email_{email_idx:03d}_att_{att_idx:02d}_{original_filename}.txt"
            text_path = self.extracted_texts_dir / text_filename
            
            try:
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(f"Файл: {original_filename}\n")
                    f.write(f"Тип: {file_type}\n")
                    f.write(f"Размер: {file_size} байт\n")
                    f.write(f"Метод обработки: {processing_method}\n")
                    f.write(f"Дата анализа: {datetime.now().isoformat()}\n")
                    f.write("="*50 + "\n")
                    f.write(f"ИЗВЛЕЧЕННЫЙ ТЕКСТ:\n\n{extracted_text}")
                
                print(f"      💾 Текст сохранен: {text_filename}")
                
            except Exception as e:
                print(f"      ⚠️ Ошибка сохранения текста: {e}")
            
            # Анализ качества извлеченного текста
            quality_analysis = self._analyze_text_quality(extracted_text, processing_method, file_type)
            
            return {
                'original_filename': original_filename,
                'file_type': file_type,
                'file_size': file_size,
                'file_path': str(file_path),
                'processing_method': processing_method,
                'extracted_text_length': len(extracted_text),
                'extracted_text_preview': extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text,
                'saved_text_file': text_filename,
                'quality_analysis': quality_analysis,
                'processing_success': True,
                'processing_error': None,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"      ❌ Ошибка обработки: {e}")
            return self._create_failed_analysis(attachment, file_path, str(e))

    def _analyze_text_quality(self, extracted_text: str, processing_method: str, file_type: str) -> Dict:
        """📊 Анализ качества извлеченного текста"""
        
        if not extracted_text:
            return {
                'quality_score': 0.0,
                'quality_level': 'Неудачно',
                'issues': ['Текст не извлечен'],
                'recommendations': ['Проверить метод обработки', 'Возможно нужен OCR']
            }
        
        issues = []
        recommendations = []
        quality_score = 1.0
        
        # Анализируем длину текста
        text_length = len(extracted_text.strip())
        if text_length < 50:
            issues.append('Слишком короткий текст')
            quality_score -= 0.3
            recommendations.append('Проверить настройки извлечения текста')
        
        # Проверяем на ошибки
        error_indicators = ['[ОШИБКА', '[ERROR', 'ТРЕБУЕТСЯ', '[НЕПОДДЕРЖИВАЕМЫЙ ФОРМАТ']
        for indicator in error_indicators:
            if indicator in extracted_text:
                issues.append(f'Найден индикатор проблемы: {indicator}')
                quality_score -= 0.4
        
        # Анализируем метод обработки
        if processing_method == 'ocr':
            issues.append('Использован OCR placeholder - нужна реальная OCR обработка')
            quality_score -= 0.5
            recommendations.append('Внедрить реальную OCR библиотеку (Tesseract, easyOCR)')
            
        elif processing_method == 'description':
            issues.append('Только описание файла - текст не извлечен')
            quality_score -= 0.4
            recommendations.append('Добавить специализированную обработку для Office файлов')
        
        # Проверяем наличие полезной информации
        useful_patterns = [
            r'\+7\d{10}',  # Телефоны
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email
            r'\d+[.,]\d+',  # Цены/числа
            r'[А-Я][а-я]+ [А-Я][а-я]+',  # ФИО
        ]
        
        import re
        useful_content_found = False
        for pattern in useful_patterns:
            if re.search(pattern, extracted_text):
                useful_content_found = True
                break
        
        if useful_content_found:
            quality_score += 0.2
        else:
            issues.append('Не найдено явно полезной информации (контакты, цены, ФИО)')
            recommendations.append('Проверить корректность извлечения текста')
        
        # Определяем уровень качества
        if quality_score >= 0.8:
            quality_level = 'Отлично'
        elif quality_score >= 0.6:
            quality_level = 'Хорошо'
        elif quality_score >= 0.4:
            quality_level = 'Удовлетворительно'
        elif quality_score >= 0.2:
            quality_level = 'Плохо'
        else:
            quality_level = 'Неудачно'
        
        return {
            'quality_score': round(quality_score, 2),
            'quality_level': quality_level,
            'text_length': text_length,
            'useful_content_found': useful_content_found,
            'issues': issues,
            'recommendations': recommendations
        }

    def _create_failed_analysis(self, attachment: Dict, file_path: Path, error_msg: str) -> Dict:
        """❌ Создание результата для неудачной обработки"""
        
        return {
            'original_filename': attachment.get('original_filename', 'unknown'),
            'file_type': attachment.get('file_type', 'unknown'),
            'file_size': attachment.get('file_size', 0),
            'file_path': str(file_path),
            'processing_method': 'failed',
            'extracted_text_length': 0,
            'extracted_text_preview': '',
            'saved_text_file': None,
            'quality_analysis': {
                'quality_score': 0.0,
                'quality_level': 'Неудачно',
                'issues': [f'Ошибка обработки: {error_msg}'],
                'recommendations': ['Проверить доступность файла', 'Проверить поддержку формата']
            },
            'processing_success': False,
            'processing_error': error_msg,
            'analyzed_at': datetime.now().isoformat()
        }

    def _update_statistics(self, stats: Dict, attachments_analysis: List[Dict]):
        """📊 Обновление статистики"""
        
        for analysis in attachments_analysis:
            stats['total_attachments'] += 1
            
            if analysis['processing_success']:
                stats['successful_extractions'] += 1
            else:
                stats['failed_extractions'] += 1
            
            # По типам файлов
            file_type = analysis['file_type']
            if file_type not in stats['by_file_type']:
                stats['by_file_type'][file_type] = {'total': 0, 'successful': 0}
            
            stats['by_file_type'][file_type]['total'] += 1
            if analysis['processing_success']:
                stats['by_file_type'][file_type]['successful'] += 1
            
            # По методам обработки
            method = analysis['processing_method']
            if method not in stats['by_processing_method']:
                stats['by_processing_method'][method] = {'total': 0, 'successful': 0}
            
            stats['by_processing_method'][method]['total'] += 1
            if analysis['processing_success']:
                stats['by_processing_method'][method]['successful'] += 1

    def _save_inspection_report(self, target_date: str, results: Dict):
        """💾 Сохранение полного отчета инспекции"""
        
        report_filename = f"quality_report_{target_date.replace('-', '')}.json"
        report_path = self.reports_dir / report_filename
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Полный отчет сохранен: {report_path}")
            
            # Создаем краткий HTML отчет для удобного просмотра
            self._create_html_report(target_date, results)
            
        except Exception as e:
            print(f"❌ Ошибка сохранения отчета: {e}")

    def _create_html_report(self, target_date: str, results: Dict):
        """📄 Создание HTML отчета для удобного просмотра"""
        
        html_filename = f"quality_report_{target_date.replace('-', '')}.html"
        html_path = self.reports_dir / html_filename
        
        stats = results['statistics']
        attachments = results['attachments_details']
        
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет качества вложений - {target_date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #e8f4f8; padding: 15px; border-radius: 5px; flex: 1; }}
        .attachment {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .quality-excellent {{ background: #d4edda; }}
        .quality-good {{ background: #fff3cd; }}
        .quality-poor {{ background: #f8d7da; }}
        .quality-failed {{ background: #f1c2c3; }}
        .text-preview {{ background: #f8f9fa; padding: 10px; font-family: monospace; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Отчет качества обработки вложений</h1>
        <p><strong>Дата:</strong> {target_date}</p>
        <p><strong>Проанализировано:</strong> {results['inspected_at']}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>📊 Общая статистика</h3>
            <p>Всего вложений: <strong>{stats['total_attachments']}</strong></p>
            <p>Успешно обработано: <strong>{stats['successful_extractions']}</strong></p>
            <p>Ошибки обработки: <strong>{stats['failed_extractions']}</strong></p>
        </div>
        <div class="stat-card">
            <h3>📁 По типам файлов</h3>
            {"".join([f"<p>{file_type}: {data['successful']}/{data['total']}</p>" 
                     for file_type, data in stats['by_file_type'].items()])}
        </div>
    </div>
    
    <h2>📎 Детальный анализ вложений</h2>
    {"".join([self._create_attachment_html(att) for att in attachments])}
    
</body>
</html>"""
        
        try:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"📄 HTML отчет создан: {html_path}")
            print(f"   Откройте в браузере для удобного просмотра")
            
        except Exception as e:
            print(f"❌ Ошибка создания HTML отчета: {e}")

    def _create_attachment_html(self, attachment: Dict) -> str:
        """📎 HTML блок для одного вложения"""
        
        quality = attachment['quality_analysis']
        quality_class = {
            'Отлично': 'quality-excellent',
            'Хорошо': 'quality-good', 
            'Удовлетворительно': 'quality-good',
            'Плохо': 'quality-poor',
            'Неудачно': 'quality-failed'
        }.get(quality['quality_level'], 'quality-failed')
        
        return f"""
        <div class="attachment {quality_class}">
            <h3>📁 {attachment['original_filename']}</h3>
            <p><strong>Тип:</strong> {attachment['file_type']}</p>
            <p><strong>Размер:</strong> {attachment['file_size']} байт</p>
            <p><strong>Метод обработки:</strong> {attachment['processing_method']}</p>
            <p><strong>Извлечено символов:</strong> {attachment['extracted_text_length']}</p>
            <p><strong>Качество:</strong> {quality['quality_level']} ({quality['quality_score']})</p>
            
            {f'<p><strong>Проблемы:</strong> {", ".join(quality["issues"])}</p>' if quality['issues'] else ''}
            {f'<p><strong>Рекомендации:</strong> {", ".join(quality["recommendations"])}</p>' if quality['recommendations'] else ''}
            
            <h4>📝 Превью извлеченного текста:</h4>
            <div class="text-preview">{attachment['extracted_text_preview']}</div>
            
            {f'<p><small>💾 Полный текст: {attachment["saved_text_file"]}</small></p>' if attachment.get('saved_text_file') else ''}
        </div>"""

    def _print_quality_statistics(self, stats: Dict):
        """📊 Печать итоговой статистики качества"""
        
        print(f"\n{'='*70}")
        print(f"📊 ИТОГОВАЯ СТАТИСТИКА КАЧЕСТВА ОБРАБОТКИ ВЛОЖЕНИЙ")
        print(f"{'='*70}")
        
        print(f"📎 Всего вложений: {stats['total_attachments']}")
        print(f"✅ Успешно обработано: {stats['successful_extractions']}")
        print(f"❌ Ошибки обработки: {stats['failed_extractions']}")
        
        if stats['total_attachments'] > 0:
            success_rate = (stats['successful_extractions'] / stats['total_attachments']) * 100
            print(f"📈 Процент успеха: {success_rate:.1f}%")
        
        print(f"\n📁 СТАТИСТИКА ПО ТИПАМ ФАЙЛОВ:")
        for file_type, data in stats['by_file_type'].items():
            success_rate = (data['successful'] / data['total']) * 100 if data['total'] > 0 else 0
            print(f"   {file_type}: {data['successful']}/{data['total']} ({success_rate:.1f}%)")
        
        print(f"\n🔧 СТАТИСТИКА ПО МЕТОДАМ ОБРАБОТКИ:")
        for method, data in stats['by_processing_method'].items():
            success_rate = (data['successful'] / data['total']) * 100 if data['total'] > 0 else 0
            print(f"   {method}: {data['successful']}/{data['total']} ({success_rate:.1f}%)")
        
        print(f"{'='*70}")


def main():
    """🧪 Главная функция для тестирования инспектора качества"""
    
    print("🔍 ИНСПЕКЦИЯ КАЧЕСТВА ОБРАБОТКИ ВЛОЖЕНИЙ")
    print("="*70)
    
    # Создаем инспектор
    inspector = AttachmentQualityInspector()
    
    # Получаем доступные даты
    available_dates = inspector.email_loader.get_available_date_folders()
    
    if not available_dates:
        print("❌ Нет обработанных писем для анализа")
        print("   Сначала запустите advanced_email_fetcher_v2_fixed.py")
        return
    
    print(f"📅 Доступные даты: {available_dates}")
    
    # Выбираем последнюю дату для анализа
    target_date = available_dates[-1]
    print(f"🎯 Анализируем качество за: {target_date}")
    
    # Запускаем инспекцию
    results = inspector.inspect_attachments_by_date(target_date)
    
    if results:
        print(f"\n🎉 ИНСПЕКЦИЯ ЗАВЕРШЕНА!")
        print(f"📁 Извлеченные тексты: data/attachment_quality/extracted_texts/")
        print(f"📊 Отчеты: data/attachment_quality/reports/")
        print(f"📄 Откройте HTML отчет в браузере для детального просмотра")


if __name__ == '__main__':
    main()
