# РЕЖИМ ПЛАНИРОВАНИЯ MEMORY BANK

Ваша роль — создать детальный план выполнения задач на основе уровня сложности, определенного в режиме ИНИЦИАЛИЗАЦИИ.

```mermaid
graph TD
    Start["🚀 НАЧАТЬ ПЛАНИРОВАНИЕ"] --> ReadTasks["📚 Прочитать tasks.md<br>.cursor/rules/isolation_rules/main.mdc"]
    
    %% Complexity Level Determination
    ReadTasks --> CheckLevel{"🧩 Определить<br>уровень сложности"}
    CheckLevel -->|"Уровень 2"| Level2["📝 ПЛАНИРОВАНИЕ УРОВНЯ 2<br>.cursor/rules/isolation_rules/visual-maps/plan-mode-map.mdc"]
    CheckLevel -->|"Уровень 3"| Level3["📋 ПЛАНИРОВАНИЕ УРОВНЯ 3<br>.cursor/rules/isolation_rules/visual-maps/plan-mode-map.mdc"]
    CheckLevel -->|"Уровень 4"| Level4["📊 ПЛАНИРОВАНИЕ УРОВНЯ 4<br>.cursor/rules/isolation_rules/visual-maps/plan-mode-map.mdc"]
    
    %% Level 2 Planning
    Level2 --> L2Review["🔍 Проверить структуру<br>кода"]
    L2Review --> L2Document["📄 Документировать<br>запланированные изменения"]
    L2Document --> L2Challenges["⚠️ Определить<br>проблемы"]
    L2Challenges --> L2Checklist["✅ Создать список<br>задач"]
    L2Checklist --> L2Update["📝 Обновить tasks.md<br>с планом"]
    L2Update --> L2Verify["✓ Проверить<br>полноту плана"]
    
    %% Level 3 Planning
    Level3 --> L3Review["🔍 Проверить структуру<br>кодовой базы"]
    L3Review --> L3Requirements["📋 Документировать детальные<br>требования"]
    L3Requirements --> L3Components["🧩 Определить затронутые<br>компоненты"]
    L3Components --> L3Plan["📝 Создать полный<br>план реализации"]
    L3Plan --> L3Challenges["⚠️ Документировать проблемы<br>и решения"]
    L3Challenges --> L3Update["📝 Обновить tasks.md<br>с планом"]
    L3Update --> L3Flag["🎨 Пометить компоненты,<br>требующие CREATIVE"]
    L3Flag --> L3Verify["✓ Проверить<br>полноту плана"]
    
    %% Level 4 Planning
    Level4 --> L4Analysis["🔍 Анализ структуры<br>кодовой базы"]
    L4Analysis --> L4Requirements["📋 Документировать полные<br>требования"]
    L4Requirements --> L4Diagrams["📊 Создать архитектурные<br>диаграммы"]
    L4Diagrams --> L4Subsystems["🧩 Определить затронутые<br>подсистемы"]
    L4Subsystems --> L4Dependencies["🔄 Документировать зависимости<br>и точки интеграции"]
    L4Dependencies --> L4Plan["📝 Создать поэтапный<br>план реализации"]
    L4Plan --> L4Update["📝 Обновить tasks.md<br>с планом"]
    L4Update --> L4Flag["🎨 Пометить компоненты,<br>требующие CREATIVE"]
    L4Flag --> L4Verify["✓ Проверить<br>полноту плана"]
    
    %% Verification & Completion
    L2Verify & L3Verify & L4Verify --> CheckCreative{"🎨 Требуются<br>фазы CREATIVE?"}
    
    %% Mode Transition
    CheckCreative -->|"Да"| RecCreative["⏭️ СЛЕДУЮЩИЙ РЕЖИМ:<br>CREATIVE MODE"]
    CheckCreative -->|"Нет"| RecImplement["⏭️ СЛЕДУЮЩИЙ РЕЖИМ:<br>IMPLEMENT MODE"]
    
    %% Template Selection
    L2Update -.- Template2["ШАБЛОН УРОВНЯ 2:<br>- Обзор<br>- Файлы для изменения<br>- Шаги реализации<br>- Потенциальные проблемы"]
    L3Update & L4Update -.- TemplateAdv["ШАБЛОН УРОВНЕЙ 3-4:<br>- Анализ требований<br>- Затронутые компоненты<br>- Архитектурные соображения<br>- Стратегия реализации<br>- Детальные шаги<br>- Зависимости<br>- Проблемы и способы их устранения<br>- Компоненты фазы CREATIVE"]
    
    %% Validation Options
    Start -.-> Validation["🔍 ОПЦИИ ВАЛИДАЦИИ:<br>- Проверить уровень сложности<br>- Создать шаблоны планирования<br>- Определить потребности CREATIVE<br>- Сгенерировать документы плана<br>- Показать переход между режимами"]

    %% Styling
    style Start fill:#4da6ff,stroke:#0066cc,color:white
    style ReadTasks fill:#80bfff,stroke:#4da6ff,color:black
    style CheckLevel fill:#d94dbb,stroke:#a3378a,color:white
    style Level2 fill:#4dbb5f,stroke:#36873f,color:white
    style Level3 fill:#ffa64d,stroke:#cc7a30,color:white
    style Level4 fill:#ff5555,stroke:#cc0000,color:white
    style CheckCreative fill:#d971ff,stroke:#a33bc2,color:white
    style RecCreative fill:#ffa64d,stroke:#cc7a30,color:black
    style RecImplement fill:#4dbb5f,stroke:#36873f,color:black
```

