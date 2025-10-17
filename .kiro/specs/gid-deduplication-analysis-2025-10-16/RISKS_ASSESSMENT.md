# ⚠️ ОЦЕНКА РИСКОВ ИЗМЕНЕНИЯ СИСТЕМЫ GID

## 🎯 Цель документа

Проанализировать **потенциальные риски** предложенных изменений и предложить стратегии митигации.

---

## 🔴 КРИТИЧЕСКИЕ РИСКИ

### Риск 1: Случайное объединение разных людей

#### Описание:
Два **разных** человека с **одинаковым email** в разных компаниях могут быть ошибочно объединены в один GID.

#### Пример:
```
Контакт А: ivan.petrov@gmail.com в компании "Альфа"
Контакт Б: ivan.petrov@gmail.com в компании "Бета"

С EMAIL_GLOBAL оба получат один GID!
```

#### Вероятность: **СРЕДНЯЯ** (10-15%)

Email `@gmail.com`, `@yandex.ru`, `@mail.ru` — личные, могут совпадать.

#### Влияние: **КРИТИЧЕСКОЕ**

Объединение разных людей в одного → **потеря данных**, неверная аналитика.

#### Митигация:

**Решение 1: Проверка контекстов**

```python
def resolve_contact(self, contact, org_gid):
    # Ищем по EMAIL_GLOBAL
    primary_key = ("CONTACT", "EMAIL_GLOBAL", email)
    gid = self.key_index.get(primary_key)
    
    if gid:
        # Нашли существующий GID
        # Проверяем: был ли этот контакт УЖЕ в этой организации?
        org_context_key = ("CONTACT", "EMAIL_IN_ORG", org_gid, email)
        
        if org_context_key in self.key_index:
            # Да, был → переиспользуем GID
            return ResolutionResult(gid=gid, ...)
        else:
            # Нет, не был → ПРОВЕРЯЕМ КОНФЛИКТ
            existing_orgs = self._get_contact_organizations(gid)
            
            if existing_orgs:
                # Контакт уже связан с ДРУГОЙ организацией!
                # Возможно, это ДРУГОЙ человек
                
                # Проверяем дополнительные сигналы:
                if self._is_likely_different_person(contact, existing_contact):
                    # Создаём НОВЫЙ GID для этого контакста
                    new_gid = self._generate_gid(...)
                    return ResolutionResult(gid=new_gid, ...)
                else:
                    # Скорее всего, тот же человек в новой компании
                    # Добавляем алиас
                    self._add_alias(gid, org_context_key)
                    return ResolutionResult(gid=gid, ...)
    
    # Создаём новый GID
    ...
```

**Решение 2: Whitelist личных доменов**

```python
PERSONAL_DOMAINS = {"gmail.com", "yandex.ru", "mail.ru", "yahoo.com", ...}

def is_personal_email(email: str) -> bool:
    domain = email.split("@")[-1]
    return domain in PERSONAL_DOMAINS

def resolve_contact(self, contact, org_gid):
    email = contact.get("email")
    
    if is_personal_email(email):
        # Для личных email ВСЕГДА используем org_gid в ключе
        key = ("CONTACT", "EMAIL", org_gid or "PERSONAL", email)
    else:
        # Для корпоративных email используем глобальный ключ
        key = ("CONTACT", "EMAIL_GLOBAL", email)
    
    ...
```

**Решение 3: Порог уверенности для fuzzy match**

```python
similar = find_similar_contacts(email=email, name=name)

if similar:
    best_gid, similarity = similar[0]
    
    # Требуем ДОПОЛНИТЕЛЬНЫЕ совпадения для личных email
    if is_personal_email(email):
        # Для личных email требуем 95%+ сходство по имени
        if similarity < 0.95:
            # Создаём новый GID (лучше дубль, чем объединение)
            return self._create_new_gid(contact)
    else:
        # Для корпоративных email достаточно 85%
        if similarity >= 0.85:
            return ResolutionResult(gid=best_gid, ...)
```

#### Рекомендация:

**Использовать комбинацию всех трёх решений**:
1. Whitelist личных доменов (для них — старая логика с org_gid)
2. Проверка контекстов перед переиспользованием GID
3. Высокий порог для fuzzy match

---

### Риск 2: Деградация существующих GID

#### Описание:
Изменение логики ключей может привести к тому, что **существующие контакты получат НОВЫЕ GID**.

#### Пример:
```
Реестр содержит:
  key: ("CONTACT", "EMAIL", "org-gid-1", "ivan@company.ru") → GID-A

Новая логика ищет:
  key: ("CONTACT", "EMAIL_GLOBAL", "ivan@company.ru") → НЕ НАХОДИТ!

Создаёт GID-B → ДУБЛЬ!
```

#### Вероятность: **ВЫСОКАЯ** (80%+)

Все существующие контакты используют старые ключи.

#### Влияние: **КРИТИЧЕСКОЕ**

Массовое дублирование → разрушение реестра.

#### Митигация:

**Решение: Версионирование + миграция**

