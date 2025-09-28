# Поиск и индексация

## Поисковые сценарии (день 1)
- Контакты: ФИО, телефон, email, город, организация.
- Организации: название, ИНН, город, домен, наличие активных КП.
- КП: по конечному пользователю, посреднику, номеру/дате, статусу, сроку действия (valid_until), диапазону дат.

## Индексация (MySQL)
- `contacts`: INDEX(city), INDEX(organization_id), UNIQUE по email/телефону (через подсущности).
- `organizations`: INDEX(city), INDEX(inn), INDEX(name).
- `commercial_offers`: INDEX(status), INDEX(valid_until), INDEX(offer_date), INDEX(organization_id).

## Сохранённые фильтры
- Таблица `saved_views` (user_id, entity, query_json, title).

## Примеры запросов
```sql
-- Контакты в Новосибирске с телефоном:
SELECT c.* FROM contacts c
JOIN contact_phones p ON p.contact_id=c.id
WHERE c.city='Новосибирск' AND p.e164 LIKE '+7%'
ORDER BY c.full_name;

-- КП, срок которых истекает в ближайшие 14 дней:
SELECT * FROM commercial_offers
WHERE valid_until BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 14 DAY)
ORDER BY valid_until;
```
