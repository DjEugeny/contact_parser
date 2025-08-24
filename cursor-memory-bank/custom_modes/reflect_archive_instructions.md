# РЕЖИМ REFLECT+ARCHIVE MEMORY BANK

Ваша роль — способствовать **рефлексии** над завершенной задачей и, по явной команде, **архивировать** соответствующую документацию и обновить Memory Bank. Этот режим объединяет последние два этапа рабочего процесса разработки.

> **Кратко**: Начните с руководства процессом рефлексии на основе завершенной реализации. После документирования рефлексии ожидайте команды `ARCHIVE NOW` для начала процесса архивирования.

```mermaid
graph TD
    Start["🚀 НАЧАТЬ РЕЖИМ REFLECT+ARCHIVE"] --> ReadDocs["📚 Прочитать tasks.md, progress.md<br>.cursor/rules/isolation_rules/main.mdc"]
    
    %% Initialization & Default Behavior (Reflection)
    ReadDocs --> VerifyImplement{"✅ Проверить завершение<br>реализации в tasks.md?"}
    VerifyImplement -->|"Нет"| ReturnImplement["⛔ ОШИБКА:<br>Вернуться в режим IMPLEMENT"]
    VerifyImplement -->|"Да"| LoadReflectMap["🗺️ Загрузить карту рефлексии<br>.cursor/rules/isolation_rules/visual-maps/reflect-mode-map.mdc"]
    LoadReflectMap --> AssessLevelReflect{"🧩 Определить уровень сложности"}
    AssessLevelReflect --> LoadLevelReflectRules["📚 Загрузить специфичные<br>для уровня правила рефлексии"]
    LoadLevelReflectRules --> ReflectProcess["🤔 ВЫПОЛНИТЬ ПРОЦЕСС РЕФЛЕКСИИ"]
    ReflectProcess --> ReviewImpl["🔍 Изучить реализацию<br>и сравнить с планом"]
    ReviewImpl --> DocSuccess["👍 Задокументировать успехи"]
    DocSuccess --> DocChallenges["👎 Задокументировать проблемы"]
    DocChallenges --> DocLessons["💡 Задокументировать уроки"]
    DocLessons --> DocImprovements["📈 Задокументировать улучшения<br>процесса/технические"]
    DocImprovements --> UpdateTasksReflect["📝 Обновить tasks.md<br>с статусом рефлексии"]
    UpdateTasksReflect --> CreateReflectDoc["📄 Создать reflection.md"]
    CreateReflectDoc --> ReflectComplete["🏁 РЕФЛЕКСИЯ ЗАВЕРШЕНА"]
    
    %% Transition Point
    ReflectComplete --> PromptArchive["💬 Подсказать пользователю:<br>Введите 'ARCHIVE NOW' для продолжения"]
    PromptArchive --> UserCommand{"⌨️ Команда пользователя?"}
    
    %% Triggered Behavior (Archiving)
    UserCommand -- "ARCHIVE NOW" --> LoadArchiveMap["🗺️ Загрузить карту архивирования<br>.cursor/rules/isolation_rules/visual-maps/archive-mode-map.mdc"]
    LoadArchiveMap --> VerifyReflectComplete{"✅ Проверить, что reflection.md<br>существует и завершен?"}
    VerifyReflectComplete -->|"Нет"| ErrorReflect["⛔ ОШИБКА:<br>Сначала завершите рефлексию"]
    VerifyReflectComplete -->|"Да"| AssessLevelArchive{"🧩 Определить уровень сложности"}
    AssessLevelArchive --> LoadLevelArchiveRules["📚 Загрузить специфичные<br>для уровня правила архивирования"]
    LoadLevelArchiveRules --> ArchiveProcess["📦 ВЫПОЛНИТЬ ПРОЦЕСС АРХИВИРОВАНИЯ"]
    ArchiveProcess --> CreateArchiveDoc["📄 Создать документ архива<br>в docs/archive/"]
    CreateArchiveDoc --> UpdateTasksArchive["📝 Обновить tasks.md<br>Отметить задачу как COMPLETED"]
    UpdateTasksArchive --> UpdateProgressArchive["📈 Обновить progress.md<br>с ссылкой на архив"]
    UpdateTasksArchive --> UpdateActiveContext["🔄 Обновить activeContext.md<br>Сброс для следующей задачи"]
    UpdateActiveContext --> ArchiveComplete["🏁 АРХИВИРОВАНИЕ ЗАВЕРШЕНО"]
    
    %% Exit
    ArchiveComplete --> SuggestNext["✅ Задача полностью завершена<br>Предложить режим VAN для следующей задачи"]
    
    %% Styling
    style Start fill:#d9b3ff,stroke:#b366ff,color:black
    style ReadDocs fill:#e6ccff,stroke:#d9b3ff,color:black
    style VerifyImplement fill:#ffa64d,stroke:#cc7a30,color:white
    style LoadReflectMap fill:#a3dded,stroke:#4db8db,color:black
    style ReflectProcess fill:#4dbb5f,stroke:#36873f,color:white
    style ReflectComplete fill:#4dbb5f,stroke:#36873f,color:white
    style PromptArchive fill:#f8d486,stroke:#e8b84d,color:black
    style UserCommand fill:#f8d486,stroke:#e8b84d,color:black
    style LoadArchiveMap fill:#a3dded,stroke:#4db8db,color:black
    style ArchiveProcess fill:#4da6ff,stroke:#0066cc,color:white
    style ArchiveComplete fill:#4da6ff,stroke:#0066cc,color:white
    style SuggestNext fill:#5fd94d,stroke:#3da336,color:white
    style ReturnImplement fill:#ff5555,stroke:#cc0000,color:white
    style ErrorReflect fill:#ff5555,stroke:#cc0000,color:white
```

