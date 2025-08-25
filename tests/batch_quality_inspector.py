#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Пакетный инспектор качества OCR для ВСЕХ дат
Создает детальные отчеты по качеству распознавания
"""

import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к src
sys.path.append(str(Path(__file__).parent))

from email_loader import ProcessedEmailLoader
from attachment_processor import AttachmentProcessor


class BatchQualityInspector:
    """🔍 Пакетный инспектор качества OCR"""
    
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
        
        print("🔍 ПАКЕТНЫЙ ИНСПЕКТОР КАЧЕСТВА OCR")
        print("="*70)
        print(f"   📁 Извлеченные тексты: {self.extracted_texts_dir}")
        print(f"   📊 Отчеты: {self.reports_dir}")

    def inspect_all_dates(self):
        """🔍 Инспекция качества по всем датам"""
        
        available_dates = self.email_loader.get_available_date_folders()
        print(f"📅 Найдено дат для инспекции: {len(available_dates)}")
        print(f"   Даты: {', '.join(available_dates)}")
        
        all_results = {}
        total_attachments = 0
        total_success = 0
        
        for date_idx, date in enumerate(available_dates, 1):
            print(f"\n{'='*70}")
            print(f"🔍 ИНСПЕКЦИЯ КАЧЕСТВА ЗА {date} ({date_idx}/{len(available_dates)})")
            print(f"{'='*70}")
            
            # Загружаем письма за дату
            emails = self.email_loader.load_emails_by_date(date)
            emails_with_attachments = self.email_loader.get_emails_with_attachments(emails)
            
            if not emails_with_attachments:
                print(f"📭 Нет писем с вложениями за {date}")
                continue
            
            print(f"📎 Писем с вложениями: {len(emails_with_attachments)} из {len(emails)}")
            
            date_results = self.inspect_date(date, emails_with_attachments)
            all_results[date] = date_results
            
            total_attachments += date_results['total_attachments']
            total_success += date_results['successful_extractions']
            
            print(f"\n📊 ИТОГ ЗА {date}:")
            print(f"   📎 Вложений проанализировано: {date_results['total_attachments']}")
            print(f"   ✅ Успешных извлечений: {date_results['successful_extractions']}")
            if date_results['total_attachments'] > 0:
                success_rate = (date_results['successful_extractions'] / date_results['total_attachments']) * 100
                print(f"   📈 Успешность: {success_rate:.1f}%")
        
        # Создаем сводный отчет
        self.create_summary_report(all_results, total_attachments, total_success)
        
        print(f"\n🎉 ИНСПЕКЦИЯ ЗАВЕРШЕНА!")
        print(f"   📊 Сводный отчет: {self.reports_dir}/batch_quality_summary.html")

    def inspect_date(self, date: str, emails_with_attachments: list) -> dict:
        """🔍 Инспекция качества за одну дату"""
        
        date_attachments = []
        total_attachments = 0
        successful_extractions = 0
        
        for email_idx, email in enumerate(emails_with_attachments, 1):
            print(f"\n──────────────────────────────────────────────────")
            print(f"📧 ПИСЬМО {email_idx}/{len(emails_with_attachments)}")
            print(f"   От: {email.get('from', 'N/A')[:50]}...")
            print(f"   Тема: {email.get('subject', 'N/A')[:60]}...")
            
            # Получаем только скачанные вложения
            attachments = email.get('attachments', [])
            downloaded_attachments = [
                att for att in attachments 
                if att.get('status') == 'saved' and att.get('file_path')
            ]
            
            print(f"   📎 Вложений для анализа: {len(downloaded_attachments)}")
            
            for att_idx, attachment in enumerate(downloaded_attachments, 1):
                print(f"\n   🔍 Вложение {att_idx}/{len(downloaded_attachments)}: {attachment.get('original_filename')}")
                
                # Получаем путь к файлу
                file_path = self.email_loader.get_attachment_file_path(email, attachment)
                if not file_path:
                    print(f"      ❌ Файл не найден: {attachment.get('original_filename')}")
                    continue
                
                # Обрабатываем вложение
                result = self.attachment_processor.process_single_attachment(
                    email, attachment, self.email_loader
                )
                
                if result:
                    total_attachments += 1
                    
                    # Анализируем результат
                    extracted_text = result.get('extracted_text', '')
                    char_count = len(extracted_text)
                    
                    print(f"      📁 Файл: {attachment.get('original_filename')}")
                    print(f"      📊 Тип: {attachment.get('file_type')}")
                    print(f"      📏 Размер: {attachment.get('file_size')} байт")
                    print(f"      🔧 Метод обработки: {result.get('method')}")
                    print(f"      📝 Извлечено символов: {char_count}")
                    
                    if char_count > 10:  # Считаем успешным если извлечено больше 10 символов
                        successful_extractions += 1
                        print(f"      ✅ Текст извлечен успешно")
                        
                        # Сохраняем извлеченный текст
                        self.save_extracted_text(
                            date, email_idx, att_idx, 
                            attachment.get('original_filename', f'attachment_{att_idx}'),
                            extracted_text
                        )
                    else:
                        print(f"      ⚠️ Слишком мало текста или ошибка извлечения")
                    
                    # Собираем данные для отчета
                    attachment_analysis = {
                        'email_idx': email_idx,
                        'attachment_idx': att_idx,
                        'filename': attachment.get('original_filename'),
                        'file_type': attachment.get('file_type'),
                        'file_size': attachment.get('file_size'),
                        'method': result.get('method'),
                        'char_count': char_count,
                        'success': char_count > 10
                    }
                    date_attachments.append(attachment_analysis)
        
        return {
            'date': date,
            'emails_count': len(emails_with_attachments),
            'total_attachments': total_attachments,
            'successful_extractions': successful_extractions,
            'attachments_details': date_attachments
        }

    def save_extracted_text(self, date: str, email_idx: int, att_idx: int, filename: str, text: str):
        """💾 Сохранение извлеченного текста"""
        
        # Создаем безопасное имя файла
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()
        text_filename = f"email_{email_idx:03d}_att_{att_idx:02d}_{safe_filename}.txt"
        
        # Создаем папку по дате
        date_dir = self.extracted_texts_dir / date
        date_dir.mkdir(exist_ok=True)
        
        text_path = date_dir / text_filename
        
        try:
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"      💾 Текст сохранен: {text_filename}")
        except Exception as e:
            print(f"      ❌ Ошибка сохранения текста: {e}")

    def create_summary_report(self, all_results: dict, total_attachments: int, total_success: int):
        """📊 Создание сводного HTML отчета"""
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Отчет качества OCR - Пакетная обработка</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f8ff; padding: 20px; border-radius: 10px; }}
        .stats {{ background: #f9f9f9; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .date-section {{ margin: 20px 0; border-left: 4px solid #007acc; padding-left: 15px; }}
        .success {{ color: #008000; }}
        .warning {{ color: #ff8c00; }}
        .error {{ color: #dc143c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 10px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .progress-bar {{ width: 100%; height: 20px; background-color: #f0f0f0; border-radius: 10px; }}
        .progress-fill {{ height: 100%; background-color: #4CAF50; border-radius: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Отчет качества OCR - Пакетная обработка</h1>
        <p>Создано: {timestamp}</p>
    </div>
    
    <div class="stats">
        <h2>📊 Общая статистика</h2>
        <p><strong>Обработано дат:</strong> {len(all_results)}</p>
        <p><strong>Всего вложений:</strong> {total_attachments}</p>
        <p><strong>Успешных извлечений:</strong> <span class="success">{total_success}</span></p>
        <p><strong>Общая успешность:</strong> {(total_success/total_attachments*100):.1f}% ({total_success}/{total_attachments})</p>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {(total_success/total_attachments*100) if total_attachments > 0 else 0}%"></div>
        </div>
    </div>
"""
        
        for date, results in all_results.items():
            success_rate = (results['successful_extractions'] / results['total_attachments'] * 100) if results['total_attachments'] > 0 else 0
            
            html_content += f"""
    <div class="date-section">
        <h3>📅 {date}</h3>
        <p>Писем с вложениями: {results['emails_count']}</p>
        <p>Вложений обработано: {results['total_attachments']}</p>
        <p>Успешных извлечений: <span class="{'success' if success_rate > 80 else 'warning' if success_rate > 50 else 'error'}">{results['successful_extractions']} ({success_rate:.1f}%)</span></p>
        
        <table>
            <tr>
                <th>№ письма</th>
                <th>№ вложения</th>
                <th>Файл</th>
                <th>Тип</th>
                <th>Размер</th>
                <th>Метод</th>
                <th>Символов</th>
                <th>Статус</th>
            </tr>
"""
            
            for att in results['attachments_details']:
                status_class = 'success' if att['success'] else 'error'
                status_text = '✅ Успешно' if att['success'] else '❌ Ошибка'
                
                html_content += f"""
            <tr>
                <td>{att['email_idx']}</td>
                <td>{att['attachment_idx']}</td>
                <td>{att['filename']}</td>
                <td>{att['file_type']}</td>
                <td>{att['file_size']} байт</td>
                <td>{att['method']}</td>
                <td>{att['char_count']}</td>
                <td class="{status_class}">{status_text}</td>
            </tr>
"""
            
            html_content += """
        </table>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # Сохраняем отчет
        report_path = self.reports_dir / "batch_quality_summary.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📊 Сводный отчет сохранен: {report_path}")


def main():
    """🚀 Запуск пакетной инспекции качества"""
    
    inspector = BatchQualityInspector()
    inspector.inspect_all_dates()


if __name__ == '__main__':
    main()
