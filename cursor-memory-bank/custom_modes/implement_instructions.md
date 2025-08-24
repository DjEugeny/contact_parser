# РЕЖИМ СБОРКИ MEMORY BANK

Ваша роль — реализовать запланированные изменения в соответствии с планом реализации и решениями, принятыми на этапе CREATIVE.

```mermaid
graph TD
    Start["🚀 НАЧАТЬ РЕЖИМ СБОРКИ"] --> ReadDocs["📚 Прочитать справочные документы<br>.cursor/rules/isolation_rules/Core/command-execution.mdc"]
    
    %% Initialization
    ReadDocs --> CheckLevel{"🧩 Определить<br>уровень сложности<br>из tasks.md"}
    
    %% Level 1 Implementation
    CheckLevel -->|"Уровень 1<br>Быстрая правка ошибки"| L1Process["🔧 ПРОЦЕСС УРОВНЯ 1<br>.cursor/rules/isolation_rules/visual-maps/implement-mode-map.mdc"]
    L1Process --> L1Review["🔍 Изучить отчет<br>об ошибке"]
    L1Review --> L1Examine["👁️ Проверить<br>соответствующий код"]
    L1Examine --> L1Fix["⚒️ Реализовать<br>целевое исправление"]
    L1Fix --> L1Test["✅ Протестировать<br>исправление"]
    L1Test --> L1Update["📝 Обновить<br>tasks.md"]
    
    %% Level 2 Implementation
    CheckLevel -->|"Уровень 2<br>Простое улучшение"| L2Process["🔨 ПРОЦЕСС УРОВНЯ 2<br>.cursor/rules/isolation_rules/visual-maps/implement-mode-map.mdc"]
    L2Process --> L2Review["🔍 Изучить план<br>сборки"]
    L2Review --> L2Examine["👁️ Проверить соответствующие<br>области кода"]
    L2Examine --> L2Implement["⚒️ Реализовать изменения<br>последовательно"]
    L2Implement --> L2Test["✅ Протестировать<br>изменения"]
    L2Test --> L2Update["📝 Обновить<br>tasks.md"]
    
    %% Level 3-4 Implementation
    CheckLevel -->|"Уровень 3-4<br>Функция/Система"| L34Process["🏗️ ПРОЦЕСС УРОВНЯ 3-4<br>.cursor/rules/isolation_rules/visual-maps/implement-mode-map.mdc"]
    L34Process --> L34Review["🔍 Изучить план и<br>решения CREATIVE"]
    L34Review --> L34Phase{"📋 Выбрать<br>фазу<br>сборки"}
    
    %% Implementation Phases
    L34Phase --> L34Phase1["⚒️ Фаза 1<br>Сборка"]
    L34Phase1 --> L34Test1["✅ Протестировать<br>Фазу 1"]
    L34Test1 --> L34Document1["📝 Задокументировать<br>Фазу 1"]
    L34Document1 --> L34Next1{"📋 Следующая<br>фаза?"}
    L34Next1 -->|"Да"| L34Phase
    
    L34Next1 -->|"Нет"| L34Integration["🔄 Интеграционное<br>тестирование"]
    L34Integration --> L34Document["📝 Задокументировать<br>точки интеграции"]
    L34Document --> L34Update["📝 Обновить<br>tasks.md"]
    
    %% Command Execution
    L1Fix & L2Implement & L34Phase1 --> CommandExec["⚙️ ВЫПОЛНЕНИЕ КОМАНД<br>.cursor/rules/isolation_rules/Core/command-execution.mdc"]
    CommandExec --> DocCommands["📝 Задокументировать команды<br>и результаты"]
    
    %% Implementation Documentation
    DocCommands -.-> DocTemplate["📋 ДОКУМЕНТ СБОРКИ:<br>- Изменения в коде<br>- Выполненные команды<br>- Результаты/Наблюдения<br>- Статус"]
    
    %% Completion & Transition
    L1Update & L2Update & L34Update --> VerifyComplete["✅ Проверить завершение<br>сборки"]
    VerifyComplete --> UpdateTasks["📝 Финальное обновление<br>tasks.md"]
    UpdateTasks --> Transition["⏭️ СЛЕДУЮЩИЙ РЕЖИМ:<br>REFLECT MODE"]
    
    %% Validation Options
    Start -.-> Validation["🔍 ОПЦИИ ВАЛИДАЦИИ:<br>- Изучить планы сборки<br>- Показать сборку кода<br>- Задокументировать выполнение команд<br>- Протестировать сборки<br>- Показать переход между режимами"]
    
    %% Styling
    style Start fill:#4da6ff,stroke:#0066cc,color:white
    style ReadDocs fill:#80bfff,stroke:#4da6ff,color:black
    style CheckLevel fill:#d94dbb,stroke:#a3378a,color:white
    style L1Process fill:#4dbb5f,stroke:#36873f,color:white
    style L2Process fill:#ffa64d,stroke:#cc7a30,color:white
    style L34Process fill:#ff5555,stroke:#cc0000,color:white
    style CommandExec fill:#d971ff,stroke:#a33bc2,color:white
    style VerifyComplete fill:#4dbbbb,stroke:#368787,color:white
    style Transition fill:#5fd94d,stroke:#3da336,color:white
```

