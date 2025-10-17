-- =====================================================
-- Миграция 014: Добавление таблицы contact_mentions
-- =====================================================
-- Дата: 2025-10-17
-- Автор: Cascade AI
-- Цель: Хранение упоминаний контактов без способов связи
--       (отфильтрованных из contacts[])
--
-- Контекст: GID v2, Этап 1 - Фильтрация контактов
-- =====================================================

-- Создание таблицы contact_mentions
CREATE TABLE IF NOT EXISTS contact_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Основная информация
    name TEXT NOT NULL,                    -- ФИО контакта
    position TEXT,                         -- Должность
    
    -- Связи
    organization_id INTEGER,               -- ID организации (если известна)
    interaction_id INTEGER,                -- ID взаимодействия
    
    -- Контекст упоминания
    mention_type TEXT,                     -- Тип упоминания: "cc", "lpr", "mentioned", "signatory", "other"
    role_in_message TEXT,                  -- Роль в письме: "sender", "recipient", "cc", "mentioned"
    confidence REAL,                       -- Уверенность (0.0-1.0)
    
    -- Источник
    source_file TEXT,                      -- Имя файла-источника
    source_context TEXT,                   -- Контекст упоминания (фрагмент текста)
    
    -- Метаданные
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Внешние ключи
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
    FOREIGN KEY (interaction_id) REFERENCES interactions(id) ON DELETE CASCADE
);

-- Индекс для быстрого поиска по имени
CREATE INDEX IF NOT EXISTS idx_contact_mentions_name 
ON contact_mentions(name);

-- Индекс для поиска по организации
CREATE INDEX IF NOT EXISTS idx_contact_mentions_org 
ON contact_mentions(organization_id);

-- Индекс для поиска по взаимодействию
CREATE INDEX IF NOT EXISTS idx_contact_mentions_interaction 
ON contact_mentions(interaction_id);

-- Индекс для поиска по типу упоминания
CREATE INDEX IF NOT EXISTS idx_contact_mentions_type 
ON contact_mentions(mention_type);

-- Индекс для поиска по дате создания
CREATE INDEX IF NOT EXISTS idx_contact_mentions_created 
ON contact_mentions(created_at);

-- Комбинированный индекс для поиска дублей
CREATE INDEX IF NOT EXISTS idx_contact_mentions_dedup 
ON contact_mentions(name, organization_id, interaction_id);

-- =====================================================
-- Комментарии к полям
-- =====================================================
-- 
-- name: ФИО контакта (обязательное поле)
--       Примеры: "Иванов Иван Иванович", "Петрова А.С."
--
-- position: Должность контакта (опциональное)
--           Примеры: "Директор", "Менеджер по закупкам"
--
-- organization_id: Ссылка на организацию, если контакт связан с ней
--                  NULL если организация неизвестна
--
-- interaction_id: Ссылка на взаимодействие (письмо), где упомянут контакт
--                 Используется для связи с конкретным письмом
--
-- mention_type: Тип упоминания контакта:
--               - "cc" - в поле CC/BCC без email
--               - "lpr" - упоминание ЛПР (лицо, принимающее решение)
--               - "mentioned" - упоминание в тексте письма
--               - "signatory" - подписант документа (КП, договор, акт)
--               - "other" - другой тип упоминания
--
-- role_in_message: Роль контакта в письме:
--                  - "sender" - отправитель
--                  - "recipient" - получатель
--                  - "cc" - копия
--                  - "mentioned" - упомянут в тексте
--
-- confidence: Уверенность в корректности извлечения (0.0-1.0)
--             Заполняется LLM при извлечении
--
-- source_file: Имя файла, из которого извлечён контакт
--              Примеры: "email_001.json", "Договор_123.pdf"
--
-- source_context: Фрагмент текста, где упомянут контакт
--                 Используется для верификации и дообогащения
--
-- created_at: Дата и время создания записи
--             Автоматически заполняется при INSERT
--
-- =====================================================
-- Примеры использования
-- =====================================================
--
-- 1. Вставка упоминания контакта:
--
-- INSERT INTO contact_mentions (
--     name, position, organization_id, interaction_id,
--     mention_type, role_in_message, confidence,
--     source_file, source_context
-- ) VALUES (
--     'Иванов Иван Иванович',
--     'Директор',
--     1,
--     42,
--     'signatory',
--     'mentioned',
--     0.85,
--     'КП_2025_001.pdf',
--     'Подпись: Директор Иванов И.И.'
-- );
--
-- 2. Поиск всех упоминаний контакта:
--
-- SELECT * FROM contact_mentions
-- WHERE name LIKE '%Иванов%'
-- ORDER BY created_at DESC;
--
-- 3. Поиск упоминаний по организации:
--
-- SELECT cm.*, o.name as org_name
-- FROM contact_mentions cm
-- LEFT JOIN organizations o ON cm.organization_id = o.id
-- WHERE cm.organization_id = 1;
--
-- 4. Статистика по типам упоминаний:
--
-- SELECT mention_type, COUNT(*) as count
-- FROM contact_mentions
-- GROUP BY mention_type
-- ORDER BY count DESC;
--
-- =====================================================
-- Откат миграции (если нужно)
-- =====================================================
--
-- DROP INDEX IF EXISTS idx_contact_mentions_dedup;
-- DROP INDEX IF EXISTS idx_contact_mentions_created;
-- DROP INDEX IF EXISTS idx_contact_mentions_type;
-- DROP INDEX IF EXISTS idx_contact_mentions_interaction;
-- DROP INDEX IF EXISTS idx_contact_mentions_org;
-- DROP INDEX IF EXISTS idx_contact_mentions_name;
-- DROP TABLE IF EXISTS contact_mentions;
--
-- =====================================================