## ШАГИ РЕАЛИЗАЦИИ

### Шаг 1: ЧТЕНИЕ ОСНОВНОГО ПРАВИЛА И ЗАДАЧ
```
read_file({
  target_file: ".cursor/rules/isolation_rules/main.mdc",
  should_read_entire_file: true
})

read_file({
  target_file: "tasks.md",
  should_read_entire_file: true
})
```

### Шаг 2: ЗАГРУЗКА КАРТЫ РЕЖИМА PLAN
```
read_file({
  target_file: ".cursor/rules/isolation_rules/visual-maps/plan-mode-map.mdc",
  should_read_entire_file: true
})
```

### Шаг 3: ЗАГРУЗКА СПЕЦИФИЧНЫХ ДЛЯ СЛОЖНОСТИ СПРАВОЧНЫХ МАТЕРИАЛОВ ПЛАНИРОВАНИЯ
В зависимости от уровня сложности, определенного в tasks.md, загрузите один из:

#### Для уровня 2:
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Level2/task-tracking-basic.mdc",
  should_read_entire_file: true
})
```

#### Для уровня 3:
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Level3/task-tracking-intermediate.mdc",
  should_read_entire_file: true
})

read_file({
  target_file: ".cursor/rules/isolation_rules/Level3/planning-comprehensive.mdc",
  should_read_entire_file: true
})
```

#### Для уровня 4:
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Level4/task-tracking-advanced.mdc",
  should_read_entire_file: true
})

read_file({
  target_file: ".cursor/rules/isolation_rules/Level4/architectural-planning.mdc",
  should_read_entire_file: true
})
```

## ПОДХОД К ПЛАНИРОВАНИЮ

Создайте детальный план реализации на основе уровня сложности, определенного во время инициализации. Ваш подход должен предоставлять четкое руководство, оставаясь при этом адаптируемым к требованиям проекта и техническим ограничениям.

### Уровень 2: Планирование простых улучшений

Для задач уровня 2 сосредоточьтесь на создании упрощенного плана, который определяет конкретные необходимые изменения и возможные проблемы. Изучите структуру кодовой базы, чтобы понять области, затронутые улучшением, и задокументируйте прямолинейный подход к реализации.

```mermaid
graph TD
    L2["📝 ПЛАНИРОВАНИЕ УРОВНЯ 2"] --> Doc["Документировать план со следующими компонентами:"]
    Doc --> OV["📋 Обзор изменений"]
    Doc --> FM["📁 Файлы для изменения"]
    Doc --> IS["🔄 Шаги реализации"]
    Doc --> PC["⚠️ Потенциальные проблемы"]
    Doc --> TS["✅ Стратегия тестирования"]
    
    style L2 fill:#4dbb5f,stroke:#36873f,color:white
    style Doc fill:#80bfff,stroke:#4da6ff,color:black
    style OV fill:#cce6ff,stroke:#80bfff,color:black
    style FM fill:#cce6ff,stroke:#80bfff,color:black
    style IS fill:#cce6ff,stroke:#80bfff,color:black
    style PC fill:#cce6ff,stroke:#80bfff,color:black
    style TS fill:#cce6ff,stroke:#80bfff,color:black
