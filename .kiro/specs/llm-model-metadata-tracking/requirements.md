# Requirements Document

## Introduction

В текущей реализации результаты обработки писем содержат только информацию о провайдере (например, "Replicate" или "OpenRouter"), но не содержат информации о конкретной модели, которая была использована. Это затрудняет анализ качества работы разных моделей и сравнение их эффективности. Необходимо добавить детальную информацию о модели в метаданные результатов обработки, чтобы можно было отслеживать, какая именно модель обработала каждое письмо.

## Requirements

### Requirement 1: Сохранение информации о модели в llm_metadata

**User Story:** As a data analyst, I want to see which specific model processed each email, so that I can compare quality and performance across different models.

#### Acceptance Criteria

1. WHEN email is processed by LLM THEN the result SHALL include model name in llm_metadata
2. WHEN llm_metadata is created THEN it SHALL contain both 'provider' and 'model' fields
3. WHEN OpenRouter processes email THEN model field SHALL contain full model name (e.g., "google/gemini-2.0-flash-exp:free")
4. WHEN Replicate processes email THEN model field SHALL contain full model name (e.g., "deepseek-ai/deepseek-v3.1")
5. IF model information is not available THEN model field SHALL be set to "Unknown"

### Requirement 2: Передача информации о модели через pipeline

**User Story:** As a developer, I want model information to flow through the entire processing pipeline, so that it's preserved in the final output.

#### Acceptance Criteria

1. WHEN provider returns response THEN it SHALL include 'model' field from config
2. WHEN api_pipeline_validator creates llm_metadata THEN it SHALL extract 'model' from llm_response
3. WHEN llm_response contains 'model' field THEN it SHALL be copied to result's llm_metadata
4. WHEN result is saved to JSON THEN llm_metadata SHALL contain both provider and model
5. IF provider doesn't return model info THEN system SHALL use "Unknown" as default

### Requirement 3: Логирование выбранной модели

**User Story:** As a system administrator, I want to see which model was selected for each email in logs, so that I can track model usage and switches.

#### Acceptance Criteria

1. WHEN ModelsManager selects model THEN it SHALL log provider name and model name
2. WHEN model is logged THEN log SHALL include model priority level
3. WHEN provider makes request THEN it SHALL log which model is being used
4. WHEN model switch occurs THEN it SHALL log old model and new model names
5. WHEN processing completes THEN logs SHALL show clear model selection history

### Requirement 4: Обратная совместимость с существующими результатами

**User Story:** As a developer, I want the system to handle old results without model field gracefully, so that existing data remains valid.

#### Acceptance Criteria

1. WHEN reading old result files THEN system SHALL not fail if 'model' field is missing
2. WHEN displaying results THEN system SHALL show "Unknown" for missing model field
3. WHEN comparing results THEN system SHALL handle both old and new metadata formats
4. IF model field is missing THEN it SHALL not affect other processing logic
5. WHEN migrating data THEN old results SHALL remain valid without modification

### Requirement 5: Формат метаданных в результатах

**User Story:** As a data analyst, I want consistent metadata format across all processed emails, so that I can easily analyze and compare results.

#### Acceptance Criteria

1. WHEN result is saved THEN llm_metadata SHALL have structure: {provider, model, response_time, timestamp}
2. WHEN usage data is available THEN llm_metadata SHALL also include 'usage' field
3. WHEN model field is present THEN it SHALL be a string with full model identifier
4. WHEN provider is OpenRouter THEN model SHALL include namespace (e.g., "google/gemini-2.0-flash-exp:free")
5. WHEN provider is Replicate THEN model SHALL include owner and name (e.g., "deepseek-ai/deepseek-v3.1")

### Requirement 6: Тестирование с новыми метаданными

**User Story:** As a developer, I want to verify that model metadata is correctly saved, so that analysts can use it for quality comparison.

#### Acceptance Criteria

1. WHEN test processes emails THEN all results SHALL contain model field in llm_metadata
2. WHEN multiple models are used THEN each result SHALL show which model processed it
3. WHEN viewing results THEN it SHALL be easy to identify which model was used
4. WHEN analyzing batch results THEN it SHALL be possible to group by model name
5. WHEN test completes THEN no results SHALL have missing or null model field (except "Unknown")
