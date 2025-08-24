# ИНТЕГРАЦИИ И ЭКСПОРТ
google_sheets_export:
  tables: 
    - "Контакты: ФИО, телефон, email, компания, приоритет"
    - "Summary: дата, от кого, тема, содержание, важность" 
    - "КП: товар, цена, условия, поставщик"
  library: "gspread + service_account"

google_contacts_export:
  groups: ["Высокий приоритет", "Средний", "Региональные"]
  fields: "ФИО, телефон, email, компания, должность"
  library: "google-api-python-client"