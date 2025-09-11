#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 ИСПРАВЛЕННЫЙ LLM тестер - без перепутывания писем и вложений + обработка Qwen3
"""

import json
import requests
import sys
import os
import re  # 🆕 Добавляем для работы с регулярными выражениями
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(str(Path(__file__).parent))
from email_loader import ProcessedEmailLoader

class CommercialOfferLLMTester:
    """🤖 Исправленный тестер коммерческих предложений с поддержкой Qwen3"""
    
    def __init__(self):
        # OpenRouter настройки
        self.api_key = "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"
        self.model = "qwen/qwen3-235b-a22b:free"
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://localhost:3000',
            'X-Title': 'Email Parser LLM Test'
        }
        
        self.email_loader = ProcessedEmailLoader()
        self.data_dir = Path("data")
        self.results_dir = self.data_dir / "llm_test_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.prompt = self.load_commercial_prompt()
        
        print(f"🤖 Настройки OpenRouter с поддержкой Qwen3:")
        print(f"   API ключ: {self.api_key[:20]}...")
        print(f"   Модель: {self.model}")
        print(f"   Endpoint: {self.base_url}")
        print(f"   🧹 Очистка <think> тегов: ✅")
    
    def load_commercial_prompt(self) -> str:
        """📝 Улучшенный промпт с требованием чистого JSON"""
        
        return """
🏢 Ты эксперт по анализу деловой переписки в сфере лабораторного оборудования.

🎯 ЗАДАЧА: Проанализируй письмо + вложения и извлеки:
1. КОНТАКТНЫЕ ДАННЫЕ  
2. КОММЕРЧЕСКИЕ ПРЕДЛОЖЕНИЯ (только если есть амплификаторы)
3. ОБЩИЙ КОНТЕКСТ

⚠️ ВАЖНО: Отвечай ТОЛЬКО в формате JSON без дополнительного текста, рассуждений и тегов!

📊 СТРУКТУРА АНАЛИЗА:

### 1. КОНТАКТЫ:
- ФИО отправителя
- Email отправителя
- Телефон (если есть)
- Организация
- Должность  
- Город

### 2. КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ:
⚡ Ищи слово "амплификатор" (любой регистр)
ЕСЛИ НАЙДЕНО - извлекай:
- № КП (или "б/н") 
- Дата КП
- Конечный пользователь
- Город пользователя
- Посредник
- Условия оплаты
- Срок поставки
- Доставка
- Действительно до
- Кто выставил
- Данные по амплификатору (артикул, модель, цена, количество)

### 3. КОНТЕКСТ:
- Тема переписки
- Суть запроса/предложения
- Статус (запрос/предложение/информация)
- Приоритет

ФОРМАТ ОТВЕТА - строго JSON без рассуждений:
{
  "contacts": {
    "sender_name": "ФИО",
    "sender_email": "email@company.ru", 
    "sender_phone": "+7-xxx-xxx-xx-xx",
    "sender_organization": "Название компании",
    "sender_position": "Должность",
    "sender_city": "Город"
  },
  "commercial_offer": {
    "found": true/false,
    "amplifier_found": true/false,
    "data": {
      "offer_number": "123" или "б/н",
      "offer_date": "2025-07-30",
      "end_user": "Название организации",
      "end_user_city": "Город",
      "intermediary": "Посредник",
      "payment_terms": "Условия оплаты", 
      "delivery_time": "Срок поставки",
      "delivery_terms": "Условия доставки",
      "valid_until": "Срок действия",
      "issuer": "Кто выставил",
      "amplifier_data": {
        "model": "Модель амплификатора",
        "article": "Артикул",
        "price": "Цена",
        "quantity": "Количество",
        "specifications": "Характеристики"
      }
    }
  },
  "context": {
    "subject": "Тема переписки",
    "request_summary": "Краткое описание сути",
    "status": "запрос/предложение/информация",
    "priority": "высокий/средний/низкий"
  }
}

