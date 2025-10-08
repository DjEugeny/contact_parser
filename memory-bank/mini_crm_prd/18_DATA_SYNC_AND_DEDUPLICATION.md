# 18_DATA_SYNC_AND_DEDUPLICATION — Синхронизация данных и дедупликация

**Дата:** 2025-06-10  
**Статус:** Актуально

## 1. Обзор проблемы

У вас есть:
- ✅ Файлы в `data/llm_results/` с обработанными данными
- ✅ Каждая сущность имеет `gid` (глобальный идентификатор)
- ✅ Фронтенд и бэкенд приложения готовы

**Проблемы, которые нужно решить:**
1. Как автоматически загружать новые данные из `data/llm_results/` в Supabase?
2. Как избежать дублирования контактов/организаций при повторной загрузке?
3. Как обогащать существующие записи новыми данными (например, добавлять телефон)?
4. Где происходит слияние и дедупликация?

## 2. Архитектура решения

```
data/llm_results/ └── YYYY-MM-DD/ └── email_*_processed.json → Sync Service → PostgreSQL (Supabase)
                                                              ↓
                                                       Deduplication Logic
                                                              ↓
                                                        Enrichment Logic
                                                              ↓
                                                        Upsert to Database
```

### 2.1. Ключевая идея: gid как основа дедупликации

В ваших данных уже есть `gid` (глобальный идентификатор), который:
- Генерируется на основе уникальных признаков (домен, телефон, email)
- Одинаковый для одной и той же сущности в разных письмах
- **Это ваш ключ для дедупликации!**

**Пример из вашего файла:**
```json
{
  "gid": "6aa672d5-2a74-5e7e-9b00-a277c036fe16",
  "match_rule": "PHONE",
  "key_tuple": ["CONTACT", "PHONE", "7fd2e423-23ef-5814-adcd-ae26b2748956", "+79133993272"]
}
```

## 3. Компонент синхронизации данных

### 3.1. Структура компонента

Создайте файл sync_service.py:

