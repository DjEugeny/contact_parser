#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏥 Проверка здоровья Global ID Registry
Мониторинг состояния реестра, выявление проблем
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Добавляем корень проекта в path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.registry import GlobalIDRegistry


class RegistryHealthChecker:
    """Проверка здоровья реестра"""
    
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}
    
    def check_all(self) -> Dict[str, Any]:
        """Полная проверка"""
        print("🏥 Проверка здоровья Global ID Registry")
        print(f"📁 Путь: {self.registry_path}")
        print()
        
        self._check_files_exist()
        self._check_file_sizes()
        self._check_lock_files()
        self._check_registry_integrity()
        self._check_duplicates()
        self._calculate_stats()
        self._check_phone_overrides()
        
        return self._generate_report()
    
    def _check_files_exist(self):
        """Проверка наличия файлов"""
        print("📋 Проверка файлов...")
        
        required_files = [
            "organizations.jsonl",
            "contacts.jsonl",
        ]
        
        for filename in required_files:
            filepath = self.registry_path / filename
            if not filepath.exists():
                self.issues.append(f"❌ Отсутствует файл: {filename}")
            else:
                print(f"  ✅ {filename}")
    
    def _check_file_sizes(self):
        """Проверка размеров файлов"""
        print("\n📊 Размеры файлов:")
        
        for filename in ["organizations.jsonl", "contacts.jsonl"]:
            filepath = self.registry_path / filename
            if filepath.exists():
                size_bytes = filepath.stat().st_size
                size_mb = size_bytes / (1024 * 1024)
                
                print(f"  {filename}: {size_mb:.2f} MB ({size_bytes:,} bytes)")
                
                # Предупреждение при большом размере (>100 MB)
                if size_mb > 100:
                    self.warnings.append(
                        f"⚠️  {filename} очень большой ({size_mb:.2f} MB). "
                        "Рекомендуется оптимизация."
                    )
    
    def _check_lock_files(self):
        """Проверка lock-файлов"""
        print("\n🔒 Проверка lock-файлов:")
        
        lock_files = [
            "organizations.lock",
            "contacts.lock",
        ]
        
        stale_locks = []
        for lock_file in lock_files:
            lock_path = self.registry_path / lock_file
            if lock_path.exists():
                # Проверяем размер (пустой файл = нормально)
                if lock_path.stat().st_size > 0:
                    stale_locks.append(lock_file)
                    print(f"  ⚠️  {lock_file} (возможно, завис процесс)")
                else:
                    print(f"  ✅ {lock_file}")
        
        if stale_locks:
            self.warnings.append(
                f"⚠️  Обнаружены активные lock-файлы: {', '.join(stale_locks)}. "
                "Возможно, процесс был аварийно завершён."
            )
    
    def _check_registry_integrity(self):
        """Проверка целостности реестра"""
        print("\n🔍 Проверка целостности...")
        
        try:
            registry = GlobalIDRegistry(registry_dir=self.registry_path)
            print(f"  ✅ Реестр загружен успешно")
            
            # Подсчёт записей
            org_count = len([g for g in registry.gid_index.keys() 
                           if any(k for k in registry.get_all_keys_for_gid(g) 
                                 if k[0] == "ORG")])
            contact_count = len([g for g in registry.gid_index.keys() 
                               if any(k for k in registry.get_all_keys_for_gid(g) 
                                     if k[0] == "CONTACT")])
            
            self.stats['organizations_count'] = org_count
            self.stats['contacts_count'] = contact_count
            
            print(f"  📊 Организаций: {org_count}")
            print(f"  📊 Контактов: {contact_count}")
            
        except Exception as e:
            self.issues.append(f"❌ Ошибка загрузки реестра: {e}")
    
    def _check_duplicates(self):
        """Проверка на дубликаты gid"""
        print("\n🔎 Проверка дубликатов gid...")
        
        def check_file(filepath: Path, entity_type: str):
            if not filepath.exists():
                return

            seen_gids = set()
            duplicates = []

            with filepath.open('r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)
                        gid = record.get('gid')
                        event = record.get('event', 'create')
                        if gid and event == 'create':
                            if gid in seen_gids:
                                duplicates.append((gid, line_num))
                            else:
                                seen_gids.add(gid)
                    except json.JSONDecodeError:
                        self.warnings.append(
                            f"⚠️  {entity_type}: строка {line_num} содержит невалидный JSON"
                        )
            
            if duplicates:
                self.issues.append(
                    f"❌ {entity_type}: найдены дублирующиеся gid: {duplicates}"
                )
            else:
                print(f"  ✅ {entity_type}: дубликатов не найдено")
        
        check_file(self.registry_path / "organizations.jsonl", "Организации")
        check_file(self.registry_path / "contacts.jsonl", "Контакты")
    
    def _calculate_stats(self):
        """Дополнительная статистика"""
        print("\n📈 Статистика:")
        
        # Подсчёт событий по типам
        for entity_type, filename in [
            ("organizations", "organizations.jsonl"),
            ("contacts", "contacts.jsonl"),
        ]:
            filepath = self.registry_path / filename
            if not filepath.exists():
                continue
            
            event_counts = {"create": 0, "alias": 0}
            
            with filepath.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        event = record.get('event', 'create')
                        event_counts[event] = event_counts.get(event, 0) + 1
                    except json.JSONDecodeError:
                        pass
            
            total = sum(event_counts.values())
            print(f"  {entity_type.capitalize()}:")
            print(f"    - Всего событий: {total}")
            print(f"    - Create: {event_counts.get('create', 0)}")
            print(f"    - Alias: {event_counts.get('alias', 0)}")
            
            self.stats[f'{entity_type}_events'] = event_counts
    
    def _generate_report(self) -> Dict[str, Any]:
        """Генерация итогового отчёта"""
        print("\n" + "=" * 60)
        print("📋 ИТОГОВЫЙ ОТЧЁТ")
        print("=" * 60)
        
        if not self.issues and not self.warnings:
            print("✅ Все проверки пройдены успешно!")
            status = "healthy"
        elif self.issues:
            print("❌ ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
            for issue in self.issues:
                print(f"  {issue}")
            status = "critical"
        else:
            print("⚠️  Обнаружены предупреждения:")
            for warning in self.warnings:
                print(f"  {warning}")
            status = "warning"
        
        if self.warnings and not self.issues:
            print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        print("\n📊 Статистика:")
        for key, value in self.stats.items():
            if not isinstance(value, dict):
                print(f"  {key}: {value}")
        
        return {
            "status": status,
            "issues": self.issues,
            "warnings": self.warnings,
            "stats": self.stats,
        }


def main():
    """Основная функция"""
    registry_path = PROJECT_ROOT / "src" / "registry"
    
    checker = RegistryHealthChecker(registry_path)
    report = checker.check_all()
    
    # Возвращаем exit code в зависимости от статуса
    if report["status"] == "critical":
        sys.exit(1)
    elif report["status"] == "warning":
        sys.exit(0)  # Предупреждения не критичны
    else:
        sys.exit(0)


    def _check_phone_overrides(self):
        """Проверка phone_overrides.yml"""
        print("\n📞 Проверка phone_overrides...")
        
        overrides_path = self.registry_path / "phone_overrides.yml"
        if not overrides_path.exists():
            self.warnings.append("⚠️  phone_overrides.yml отсутствует. Создайте файл для ручных overrides телефонов.")
            print("  ⚠️  Файл отсутствует")
            return
        
        try:
            import yaml
            with overrides_path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            overrides = data.get('phone_overrides', [])
            
            if not overrides:
                print("  ✅ Файл пуст или без overrides")
                return
            
            phone_to_gid = {}
            duplicates = []
            for item in overrides:
                number = item.get('number')
                gid = item.get('owner_gid')
                if not number or not gid:
                    self.warnings.append(f"⚠️  Некорректный override: {item}")
                    continue
                norm_phone = self._normalize_phone(number)  # Use same norm as postprocessor
                if norm_phone in phone_to_gid:
                    duplicates.append((norm_phone, phone_to_gid[norm_phone], gid))
                else:
                    phone_to_gid[norm_phone] = gid
            
            count = len(phone_to_gid)
            self.stats['phone_overrides_count'] = count
            
            print(f"  ✅ Загружено {count} phone overrides")
            if duplicates:
                self.issues.append(f"❌ Дублирующиеся номера в overrides: {duplicates}")
                print(f"  ❌ Найдено {len(duplicates)} дубликатов")
            else:
                print("  ✅ Дубликатов номеров не найдено")
                
        except Exception as e:
            self.issues.append(f"❌ Ошибка чтения phone_overrides.yml: {e}")
            print(f"  ❌ Ошибка: {e}")
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Нормализация телефона как в PostProcessor."""
        import re
        digits = re.sub(r'\D+', '', phone)
        if digits.startswith('8') and len(digits) == 11:
            digits = '7' + digits[1:]
        if digits.startswith('7') and not digits.startswith('+'):
            digits = '+' + digits
        if not digits.startswith('+'):
            digits = '+' + digits
        return digits

if __name__ == "__main__":
    main()
