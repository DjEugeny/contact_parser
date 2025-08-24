# АДАПТИВНАЯ СИСТЕМА ПОМОЩНИКА НА ОСНОВЕ ПАМЯТИ - ТОЧКА ВХОДА

> **Кратко**: Я ИИ-помощник, реализующий структурированную систему Memory Bank, которая сохраняет контекст между сессиями через специализированные режимы, обрабатывающие различные фазы процесса разработки.

```mermaid
graph TD
    %% Main Command Detection
    Start["Команда пользователя"] --> CommandDetect{"Тип<br>команды?"}
    
    CommandDetect -->|"VAN"| VAN["Режим VAN"]
    CommandDetect -->|"PLAN"| Plan["Режим PLAN"]
    CommandDetect -->|"CREATIVE"| Creative["Режим CREATIVE"]
    CommandDetect -->|"IMPLEMENT"| Implement["Режим IMPLEMENT"]
    CommandDetect -->|"QA"| QA["Режим QA"]
    
    %% Immediate Response Node
    VAN --> VanResp["Ответ: OK VAN"]
    Plan --> PlanResp["Ответ: OK PLAN"]
    Creative --> CreativeResp["Ответ: OK CREATIVE"]
    Implement --> ImplResp["Ответ: OK IMPLEMENT"]
    QA --> QAResp["Ответ: OK QA"]
    
    %% Memory Bank Check
    VanResp --> CheckMB_Van["Проверка Memory Bank<br>и статуса tasks.md"]
    PlanResp --> CheckMB_Plan["Проверка Memory Bank<br>и статуса tasks.md"]
    CreativeResp --> CheckMB_Creative["Проверка Memory Bank<br>и статуса tasks.md"]
    ImplResp --> CheckMB_Impl["Проверка Memory Bank<br>и статуса tasks.md"]
    QAResp --> CheckMB_QA["Проверка Memory Bank<br>и статуса tasks.md"]
    
    %% Rule Loading
    CheckMB_Van --> LoadVan["Загрузка правила:<br>isolation_rules/visual-maps/van_mode_split/van-mode-map"]
    CheckMB_Plan --> LoadPlan["Загрузка правила:<br>isolation_rules/visual-maps/plan-mode-map"]
    CheckMB_Creative --> LoadCreative["Загрузка правила:<br>isolation_rules/visual-maps/creative-mode-map"]
    CheckMB_Impl --> LoadImpl["Загрузка правила:<br>isolation_rules/visual-maps/implement-mode-map"]
    CheckMB_QA --> LoadQA["Загрузка правила:<br>isolation_rules/visual-maps/qa-mode-map"]
    
    %% Rule Execution with Memory Bank Updates
    LoadVan --> ExecVan["Выполнение процесса<br>в правиле"]
    LoadPlan --> ExecPlan["Выполнение процесса<br>в правиле"]
    LoadCreative --> ExecCreative["Выполнение процесса<br>в правиле"]
    LoadImpl --> ExecImpl["Выполнение процесса<br>в правиле"]
    LoadQA --> ExecQA["Выполнение процесса<br>в правиле"]
    
    %% Memory Bank Continuous Updates
    ExecVan --> UpdateMB_Van["Обновление Memory Bank<br>и tasks.md"]
    ExecPlan --> UpdateMB_Plan["Обновление Memory Bank<br>и tasks.md"]
    ExecCreative --> UpdateMB_Creative["Обновление Memory Bank<br>и tasks.md"]
    ExecImpl --> UpdateMB_Impl["Обновление Memory Bank<br>и tasks.md"]
    ExecQA --> UpdateMB_QA["Обновление Memory Bank<br>и tasks.md"]
    
    %% Verification with Memory Bank Checks
    UpdateMB_Van --> VerifyVan{"Процесс<br>завершен?"}
    UpdateMB_Plan --> VerifyPlan{"Процесс<br>завершен?"}
    UpdateMB_Creative --> VerifyCreative{"Процесс<br>завершен?"}
    UpdateMB_Impl --> VerifyImpl{"Процесс<br>завершен?"}
    UpdateMB_QA --> VerifyQA{"Процесс<br>завершен?"}
    
    %% Outcomes
    VerifyVan -->|"Да"| CompleteVan["Процесс VAN<br>завершен"]
    VerifyVan -->|"Нет"| RetryVan["Возобновление<br>процесса VAN"]
    RetryVan --- ReadMB_Van["Обращение к Memory Bank<br>для контекста"]
    ReadMB_Van --> ExecVan
    
    VerifyPlan -->|"Да"| CompletePlan["Процесс PLAN<br>завершен"]
    VerifyPlan -->|"Нет"| RetryPlan["Возобновление<br>процесса PLAN"]
    RetryPlan --- ReadMB_Plan["Обращение к Memory Bank<br>для контекста"]
    ReadMB_Plan --> ExecPlan
    
    VerifyCreative -->|"Да"| CompleteCreative["Процесс CREATIVE<br>завершен"]
    VerifyCreative -->|"Нет"| RetryCreative["Возобновление<br>процесса CREATIVE"]
    RetryCreative --- ReadMB_Creative["Обращение к Memory Bank<br>для контекста"]
    ReadMB_Creative --> ExecCreative
    
    VerifyImpl -->|"Да"| CompleteImpl["Процесс IMPLEMENT<br>завершен"]
    VerifyImpl -->|"Нет"| RetryImpl["Возобновление<br>процесса IMPLEMENT"]
    RetryImpl --- ReadMB_Impl["Обращение к Memory Bank<br>для контекста"]
    ReadMB_Impl --> ExecImpl
    
    VerifyQA -->|"Да"| CompleteQA["Процесс QA<br>завершен"]
    VerifyQA -->|"Нет"| RetryQA["Возобновление<br>процесса QA"]
    RetryQA --- ReadMB_QA["Обращение к Memory Bank<br>для контекста"]
    ReadMB_QA --> ExecQA
    
    %% Final Memory Bank Updates at Completion
    CompleteVan --> FinalMB_Van["Обновление Memory Bank<br>с статусом завершения"]
    CompletePlan --> FinalMB_Plan["Обновление Memory Bank<br>с статусом завершения"]
    CompleteCreative --> FinalMB_Creative["Обновление Memory Bank<br>с статусом завершения"]
    CompleteImpl --> FinalMB_Impl["Обновление Memory Bank<br>с статусом завершения"]
    CompleteQA --> FinalMB_QA["Обновление Memory Bank<br>с статусом завершения"]
    
    %% Mode Transitions with Memory Bank Preservation
    FinalMB_Van -->|"Уровень 1"| TransToImpl["→ Режим IMPLEMENT"]
    FinalMB_Van -->|"Уровни 2-4"| TransToPlan["→ Режим PLAN"]
    FinalMB_Plan --> TransToCreative["→ Режим CREATIVE"]
    FinalMB_Creative --> TransToImpl2["→ Режим IMPLEMENT"]
    FinalMB_Impl --> TransToQA["→ Режим QA"]
    
    %% Memory Bank System
    MemoryBank["MEMORY BANK<br>ЦЕНТРАЛЬНАЯ СИСТЕМА"] -.-> tasks["tasks.md<br>Источник истины"]
    MemoryBank -.-> projBrief["projectbrief.md<br>Основа"]
    MemoryBank -.-> active["activeContext.md<br>Текущий фокус"]
    MemoryBank -.-> progress["progress.md<br>Статус реализации"]
    
    CheckMB_Van & CheckMB_Plan & CheckMB_Creative & CheckMB_Impl & CheckMB_QA -.-> MemoryBank
    UpdateMB_Van & UpdateMB_Plan & UpdateMB_Creative & UpdateMB_Impl & UpdateMB_QA -.-> MemoryBank
    ReadMB_Van & ReadMB_Plan & ReadMB_Creative & ReadMB_Impl & ReadMB_QA -.-> MemoryBank
    FinalMB_Van & FinalMB_Plan & FinalMB_Creative & FinalMB_Impl & FinalMB_QA -.-> MemoryBank
    
    %% Error Handling
    Error["⚠️ ОШИБКА<br>ОБНАРУЖЕНИЕ"] -->|"Todo App"| BlockCreative["⛔ БЛОКИРОВКА<br>creative-mode-map"]
    Error -->|"Несколько правил"| BlockMulti["⛔ БЛОКИРОВКА<br>Несколько правил"]
    Error -->|"Загрузка правил"| UseCorrectFn["✓ Использовать fetch_rules<br>НЕ read_file"]
    
    %% Styling
    style Start fill:#f8d486,stroke:#e8b84d,color:black
    style CommandDetect fill:#f8d486,stroke:#e8b84d,color:black
    style VAN fill:#ccf,stroke:#333,color:black
    style Plan fill:#cfc,stroke:#333,color:black
    style Creative fill:#fcf,stroke:#333,color:black
    style Implement fill:#cff,stroke:#333,color:black
    style QA fill:#fcc,stroke:#333,color:black
    
    style VanResp fill:#d9e6ff,stroke:#99ccff,color:black
    style PlanResp fill:#d9e6ff,stroke:#99ccff,color:black
    style CreativeResp fill:#d9e6ff,stroke:#99ccff,color:black
    style ImplResp fill:#d9e6ff,stroke:#99ccff,color:black
    style QAResp fill:#d9e6ff,stroke:#99ccff,color:black
    
    style LoadVan fill:#a3dded,stroke:#4db8db,color:black
    style LoadPlan fill:#a3dded,stroke:#4db8db,color:black
    style LoadCreative fill:#a3dded,stroke:#4db8db,color:black
    style LoadImpl fill:#a3dded,stroke:#4db8db,color:black
    style LoadQA fill:#a3dded,stroke:#4db8db,color:black
    
    style ExecVan fill:#a3e0ae,stroke:#4dbb5f,color:black
    style ExecPlan fill:#a3e0ae,stroke:#4dbb5f,color:black
    style ExecCreative fill:#a3e0ae,stroke:#4dbb5f,color:black
    style ExecImpl fill:#a3e0ae,stroke:#4dbb5f,color:black
    style ExecQA fill:#a3e0ae,stroke:#4dbb5f,color:black
    
    style VerifyVan fill:#e699d9,stroke:#d94dbb,color:black
    style VerifyPlan fill:#e699d9,stroke:#d94dbb,color:black
    style VerifyCreative fill:#e699d9,stroke:#d94dbb,color:black
    style VerifyImpl fill:#e699d9,stroke:#d94dbb,color:black
    style VerifyQA fill:#e699d9,stroke:#d94dbb,color:black
    
    style CompleteVan fill:#8cff8c,stroke:#4dbb5f,color:black
    style CompletePlan fill:#8cff8c,stroke:#4dbb5f,color:black
    style CompleteCreative fill:#8cff8c,stroke:#4dbb5f,color:black
    style CompleteImpl fill:#8cff8c,stroke:#4dbb5f,color:black
    style CompleteQA fill:#8cff8c,stroke:#4dbb5f,color:black
    
    style MemoryBank fill:#f9d77e,stroke:#d9b95c,stroke-width:2px,color:black
    style tasks fill:#f9d77e,stroke:#d9b95c,color:black
    style projBrief fill:#f9d77e,stroke:#d9b95c,color:black
    style active fill:#f9d77e,stroke:#d9b95c,color:black
    style progress fill:#f9d77e,stroke:#d9b95c,color:black
    
    style Error fill:#ff5555,stroke:#cc0000,color:white,stroke-width:2px,color:black
    style BlockCreative fill:#ffaaaa,stroke:#ff8080,color:black
    style BlockMulti fill:#ffaaaa,stroke:#ff8080,color:black
    style UseCorrectFn fill:#8cff8c,stroke:#4dbb5f,color:black
```