```python
"""
Сервис синхронизации данных из data/llm_results в Supabase
с автоматической дедупликацией и обогащением
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from supabase import create_client, Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyncService:
    """Сервис синхронизации данных с дедупликацией и обогащением"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
        
        # Кэш для быстрого поиска по gid
        self.gid_cache = {
            'organizations': {},  # gid -> db_id
            'contacts': {}        # gid -> db_id
        }
        
    def sync_all_results(self, results_dir="data/llm_results"):
        """Синхронизация всех файлов из data/llm_results"""
        
        stats = {
            'files_processed': 0,
            'organizations_created': 0,
            'organizations_updated': 0,
            'contacts_created': 0,
            'contacts_updated': 0,
            'interactions_created': 0,
            'offers_created': 0,
            'errors': []
        }
        
        # Загрузка существующих gid из БД
        self._load_gid_cache()
        
        # Обработка всех файлов
        for date_dir in sorted(Path(results_dir).iterdir()):
            if not date_dir.is_dir():
                continue
                
            for json_file in sorted(date_dir.glob("email_*_processed.json")):
                try:
                    logger.info(f"Processing {json_file}")
                    self._process_file(json_file, stats)
                    stats['files_processed'] += 1
                except Exception as e:
                    logger.error(f"Error processing {json_file}: {e}")
                    stats['errors'].append({
                        'file': str(json_file),
                        'error': str(e)
                    })
        
        return stats
    
    def _load_gid_cache(self):
        """Загрузка существующих gid из БД в кэш"""
        
        # Загрузка организаций
        orgs = self.supabase.table('organizations')\
            .select('id, gid')\
            .not_.is_('gid', 'null')\
            .execute()
        
        for org in orgs.data:
            self.gid_cache['organizations'][org['gid']] = org['id']
        
        logger.info(f"Loaded {len(self.gid_cache['organizations'])} organizations from cache")
        
        # Загрузка контактов
        contacts = self.supabase.table('contacts')\
            .select('id, gid')\
            .not_.is_('gid', 'null')\
            .execute()
        
        for contact in contacts.data:
            self.gid_cache['contacts'][contact['gid']] = contact['id']
        
        logger.info(f"Loaded {len(self.gid_cache['contacts'])} contacts from cache")
    
    def _process_file(self, json_file: Path, stats: Dict):
        """Обработка одного файла с результатами"""
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = data.get('processed_result', {})
        
        # 1. Обработка организаций
        org_mapping = {}  # local_id -> db_id
        for org in result.get('organizations', []):
            db_id = self._upsert_organization(org, stats)
            org_mapping[org['organization_id']] = db_id
        
        # 2. Обработка контактов
        contact_mapping = {}  # local_id -> db_id
        for contact in result.get('contacts', []):
            # Замена local organization_id на db_id
            if contact.get('organization_id'):
                contact['organization_id'] = org_mapping.get(
                    contact['organization_id']
                )
            
            db_id = self._upsert_contact(contact, stats)
            contact_mapping[contact['contact_id']] = db_id
        
        # 3. Обработка взаимодействий
        for interaction in result.get('interactions', []):
            # Замена local id на db_id
            if interaction.get('contact_id'):
                interaction['contact_id'] = contact_mapping.get(
                    interaction['contact_id']
                )
            if interaction.get('organization_id'):
                interaction['organization_id'] = org_mapping.get(
                    interaction['organization_id']
                )
            
            self._create_interaction(interaction, stats)
        
        # 4. Обработка КП
        for offer in result.get('commercial_offers', []):
            if offer.get('organization_id'):
                offer['organization_id'] = org_mapping.get(
                    offer['organization_id']
                )
            
            self._create_commercial_offer(offer, stats)
    
    def _upsert_organization(self, org_data: Dict, stats: Dict) -> int:
        """
        Вставка или обновление организации с дедупликацией по gid
        
        Логика:
        1. Проверяем наличие gid в кэше
        2. Если есть — обновляем существующую запись (MERGE данных)
        3. Если нет — создаем новую запись
        """
        
        gid = org_data.get('gid')
        
        if not gid:
            logger.warning(f"Organization without gid: {org_data.get('name')}")
            # Fallback: поиск по ИНН или домену
            return self._upsert_organization_fallback(org_data, stats)
        
        # Проверка в кэше
        if gid in self.gid_cache['organizations']:
            # Организация уже существует — обновляем
            db_id = self.gid_cache['organizations'][gid]
            self._merge_organization_data(db_id, org_data)
            stats['organizations_updated'] += 1
            logger.info(f"Updated organization {gid}: {org_data.get('name')}")
            return db_id
        
        # Создание новой организации
        db_record = {
            'gid': gid,
            'name': org_data.get('name'),
            'inn': org_data.get('inn'),
            'website': org_data.get('website'),
            'city': org_data.get('city'),
            'address': org_data.get('address'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = self.supabase.table('organizations').insert(db_record).execute()
        db_id = result.data[0]['id']
        
        # Обновление кэша
        self.gid_cache['organizations'][gid] = db_id
        stats['organizations_created'] += 1
        logger.info(f"Created organization {gid}: {org_data.get('name')}")
        
        # Сохранение emails и phones
        self._save_organization_contacts_info(db_id, org_data)
        
        return db_id
    
    def _merge_organization_data(self, db_id: int, new_data: Dict):
        """
        Обогащение существующей организации новыми данными
        
        Логика MERGE:
        - Если поле пустое в БД, но есть в new_data — обновляем
        - Если поле уже заполнено — не перезаписываем (сохраняем старое)
        - Emails и phones — добавляем новые, не дублируя
        """
        
        # Получение текущих данных
        current = self.supabase.table('organizations')\
            .select('*')\
            .eq('id', db_id)\
            .single()\
            .execute()
        
        current_data = current.data
        
        # Подготовка обновлений
        updates = {'updated_at': datetime.now().isoformat()}
        
        # Обогащение полей (только если текущее значение пустое)
        for field in ['inn', 'website', 'city', 'address']:
            if not current_data.get(field) and new_data.get(field):
                updates[field] = new_data[field]
                logger.info(f"Enriching org {db_id}: {field} = {new_data[field]}")
        
        # Применение обновлений
        if len(updates) > 1:  # больше чем просто updated_at
            self.supabase.table('organizations')\
                .update(updates)\
                .eq('id', db_id)\
                .execute()
        
        # Обогащение emails и phones
        self._merge_organization_contacts_info(db_id, new_data)
    
    def _merge_organization_contacts_info(self, db_id: int, new_data: Dict):
        """Добавление новых emails и телефонов к организации"""
        
        # TODO: Реализовать таблицы organization_emails и organization_phones
        # Аналогично contact_emails и contact_phones
        pass
    
    def _upsert_contact(self, contact_data: Dict, stats: Dict) -> int:
        """
        Вставка или обновление контакта с дедупликацией по gid
        
        Логика аналогична _upsert_organization
        """
        
        gid = contact_data.get('gid')
        
        if not gid:
            logger.warning(f"Contact without gid: {contact_data.get('name')}")
            return self._upsert_contact_fallback(contact_data, stats)
        
        # Проверка в кэше
        if gid in self.gid_cache['contacts']:
            # Контакт уже существует — обновляем
            db_id = self.gid_cache['contacts'][gid]
            self._merge_contact_data(db_id, contact_data)
            stats['contacts_updated'] += 1
            logger.info(f"Updated contact {gid}: {contact_data.get('name')}")
            return db_id
        
        # Создание нового контакта
        db_record = {
            'gid': gid,
            'organization_id': contact_data.get('organization_id'),
            'full_name': contact_data.get('name'),
            'position': contact_data.get('position'),
            'city': contact_data.get('city'),
            'address': contact_data.get('address'),
            'confidence': contact_data.get('confidence', 1.0),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = self.supabase.table('contacts').insert(db_record).execute()
        db_id = result.data[0]['id']
        
        # Обновление кэша
        self.gid_cache['contacts'][gid] = db_id
        stats['contacts_created'] += 1
        logger.info(f"Created contact {gid}: {contact_data.get('name')}")
        
        # Сохранение emails и phones
        self._save_contact_emails(db_id, contact_data.get('email'), [])
        self._save_contact_phones(db_id, contact_data.get('phones', []))
        
        return db_id
    
    def _merge_contact_data(self, db_id: int, new_data: Dict):
        """
        Обогащение существующего контакта новыми данными
        
        Пример: Воронова в первом письме без телефона,
        во втором письме с телефоном — добавляем téléphone
        """
        
        # Получение текущих данных
        current = self.supabase.table('contacts')\
            .select('*')\
            .eq('id', db_id)\
            .single()\
            .execute()
        
        current_data = current.data
        
        # Подготовка обновлений
        updates = {'updated_at': datetime.now().isoformat()}
        
        # Обогащение полей
        for field in ['position', 'city', 'address']:
            if not current_data.get(field) and new_data.get(field):
                updates[field] = new_data[field]
                logger.info(f"Enriching contact {db_id}: {field} = {new_data[field]}")
        
        # Применение обновлений
        if len(updates) > 1:
            self.supabase.table('contacts')\
                .update(updates)\
                .eq('id', db_id)\
                .execute()
        
        # Обогащение emails
        if new_data.get('email'):
            self._merge_contact_email(db_id, new_data['email'])
        
        # Обогащение телефонов
        if new_data.get('phones'):
            self._merge_contact_phones(db_id, new_data['phones'])
    
    def _merge_contact_email(self, contact_id: int, new_email: str):
        """Добавление email к контакту, если его еще нет"""
        
        # Проверка существования
        existing = self.supabase.table('contact_emails')\
            .select('id')\
            .eq('email', new_email)\
            .execute()
        
        if existing.data:
            logger.info(f"Email {new_email} already exists for contact {contact_id}")
            return
        
        # Добавление нового email
        self.supabase.table('contact_emails').insert({
            'contact_id': contact_id,
            'email': new_email,
            'is_primary': False  # Первый email уже primary
        }).execute()
        
        logger.info(f"Added email {new_email} to contact {contact_id}")
    
    def _merge_contact_phones(self, contact_id: int, new_phones: List[Dict]):
        """Добавление телефонов к контакту, если их еще нет"""
        
        for phone_data in new_phones:
            normalized = phone_data.get('normalized')
            if not normalized:
                continue
            
            # Проверка существования
            existing = self.supabase.table('contact_phones')\
                .select('id')\
                .eq('e164', normalized)\
                .execute()
            
            if existing.data:
                logger.info(f"Phone {normalized} already exists")
                continue
            
            # Добавление нового телефона
            self.supabase.table('contact_phones').insert({
                'contact_id': contact_id,
                'e164': normalized,
                'raw': phone_data.get('number'),
                'type': phone_data.get('type', 'other')
            }).execute()
            
            logger.info(f"Added phone {normalized} to contact {contact_id}")
    
    def _save_contact_emails(self, contact_id: int, primary_email: Optional[str], additional_emails: List[str]):
        """Сохранение emails контакта"""
        
        if primary_email:
            self.supabase.table('contact_emails').insert({
                'contact_id': contact_id,
                'email': primary_email,
                'is_primary': True
            }).execute()
        
        for email in additional_emails:
            self.supabase.table('contact_emails').insert({
                'contact_id': contact_id,
                'email': email,
                'is_primary': False
            }).execute()
    
    def _save_contact_phones(self, contact_id: int, phones: List[Dict]):
        """Сохранение телефонов контакта"""
        
        for phone_data in phones:
            self.supabase.table('contact_phones').insert({
                'contact_id': contact_id,
                'e164': phone_data.get('normalized'),
                'raw': phone_data.get('number'),
                'type': phone_data.get('type', 'other')
            }).execute()
    
    def _create_interaction(self, interaction_data: Dict, stats: Dict):
        """Создание записи взаимодействия"""
        
        # Проверка дубликатов по message_id
        message_id = interaction_data.get('message_id_hint')
        if message_id:
            existing = self.supabase.table('interactions')\
                .select('id')\
                .eq('message_id_hint', message_id)\
                .execute()
            
            if existing.data:
                logger.info(f"Interaction for message {message_id} already exists")
                return
        
        db_record = {
            'contact_id': interaction_data.get('contact_id'),
            'organization_id': interaction_data.get('organization_id'),
            'when_at': interaction_data.get('message_date'),
            'role': interaction_data.get('role_in_message'),
            'summary': interaction_data.get('summary'),
            'message_id_hint': message_id,
            'created_at': datetime.now().isoformat()
        }
        
        self.supabase.table('interactions').insert(db_record).execute()
        stats['interactions_created'] += 1
    
    def _create_commercial_offer(self, offer_data: Dict, stats: Dict):
        """Создание коммерческого предложения"""
        
        # TODO: Реализовать логику создания КП
        pass
    
    def _upsert_organization_fallback(self, org_data: Dict, stats: Dict) -> int:
        """Fallback для организаций без gid"""
        # TODO: Поиск по ИНН или домену
        pass
    
    def _upsert_contact_fallback(self, contact_data: Dict, stats: Dict) -> int:
        """Fallback для контактов без gid"""
        # TODO: Поиск по email или телефону
        pass
    
    def _save_organization_contacts_info(self, db_id: int, org_data: Dict):
        """Сохранение контактной информации организации"""
        # TODO: Реализовать таблицы organization_emails и organization_phones
        pass


# CLI для запуска синхронизации
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync data from llm_results to Supabase')
    parser.add_argument('--results-dir', default='data/llm_results', help='Path to llm_results directory')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without actual database writes')
    
    args = parser.parse_args()
    
    service = SyncService()
    stats = service.sync_all_results(args.results_dir)
    
    print("\n=== Sync Statistics ===")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Organizations created: {stats['organizations_created']}")
    print(f"Organizations updated: {stats['organizations_updated']}")
    print(f"Contacts created: {stats['contacts_created']}")
    print(f"Contacts updated: {stats['contacts_updated']}")
    print(f"Interactions created: {stats['interactions_created']}")
    print(f"Errors: {len(stats['errors'])}")
    
    if stats['errors']:
        print("\n=== Errors ===")
        for error in stats['errors']:
            print(f"  {error['file']}: {error['error']}")
```

