#!/usr/bin/env python3
"""
🔄 Простой сброс Circuit Breaker через перезапуск процесса
"""

import os
import time

def reset_circuit_breaker():
    """Сброс Circuit Breaker через информирование пользователя"""
    print("🔄 СБРОС Circuit Breaker")
    print("=" * 30)
    
    print("ℹ️ Circuit Breaker хранится в памяти процесса")
    print("✅ Новый процесс Python = сброшенный Circuit Breaker")
    
    current_time = time.strftime("%H:%M:%S")
    print(f"⏰ Текущее время: {current_time}")
    
    print("\n💡 Рекомендации:")
    print("   1. Запустите новый тест пайплайна")
    print("   2. Circuit Breaker будет сброшен автоматически")
    print("   3. Если ошибки были более 5 минут назад, он разблокируется сам")
    
    print("\n🚀 Готово к тестированию!")

if __name__ == "__main__":
    reset_circuit_breaker()