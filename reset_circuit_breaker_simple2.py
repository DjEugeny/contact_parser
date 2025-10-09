#!/usr/bin/env python3
"""
Простой сброс Circuit Breaker через удаление файла состояния
"""

import os
from pathlib import Path

def reset_circuit_breaker():
    """Сброс Circuit Breaker через удаление файла состояния"""
    print("🔄 СБРОС CIRCUIT BREAKER")
    print("=" * 40)
    
    # Ищем файлы состояния Circuit Breaker
    cache_dir = Path("cache")
    
    if not cache_dir.exists():
        print("❌ Директория cache не найдена")
        return
    
    # Ищем файлы circuit breaker
    cb_files = list(cache_dir.glob("*circuit_breaker*.json"))
    
    if not cb_files:
        print("✅ Файлы Circuit Breaker не найдены (уже сброшен)")
        return
    
    print(f"📁 Найдено файлов: {len(cb_files)}")
    
    for cb_file in cb_files:
        try:
            print(f"   🗑️ Удаляем: {cb_file.name}")
            cb_file.unlink()
            print(f"   ✅ Удален: {cb_file.name}")
        except Exception as e:
            print(f"   ❌ Ошибка удаления {cb_file.name}: {e}")
    
    print("\n✅ Circuit Breaker сброшен!")
    print("🚀 Теперь можно запускать API Pipeline Validator")

if __name__ == "__main__":
    reset_circuit_breaker()
