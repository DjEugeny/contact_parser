-- Mini-CRM Seed Data Import Script
-- Дата: 04.10.2025
-- Описание: Импорт тестовых данных из обработанных email

-- =====================================================
-- 1. ORGANIZATIONS (3 основные организации)
-- =====================================================

INSERT INTO organizations (gid, name, inn, website, city, address, created_at, updated_at)
VALUES 
  ('58a49494-b44e-5b2f-9263-0ce9005f10e3', 'ДНК-Технология', '7723537840', 'dna-technology.ru', 'Москва', 'Варшавское шоссе, дом 125Ж, корпус 6, этаж 5', NOW(), NOW()),
  ('79ef90eb-b1bc-547f-9121-003d2b620b71', 'Компания Хеликон', NULL, 'helicon.ru', 'Москва', 'ул. Вавилова, 88', NOW(), NOW()),
  ('d5fe73ec-73c1-5eb7-8af0-0278a764a70e', 'ФГБОУ ВО Красгму', '1901066506', NULL, 'Красноярск', NULL, NOW(), NOW())
ON CONFLICT (gid) DO NOTHING;

-- =====================================================
-- 2. CONTACTS (5 основных контактов)
-- =====================================================

-- Сначала получаем id организаций для foreign keys
WITH org_ids AS (
  SELECT id, gid FROM organizations WHERE gid IN (
    '58a49494-b44e-5b2f-9263-0ce9005f10e3',
    '79ef90eb-b1bc-547f-9121-003d2b620b71'
  )
)
INSERT INTO contacts (gid, name, position, organization_id, city, address, confidence, role_in_message, website, created_at, updated_at)
SELECT 
  '0c3a3bae-6975-5223-a507-65aaaf84c57d',
  'Козлова Ольга',
  'Ведущий сервис-менеджер',
  (SELECT id FROM org_ids WHERE gid = '58a49494-b44e-5b2f-9263-0ce9005f10e3'),
  'Москва',
  'Варшавское шоссе, дом 125Ж, корпус 6, этаж 5',
  1.0,
  'sender',
  'https://www.dna-technology.ru',
  NOW(),
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM contacts WHERE gid = '0c3a3bae-6975-5223-a507-65aaaf84c57d');

INSERT INTO contacts (gid, name, position, organization_id, city, address, confidence, role_in_message, created_at, updated_at)
SELECT 
  '2e8f3c1a-9876-5432-b123-456789abcdef',
  'Тарасова Ирина Александровна',
  'Ведущий специалист по проектам Группы КДЛ',
  (SELECT id FROM organizations WHERE gid = '58a49494-b44e-5b2f-9263-0ce9005f10e3'),
  'Москва',
  NULL,
  1.0,
  'sender',
  NOW(),
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM contacts WHERE gid = '2e8f3c1a-9876-5432-b123-456789abcdef');

INSERT INTO contacts (gid, name, position, organization_id, city, confidence, role_in_message, created_at, updated_at)
SELECT 
  '1a2b3c4d-5e6f-7890-abcd-ef1234567890',
  'Гоголева Мария',
  NULL,
  (SELECT id FROM organizations WHERE gid = '58a49494-b44e-5b2f-9263-0ce9005f10e3'),
  'Москва',
  0.9,
  'recipient',
  NOW(),
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM contacts WHERE gid = '1a2b3c4d-5e6f-7890-abcd-ef1234567890');

-- =====================================================
-- 3. CONTACT EMAILS
-- =====================================================

INSERT INTO contact_emails (contact_id, email, is_primary)
SELECT 
  c.id,
  'kozlova@dna-technology.ru',
  TRUE
FROM contacts c
WHERE c.gid = '0c3a3bae-6975-5223-a507-65aaaf84c57d'
ON CONFLICT (email) DO NOTHING;

INSERT INTO contact_emails (contact_id, email, is_primary)
SELECT 
  c.id,
  'tarasova@dna-technology.ru',
  TRUE
FROM contacts c
WHERE c.gid = '2e8f3c1a-9876-5432-b123-456789abcdef'
ON CONFLICT (email) DO NOTHING;

INSERT INTO contact_emails (contact_id, email, is_primary)
SELECT 
  c.id,
  'm.gogoleva@dna-technology.ru',
  TRUE
FROM contacts c
WHERE c.gid = '1a2b3c4d-5e6f-7890-abcd-ef1234567890'
ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- 4. CONTACT PHONES
-- =====================================================

INSERT INTO contact_phones (contact_id, type, number, normalized, extension)
SELECT 
  c.id,
  'mobile',
  '+7 (915) 252-22-43',
  '79152522243',
  NULL
FROM contacts c
WHERE c.gid = '0c3a3bae-6975-5223-a507-65aaaf84c57d'
ON CONFLICT (normalized) DO NOTHING;

INSERT INTO contact_phones (contact_id, type, number, normalized, extension)
SELECT 
  c.id,
  'office',
  '+7 (495) 640-17-71',
  '74956401771',
  '2026'
