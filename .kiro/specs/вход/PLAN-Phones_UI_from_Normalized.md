
# TASK: Телефоны — единый UI-формат из `normalized` (backend), санитайзер и правила отображения

**Цель:** убрать рассинхрон между `number` и `normalized`, исключить лишние поля (например, `confidence` внутри телефона), и гарантировать одинаковое отображение телефонов в UI.

---

## 1) Инварианты (контракт данных)

- `original` — как в письме/подписи (сырой вид, ничего не менять).
- `normalized` — единственный источник истины для номера (**E.164** или `null`).
- `number` — **всегда** формируется **из `normalized`** нашим кодом (UI‑вид). Никаких «как пришло».
- `extension` — только добавочный (цифры/DTMF `0–9#*`) или `null`.
- В элементах `phones[]` разрешены **только ключи**: `type`, `number`, `normalized`, `original`, `extension`. Любые другие (напр., `confidence`) — **удалять** при санитизации.

---

## 2) Постпроцессинг: принудительно перегенерировать `number` из `normalized`

- Для каждого `phone` в `contacts[].phones[]` и `organizations[].phones[]`:
  - Если `normalized` задан:
    - Для RU: формат UI `+7 (XXX) XXX-XX-XX` (или через libphonenumber: INTERNATIONAL → затем привести к твоему шаблону).
    - Для прочих стран: `libphonenumber` INTERNATIONAL.
    - Записать результат в `number`.
  - Если `normalized = null`:
    - Фолбэк: аккуратно отформатировать (`number` или `original`) без доб. части, записать в `number`.
  - `original` не менять, `extension` не трогать.

Пример кода (скелет):
```python
import phonenumbers as pn

def format_ui_from_e164(e164: str) -> str:
    num = pn.parse(e164, None)
    region = pn.region_code_for_number(num)
    intl = pn.format_number(num, pn.PhoneNumberFormat.INTERNATIONAL)
    if region == "RU":
        # приведи intl к "+7 (XXX) XXX-XX-XX", если нужен строго такой шаблон
        return intl
    return intl

def enforce_phone_ui(phone: dict) -> dict:
    e164 = phone.get("normalized")
    if e164:
        try:
            phone["number"] = format_ui_from_e164(e164)
        except Exception:
            phone["number"] = (phone.get("number") or phone.get("original") or "").strip()
    else:
        phone["number"] = (phone.get("number") or phone.get("original") or "").strip()
    return phone
```

Встраивание: после санитайза сущности и присвоения GID, до финальной нормализации и записи файла (этап `postprocessor`).

---

## 3) Санитайзер для `phones[]` (жёсткий whitelist)

- На уровнях `contacts[].phones[]` и `organizations[].phones[]` **оставь только**:
  - `type`, `number`, `normalized`, `original`, `extension`.
- Все прочее (например, `confidence` внутри телефона) — удалить.
- Если удалены лишние поля — логируй это в `postprocessing_metadata.sanitizer.removed_props` (не меняя итоговую схему).

Псевдокод:
```python
PHONE_KEYS = {"type","number","normalized","original","extension"}

def sanitize_phone_obj(p: dict) -> dict:
    return {k: v for k, v in p.items() if k in PHONE_KEYS}
```

---

## 4) UI‑рендеринг (фронтенд)

- Отображение формируй **из `normalized`** (или из уже пересчитанного `number`):
  - Основной номер: `number` (который бэкенд пересчитал из `normalized`).
  - Если `extension`: добавляй `" (доб. {extension})"` к отображению.
- Click‑to‑call: `tel:{normalized}` и, при поддержке, `;ext={extension}` или запятая `,` как фолбэк.
- Не доверяй `original` для отображения — использовать только для аудита/диагностики.

---

## DoD / Приёмка

- Во всех итоговых JSON **нет лишних ключей** в `phones[]` (например, `confidence`).
- `number` везде согласован с `normalized` (перегенерирован на бэке).
- UI показывает номера в едином формате; доб. отображается как `(доб. N)` при наличии.
- Регресса по валидации нет.