```

### Уровни 3-4: Полное планирование

Для задач уровней 3-4 разработайте полный план, который охватывает архитектуру, зависимости и точки интеграции. Определите компоненты, требующие фазы CREATIVE, и задокументируйте детальные требования. Для задач уровня 4 включите архитектурные диаграммы и предложите поэтапный подход к реализации.

```mermaid
graph TD
    L34["📊 ПЛАНИРОВАНИЕ УРОВНЕЙ 3-4"] --> Doc["Документировать план со следующими компонентами:"]
    Doc --> RA["📋 Анализ требований"]
    Doc --> CA["🧩 Затронутые компоненты"]
    Doc --> AC["🏗️ Архитектурные соображения"]
    Doc --> IS["📝 Стратегия реализации"]
    Doc --> DS["🔢 Детальные шаги"]
    Doc --> DP["🔄 Зависимости"]
    Doc --> CM["⚠️ Проблемы и способы их устранения"]
    Doc --> CP["🎨 Компоненты фазы CREATIVE"]
    
    style L34 fill:#ffa64d,stroke:#cc7a30,color:white
    style Doc fill:#80bfff,stroke:#4da6ff,color:black
    style RA fill:#ffe6cc,stroke:#ffa64d,color:black
    style CA fill:#ffe6cc,stroke:#ffa64d,color:black
    style AC fill:#ffe6cc,stroke:#ffa64d,color:black
    style IS fill:#ffe6cc,stroke:#ffa64d,color:black
    style DS fill:#ffe6cc,stroke:#ffa64d,color:black
    style DP fill:#ffe6cc,stroke:#ffa64d,color:black
    style CM fill:#ffe6cc,stroke:#ffa64d,color:black
    style CP fill:#ffe6cc,stroke:#ffa64d,color:black
```

## ИДЕНТИФИКАЦИЯ ФАЗЫ CREATIVE

```mermaid
graph TD
    CPI["🎨 ИДЕНТИФИКАЦИЯ ФАЗЫ CREATIVE"] --> Question{"Требует ли компонент<br>решений по дизайну?"}
    Question -->|"Да"| Identify["Пометить для фазы CREATIVE"]
    Question -->|"Нет"| Skip["Перейти к реализации"]
    
    Identify --> Types["Определить тип фазы CREATIVE:"]
    Types --> A["🏗️ Архитектурный дизайн"]
    Types --> B["⚙️ Дизайн алгоритмов"]
    Types --> C["🎨 Дизайн UI/UX"]
    
    style CPI fill:#d971ff,stroke:#a33bc2,color:white
    style Question fill:#80bfff,stroke:#4da6ff,color:black
    style Identify fill:#ffa64d,stroke:#cc7a30,color:black
    style Skip fill:#4dbb5f,stroke:#36873f,color:black
    style Types fill:#ffe6cc,stroke:#ffa64d,color:black
```

Определите компоненты, которые требуют творческого решения проблем или значительных проектных решений. Для этих компонентов пометьте их для режима CREATIVE. Сосредоточьтесь на архитектурных соображениях, потребностях в дизайне алгоритмов или требованиях к UI/UX, которые выиграют от структурированного исследования дизайна.

## ВЕРИФИКАЦИЯ

```mermaid
graph TD
    V["✅ СПИСОК ПРОВЕРОК ВЕРИФИКАЦИИ"] --> P["План охватывает все требования?"]
    V --> C["Определены ли компоненты, требующие фаз CREATIVE?"]
    V --> S["Четко ли определены шаги реализации?"]
    V --> D["Задокументированы ли зависимости и проблемы?"]
    
    P & C & S & D --> Decision{"Все проверено?"}
    Decision -->|"Да"| Complete["Готово к следующему режиму"]
    Decision -->|"Нет"| Fix["Дополнить недостающие элементы"]
    
    style V fill:#4dbbbb,stroke:#368787,color:white
    style Decision fill:#ffa64d,stroke:#cc7a30,color:white
    style Complete fill:#5fd94d,stroke:#3da336,color:white
    style Fix fill:#ff5555,stroke:#cc0000,color:white
```

Перед завершением фазы планирования убедитесь, что все требования учтены в плане, определены компоненты, требующие фазы CREATIVE, шаги реализации четко определены, а зависимости и проблемы задокументированы. Обновите tasks.md с полным планом и порекомендуйте подходящий следующий режим в зависимости от того, требуются ли фазы CREATIVE.