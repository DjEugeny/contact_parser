# Requirements Document

## Introduction

После внедрения ModelsManager в систему обнаружен регресс в обработке писем. Модель qwen/qwen3-235b-a22b:free, установленная как первая в приоритете, демонстрирует критические проблемы: возвращает пустые ответы, быстро упирается в rate limits, и имеет недостаточный context window для больших писем. Дополнительно обнаружены критические баги в постобработке (TypeError при дедупликации организаций) и проблемы с нормализацией телефонов. Необходимо исправить приоритеты моделей, устранить критические баги и обеспечить стабильную работу системы.

## Requirements

### Requirement 1: Исправление приоритетов моделей в models_config.yaml

**User Story:** As a system administrator, I want reliable models to be prioritized first, so that the system processes emails successfully without empty responses and rate limit issues.

#### Acceptance Criteria

1. WHEN models_config.yaml is updated THEN deepseek/deepseek-chat-v3.1:free SHALL be the first priority model for OpenRouter
2. WHEN models_config.yaml is updated THEN qwen models SHALL be moved to lower priority positions
3. WHEN models_config.yaml is updated THEN google/gemini-2.0-flash-exp:free SHALL be second priority
4. WHEN models are reordered THEN the system SHALL use deepseek as the default model
5. IF deepseek fails THEN the system SHALL fallback to gemini, not qwen

### Requirement 2: Исправление бага TypeError в organization_deduplicator

**User Story:** As a developer, I want organization deduplication to work correctly with phone data, so that the system doesn't crash during postprocessing.

#### Acceptance Criteria

1. WHEN organization has phones as list of dicts THEN _merge_organization_data SHALL handle them correctly
2. WHEN creating set from phones THEN the system SHALL extract phone numbers as strings, not dict objects
3. WHEN merging phone data THEN the system SHALL preserve phone metadata (type, source, etc.)
4. IF phones are in dict format THEN the system SHALL convert them to hashable format before set operations
5. WHEN postprocessing completes THEN no TypeError exceptions SHALL occur

### Requirement 3: Улучшение обработки пустых ответов LLM

**User Story:** As a system operator, I want the system to detect and handle empty LLM responses gracefully, so that processing continues with fallback to next model.

#### Acceptance Criteria

1. WHEN LLM returns empty response (0 characters) THEN the system SHALL treat it as an error
2. WHEN empty response is detected THEN the system SHALL report error to ModelsManager
3. WHEN error is reported THEN ModelsManager SHALL switch to next priority model
4. WHEN switching models THEN the system SHALL retry the request with new model
5. IF all models return empty responses THEN the system SHALL log detailed error and skip the email

### Requirement 4: Добавление валидации context length перед запросом

**User Story:** As a developer, I want the system to validate input size before sending to LLM, so that we avoid context length errors and choose appropriate models.

#### Acceptance Criteria

1. WHEN preparing LLM request THEN the system SHALL estimate token count of input
2. WHEN token count exceeds model's context window THEN the system SHALL skip that model
3. WHEN model is skipped due to context size THEN the system SHALL try next model with larger context
4. WHEN no model has sufficient context THEN the system SHALL apply chunking strategy
5. WHEN context validation is performed THEN it SHALL log the estimated tokens and model limits

### Requirement 5: Исправление нормализации телефонов

**User Story:** As a data quality specialist, I want all phone numbers to be properly normalized, so that we don't see warnings about missing normalized fields.

#### Acceptance Criteria

1. WHEN phone number is extracted by LLM THEN it SHALL be normalized before validation
2. WHEN phone lacks country code THEN the system SHALL attempt to infer it from context
3. WHEN phone is invalid format (e.g., "28-54-83") THEN the system SHALL log it as invalid, not as missing normalized field
4. WHEN phone normalization fails THEN the system SHALL preserve original value with metadata about failure
5. WHEN phones are saved THEN all valid phones SHALL have normalized field populated

### Requirement 6: Улучшение логирования переключений моделей

**User Story:** As a system administrator, I want detailed logs of model switches and reasons, so that I can understand system behavior and optimize model configuration.

#### Acceptance Criteria

1. WHEN model switch occurs THEN the system SHALL log old model, new model, and reason
2. WHEN model fails THEN the system SHALL log error type, error message, and response details
3. WHEN empty response is received THEN the system SHALL log it as "empty_response" error type
4. WHEN context length error occurs THEN the system SHALL log estimated tokens and model limit
5. WHEN all models fail THEN the system SHALL create detailed error report with all attempts

### Requirement 7: Тестирование с исправленной конфигурацией

**User Story:** As a developer, I want to verify that fixes resolve the regression, so that we can confidently deploy the corrected system.

#### Acceptance Criteria

1. WHEN test runs with corrected models_config.yaml THEN success rate SHALL be > 90%
2. WHEN test processes emails from 2025-07-28 THEN no empty responses SHALL occur
3. WHEN test processes large emails THEN context length errors SHALL be handled gracefully
4. WHEN test completes THEN no TypeError exceptions SHALL occur in postprocessing
5. WHEN test completes THEN phone normalization warnings SHALL be reduced or eliminated

