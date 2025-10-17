# Анализ письма email_001 с промптом unified_contact_extraction_structured.txt

**Дата анализа:** 2025-09-08 22:30 (UTC+07)  
**Email файл:** email_001_20250729_20250729_centerld_ru_d03bd60b.json  
**Промпт:** unified_contact_extraction_structured.txt  

## Исходные данные письма

**От:** sklad@centerld.ru  
**Кому:** fetisova@dna-technology.ru, torgi@dna-technology.ru, s.voronova@dna-technology.ru  
**Тема:** Заказ.  
**Дата:** Tue, 29 Jul 2025 10:10:51 +0700  
**Вложения:** 0  

**Текст письма:**
```
Просим уточнить, когда планируется отгрузка товара по Счету на оплату № 8164 от 16 июля 2025 г.. нам важно понимать сроки поставки.
Будем благодарны за оперативный ответ.
График работы:
Пн-Пт: с 9:00 до 16:00
Обед: с 12:00 до 13:00
Контакты:
📍 Адрес: 630075, г. Новосибирск, ул. Народная, 3
📞 Руководитель ОМТС: Бабиченко Иван Сергеевич
☎ Телефон: +7-913-399-32-72
"Центр Лабораторной Диагностики"
```

## Результат анализа с промптом structured

```json
{
  "contacts": [
    {
      "name": "Бабиченко Иван Сергеевич",
      "phone": "+7-913-399-32-72",
      "email": "sklad@centerld.ru",
      "organization": "Центр Лабораторной Диагностики",
      "position": "Руководитель ОМТС",
      "inn": null,
      "website": null,
      "city": "Новосибирск",
      "confidence": 0.95
    },
    {
      "name": null,
      "phone": null,
      "email": "fetisova@dna-technology.ru",
      "organization": "ДНК-Технология",
      "position": null,
      "inn": null,
      "website": "dna-technology.ru",
      "city": null,
      "confidence": 0.8
    },
    {
      "name": null,
      "phone": null,
      "email": "torgi@dna-technology.ru",
      "organization": "ДНК-Технология",
      "position": null,
      "inn": null,
      "website": "dna-technology.ru",
      "city": null,
      "confidence": 0.8
    },
    {
      "name": null,
      "phone": null,
      "email": "s.voronova@dna-technology.ru",
      "organization": "ДНК-Технология",
      "position": null,
      "inn": null,
      "website": "dna-technology.ru",
      "city": null,
      "confidence": 0.8
    }
  ],
  "business_context": "Запрос о сроках отгрузки товара по счету № 8164 от 16 июля 2025 г. от Центра Лабораторной Диагностики в Новосибирске к компании ДНК-Технология. Клиент уточняет сроки поставки уже оплаченного заказа.",
  "summary": {
    "topic": "Доставка и логистика",
    "product_interest": "Лабораторное оборудование (по счету № 8164)",
    "communication_stage": "Исполнение",
    "request_type": "Условия поставки"
  },
  "key_points": [
    "Запрос сроков отгрузки по счету № 8164 от 16 июля 2025 г.",
    "Важность понимания сроков поставки для клиента",
    "Контактное лицо: Бабиченко Иван Сергеевич, Руководитель ОМТС",
    "График работы: Пн-Пт с 9:00 до 16:00, обед 12:00-13:00"
  ],
  "commercial_offers": []
}
```

## Таблица извлеченных контактов

| № | Имя | Должность | Организация | Телефон | Email | ИНН | Сайт | Город |
|---|-----|-----------|-------------|---------|-------|-----|------|-------|
| 1 | Бабиченко Иван Сергеевич | Руководитель ОМТС | Центр Лабораторной Диагностики | +7-913-399-32-72 | sklad@centerld.ru | - | - | Новосибирск |
| 2 | - | - | ДНК-Технология | - | fetisova@dna-technology.ru | - | dna-technology.ru | - |
| 3 | - | - | ДНК-Технология | - | torgi@dna-technology.ru | - | dna-technology.ru | - |
| 4 | - | - | ДНК-Технология | - | s.voronova@dna-technology.ru | - | dna-technology.ru | - |
