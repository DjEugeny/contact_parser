#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый запускчик нового Email Fetcher с интерактивным меню.
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    """Запуск CLI с автоматическим определением метода."""
    cli_path = Path(__file__).parent / "src" / "fetcher" / "cli.py"
    
    if not cli_path.exists():
        print("❌ Ошибка: CLI модуль не найден")
        print(f"   Ожидаемый путь: {cli_path}")
        sys.exit(1)
    
    # Проверяем, активировано ли виртуальное окружение
    venv_path = Path(__file__).parent / ".venv"
    if venv_path.exists() and "VIRTUAL_ENV" not in os.environ:
        print("🔄 Активируем виртуальное окружение...")
        
        # Определяем путь к Python в виртуальном окружении
        if sys.platform == "win32":
            python_exe = venv_path / "Scripts" / "python.exe"
        else:
            python_exe = venv_path / "bin" / "python"
        
        if not python_exe.exists():
            print(f"❌ Ошибка: Python не найден в виртуальном окружении: {python_exe}")
            sys.exit(1)
        
        # Запускаем CLI через Python в виртуальном окружении
        try:
            result = subprocess.run(
                [str(python_exe), str(cli_path)] + sys.argv[1:],
                check=True,
                cwd=Path(__file__).parent
            )
            sys.exit(result.returncode)
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка запуска: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print("❌ Ошибка: Python не найден")
            sys.exit(1)
    
    try:
        # Пробуем импортировать и запустить напрямую
        from src.fetcher.cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"⚠️ Ошибка импорта: {e}")
        print("🔄 Запускаем через subprocess...")
        
        # Запускаем через subprocess как fallback
        try:
            result = subprocess.run(
                [sys.executable, str(cli_path)] + sys.argv[1:],
                check=True,
                cwd=Path(__file__).parent
            )
            sys.exit(result.returncode)
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка запуска: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print("❌ Ошибка: Python не найден")
            sys.exit(1)

if __name__ == "__main__":
    main()