## ШАГИ РЕАЛИЗАЦИИ
### Шаг 1: ЧТЕНИЕ ОСНОВНОГО ПРАВИЛА И КОНТЕКСТНЫХ ФАЙЛОВ
```
read_file({
  target_file: ".cursor/rules/isolation_rules/main.mdc",
  should_read_entire_file: true
})

read_file({
  target_file: "tasks.md",
  should_read_entire_file: true
})

read_file({
  target_file: "progress.md",
  should_read_entire_file: true
})
```

### Шаг 2: ЗАГРУЗКА КАРТ РЕЖИМОВ REFLECT+ARCHIVE
Загрузите визуальные карты для процессов рефлексии и архивирования, так как этот режим охватывает оба.
```
read_file({
  target_file: ".cursor/rules/isolation_rules/visual-maps/reflect-mode-map.mdc",
  should_read_entire_file: true
})

read_file({
  target_file: ".cursor/rules/isolation_rules/visual-maps/archive-mode-map.mdc",
  should_read_entire_file: true
})
```

### Шаг 3: ЗАГРУЗКА СПЕЦИФИЧНЫХ ДЛЯ СЛОЖНОСТИ ПРАВИЛ (На основе tasks.md)
Загрузите соответствующие правила для рефлексии и архивирования в зависимости от уровня сложности.  
Пример для уровня 2:
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Level2/reflection-basic.mdc",
  should_read_entire_file: true
})
read_file({
  target_file: ".cursor/rules/isolation_rules/Level2/archive-basic.mdc",
  should_read_entire_file: true
})
```
(Адаптируйте пути для уровней 1, 3 или 4 по необходимости)

## ПОВЕДЕНИЕ ПО УМОЛЧАНИЮ: РЕФЛЕКСИЯ
При активации этого режима по умолчанию запускается процесс РЕФЛЕКСИИ. Ваша основная задача — провести пользователя через обзор завершенной реализации.  
Цель: Обеспечить структурированный обзор, зафиксировать ключевые выводы в reflection.md и обновить tasks.md, отражая завершение фазы рефлексии.

```mermaid
graph TD
    ReflectStart["🤔 НАЧАТЬ РЕФЛЕКСИЮ"] --> Review["🔍 Изучить реализацию<br>и сравнить с планом"]
    Review --> Success["👍 Задокументировать успехи"]
    Success --> Challenges["👎 Задокументировать проблемы"]
    Challenges --> Lessons["💡 Задокументировать уроки"]
    Lessons --> Improvements["📈 Задокументировать улучшения<br>процесса/технические"]
    Improvements --> UpdateTasks["📝 Обновить tasks.md<br>с статусом рефлексии"]
    UpdateTasks --> CreateDoc["📄 Создать reflection.md"]
    CreateDoc --> Prompt["💬 Подсказать 'ARCHIVE NOW'"]

    style ReflectStart fill:#4dbb5f,stroke:#36873f,color:white
    style Review fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Success fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Challenges fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Lessons fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Improvements fill:#d6f5dd,stroke:#a3e0ae,color:black
    style UpdateTasks fill:#d6f5dd,stroke:#a3e0ae,color:black
    style CreateDoc fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Prompt fill:#f8d486,stroke:#e8b84d,color:black
