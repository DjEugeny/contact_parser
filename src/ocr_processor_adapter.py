#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔌 Адаптер для интеграции OCRProcessor с существующим интерфейсом IntegratedLLMProcessor
"""

from pathlib import Path
from typing import Dict, List, Optional
from ocr_processor import OCRProcessor

class OCRProcessorAdapter:
    """🔌 Адаптер для совместимости OCRProcessor с AttachmentProcessor интерфейсом"""
    
    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.data_dir = Path("data")
        self.attachments_dir = self.data_dir / "attachments"
        
    def process_email_attachments(self, email: Dict, email_loader) -> Dict:
        """📎 Обработка вложений письма через OCRProcessor"""
        
        attachments = email.get('attachments', [])
        if not attachments:
            return {
                'attachments_processed': 0,
                'attachments_text': [],
                'total_text_length': 0
            }
        
        # Извлекаем дату из email для проверки кэша
        # Приоритет: date_folder (уже в формате YYYY-MM-DD) -> parsed_date -> date
        date_for_cache = email.get('date_folder')
        
        if not date_for_cache:
            # Пробуем parsed_date
            parsed_date = email.get('parsed_date', '')
            if parsed_date:
                try:
                    from datetime import datetime
                    # parsed_date в формате ISO: "2025-07-01T14:37:39+07:00"
                    if 'T' in parsed_date:
                        date_for_cache = parsed_date.split('T')[0]  # Берем только дату
                except Exception:
                    pass
        
        if not date_for_cache:
            # Последняя попытка - парсим поле date
            email_date = email.get('date', '')
            if email_date:
                try:
                    from datetime import datetime
                    if isinstance(email_date, str):
                        # Парсим различные форматы дат
                        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d']:
                            try:
                                parsed_date = datetime.strptime(email_date[:10], fmt)
                                date_for_cache = parsed_date.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                continue
                        
                        # Если не удалось распарсить, попробуем извлечь из строки
                        if not date_for_cache and len(email_date) >= 10:
                            date_part = email_date[:10]
                            if date_part.count('-') == 2 or date_part.count('/') == 2 or date_part.count('.') == 2:
                                date_for_cache = date_part.replace('/', '-').replace('.', '-')
                except Exception:
                    pass
        
        print(f"   📎 К обработке: {len(attachments)} из {len(attachments)} вложений")
        if date_for_cache:
            print(f"   📅 Дата для проверки кэша: {date_for_cache}")
        
        processed_attachments = []
        total_text_length = 0
        
        for i, attachment in enumerate(attachments, 1):
            try:
                # Получаем путь к файлу вложения
                file_path_str = attachment.get('file_path', '')
                if not file_path_str:
                    print(f"      ⚠️ {i}/{len(attachments)}: Путь к файлу не указан")
                    continue
                
                attachment_path = Path(file_path_str)
                if not attachment_path.exists():
                    print(f"      ⚠️ {i}/{len(attachments)}: Файл не найден - {attachment_path}")
                    continue
                
                print(f"      ✅ {i}/{len(attachments)}: {attachment_path.name}")
                
                # Обрабатываем файл через OCRProcessor
                ocr_result = self.ocr_processor.extract_text_from_file(attachment_path, date=date_for_cache)
                
                if ocr_result.get('success'):
                    text = ocr_result.get('text', '')
                    method = ocr_result.get('method', 'unknown')
                    confidence = ocr_result.get('confidence', 0)
                    
                    processed_attachments.append({
                        'file_name': attachment_path.name,
                        'file_path': str(attachment_path),
                        'text': text,
                        'method': method,
                        'confidence': confidence,
                        'success': True
                    })
                    
                    total_text_length += len(text)
                    print(f"         📝 Извлечено {len(text)} символов ({method}, confidence: {confidence:.2%})")
                else:
                    error = ocr_result.get('error', 'Unknown error')
                    print(f"         ❌ Ошибка OCR: {error}")
                    
                    processed_attachments.append({
                        'file_name': attachment_path.name,
                        'file_path': str(attachment_path),
                        'text': '',
                        'method': 'failed',
                        'confidence': 0,
                        'success': False,
                        'error': error
                    })
                    
            except Exception as e:
                print(f"      ❌ {i}/{len(attachments)}: Ошибка обработки - {e}")
                processed_attachments.append({
                    'file_name': attachment.get('file_name', 'unknown'),
                    'file_path': attachment.get('file_path', ''),
                    'text': '',
                    'method': 'error',
                    'confidence': 0,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'attachments_processed': len([a for a in processed_attachments if a['success']]),
            'attachments_text': processed_attachments,
            'total_text_length': total_text_length
        }
    
    def combine_email_with_attachments(self, email: Dict, attachments_result: Dict) -> str:
        """🔗 Объединение текста письма с содержимым вложений"""
        
        # Базовый текст письма
        email_text = email.get('body', '') or email.get('text', '') or ''
        
        # Добавляем заголовки
        combined_text = f"ТЕМА: {email.get('subject', '')}\n"
        combined_text += f"ОТ: {email.get('from', '')}\n"
        combined_text += f"К: {email.get('to', '')}\n"
        combined_text += f"ДАТА: {email.get('date', '')}\n"
        combined_text += f"THREAD ID: {email.get('thread_id', '')}\n"
        combined_text += "=" * 50 + "\n\n"
        combined_text += email_text
        
        # Добавляем текст из вложений
        attachments_text = attachments_result.get('attachments_text', [])
        if attachments_text:
            combined_text += "\n\n" + "=" * 50 + "\n"
            combined_text += "СОДЕРЖИМОЕ ВЛОЖЕНИЙ:\n"
            combined_text += "=" * 50 + "\n\n"
            
            for i, attachment in enumerate(attachments_text, 1):
                if attachment.get('success') and attachment.get('text'):
                    combined_text += f"--- ВЛОЖЕНИЕ {i}: {attachment['file_name']} ---\n"
                    combined_text += f"Метод обработки: {attachment['method']}\n"
                    combined_text += f"Уверенность: {attachment['confidence']:.2%}\n"
                    combined_text += "=" * 30 + "\n"
                    combined_text += attachment['text']
                    combined_text += "\n\n"
        
        return combined_text
