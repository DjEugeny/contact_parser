#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 Бэкап Global ID Registry
Создание резервных копий реестра с ротацией
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Добавляем корень проекта в path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class RegistryBackup:
    """Управление бэкапами реестра"""
    
    def __init__(
        self,
        registry_path: Path,
        backup_dir: Optional[Path] = None,
        keep_days: int = 30
    ):
        self.registry_path = registry_path
        self.backup_dir = backup_dir or (registry_path / "backups")
        self.keep_days = keep_days
        
        # Создаём папку для бэкапов
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self) -> Path:
        """Создание бэкапа"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / f"backup_{timestamp}"
        backup_subdir.mkdir(parents=True, exist_ok=True)
        
        print(f"💾 Создание бэкапа в {backup_subdir}")
        
        files_to_backup = [
            "organizations.jsonl",
            "contacts.jsonl",
            "overrides.yml",
        ]
        
        backed_up = []
        for filename in files_to_backup:
            source = self.registry_path / filename
            if not source.exists():
                print(f"  ⏭️  {filename} не существует, пропускаем")
                continue
            
            dest = backup_subdir / filename
            shutil.copy2(source, dest)
            
            size_mb = source.stat().st_size / (1024 * 1024)
            print(f"  ✅ {filename} ({size_mb:.2f} MB)")
            backed_up.append(filename)
        
        # Создаём метаданные бэкапа
        metadata = {
            "timestamp": timestamp,
            "files": backed_up,
            "registry_path": str(self.registry_path),
        }
        
        metadata_file = backup_subdir / "metadata.txt"
        with metadata_file.open('w', encoding='utf-8') as f:
            f.write(f"Backup created: {datetime.now().isoformat()}\n")
            f.write(f"Registry path: {self.registry_path}\n")
            f.write(f"Files backed up: {', '.join(backed_up)}\n")
        
        print(f"\n✅ Бэкап создан: {backup_subdir}")
        return backup_subdir
    
    def rotate_backups(self):
        """Ротация старых бэкапов"""
        print(f"\n🔄 Ротация бэкапов (хранение: {self.keep_days} дней)")
        
        if not self.backup_dir.exists():
            return
        
        cutoff_date = datetime.now().timestamp() - (self.keep_days * 24 * 60 * 60)
        
        removed_count = 0
        for backup_path in self.backup_dir.iterdir():
            if not backup_path.is_dir():
                continue
            
            # Проверяем возраст бэкапа
            backup_time = backup_path.stat().st_mtime
            if backup_time < cutoff_date:
                print(f"  🗑️  Удаляем старый бэкап: {backup_path.name}")
                shutil.rmtree(backup_path)
                removed_count += 1
        
        if removed_count == 0:
            print("  ✅ Старых бэкапов не найдено")
        else:
            print(f"  ✅ Удалено бэкапов: {removed_count}")
    
    def list_backups(self):
        """Список всех бэкапов"""
        print("\n📋 Список бэкапов:")
        
        if not self.backup_dir.exists():
            print("  Бэкапов нет")
            return
        
        backups = sorted(
            [d for d in self.backup_dir.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not backups:
            print("  Бэкапов нет")
            return
        
        for backup_path in backups:
            mtime = datetime.fromtimestamp(backup_path.stat().st_mtime)
            age_days = (datetime.now() - mtime).days
            
            # Подсчёт размера
            total_size = sum(
                f.stat().st_size 
                for f in backup_path.rglob('*') 
                if f.is_file()
            )
            size_mb = total_size / (1024 * 1024)
            
            print(f"  📦 {backup_path.name}")
            print(f"     Дата: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Возраст: {age_days} дней")
            print(f"     Размер: {size_mb:.2f} MB")
    
    def restore_backup(self, backup_name: str, force: bool = False):
        """Восстановление из бэкапа"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            print(f"❌ Бэкап не найден: {backup_name}")
            return False
        
        print(f"🔄 Восстановление из бэкапа: {backup_name}")
        
        if not force:
            response = input("⚠️  Это перезапишет текущий реестр. Продолжить? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Отменено")
                return False
        
        # Создаём бэкап текущего состояния перед восстановлением
        print("\n💾 Создаём бэкап текущего состояния...")
        self.create_backup()
        
        # Восстанавливаем файлы
        print(f"\n🔄 Восстановление файлов из {backup_path}")
        
        for backup_file in backup_path.iterdir():
            if backup_file.name == "metadata.txt":
                continue
            
            dest = self.registry_path / backup_file.name
            shutil.copy2(backup_file, dest)
            print(f"  ✅ {backup_file.name}")
        
        print("\n✅ Восстановление завершено")
        return True


def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="💾 Управление бэкапами Global ID Registry"
    )
    parser.add_argument(
        'action',
        choices=['create', 'list', 'restore', 'rotate'],
        help="Действие: create (создать), list (список), restore (восстановить), rotate (ротация)"
    )
    parser.add_argument(
        '--backup-name',
        help="Имя бэкапа для восстановления (для action=restore)"
    )
    parser.add_argument(
        '--registry-path',
        type=Path,
        default=PROJECT_ROOT / "src" / "registry",
        help="Путь к реестру"
    )
    parser.add_argument(
        '--backup-dir',
        type=Path,
        help="Папка для бэкапов (по умолчанию: registry/backups)"
    )
    parser.add_argument(
        '--keep-days',
        type=int,
        default=30,
        help="Количество дней хранения бэкапов"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help="Не запрашивать подтверждение при восстановлении"
    )
    
    args = parser.parse_args()
    
    backup_manager = RegistryBackup(
        registry_path=args.registry_path,
        backup_dir=args.backup_dir,
        keep_days=args.keep_days
    )
    
    if args.action == 'create':
        backup_manager.create_backup()
        backup_manager.rotate_backups()
    
    elif args.action == 'list':
        backup_manager.list_backups()
    
    elif args.action == 'restore':
        if not args.backup_name:
            print("❌ Укажите --backup-name для восстановления")
            sys.exit(1)
        backup_manager.restore_backup(args.backup_name, force=args.force)
    
    elif args.action == 'rotate':
        backup_manager.rotate_backups()


if __name__ == "__main__":
    main()