ОТВЕЧАЙ ТОЛЬКО JSON БЕЗ ДОПОЛНИТЕЛЬНОГО ТЕКСТА!
"""
    
    def clean_qwen_response(self, response: str) -> str:
        """🧹 Очистка ответа Qwen3 от служебных тегов"""
        
        print(f"   🧹 Очищаем ответ от тегов Qwen3...")
        
        # 1. Убираем теги <think>...</think>
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        
        # 2. Убираем другие возможные теги
        cleaned = re.sub(r'</?[a-zA-Z][^>]*>', '', cleaned)
        
        # 3. Убираем markdown разметку
        cleaned = cleaned.replace('``````', '')
        
        # 4. Убираем лишние пробелы и переносы
        cleaned = cleaned.strip()
        
        # 5. Ищем JSON блок между фигурными скобками
        json_match = re.search(r'\{.*\}', cleaned, flags=re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            print(f"   ✅ JSON блок найден и извлечен")
            return json_text
        
        # 6. Если не нашли JSON блок, возвращаем очищенный текст
        print(f"   ⚠️ JSON блок не найден, возвращаем очищенный текст")
        return cleaned
    
    def test_specific_email(self, date: str, email_number: int) -> Dict:
        """🧪 ИСПРАВЛЕННОЕ тестирование конкретного письма"""
        
        # Проверяем подключение
        if not self.test_connection():
            return {
                'error': 'Не удалось подключиться к OpenRouter'
            }
        
        print(f"🎯 Тестирование письма #{email_number} за {date}")
        
        # Загружаем письма за дату
        emails = self.email_loader.load_emails_by_date(date)
        
        if not emails or email_number > len(emails):
            return {
                'error': f'Письмо #{email_number} не найдено за {date}. Всего писем: {len(emails)}'
            }
        
        # Берем нужное письмо
        target_email = emails[email_number - 1]
        
        print(f"📧 От: {target_email.get('from', '')[:50]}...")
        print(f"📧 Тема: {target_email.get('subject', '')[:60]}...")
        
        # 🔧 ИСПРАВЛЕНИЕ: Загружаем OCR тексты НАПРЯМУЮ из JSON письма
        extracted_texts = self.load_extracted_texts_from_email_json(target_email, date)
        
        print(f"📎 Реальное количество вложений в письме: {len(target_email.get('attachments', []))}")
        print(f"📎 Найдено OCR текстов: {len(extracted_texts)}")
        
        # Если нет вложений, показываем это явно
        if len(target_email.get('attachments', [])) == 0:
            print(f"📭 В этом письме НЕТ ВЛОЖЕНИЙ - анализируем только текст письма")
        
        # Тестируем через LLM
        result = self.test_single_email_with_attachments(target_email, extracted_texts)
        
        return result
    
    def load_extracted_texts_from_email_json(self, email_data: Dict, date: str) -> List[str]:
        """📄 🔧 ИСПРАВЛЕННАЯ загрузка OCR текстов ИЗ САМОГО JSON ПИСЬМА"""
        
        extracted_texts = []
        attachments = email_data.get('attachments', [])
        
        # Если нет вложений в JSON - возвращаем пустой список
        if not attachments:
            print(f"📭 В JSON письма нет сохраненных вложений")
            return []
        
        print(f"📎 В JSON письма найдено {len(attachments)} вложений:")
        
        for idx, attachment in enumerate(attachments, 1):
            filename = attachment.get('original_filename', f'attachment_{idx}')
            status = attachment.get('status', 'unknown')
            
            print(f"   {idx}. {filename} (статус: {status})")
            
            # Обрабатываем только успешно сохраненные вложения
            if status == 'saved':
                # Ищем соответствующий OCR текст
                ocr_text = self.find_ocr_text_for_attachment(date, filename, idx)
                if ocr_text:
                    extracted_texts.append(ocr_text)
                    print(f"      ✅ OCR текст найден: {len(ocr_text)} символов")
                else:
                    print(f"      ⚠️ OCR текст не найден")
            else:
                print(f"      🚫 Пропуск - статус: {status}")
        
        return extracted_texts
    
    def find_ocr_text_for_attachment(self, date: str, original_filename: str, attachment_idx: int) -> Optional[str]:
        """🔍 Поиск OCR текста для конкретного вложения"""
        
        extracted_texts_dir = Path("data/attachment_quality/extracted_texts")
        date_dir = extracted_texts_dir / date
        
        if not date_dir.exists():
            return None
        
        # Ищем файл OCR текста для данного вложения
        # Возможные варианты имен файлов
        possible_patterns = [
            f"*att_{attachment_idx:02d}_*{Path(original_filename).stem}*.txt",
            f"*att_{attachment_idx:02d}_*.txt"
        ]
        
        for pattern in possible_patterns:
            text_files = list(date_dir.glob(pattern))
            if text_files:
                # Берем первый найденный файл
                text_file = text_files[0]
                try:
                    with open(text_file, 'r', encoding='utf-8') as f:
                        text = f.read().strip()
                        if text:
                            return text
                except Exception as e:
                    print(f"      ⚠️ Ошибка чтения {text_file}: {e}")
        
        return None
    
    def test_connection(self) -> bool:
        """🔌 Тест подключения"""
        
        print(f"🔌 Тестирование подключения к OpenRouter...")
        
        test_payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "Привет! Это тест подключения."}
            ],
            "max_tokens": 50
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=test_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Подключение успешно! Модель {self.model} доступна")
                return True
            else:
                print(f"❌ Ошибка подключения: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Детали: {error_data}")
                except:
                    print(f"   Ответ: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def test_single_email_with_attachments(self, email_data: Dict, extracted_texts: List[str]) -> Dict:
        """🧪 Тестирование письма с вложениями"""
        
        # Собираем текст для анализа
        email_text = email_data.get('body', '')
        
        combined_text = f"""