FROM contacts c
WHERE c.gid = '0c3a3bae-6975-5223-a507-65aaaf84c57d'
ON CONFLICT (normalized) DO NOTHING;

INSERT INTO contact_phones (contact_id, type, number, normalized, extension)
SELECT 
  c.id,
  'mobile',
  '+7 (953) 794-60-38',
  '79537946038',
  NULL
FROM contacts c
WHERE c.gid = '2e8f3c1a-9876-5432-b123-456789abcdef'
ON CONFLICT (normalized) DO NOTHING;

-- =====================================================
-- 5. COMMERCIAL OFFERS (2 КП)
-- =====================================================

INSERT INTO commercial_offers (offer_number, offer_date, valid_until, total_cost, status, end_user, end_user_inn, intermediary, intermediary_inn, created_at, updated_at)
VALUES 
  ('б/н', '2025-03-21', '2025-06-25', 3152100.00, 'sent', 'ФГБОУ ВО Красгму им. Проф. В.Ф. Войно-Ясенецкого Минздрава России', '1901066506', NULL, NULL, NOW(), NOW()),
  ('б/н', '2025-03-14', '2025-06-15', 2612400.00, 'sent', 'ФБУЗ Центр Гигиены и Эпидемиологии в Республике Хакасия', NULL, NULL, NULL, NOW(), NOW());

-- =====================================================
-- 6. COMMERCIAL OFFER ITEMS (4 позиции)
-- =====================================================

INSERT INTO commercial_offer_items (offer_id, name, model, article, quantity, unit_price, total_price, vat)
SELECT 
  co.id,
  'Амплификатор ДТ-322',
  'ДТ-322',
  'F-322',
  5,
  450000.00,
  2250000.00,
  '20%'
FROM commercial_offers co
WHERE co.offer_number = 'б/н' AND co.offer_date = '2025-03-21';

INSERT INTO commercial_offer_items (offer_id, name, model, article, quantity, unit_price, total_price, vat)
SELECT 
  co.id,
  'Центрифуга МиниСпин',
  'МС-6000',
  'C-600',
  2,
  175000.00,
  350000.00,
  '20%'
FROM commercial_offers co
WHERE co.offer_number = 'б/н' AND co.offer_date = '2025-03-21';

-- =====================================================
-- 7. INTERACTIONS (3 примера взаимодействий)
-- =====================================================

INSERT INTO interactions (contact_id, organization_id, message_subject, message_date, role_in_message, interaction_type, summary, human_note, created_at)
SELECT 
  c.id,
  o.id,
  'Коммерческое предложение на поставку реагентов',
  '2025-07-29 14:30:00'::timestamptz,
  'sender',
  'email',
  'Козлова Ольга отправила коммерческое предложение',
  'Ольга Козлова (ДНК-Технология) отправила КП на поставку реагентов для ПЦР-диагностики',
  NOW()
FROM contacts c, organizations o
WHERE c.gid = '0c3a3bae-6975-5223-a507-65aaaf84c57d'
  AND o.gid = '58a49494-b44e-5b2f-9263-0ce9005f10e3';

INSERT INTO interactions (contact_id, organization_id, message_subject, message_date, role_in_message, interaction_type, summary, human_note, created_at)
SELECT 
  c.id,
  o.id,
  'Запрос информации о наборах реагентов',
  '2025-07-15 10:20:00'::timestamptz,
  'recipient',
  'email',
  'Получен запрос на информацию о реагентах',
  'Клиент запросил информацию о наличии и ценах на наборы для ПЦР',
  NOW()
FROM contacts c, organizations o
WHERE c.gid = '2e8f3c1a-9876-5432-b123-456789abcdef'
  AND o.gid = '58a49494-b44e-5b2f-9263-0ce9005f10e3';

-- =====================================================
-- ПРОВЕРКА ИМПОРТА
-- =====================================================

-- Подсчёт записей
SELECT 'organizations' as table_name, COUNT(*) as count FROM organizations
UNION ALL
SELECT 'contacts', COUNT(*) FROM contacts
UNION ALL
SELECT 'contact_emails', COUNT(*) FROM contact_emails
UNION ALL
SELECT 'contact_phones', COUNT(*) FROM contact_phones
UNION ALL
SELECT 'commercial_offers', COUNT(*) FROM commercial_offers
UNION ALL
SELECT 'commercial_offer_items', COUNT(*) FROM commercial_offer_items
UNION ALL
SELECT 'interactions', COUNT(*) FROM interactions;

-- Проверка связей
SELECT 
  c.name as contact_name,
  o.name as organization_name,
  ce.email,
  cp.number as phone
FROM contacts c
LEFT JOIN organizations o ON c.organization_id = o.id
LEFT JOIN contact_emails ce ON ce.contact_id = c.id
LEFT JOIN contact_phones cp ON cp.contact_id = c.id
LIMIT 10;