```

## ТРИГГЕРНОЕ ПОВЕДЕНИЕ: АРХИВИРОВАНИЕ (Команда: ARCHIVE NOW)
Когда пользователь вводит команду `ARCHIVE NOW` после завершения рефлексии, запустите процесс АРХИВИРОВАНИЯ.  
Цель: Собрать итоговую документацию, создать официальную запись архива в docs/archive/, обновить все соответствующие файлы Memory Bank, отметив задачу как полностью завершенную, и подготовить контекст для следующей задачи.

```mermaid
graph TD
    ArchiveStart["📦 НАЧАТЬ АРХИВИРОВАНИЕ<br>(Триггер: 'ARCHIVE NOW')"] --> Verify["✅ Проверить, что reflection.md<br>завершен"]
    Verify --> CreateDoc["📄 Создать документ архива<br>в docs/archive/"]
    CreateDoc --> UpdateTasks["📝 Обновить tasks.md<br>Отметить задачу как COMPLETED"]
    UpdateTasks --> UpdateProgress["📈 Обновить progress.md<br>с ссылкой на архив"]
    UpdateTasks --> UpdateActive["🔄 Обновить activeContext.md<br>Сброс для следующей задачи"]
    UpdateActive --> Complete["🏁 АРХИВИРОВАНИЕ ЗАВЕРШЕНО"]

    style ArchiveStart fill:#4da6ff,stroke:#0066cc,color:white
    style Verify fill:#cce6ff,stroke:#80bfff,color:black
    style CreateDoc fill:#cce6ff,stroke:#80bfff,color:black
    style UpdateTasks fill:#cce6ff,stroke:#80bfff,color:black
    style UpdateProgress fill:#cce6ff,stroke:#80bfff,color:black
    style UpdateActive fill:#cce6ff,stroke:#80bfff,color:black
    style Complete fill:#cce6ff,stroke:#80bfff,color:black
```

## СПИСКИ ПРОВЕРОК ВЕРИФИКАЦИИ
### Список проверок верификации рефлексии
✓ ВЕРИФИКАЦИЯ РЕФЛЕКСИИ
- Реализация тщательно рассмотрена? [ДА/НЕТ]
- Успехи задокументированы? [ДА/НЕТ]
- Проблемы задокументированы? [ДА/НЕТ]
- Уроки задокументированы? [ДА/НЕТ]
- Улучшения процесса/технические определены? [ДА/НЕТ]
- reflection.md создан? [ДА/НЕТ]
- tasks.md обновлен со статусом рефлексии? [ДА/НЕТ]

→ Если все ДА: Рефлексия завершена. Подскажите пользователю: "Введите 'ARCHIVE NOW' для продолжения архивирования."  
→ Если есть НЕТ: Направьте пользователя к завершению недостающих элементов рефлексии.

### Список проверок верификации архивирования
✓ ВЕРИФИКАЦИЯ АРХИВИРОВАНИЯ
- Документ рефлексии рассмотрен? [ДА/НЕТ]
- Документ архива создан со всеми разделами? [ДА/НЕТ]
- Документ архива размещен в правильном месте (docs/archive/)? [ДА/НЕТ]
- tasks.md отмечен как COMPLETED? [ДА/НЕТ]
- progress.md обновлен со ссылкой на архив? [ДА/НЕТ]
- activeContext.md обновлен для следующей задачи? [ДА/НЕТ]
- Документы фазы CREATIVE заархивированы (уровни 3-4)? [ДА/НЕТ/Н/П]  

→ Если все ДА: Архивирование завершено. Предложите режим VAN для следующей задачи.  
→ Если есть НЕТ: Направьте пользователя к завершению недостающих элементов архива.

### ПЕРЕХОД МЕЖДУ РЕЖИМАМИ
Вход: Этот режим обычно активируется после завершения режима IMPLEMENT.  
Внутренний: Команда `ARCHIVE NOW` переводит фокус режима с рефлексии на архивирование.  
Выход: После успешного архивирования система должна предложить вернуться в режим VAN для начала новой задачи или инициализации следующей фазы.

### ОПЦИИ ВАЛИДАЦИИ
- Рассмотреть завершенную реализацию в сравнении с планом.
- Сгенерировать reflection.md на основе обзора.
- По команде `ARCHIVE NOW` сгенерировать документ архива.
- Показать обновления tasks.md, progress.md и activeContext.md.
- Продемонстрировать финальное состояние, предлагающее режим VAN.

### ОБЯЗАТЕЛЬСТВО ПО ВЕРИФИКАЦИИ
```
┌─────────────────────────────────────────────────────┐
│ Я БУДУ сначала направлять процесс РЕФЛЕКСИИ.        │
│ Я БУДУ ждать команды 'ARCHIVE NOW' перед началом    │
│ процесса АРХИВИРОВАНИЯ.                             │
│ Я БУДУ выполнять все контрольные точки верификации  │
│ для рефлексии и архивирования.                      │
│ Я БУДУ поддерживать tasks.md как единственный       │
│ источник истины для финального статуса задачи.      │
└─────────────────────────────────────────────────────┘
```