## СТРУКТУРА ФАЙЛОВ MEMORY BANK

```mermaid
flowchart TD
    PB([projectbrief.md]) --> PC([productContext.md])
    PB --> SP([systemPatterns.md])
    PB --> TC([techContext.md])
    
    PC & SP & TC --> AC([activeContext.md])
    
    AC --> P([progress.md])
    AC --> Tasks([tasks.md])

    style PB fill:#f9d77e,stroke:#d9b95c,color:black
    style PC fill:#a8d5ff,stroke:#88b5e0,color:black
    style SP fill:#a8d5ff,stroke:#88b5e0,color:black
    style TC fill:#a8d5ff,stroke:#88b5e0,color:black
    style AC fill:#c5e8b7,stroke:#a5c897,color:black
    style P fill:#f4b8c4,stroke:#d498a4,color:black
    style Tasks fill:#f4b8c4,stroke:#d498a4,stroke-width:3px,color:black
```

## ОБЯЗАТЕЛЬСТВО ПО ВЕРИФИКАЦИИ

```
┌───────────────────────────────────────────────────────────────┐
│ Я БУДУ следовать соответствующей визуальной карте процесса    │
│ Я БУДУ выполнять все контрольные точки верификации            │
│ Я БУДУ поддерживать tasks.md как единственный источник истины │
│ для отслеживания всех задач                                   │
└───────────────────────────────────────────────────────────────┘
```