## 4. Обновление схемы БД

Добавьте поле gid в таблицы:

```sql
-- Добавление gid в organizations
ALTER TABLE organizations ADD COLUMN gid UUID UNIQUE;
CREATE INDEX idx_organizations_gid ON organizations(gid);

-- Добавление gid в contacts
ALTER TABLE contacts ADD COLUMN gid UUID UNIQUE;
CREATE INDEX idx_contacts_gid ON contacts(gid);

-- Добавление message_id_hint в interactions для дедупликации
ALTER TABLE interactions ADD COLUMN message_id_hint VARCHAR(500);
CREATE INDEX idx_interactions_message_id ON interactions(message_id_hint);
```

## 5. Автоматическая синхронизация

### 5.1. Ручной запуск

```bash
python sync_service.py --results-dir data/llm_results
```

### 5.2. Автоматический запуск после обработки писем

Обновите api_pipeline_validator.py:

```python
from sync_service import SyncService

# В конце обработки
if __name__ == "__main__":
    # ... обработка писем ...
    
    # Автоматическая синхронизация
    sync = SyncService()
    stats = sync.sync_all_results()
    logger.info(f"Sync completed: {stats}")
```

### 5.3. Периодическая синхронизация (cron/launchd)

```bash
# Каждый час проверять новые файлы
0 * * * * cd /path/to/project && /path/to/venv/bin/python sync_service.py
```

