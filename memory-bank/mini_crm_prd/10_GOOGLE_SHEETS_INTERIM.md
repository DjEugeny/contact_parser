# 10_GOOGLE_SHEETS_INTERIM — Промежуточный репорт в таблицах

> **СТАТУС: ОТМЕНЕНО**  
> Данная стадия исключена из текущей реализации проекта.  
> Вместо экспорта в Google Sheets данные напрямую записываются в PostgreSQL (Supabase).  
> Документ сохранён для истории и возможного использования в будущем.

---

## ~~Листы и ключевые колонки~~ (АРХИВ)

## Листы и ключевые колонки
1. **Организации**: id, name, inn, website, city, address, emails[], phones[].  
2. **Контакты**: id, organization_id, name, position, emails, phones[], city, last_interaction_at.  
3. **История**: date, contact_id, organization_id, **role_in_message**, subject, **message_id**, links.  
4. **КП**: id/number/date/valid_until/total_cost/status, end_user_id, intermediary_id, **source_message_id**, links.  
5. **Inbox (модерация)**: тип, сырые данные, причина, дата.

## Поля ссылок (links)
- **`eml_link`** — путь/URL к `.eml` если сохранён;  
- **`json_link`** — путь/URL к JSON письма (всегда);  
- **`attachments[]`** — список путей к файлам вложений.  
> Если .eml пока не сохраняется, `eml_link` пустой. Для Google Sheets можно использовать ссылки на Google Drive/VPS; для Excel — локальные файловые пути.

