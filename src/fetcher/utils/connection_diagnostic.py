#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для диагностики подключения к почтовому серверу.
"""

import socket
import ssl
import imaplib
import sys
import time
from typing import Tuple, Optional

# Загрузка переменных окружения
import os
from dotenv import load_dotenv
load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", 143))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")


def test_tcp_connection(host: str, port: int, timeout: int = 10) -> Tuple[bool, str]:
    """
    Проверка TCP-соединения с сервером.
    
    Args:
        host: Хост сервера
        port: Порт сервера
        timeout: Таймаут в секундах
        
    Returns:
        Кортеж (успех, сообщение)
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            return True, f"✅ TCP-соединение с {host}:{port} установлено"
    except socket.timeout:
        return False, f"❌ Таймаут подключения к {host}:{port}"
    except socket.gaierror as e:
        return False, f"❌ Ошибка разрешения имени {host}: {e}"
    except ConnectionRefusedError:
        return False, f"❌ Соединение отклонено {host}:{port}"
    except OSError as e:
        return False, f"❌ Ошибка сети: {e}"
    except Exception as e:
        return False, f"❌ Неизвестная ошибка: {e}"


def test_ssl_connection(host: str, port: int, timeout: int = 10) -> Tuple[bool, str]:
    """
    Проверка SSL-соединения с сервером.
    
    Args:
        host: Хост сервера
        port: Порт сервера
        timeout: Таймаут в секундах
        
    Returns:
        Кортеж (успех, сообщение)
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cipher = ssock.cipher()
                cert = ssock.getpeercert()
                return True, f"✅ SSL-соединение установлено. Шифр: {cipher[0]}"
    except ssl.SSLCertVerificationError as e:
        return False, f"❌ Ошибка сертификата: {e}"
    except ssl.SSLError as e:
        return False, f"❌ SSL ошибка: {e}"
    except Exception as e:
        return False, f"❌ Ошибка SSL-соединения: {e}"


def test_imap_connection(host: str, port: int, use_ssl: bool = False, timeout: int = 10) -> Tuple[bool, str]:
    """
    Проверка IMAP-соединения с сервером.
    
    Args:
        host: Хост сервера
        port: Порт сервера
        use_ssl: Использовать SSL
        timeout: Таймаут в секундах
        
    Returns:
        Кортеж (успех, сообщение)
    """
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
        
        # Проверяем ответ сервера
        greeting = mail.welcome.decode('utf-8') if isinstance(mail.welcome, bytes) else str(mail.welcome)
        mail.logout()
        return True, f"✅ IMAP-соединение установлено. Приветствие: {greeting[:50]}..."
    except imaplib.IMAP4.error as e:
        return False, f"❌ IMAP ошибка: {e}"
    except Exception as e:
        return False, f"❌ Ошибка IMAP-соединения: {e}"


def test_imap_login(host: str, port: int, user: str, password: str, use_ssl: bool = False, timeout: int = 10) -> Tuple[bool, str]:
    """
    Проверка IMAP-аутентификации.
    
    Args:
        host: Хост сервера
        port: Порт сервера
        user: Имя пользователя
        password: Пароль
        use_ssl: Использовать SSL
        timeout: Таймаут в секундах
        
    Returns:
        Кортеж (успех, сообщение)
    """
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
        
        try:
            mail.login(user, password)
            mail.logout()
            return True, f"✅ Аутентификация успешна для пользователя {user}"
        except imaplib.IMAP4.error as e:
            mail.logout()
            return False, f"❌ Ошибка аутентификации: {e}"
    except Exception as e:
        return False, f"❌ Ошибка при входе: {e}"


def test_starttls(host: str, port: int, timeout: int = 10) -> Tuple[bool, str]:
    """
    Проверка STARTTLS для порта 143.
    
    Args:
        host: Хост сервера
        port: Порт сервера
        timeout: Таймаут в секундах
        
    Returns:
        Кортеж (успех, сообщение)
    """
    try:
        mail = imaplib.IMAP4(host, port)
        mail.starttls(ssl.create_default_context())
        greeting = mail.welcome.decode('utf-8') if isinstance(mail.welcome, bytes) else str(mail.welcome)
        mail.logout()
        return True, f"✅ STARTTLS работает. Приветствие: {greeting[:50]}..."
    except Exception as e:
        return False, f"❌ Ошибка STARTTLS: {e}"


def main():
    """Главная функция диагностики."""
    print("🔍 ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ К ПОЧТОВОМУ СЕРВЕРУ")
    print("=" * 60)
    print(f"📡 Сервер: {IMAP_SERVER}")
    print(f"🔌 Порт: {IMAP_PORT}")
    print(f"👤 Пользователь: {IMAP_USER}")
    print("=" * 60)
    
    # 1. Проверка TCP-соединения
    print("\n1️⃣ Проверка TCP-соединения...")
    success, message = test_tcp_connection(IMAP_SERVER, IMAP_PORT)
    print(message)
    if not success:
        print("\n❌ Базовое TCP-соединение не установлено. Проверьте:")
        print("   - Доступность сервера")
        print("   - Блокировку на фаерволе")
        print("   - Правильность имени сервера")
        return
    
    # 2. Проверка IMAP-соединения
    print("\n2️⃣ Проверка IMAP-соединения...")
    success, message = test_imap_connection(IMAP_SERVER, IMAP_PORT, use_ssl=False)
    print(message)
    if not success:
        print("\n❌ IMAP-сервер не отвечает на порту 143")
    
    # 3. Проверка STARTTLS
    print("\n3️⃣ Проверка STARTTLS...")
    success, message = test_starttls(IMAP_SERVER, IMAP_PORT)
    print(message)
    
    # 4. Проверка аутентификации
    print("\n4️⃣ Проверка аутентификации...")
    success, message = test_imap_login(IMAP_SERVER, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, use_ssl=False)
    print(message)
    
    # 5. Альтернативная проверка порта 993 (IMAPS)
    print("\n5️⃣ Проверка альтернативного порта 993 (IMAPS)...")
    success_993, message_993 = test_tcp_connection(IMAP_SERVER, 993)
    print(message_993)
    
    if success_993:
        print("\n5️⃣🅱️ Проверка IMAP-соединения на порту 993...")
        success_993_imap, message_993_imap = test_imap_connection(IMAP_SERVER, 993, use_ssl=True)
        print(message_993_imap)
        
        if success_993_imap:
            print("\n5️⃣🅲️ Проверка аутентификации на порту 993...")
            success_993_auth, message_993_auth = test_imap_login(IMAP_SERVER, 993, IMAP_USER, IMAP_PASSWORD, use_ssl=True)
            print(message_993_auth)
    
    # 6. Рекомендации
    print("\n📋 РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    
    # Проверяем доступность порта 993
    if success_993 and success_993_imap and success_993_auth:
        print("✅ Порт 993 (IMAPS) работает! Рекомендуем использовать его:")
        print("   - Измените IMAP_PORT=993 в .env")
        print("   - Порт 993 более стабилен и безопасен")
    
    if not success:
        print("❌ Базовые проблемы с подключением:")
        print("   1. Проверьте интернет-соединение")
        print("   2. Проверьте блокировку IP на сервере")
        print("   3. Попробуйте подключиться из другой сети")
        print("   4. Свяжитесь с администратором сервера")
    
    # 7. Предложение создать тестовое соединение
    print("\n🧪 Тестовое подключение с улучшенными параметрами...")
    
    try:
        # Пробуем подключиться с расширенными параметрами
        if IMAP_PORT == 143:
            print(f"🔄 Пробуем STARTTLS с расширенными опциями...")
            mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
            
            # Устанавливаем отладочный режим
            mail.debug = 4
            
            # Пробуем STARTTLS с расширенным контекстом
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            mail.starttls(context)
            mail.login(IMAP_USER, IMAP_PASSWORD)
            mail.select("INBOX")
            
            print("✅ Расширенное подключение успешно!")
            mail.logout()
            
    except Exception as e:
        print(f"❌ Расширенное подключение не удалось: {e}")
        print("\n💡 Возможные решения:")
        print("   1. Использовать порт 993 (IMAPS)")
        print("   2. Проверить актуальность пароля")
        print("   3. Проверить блокировку по IP")
        print("   4. Попробовать подключиться позже")


if __name__ == "__main__":
    main()