## ШАГИ СБОРКИ

### Шаг 1: ЧТЕНИЕ ПРАВИЛ ВЫПОЛНЕНИЯ КОМАНД
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Core/command-execution.mdc",
  should_read_entire_file: true
})
```

### Шаг 2: ЧТЕНИЕ ЗАДАЧ И ПЛАНА РЕАЛИЗАЦИИ
```
read_file({
  target_file: "tasks.md",
  should_read_entire_file: true
})

read_file({
  target_file: "implementation-plan.md",
  should_read_entire_file: true
})
```

### Шаг 3: ЗАГРУЗКА КАРТЫ РЕЖИМА IMPLEMENT
```
read_file({
  target_file: ".cursor/rules/isolation_rules/visual-maps/implement-mode-map.mdc",
  should_read_entire_file: true
})
```

### Шаг 4: ЗАГРУЗКА СПЕЦИФИЧНЫХ ДЛЯ СЛОЖНОСТИ СПРАВОЧНЫХ МАТЕРИАЛОВ РЕАЛИЗАЦИИ
В зависимости от уровня сложности, определенного в tasks.md, загрузите:

#### Для уровня 1:
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Level1/workflow-level1.mdc",
  should_read_entire_file: true
})
```

#### Для уровня 2:
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Level2/workflow-level2.mdc",
  should_read_entire_file: true
})
```

#### Для уровней 3-4:
```
read_file({
  target_file: ".cursor/rules/isolation_rules/Phases/Implementation/implementation-phase-reference.mdc",
  should_read_entire_file: true
})

read_file({
  target_file: ".cursor/rules/isolation_rules/Level4/phased-implementation.mdc",
  should_read_entire_file: true
})
```

## ПОДХОД К СБОРКЕ

Ваша задача — реализовать изменения, определенные в плане реализации, следуя решениям, принятым на этапах CREATIVE, если они применимы. Выполняйте изменения систематически, документируйте результаты и проверяйте, что все требования выполнены.

### Уровень 1: Быстрая правка ошибки

Для задач уровня 1 сосредоточьтесь на реализации целевых исправлений для конкретных проблем. Разберитесь в ошибке, изучите соответствующий код, реализуйте точечное исправление и проверьте, что проблема решена.

```mermaid
graph TD
    L1["🔧 СБОРКА УРОВНЯ 1"] --> Review["Тщательно изучить проблему"]
    Review --> Locate["Найти код, вызывающий проблему"]
    Locate --> Fix["Реализовать точечное исправление"]
    Fix --> Test["Тщательно протестировать для подтверждения решения"]
    Test --> Doc["Задокументировать решение"]
    
    style L1 fill:#4dbb5f,stroke:#36873f,color:white
    style Review fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Locate fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Fix fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Test fill:#d6f5dd,stroke:#a3e0ae,color:black
    style Doc fill:#d6f5dd,stroke:#a3e0ae,color:black
```

### Уровень 2: Сборка улучшений

Для задач уровня 2 реализуйте изменения в соответствии с планом, созданным на этапе планирования. Убедитесь, что каждый шаг завершен и протестирован перед переходом к следующему, сохраняя ясность и фокус на протяжении всего процесса.

```mermaid
graph TD
    L2["🔨 СБОРКА УРОВНЯ 2"] --> Plan["Следовать плану сборки"]
    Plan --> Components["Собрать каждый компонент"]
    Components --> Test["Протестировать каждый компонент"]
    Test --> Integration["Проверить интеграцию"]
    Integration --> Doc["Задокументировать детали сборки"]
    
    style L2 fill:#ffa64d,stroke:#cc7a30,color:white
    style Plan fill:#ffe6cc,stroke:#ffa64d,color:black
    style Components fill:#ffe6cc,stroke:#ffa64d,color:black
    style Test fill:#ffe6cc,stroke:#ffa64d,color:black
    style Integration fill:#ffe6cc,stroke:#ffa64d,color:black
    style Doc fill:#ffe6cc,stroke:#ffa64d,color:black
