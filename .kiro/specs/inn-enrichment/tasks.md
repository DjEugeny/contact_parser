# INN Enrichment Implementation Tasks

## Overview
Implementation of PLAN-006: Org/End-User INN Enrichment system with priority on official FNS sources and transparent decision tracking.

## Task Categories

### 1. Core Module Structure
- [x] **T001**: Create `org_inn_resolver.py` main module
- [x] **T002**: Implement configuration structure in `config/settings.py`
- [x] **T003**: Create base classes and interfaces for providers
- [x] **T004**: Set up logging and error handling framework

### 2. Data Normalization & Validation
- [x] **T005**: Implement `name_norm` normalization (remove legal forms, quotes, punct.)
- [x] **T006**: Implement `city_norm` normalization with synonyms/typos handling
- [x] **T007**: Implement `address_norm` normalization (street+house without corp/office)
- [x] **T008**: Implement `domain` extraction and normalization (e2LD, punycode)
- [x] **T009**: Implement INN validation (checksum, length 10/12)
- [x] **T010**: Create search key generation logic `(name_norm, city_norm, address_norm?, domain?)`

### 3. Provider Adapters
- [x] **T011**: Implement `DaDataClient` adapter
  - [x] T011.1: Company search by name/city/address
  - [x] T011.2: INN lookup and validation
  - [x] T011.3: Rate limiting and timeout handling
  - [x] T011.4: Response parsing and normalization
- [x] **T012**: Implement `FNSIntegrationClient` (placeholder for future API access)
- [x] **T013**: Implement `FNSPublicClient` (egrul.nalog.ru parser, if feasible)
- [x] **T014**: Create provider factory and parallel execution logic

### 4. Scoring Algorithm
- [x] **T015**: Implement candidate scoring logic
  - [x] T015.1: Name similarity scoring (string matching)
  - [x] T015.2: City/region matching
  - [x] T015.3: Address matching (street+house)
  - [x] T015.4: Domain/email matching
  - [x] T015.5: Legal form matching
  - [x] T015.6: Weighted score calculation
- [x] **T016**: Implement two-threshold decision logic (auto-accept/needs-review/reject)

### 5. Cache & Override System
- [x] **T017**: Implement `inn_cache.jsonl` operations
  - [x] T017.1: Cache key generation
  - [x] T017.2: TTL validation and expiration
  - [x] T017.3: Atomic append operations
  - [x] T017.4: Cache lookup and retrieval
- [x] **T018**: Implement `inn_overrides.yml` system
  - [x] T018.1: Override file format and validation
  - [x] T018.2: GID-based and name+city-based overrides
  - [x] T018.3: Override application logic

### 6. Metadata & Provenance
- [x] **T019**: Implement `postprocessing_metadata.enrichment.org_inn` structure
- [x] **T020**: Create decision tracking and logging
- [x] **T021**: Implement candidate information storage
- [x] **T022**: Add provenance trail for all decisions

### 7. Pipeline Integration
- [x] **T023**: Identify integration point in existing pipeline (after GID assignment)
- [x] **T024**: Implement skip logic for existing valid INNs
- [x] **T025**: Ensure no additional fields in `organizations[]` except `inn`
- [x] **T026**: Create pipeline wrapper/orchestrator
- [x] **T027**: Add configuration loading and validation

### 8. Testing Framework
- [x] **T028**: Unit tests for normalization functions
- [x] **T029**: Unit tests for INN validation
- [x] **T030**: Unit tests for scoring algorithm
- [x] **T031**: Mock provider adapters for testing
- [x] **T032**: Integration tests for cache operations
- [x] **T033**: Integration tests for override system
- [x] **T034**: End-to-end pipeline tests
- [x] **T035**: Regression tests with existing data

### 9. Error Handling & Resilience
- [x] **T036**: Implement timeout handling for all providers
- [x] **T037**: Implement graceful degradation on provider failures
- [x] **T038**: Add retry logic with exponential backoff
- [x] **T039**: Implement negative result caching (short TTL)
- [x] **T040**: Add circuit breaker pattern for unreliable providers

### 10. Documentation & Configuration
- [x] **T041**: Create configuration documentation
- [x] **T042**: Document provider setup and API keys
- [x] **T043**: Create troubleshooting guide
- [x] **T044**: Document legal compliance considerations
- [x] **T045**: Create deployment checklist

## Implementation Priority

### Phase 1: Foundation (T001-T010)
Core module structure, configuration, and data normalization

### Phase 2: DaData Integration (T011, T015-T016)
Working DaData provider with scoring and decision logic

### Phase 3: Storage Systems (T017-T022)
Cache, overrides, and metadata tracking

### Phase 4: Pipeline Integration (T023-T027)
Integration with existing processing pipeline

### Phase 5: Testing & Validation (T028-T035)
Comprehensive testing suite

### Phase 6: Production Readiness (T036-T045)
Error handling, resilience, and documentation

## Success Criteria
- [x] Organizations without INN get enriched when confidence is high (≥0.85) and single candidate
- [x] Medium confidence (0.65-0.85) or multiple candidates marked as `needs_review`
- [x] Low confidence (<0.65) results in `reject` status
- [x] All decisions tracked in `postprocessing_metadata.enrichment.org_inn`
- [x] Cache and overrides work correctly for subsequent runs
- [x] No schema violations in final JSON output
- [x] Performance impact is minimal (timeouts, parallel execution)

## Dependencies
- DaData API access (available)
- FNS API access (future)
- Existing GID assignment system
- Current postprocessing pipeline structure