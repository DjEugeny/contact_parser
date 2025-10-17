# 🔬 КОРНЕВЫЕ ПРИЧИНЫ ПРОБЛЕМ ДЕДУПЛИКАЦИИ

## 🎯 Главная проблема

**GID ключи слишком специфичны и не учитывают вариативность данных от LLM.**

---

## 🏗️ Архитектурные проблемы

### 1. **Жёсткая привязка к organization_gid**

#### Текущая логика:

```python
# src/registry/global_registry.py, строка 318-321
def iter_contact_keys(contact: Dict[str, Any], org_gid: Optional[str]) -> Iterable[Tuple[str, ...]]:
    org_key = org_gid if org_gid is not None else "PERSONAL"
    
    email = norm_email(contact.get("email"))
    if email:
        key = ("CONTACT", "EMAIL", org_key, email)  # ← org_key в ключе!
        yield key
```

#### Проблема:

Если `org_gid` меняется, ключ меняется полностью:

```python
# Письмо 1: organization_id = 1
key = ("CONTACT", "EMAIL", "58a49494-...", "s.voronova@dna-technology.ru")

# Письмо 2: organization_id = null
key = ("CONTACT", "EMAIL", "PERSONAL", "s.voronova@dna-technology.ru")

# → Ключи разные → GID разные!
```

#### Последствия:

- ✅ **Плюс**: Разделяет контакты с одинаковым email в разных организациях
  - Пример: Иван Иванов в компании A и Иван Иванов в компании B
  
- ❌ **Минус**: Создаёт дубли при изменении organization_id
  - Пример: Светлана Воронова то с org, то без org → 2 GID

---

### 2. **Нестабильные ключи организаций**

#### Текущая логика:

```python
# src/registry/global_registry.py, строки 250-308
def iter_organization_keys(org: Dict[str, Any]) -> Iterable[Tuple[str, ...]]:
    # Приоритет 1: DOMAIN (если есть website)
    website = org.get("website")
    if website:
        domain = extract_domain(website)
        if domain:
            yield ("ORG", "DOMAIN", domain)
    
    # Приоритет 2: INN (если есть)
    inn = org.get("inn")
    if inn:
        yield ("ORG", "INN", inn)
    
    # Приоритет 3: NAME_CITY (если есть название и город)
    name = norm_org_name(org.get("name"))
    city = norm_city_alias(org.get("city"))
    if name and city:
        yield ("ORG", "NAME_CITY", name, city)
    
    # Приоритет 4: FALLBACK (случайный хеш!)
    fallback_key = compute_fallback_hash(org)
    yield ("ORG", "FALLBACK", fallback_key)
```

#### Проблема:

**Fallback ключ случайный** и создаётся для каждого нового экземпляра организации:

```python
def compute_fallback_hash(org: Dict[str, Any]) -> str:
    raw = json.dumps(org, ensure_ascii=False, sort_keys=True)
    h = sha256(raw.encode("utf-8")).digest()
    return h[:8].hex()  # ← Зависит от ВСЕХ полей!
```

Если **хоть одно поле** отличается → хеш отличается:

```python
org1 = {"name": "Хеликон", "city": null}
org2 = {"name": "Хеликон", "city": "Новосибирск"}

# → Разные хеши → Разные GID!
```

#### Последствия:

- ❌ Организация без website/inn/города получает **случайный** GID каждый раз
- ❌ Изменение любого поля (phones, address, emails) меняет fallback хеш

---

### 3. **Отсутствие fuzzy matching**

#### Текущая логика:

Система ищет **точное совпадение** ключа в реестре:

```python
# src/registry/global_registry.py, строка 444
gid = self.key_index.get(key)  # ← Только точное совпадение!
if gid:
    return ResolutionResult(gid=gid, ...)
```

#### Проблема:

Нет механизма для поиска **похожих** контактов/организаций:

- Email одинаковый, но org_gid разный → не находит
- Название организации слегка отличается → не находит
- Имя контакта в разном порядке → не находит

#### Пример:

```python
# Реестр содержит:
("CONTACT", "EMAIL", "org-gid-1", "ivan@company.ru") → GID-A

# Новый контакт:
("CONTACT", "EMAIL", "org-gid-2", "ivan@company.ru") → Создаст GID-B!

# Хотя email одинаковый!
```

---

### 4. **Порядок приоритета ключей не оптимален**

#### Текущий порядок для контактов:

```python
def iter_contact_keys(contact, org_gid):
    # 1. EMAIL (если есть)
    if email:
        yield ("CONTACT", "EMAIL", org_key, email)
    
    # 2. PHONE (для каждого телефона)
    for phone in phones:
        yield ("CONTACT", "PHONE", org_key, phone)
    
    # 3. NAME_POSITION (fallback)
    yield ("CONTACT", "NAME_POSITION", org_key, name, position)
```

#### Проблема:

Если email отсутствует, используется **PHONE** или **NAME_POSITION**, которые **менее стабильны**:

- **NAME_POSITION** зависит от порядка слов в имени (нестабильно)
- **PHONE** может быть корпоративным (дублируется между контактами)

#### Пример нестабильности:

```python
# LLM извлёк имя в разном порядке:
name1 = norm_contact_name("Кондратюк Екатерина")   # → "екатерина кондратюк"
name2 = norm_contact_name("Екатерина Кондратюк")   # → "екатерина кондратюк"

# Или:
name3 = norm_contact_name("Кондратюк Е.")         # → "е кондратюк"

# → Разные ключи → Разные GID!
```

---

## 📊 Сравнение с идеальной системой

| Аспект | Текущая система | Идеальная система |
|--------|----------------|-------------------|
| **Ключ EMAIL** | Зависит от org_gid | Глобальный (не зависит от org) |
| **Fallback для организаций** | Случайный хеш | Детерминированный по названию |
| **Fuzzy matching** | Отсутствует | Есть (поиск похожих) |
| **Приоритет ключей** | EMAIL → PHONE → NAME | EMAIL (всегда), остальные — алиасы |
| **Обработка дублей** | Создаёт новый GID | Ищет существующие похожие |

---

## 💡 Почему так было сделано?

### Исходная цель:

**Разделять контакты с одинаковым email в разных организациях.**

Пример:
- Иван Петров (ivan@mail.ru) работает в компании A
- Другой Иван Петров (ivan@mail.ru) работает в компании B
- Это РАЗНЫЕ люди → должны иметь РАЗНЫЕ GID

### Решение:

Включить `org_gid` в ключ контакта:
```python
key = ("CONTACT", "EMAIL", org_gid, email)
```

### Проблема решения:

Если контакт **меняет** организацию или **теряет** организацию → новый ключ → новый GID.

---

## 🎯 Корневая проблема системы

**Компромисс между точностью и стабильностью смещён в сторону точности.**

### Что важнее?

| Сценарий | Текущая система | Желаемое поведение |
|----------|----------------|---------------------|
| Контакт меняет организацию | Создаёт новый GID ❌ | Сохраняет старый GID ✅ |
| Контакт теряет организацию (LLM ошибка) | Создаёт новый GID ❌ | Сохраняет старый GID ✅ |
| Два разных человека с одинаковым email в разных компаниях | Создаёт 2 GID ✅ | Создаёт 2 GID ✅ |
| Организация получает website после первой обработки | Создаёт новый GID ❌ | Сохраняет старый GID + alias ✅ |

### Вывод:

Текущая система **переоценивает** риск дублей и **недооценивает** риск фрагментации.

---

## 🔧 Необходимые изменения

### 1. **Глобальный ключ EMAIL для контактов**

```python
# Вместо:
key = ("CONTACT", "EMAIL", org_gid, email)

# Делать:
primary_key = ("CONTACT", "EMAIL_GLOBAL", email)
alias_key = ("CONTACT", "EMAIL_ORG", org_gid, email)
```

### 2. **Детерминированный fallback для организаций**

```python
# Вместо случайного хеша:
fallback = sha256(full_json).hex()

# Делать детерминированный по названию:
fallback = sha256(norm_name + norm_city).hex()
```

### 3. **Fuzzy matching перед созданием нового GID**

```python
# Перед созданием нового GID:
similar_contacts = find_similar_by_email(email, threshold=0.9)
if similar_contacts:
    return existing_gid  # Переиспользовать
```

### 4. **Алиасы для связи контакт-организация**

```python
# GID контакта не зависит от организации
contact_gid = resolve("CONTACT", "EMAIL_GLOBAL", email)

# Но сохраняем связь через alias:
add_alias(contact_gid, ("CONTACT", "IN_ORG", org_gid, email))
```

---

**Дата анализа**: 2025-10-16 23:35  
**Следующий документ**: [SOLUTION_PROPOSAL.md](./SOLUTION_PROPOSAL.md)