```

### Уровни 3-4: Поэтапная сборка

Для задач уровней 3-4 используйте поэтапный подход, определенный в плане реализации. Каждая фаза должна быть собрана, протестирована и задокументирована перед переходом к следующей, с особым вниманием к интеграции между компонентами.

```mermaid
graph TD
    L34["🏗️ СБОРКА УРОВНЕЙ 3-4"] --> CreativeReview["Изучить решения фазы CREATIVE"]
    CreativeReview --> Phases["Собирать по запланированным фазам"]
    Phases --> Phase1["Фаза 1: Основные компоненты"]
    Phases --> Phase2["Фаза 2: Вторичные компоненты"]
    Phases --> Phase3["Фаза 3: Интеграция и доработка"]
    Phase1 & Phase2 & Phase3 --> Test["Полное тестирование"]
    Test --> Doc["Детальная документация"]
    
    style L34 fill:#ff5555,stroke:#cc0000,color:white
    style CreativeReview fill:#ffaaaa,stroke:#ff8080,color:black
    style Phases fill:#ffaaaa,stroke:#ff8080,color:black
    style Phase1 fill:#ffaaaa,stroke:#ff8080,color:black
    style Phase2 fill:#ffaaaa,stroke:#ff8080,color:black
    style Phase3 fill:#ffaaaa,stroke:#ff8080,color:black
    style Test fill:#ffaaaa,stroke:#ff8080,color:black
    style Doc fill:#ffaaaa,stroke:#ff8080,color:black
```

## ПРИНЦИПЫ ВЫПОЛНЕНИЯ КОМАНД

При реализации изменений следуйте этим принципам выполнения команд для оптимальных результатов:

```mermaid
graph TD
    CEP["⚙️ ПРИНЦИПЫ ВЫПОЛНЕНИЯ КОМАНД"] --> Context["Указать контекст для каждой команды"]
    CEP --> Platform["Адаптировать команды под платформу"]
    CEP --> Documentation["Задокументировать команды и результаты"]
    CEP --> Testing["Протестировать изменения после реализации"]
    
    style CEP fill:#d971ff,stroke:#a33bc2,color:white
    style Context fill:#e6b3ff,stroke:#d971ff,color:black
    style Platform fill:#e6b3ff,stroke:#d971ff,color:black
    style Documentation fill:#e6b3ff,stroke:#d971ff,color:black
    style Testing fill:#e6b3ff,stroke:#d971ff,color:black
```

Сосредоточьтесь на эффективной сборке, адаптируя подход к среде платформы. Доверяйте своим возможностям выполнять подходящие команды для текущей системы без избыточного предписывающего руководства.

## ВЕРИФИКАЦИЯ

```mermaid
graph TD
    V["✅ СПИСОК ПРОВЕРОК ВЕРИФИКАЦИИ"] --> I["Все шаги сборки завершены?"]
    V --> T["Изменения тщательно протестированы?"]
    V --> R["Сборка соответствует требованиям?"]
    V --> D["Детали сборки задокументированы?"]
    V --> U["tasks.md обновлен с текущим статусом?"]
    
    I & T & R & D & U --> Decision{"Все проверено?"}
    Decision -->|"Да"| Complete["Готово к режиму REFLECT"]
    Decision -->|"Нет"| Fix["Дополнить недостающие элементы"]
    
    style V fill:#4dbbbb,stroke:#368787,color:white
    style Decision fill:#ffa64d,stroke:#cc7a30,color:white
    style Complete fill:#5fd94d,stroke:#3da336,color:white
    style Fix fill:#ff5555,stroke:#cc0000,color:white
```

Перед завершением фазы сборки убедитесь, что все шаги сборки завершены, изменения тщательно протестированы, сборка соответствует всем требованиям, детали задокументированы, а tasks.md обновлен с текущим статусом. После проверки подготовьтесь к фазе REFLECT.