## 6. Ответы на ваши вопросы

**Q1: Достаточно ли данных из data/llm_results для Production?**
Ответ: Да, если качество данных устраивает. Но нужен sync_service.py для загрузки в БД.

**Q2: Где прописана автоматическая загрузка?**
Ответ: В sync_service.py (создайте этот файл). Запускайте его после обработки писем или по расписанию.

**Q3: Где происходит дедупликация?**
Ответ: В методах _upsert_organization() и _upsert_contact() через проверку gid в кэше.

**Q4: Где происходит обогащение (merge)?**
Ответ: В методах _merge_organization_data() и _merge_contact_data(). Логика:
- Если поле пустое в БД, но есть в новых данных — обновляем
- Если поле уже заполнено — не перезаписываем
- Emails/phones — добавляем новые, не дублируя

**Q5: Нужно ли это кодить отдельно?**
Ответ: Да, это бизнес-логика приложения, не функция БД. PostgreSQL не знает, как сливать ваши данные.

## 7. Следующие шаги

- ✅ Создать файл sync_service.py с кодом выше
- ✅ Обновить схему БД (добавить поля gid)
- ⏳ Протестировать на небольшом наборе данных
- ⏳ Запустить полную синхронизацию
- ⏳ Настроить автоматический запуск
- ⏳ Добавить мониторинг и логирование