=== ОСНОВНОЕ ПИСЬМО ===
От: {email_data.get('from', '')}
Кому: {email_data.get('to', '')}
Тема: {email_data.get('subject', '')}
Дата: {email_data.get('date', '')}

Текст письма:
{email_text}
"""
        
        if extracted_texts:
            combined_text += "\n=== СОДЕРЖИМОЕ ВЛОЖЕНИЙ ==="
            for i, attachment_text in enumerate(extracted_texts, 1):
                combined_text += f"\n\n--- ВЛОЖЕНИЕ {i} ---\n{attachment_text}"
        else:
            combined_text += "\n=== ВЛОЖЕНИЙ НЕТ ==="
        
        print(f"📝 Размер текста для LLM: {len(combined_text)} символов")
        
        # Отправляем в LLM
        llm_result = self.send_to_llm(combined_text)
        
        return {
            'email_id': email_data.get('thread_id'),
            'from': email_data.get('from'),
            'subject': email_data.get('subject'),
            'date': email_data.get('date'),
            'real_attachments_count': len(email_data.get('attachments', [])),  # 🔧 Реальное количество
            'ocr_texts_found': len(extracted_texts),  # 🔧 Найдено OCR текстов
            'combined_text_length': len(combined_text),
            'llm_analysis': llm_result
        }
    
    def send_to_llm(self, text: str) -> Dict:
        """🤖 Отправка в OpenRouter с обработкой Qwen3 тегов"""
        
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.1,
                "max_tokens": 3000,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            
            print(f"🤖 Отправляем в OpenRouter...")
            print(f"   Модель: {self.model}")
            print(f"   Размер текста: {len(text)} символов")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=120
            )
            
            print(f"   Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    llm_response = result['choices'][0]['message']['content']
                    
                    # 🔧 ИСПРАВЛЕНИЕ: Очищаем ответ от тегов Qwen3
                    cleaned_response = self.clean_qwen_response(llm_response)
                    
                    try:
                        parsed_result = json.loads(cleaned_response)
                        return {
                            'success': True,
                            'data': parsed_result,
                            'tokens_used': result.get('usage', {}).get('total_tokens', 0),
                            'model': self.model,
                            'cleaning_applied': True,  # 🆕 Отмечаем что применили очистку
                            'raw_response_preview': llm_response[:200]  # 🆕 Показываем начало сырого ответа
                        }
                    except json.JSONDecodeError as e:
                        return {
                            'success': False,
                            'error': f'Некорректный JSON после очистки: {str(e)}',
                            'raw_response': llm_response,
                            'cleaned_response': cleaned_response[:500],
                            'model': self.model
                        }
                else:
                    return {
                        'success': False,
                        'error': 'Неожиданная структура ответа',
                        'raw_response': str(result)[:500]
                    }
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get('error', {}).get('message', 'Unknown error')
                except:
                    error_detail = response.text[:200]
                
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {error_detail}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка: {str(e)}'
            }
    
    def show_available_emails(self, date: str):
        """📋 Показать письма за дату с РЕАЛЬНЫМ количеством вложений"""
        
        emails = self.email_loader.load_emails_by_date(date)
        
        print(f"\n📅 Письма за {date} с РЕАЛЬНЫМ подсчетом вложений:")
        print("="*70)
        
        for i, email in enumerate(emails, 1):
            from_addr = email.get('from', 'N/A')[:40]
            subject = email.get('subject', 'N/A')[:50]
            
            # 🔧 ПРАВИЛЬНЫЙ подсчет вложений из JSON
            real_attachments = email.get('attachments', [])
            saved_attachments = [att for att in real_attachments if att.get('status') == 'saved']
            
            print(f"{i:2d}. От: {from_addr}...")
            print(f"    Тема: {subject}...")
            print(f"    📎 Всего вложений: {len(real_attachments)}")
            print(f"    ✅ Сохраненных: {len(saved_attachments)}")
            
            # Показываем типы вложений
            if saved_attachments:
                print(f"    📁 Типы: {', '.join(set(att.get('file_type', 'unknown').split('/')[-1] for att in saved_attachments))}")
            print()

def main():
    """🚀 Главная функция с исправлениями для Qwen3"""
    
    print("🤖 ИСПРАВЛЕННЫЙ ТЕСТЕР OPENROUTER + QWEN3 (с обработкой <think> тегов)")
    print("="*70)
    
    tester = CommercialOfferLLMTester()
    
    # Показываем доступные даты
    available_dates = tester.email_loader.get_available_date_folders()
    print(f"📅 Доступные даты: {available_dates}")
    
    if not available_dates:
        print("❌ Нет обработанных писем для тестирования")
        return
    
    # Тестируем подключение
    if not tester.test_connection():
        print("❌ Проблемы с подключением к OpenRouter!")
        print("💡 Проверь:")
        print("   - API ключ правильный")
        print("   - Интернет соединение")
        print("   - Модель доступна на OpenRouter")
        return
    
    # Интерактивное меню
    while True:
        print(f"\n🎯 МЕНЮ ИСПРАВЛЕННОГО ТЕСТЕРА:")
        print("1. Тестировать конкретное письмо")
        print("2. Посмотреть письма за дату (с правильным подсчетом вложений)")
        print("3. Протестировать подключение снова")
        print("4. Быстрый тест письма #1 за 2025-07-28")
        print("5. Выход")
        
        choice = input("Ваш выбор (1-5): ").strip()
        
        if choice == '1':
            # Выбор даты
            print(f"\nДоступные даты: {', '.join(available_dates)}")
            selected_date = input("Введите дату (YYYY-MM-DD): ").strip()
            
            if selected_date not in available_dates:
                print(f"❌ Дата {selected_date} не найдена!")
                continue
            
            # Показываем письма с правильным подсчетом
            tester.show_available_emails(selected_date)
            
            # Выбор письма
            try:
                email_number = int(input("Введите номер письма: "))
            except ValueError:
                print("❌ Введите корректный номер!")
                continue
            
            # Тестируем
            result = tester.test_specific_email(selected_date, email_number)
            
            # Показываем результат
            print(f"\n{'='*70}")
            print("🤖 РЕЗУЛЬТАТ ИСПРАВЛЕННОГО АНАЛИЗА:")
            print("="*70)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # Сохраняем
            if 'error' not in result:
                result_filename = f"fixed_qwen3_test_{selected_date}_email_{email_number:03d}"
                result_path = tester.results_dir / f"{result_filename}.json"
                with open(result_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"\n💾 Результат сохранен: {result_path}")
            
        elif choice == '2':
            # Просмотр писем с правильным подсчетом
            selected_date = input(f"Дата ({', '.join(available_dates)}): ").strip()
            if selected_date in available_dates:
                tester.show_available_emails(selected_date)
            else:
                print(f"❌ Дата {selected_date} не найдена!")
        
        elif choice == '3':
            tester.test_connection()
        
        elif choice == '4':
            # Быстрый тест
            print(f"\n🎯 БЫСТРЫЙ ТЕСТ ПИСЬМА #1 за 2025-07-28...")
            result = tester.test_specific_email("2025-07-28", 1)
            
            print(f"\n{'='*70}")
            print("🤖 БЫСТРЫЙ ТЕСТ - РЕЗУЛЬТАТ:")
            print("="*70)
            
            if result.get('llm_analysis', {}).get('success'):
                data = result['llm_analysis']['data']
                
                print(f"✅ JSON парсинг: УСПЕШНО")
                print(f"🧹 Очистка тегов: ПРИМЕНЕНА")
                
                # Показываем ключевые результаты
                contacts = data.get('contacts', {})
                if contacts.get('sender_name'):
                    print(f"\n👤 НАЙДЕННЫЙ КОНТАКТ:")
                    print(f"   Имя: {contacts.get('sender_name')}")
                    print(f"   Email: {contacts.get('sender_email')}")
                    print(f"   Телефон: {contacts.get('sender_phone')}")
                    print(f"   Организация: {contacts.get('sender_organization')}")
                
                commercial = data.get('commercial_offer', {})
                print(f"\n📋 КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ:")
                print(f"   Найдено: {'✓' if commercial.get('found') else '✗'}")
                print(f"   Амплификатор: {'✓' if commercial.get('amplifier_found') else '✗'}")
                
                context = data.get('context', {})
                print(f"\n🎯 КОНТЕКСТ:")
                print(f"   Статус: {context.get('status', 'N/A')}")
                print(f"   Краткое описание: {context.get('request_summary', 'N/A')[:100]}...")
                
            else:
                print(f"❌ Ошибка LLM: {result.get('llm_analysis', {}).get('error', 'Unknown')}")
                print(f"🔍 Сырой ответ: {result.get('llm_analysis', {}).get('raw_response', '')[:200]}...")
        
        elif choice == '5':
            print("👋 Завершение работы")
            break
        
        else:
            print("❌ Неверный выбор!")

if __name__ == '__main__':
    main()