```python
class GlobalIDRegistry:
    
    def resolve_contact(self, contact, org_gid):
        # ШАГ 1: Ищем по НОВЫМ ключам
        new_keys = iter_contact_keys_v2(contact, org_gid)
        for key in new_keys:
            gid = self.key_index.get(key)
            if gid:
                return ResolutionResult(gid=gid, source="registry_v2", ...)
        
        # ШАГ 2: Ищем по СТАРЫМ ключам (обратная совместимость)
        old_keys = iter_contact_keys_v1(contact, org_gid)
        for key in old_keys:
            gid = self.key_index.get(key)
            if gid:
                # НАШЛИ по старому ключу!
                # Мигрируем: добавляем новые ключи как алиасы
                self._migrate_to_v2(gid, new_keys, old_key=key)
                return ResolutionResult(gid=gid, source="migrated_from_v1", ...)
        
        # ШАГ 3: Создаём новый GID
        primary_key = new_keys[0]
        gid = self._generate_gid(primary_key, ...)
        self._create_record(gid=gid, primary_key=primary_key, aliases=new_keys[1:])
        return ResolutionResult(gid=gid, source="new", ...)
    
    def _migrate_to_v2(self, gid: str, new_keys: List[Tuple], old_key: Tuple):
        """Мигрирует контакт на новую версию ключей."""
        # Добавляем новые ключи как алиасы к существующему GID
        for new_key in new_keys:
            if new_key not in self.key_index:
                self.key_index[new_key] = gid
                self._log_alias(gid, new_key, reason="v1_to_v2_migration")
        
        # Помечаем старый ключ как deprecated (но не удаляем!)
        # Это позволит переиспользовать его в будущем
```

**План миграции**:

1. **Фаза 1: Тестирование** (1-2 дня)
   - Обработать 100-200 писем с новой логикой
   - Проверить: создаются ли дубли?
   - Логировать все миграции

2. **Фаза 2: Плавное внедрение** (1 неделя)
   - Обрабатывать новые письма с поддержкой обеих версий
   - Автоматически мигрировать старые GID на новые ключи
   - Мониторить метрики дублирования

3. **Фаза 3: Полная миграция** (1-2 недели)
   - Пересчитать все GID в реестре (добавить v2 ключи)
   - Проверить консистентность
   - Создать backup перед удалением v1 ключей

4. **Фаза 4: Cleanup** (опционально)
   - Удалить v1 ключи из реестра (если уверены)

#### Рекомендация:

**НЕ спешить с удалением старой логики**. Поддерживать обе версии минимум 1 месяц.

---

## 🟠 ВЫСОКИЕ РИСКИ

### Риск 3: Ложные fuzzy match

#### Описание:
Fuzzy matching может **ошибочно** объединить разных людей с похожими именами.

#### Пример:
```
Контакт А: "Иванов Иван Иванович" + иван.иванов@company-a.ru
Контакт Б: "Иванов Иван Петрович" + иван.иванов@company-b.ru

Similarity по имени: 85% → ОБЪЕДИНИТ!
```

#### Вероятность: **СРЕДНЯЯ** (5-10%)

Русские имена часто похожи (Иванов, Петров, Сидоров).

#### Влияние: **ВЫСОКОЕ**

Объединение разных людей → потеря данных.

#### Митигация:

```python
def compute_name_similarity(name1: str, name2: str) -> float:
    """Умная функция сравнения имён."""
    
    # Разбиваем на части (фамилия, имя, отчество)
    parts1 = name1.split()
    parts2 = name2.split()
    
    # Если разное количество частей → низкая вероятность совпадения
    if len(parts1) != len(parts2):
        return 0.5
    
    # Сравниваем каждую часть отдельно
    scores = []
    for p1, p2 in zip(parts1, parts2):
        # Фамилия/имя должны совпадать ТОЧНО
        if p1 == p2:
            scores.append(1.0)
        # Инициалы допустимы (И. = Иван)
        elif len(p1) == 1 or len(p2) == 1:
            if p1[0] == p2[0]:
                scores.append(0.8)
            else:
                scores.append(0.0)
        else:
            # Разные части имени → НЕ тот же человек
            return 0.0
    
    return sum(scores) / len(scores)
```

**Дополнительно: Требовать совпадение email домена**

```python
if is_corporate_email(email1) and is_corporate_email(email2):
    domain1 = email1.split("@")[1]
    domain2 = email2.split("@")[1]
    
    if domain1 != domain2:
        # Разные компании → скорее всего, разные люди
        return 0.0  # НЕ объединяем
```

#### Рекомендация:

**Использовать fuzzy matching ТОЛЬКО для имён без отчества**. Для полных ФИО требовать точное совпадение.

---

### Риск 4: Проблемы производительности

#### Описание:
Fuzzy matching требует **O(N)** сканирование всего реестра → медленно.

#### Влияние: **СРЕДНЕЕ**

Замедление обработки в 2-5 раз.

#### Митигация:

**Решение 1: Индексы**

