"""
Извлекатель сайтов компаний из email данных
Реализует различные методы извлечения и валидации веб-сайтов.

Author: Contact Parser Team
Created: 2025-09-08
"""

import re
import requests
import logging
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import time
import socket

logger = logging.getLogger(__name__)


class WebsiteExtractor:
    """
    Извлекатель сайтов компаний из email данных
    
    Методы извлечения:
    1. Прямое упоминание URL в тексте
    2. Извлечение из домена email (user@company.com → www.company.com)
    3. Корпоративные домены из email
    4. Валидация доступности сайтов
    """
    
    # Регулярные выражения для поиска URL
    URL_PATTERNS = [
        r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?',
        r'www\.(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?',
        r'(?:[-\w.]+\.)+(?:ru|com|org|net|info|biz|pro|site|online|store|tech|io|co|uk|de|fr|it|es|pl|cz|by|kz|ua)(?:/(?:[\w/_.])*)?',
    ]
    
    # Домены, которые часто указывают на сайты компаний
    CORPORATE_DOMAINS = {
        'mail.ru', 'yandex.ru', 'gmail.com', 'outlook.com', 'yahoo.com',
        'icloud.com', 'protonmail.com', 'zoho.com', 'aol.com'
    }
    
    def __init__(self, timeout: int = 5, max_retries: int = 2):
        """
        Инициализация извлекателя сайтов
        
        Args:
            timeout: Таймаут для HTTP запросов (секунды)
            max_retries: Максимальное количество повторных попыток
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ContactParser/1.0)'
        })
        self.logger = logging.getLogger(__name__)
    
    def extract_from_email_body(self, text: str) -> List[Dict[str, any]]:
        """
        Извлечение сайтов из текста email
        
        Args:
            text: Текст email для анализа
            
        Returns:
            List[Dict]: Список найденных сайтов с метаданными
        """
        if not text:
            return []
        
        found_urls = set()
        
        # Поиск по всем паттернам
        for pattern in self.URL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Нормализация URL
                normalized_url = self._normalize_url(match)
                if normalized_url and normalized_url not in found_urls:
                    found_urls.add(normalized_url)
        
        # Формирование результатов
        results = []
        for url in found_urls:
            confidence = self._calculate_url_confidence(url, text)
            results.append({
                'url': url,
                'confidence': confidence,
                'source': 'email_body',
                'method': 'regex_pattern'
            })
        
        return sorted(results, key=lambda x: x['confidence'], reverse=True)
    
    def extract_from_email_domain(self, email: str) -> Optional[Dict[str, any]]:
        """
        Извлечение сайта из домена email
        
        Args:
            email: Email адрес для анализа
            
        Returns:
            Dict or None: Информация о потенциальном сайте
        """
        if not email or '@' not in email:
            return None
        
        domain = email.split('@')[1].lower().strip()
        
        # Пропускаем публичные email домены
        if domain in self.CORPORATE_DOMAINS:
            return None
        
        # Формируем возможные URL
        possible_urls = [
            f"https://www.{domain}",
            f"https://{domain}",
            f"http://www.{domain}",
            f"http://{domain}"
        ]
        
        # Возвращаем наиболее вероятный URL
        primary_url = possible_urls[0]
        
        return {
            'url': primary_url,
            'domain': domain,
            'confidence': 0.7,  # Средняя уверенность для доменов
            'source': 'email_domain',
            'method': 'domain_extraction',
            'alternatives': possible_urls[1:]
        }
    
    def extract_from_corporate_email(self, email: str) -> Optional[Dict[str, any]]:
        """
        Специализированное извлечение для корпоративных email
        
        Args:
            email: Корпоративный email
            
        Returns:
            Dict or None: Информация о сайте компании
        """
        domain_info = self.extract_from_email_domain(email)
        if not domain_info:
            return None
        
        # Для корпоративных доменов повышаем уверенность
        domain_info['confidence'] = 0.8
        domain_info['method'] = 'corporate_domain'
        
        return domain_info
    
    def validate_website(self, url: str, check_content: bool = False) -> Dict[str, any]:
        """
        Валидация доступности сайта
        
        Args:
            url: URL для проверки
            check_content: Проверять ли содержимое страницы
            
        Returns:
            Dict: Результаты валидации
        """
        result = {
            'url': url,
            'accessible': False,
            'status_code': None,
            'error': None,
            'response_time': None,
            'has_content': False,
            'title': None
        }
        
        try:
            start_time = time.time()
            
            # Попытка HEAD запроса сначала
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            result['status_code'] = response.status_code
            result['response_time'] = time.time() - start_time
            
            # Если HEAD не удался, пробуем GET
            if response.status_code >= 400:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                result['status_code'] = response.status_code
                result['response_time'] = time.time() - start_time
            
            result['accessible'] = 200 <= response.status_code < 400
            
            # Проверка содержимого
            if check_content and result['accessible']:
                content_length = len(response.content)
                result['has_content'] = content_length > 1000  # Минимум 1KB
                
                # Попытка извлечь title
                if 'text/html' in response.headers.get('content-type', '').lower():
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', 
                                          response.text, re.IGNORECASE)
                    if title_match:
                        result['title'] = title_match.group(1).strip()
            
        except requests.exceptions.Timeout:
            result['error'] = 'timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'connection_error'
        except requests.exceptions.RequestException as e:
            result['error'] = str(e)
        except Exception as e:
            result['error'] = f'unexpected_error: {str(e)}'
        
        return result
    
    def is_website_accessible(self, url: str) -> bool:
        """
        Простая проверка доступности сайта (для совместимости с тестами)
        
        Args:
            url: URL для проверки
            
        Returns:
            bool: True если сайт доступен
        """
        result = self.validate_website(url)
        return result.get('accessible', False)
    
    def extract_all_websites(self, text: str, email: str = None) -> List[Dict[str, any]]:
        """
        Комплексное извлечение сайтов из текста и email
        
        Args:
            text: Текст email
            email: Email адрес отправителя
            
        Returns:
            List[Dict]: Все найденные сайты с метаданными
        """
        websites = []
        
        # 1. Извлечение из текста
        text_websites = self.extract_from_email_body(text)
        websites.extend(text_websites)
        
        # 2. Извлечение из домена email
        if email:
            domain_website = self.extract_from_email_domain(email)
            if domain_website:
                websites.append(domain_website)
        
        # 3. Удаление дубликатов
        unique_websites = self._deduplicate_websites(websites)
        
        # 4. Сортировка по уверенности
        return sorted(unique_websites, key=lambda x: x['confidence'], reverse=True)
    
    def _normalize_url(self, url: str) -> Optional[str]:
        """
        Нормализация URL для стандартизации
        
        Args:
            url: Исходный URL
            
        Returns:
            str or None: Нормализованный URL
        """
        if not url:
            return None
        
        url = url.strip()
        
        # Добавляем протокол если отсутствует
        if not url.startswith(('http://', 'https://')):
            if url.startswith('www.'):
                url = 'https://' + url
            else:
                url = 'https://www.' + url
        
        try:
            parsed = urlparse(url)
            
            # Проверяем валидность домена
            if not parsed.netloc:
                return None
            
            # Приводим к нижнему регистру
            normalized = parsed.geturl().lower()
            
            return normalized
            
        except Exception:
            return None
    
    def _calculate_url_confidence(self, url: str, context: str) -> float:
        """
        Расчет уверенности в корректности URL
        
        Args:
            url: URL для оценки
            context: Контекст, в котором найден URL
            
        Returns:
            float: Уверенность (0.0 - 1.0)
        """
        confidence = 0.5  # Базовая уверенность
        
        # Повышение уверенности за наличие https
        if url.startswith('https://'):
            confidence += 0.2
        
        # Повышение за наличие www
        if 'www.' in url:
            confidence += 0.1
        
        # Повышение за корпоративные домены верхнего уровня
        corporate_tlds = ['.ru', '.com', '.org', '.net', '.info']
        if any(url.endswith(tld) for tld in corporate_tlds):
            confidence += 0.1
        
        # Понижение за подозрительные паттерны
        suspicious_patterns = ['bit.ly', 'tinyurl', 'goo.gl', 't.co']
        if any(pattern in url for pattern in suspicious_patterns):
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    def _deduplicate_websites(self, websites: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Удаление дубликатов сайтов
        
        Args:
            websites: Список сайтов с дубликатами
            
        Returns:
            List[Dict]: Список уникальных сайтов
        """
        seen_urls = set()
        unique_websites = []
        
        for website in websites:
            url = website['url']
            normalized_url = self._normalize_url(url)
            
            if normalized_url and normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                # Обновляем URL на нормализованный
                website['url'] = normalized_url
                unique_websites.append(website)
        
        return unique_websites


# Пример использования
if __name__ == "__main__":
    extractor = WebsiteExtractor()
    
    # Тестовый текст из реального email
    test_text = """
    Добрый день, Иван Алексеевич!
    КП во вложении.
    Гоголева Мария Михайловна
    Менеджер по продаже оборудования | ООО «ДНК-Технология»
    Email: m.gogoleva@dna-technology.ru
    Сайт: dna-technology.ru
    """
    
    test_email = "m.gogoleva@dna-technology.ru"
    
    # Извлечение сайтов
    websites = extractor.extract_all_websites(test_text, test_email)
    
    print("🔍 Найденные сайты:")
    for site in websites:
        print(f"  URL: {site['url']}")
        print(f"  Уверенность: {site['confidence']:.2f}")
        print(f"  Источник: {site['source']}")
        print()