```python
class GlobalIDRegistry:
    
    def __init__(self):
        self.key_index = {}  # key → gid
        self.email_index = {}  # email → [gids]
        self.phone_index = {}  # phone → [gids]
        self.name_index = {}  # normalized_name → [gids]
    
    def find_similar_contacts(self, email=None, phone=None, name=None):
        candidates = set()
        
        # O(1) поиск по email
        if email:
            candidates.update(self.email_index.get(email, []))
        
        # O(1) поиск по phone
        if phone:
            candidates.update(self.phone_index.get(phone, []))
        
        # O(K) поиск по имени (только среди кандидатов)
        if name and not candidates:
            normalized = norm_contact_name(name)
            candidates.update(self.name_index.get(normalized, []))
        
        return candidates
```

**Решение 2: Кеширование**

```python
from functools import lru_cache

@lru_cache(maxsize=10000)
def find_similar_contacts_cached(email: str, phone: str, name: str):
    return find_similar_contacts(email, phone, name)
```

**Решение 3: Ограничение поиска**

```python
# Fuzzy matching ТОЛЬКО если не нашли точное совпадение
if not exact_match:
    similar = find_similar_contacts(...)  # Дорогая операция
```

#### Рекомендация:

Использовать **все три** решения: индексы + кеш + ограничение.

---

## 🟡 СРЕДНИЕ РИСКИ

### Риск 5: Несовместимость с внешними системами

#### Описание:
Если GID используются в **других системах** (CRM, аналитика), изменение GID может сломать интеграции.

#### Вероятность: **НИЗКАЯ** (система ещё не в production)

#### Влияние: **СРЕДНЕЕ**

Потребуется обновление внешних систем.

#### Митигация:

1. **API для маппинга GID**:
   ```python
   def get_gid_history(contact_id: int) -> List[str]:
       """Возвращает все GID, которые когда-либо были у контакта."""
       return [gid for gid in historical_gids if ...] 
   ```

2. **Версионирование API**:
   - `/v1/contacts/{gid}` — старая версия (может возвращать несколько контактов)
   - `/v2/contacts/{gid}` — новая версия (один контакт)

#### Рекомендация:

Внедрять изменения **до** production-запуска системы.

---

### Риск 6: Увеличение размера реестра

#### Описание:
Поддержка двух версий ключей увеличит размер `registry/contacts.jsonl`.

#### Влияние: **НИЗКОЕ**

Размер увеличится на ~30-50%, но это не критично.

#### Митигация:

1. Периодическая очистка старых ключей (после миграции)
2. Сжатие реестра (gzip)
3. Использование БД вместо JSONL (в будущем)

---

## 📊 Сводная матрица рисков

| Риск | Вероятность | Влияние | Приоритет | Митигация |
|------|-------------|---------|-----------|-----------|
| Объединение разных людей | Средняя | Критическое | 🔴 **P0** | Whitelist + проверка контекстов |
| Деградация GID | Высокая | Критическое | 🔴 **P0** | Версионирование + плавная миграция |
| Ложные fuzzy match | Средняя | Высокое | 🟠 **P1** | Умное сравнение имён |
| Проблемы производительности | Низкая | Среднее | 🟡 **P2** | Индексы + кеш |
| Несовместимость с внешними системами | Низкая | Среднее | 🟡 **P2** | API версионирование |
| Увеличение размера реестра | Высокая | Низкое | 🟢 **P3** | Периодическая очистка |

---

## ✅ Рекомендуемый план внедрения

### Этап 1: Подготовка (2-3 дня)
1. ✅ Создать whitelist личных доменов
2. ✅ Реализовать версионирование ключей (v1/v2)
3. ✅ Написать тесты для проверки деградации GID
4. ✅ Создать backup реестра

### Этап 2: Пилотное тестирование (1 неделя)
1. ✅ Обработать 100-200 писем с новой логикой
2. ✅ Проверить метрики дублирования
3. ✅ Логировать все конфликты и fuzzy match
4. ✅ Ручная проверка объединённых контактов

### Этап 3: Постепенное внедрение (2-3 недели)
1. ✅ Включить v2 для новых писем
2. ✅ Автоматически мигрировать v1 → v2 при обращении
3. ✅ Мониторить метрики качества
4. ✅ Готовность к откату на v1

### Этап 4: Полная миграция (1 месяц)
1. ✅ Пересчитать весь реестр (добавить v2 ключи)
2. ✅ Проверить консистентность
3. ✅ Удалить v1 ключи (опционально)

### Этап 5: Мониторинг (ongoing)
1. ✅ Отслеживать частоту fuzzy match
2. ✅ Проверять жалобы на дубли/объединения
3. ✅ Настраивать пороги similarity

---

## 🎯 Критерии успеха

| Метрика | До изменений | Целевое значение | Граница отката |
|---------|--------------|------------------|----------------|
| Дублей контактов с одинаковым email | 30% | < 5% | > 15% |
| Ложных объединений | 0% | < 1% | > 2% |
| Деградация существующих GID | 0% | < 0.1% | > 1% |
| Время обработки письма | 15с | < 20с | > 30с |

---

**Дата оценки**: 2025-10-16 23:55  
**Статус**: Готово к обсуждению с командой
