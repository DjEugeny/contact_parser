# Implementation Plan

- [x] 1. Create contact location safety module with core data structures
  - Create `src/postprocessing/contact_location_safety.py` with `ContactLocationEvidence` dataclass and `ContactLocationSafety` class
  - Implement configuration loading from `config/processing_config.json`
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 2. Implement HQ-block detection logic
  - Implement `is_hq_block()` method to detect organizational blocks with legal markers (ИНН, ОГРН, р/с, к/с, БИК, ОКПО)
  - Implement detection of addresses near organization names without personal context
  - _Requirements: 1.2, 1.3, 2.4_

- [x] 3. Implement personal location signal extraction
  - Implement `extract_contact_location_evidence()` method to extract location signals from signatures and email body
  - Detect personal markers: "г.", "город", "регион", "представитель", "офис в", "территориальный менеджер"
  - Extract city and address from personal contexts with snippet preservation
  - _Requirements: 2.1, 2.2, 2.3, 2.5_

- [x] 4. Implement confidence scoring system
  - Implement `calculate_confidence()` method with 0.0-1.0 scale
  - High confidence (>=0.9) for strong personal markers ("представитель", "офис в", "территориальный менеджер")
  - Medium confidence (>=0.8) for signature blocks with name and title
  - Low confidence (<=0.6) for body mentions near name without context
  - Zero confidence (0.0) for HQ blocks
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 5. Implement safe location application logic
  - Implement `apply_contact_location()` method that only fills empty fields
  - Protect existing contact.city and contact.address from overwriting
  - Apply location only when confidence >= min_confidence threshold
  - Handle internal domain contacts (set city=null, address=null when no personal signal)
  - _Requirements: 4.1, 4.2, 4.3, 1.4_

- [x] 6. Implement metadata tracking and debugging
  - Save metadata to `postprocessing_metadata.location_evidence[contact_gid]`
  - Include fields: applied, snippet, confidence, source_type, matched_patterns
  - Add rejected_reason for declined location data
  - Track source_type: "signature", "body_near_name", "title_context", "rejected_hq_block"
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 4.4, 4.5_

- [x] 7. Implement edge case handling
  - Handle multiple cities in signature (choose highest confidence or first mentioned)
  - Handle multiple offices in different cities (use city from contact's role context)
  - Handle format "Офис в Москве | Представитель в Новосибирске" (use role context)
  - Prevent overwriting when personal signal contradicts existing data
  - No assumptions when signature has only phone without location markers
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 8. Integrate into postprocessing pipeline
  - Import `ContactLocationSafety` in `src/postprocessing/postprocessor.py`
  - Add location safety check after `org_location_enrichment()` and before final normalization
  - Process all contacts in message with evidence extraction and application
  - Pass updated contacts and metadata to next pipeline stage
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 9. Add logging and monitoring
  - Log INFO when location data is applied (contact_gid, values, confidence)
  - Log DEBUG when location data is rejected (contact_gid, reason, snippet)
  - Log DEBUG when HQ-block is detected (text fragment)
  - Log statistics after processing: contacts processed, enriched, rejected
  - Log ERROR on exceptions and continue processing other contacts
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 10. Add configuration file
  - Create or update `config/processing_config.json` with contact_location_safety section
  - Add min_confidence (default 0.7), internal_domains, personal_markers, hq_markers, enabled flag
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 11. Test on regression cases (emails 016 and 017)
  - Verify email 016: Воронова С.С. does NOT get city=Москва or HQ-address
  - Verify email 017: Клочкова-Абельянц С.А. does NOT get city=Москва or HQ-address
  - Verify personal signal extraction works correctly
  - Verify internal employee handling (dna-technology.ru domain)
  - _Requirements: 8.1, 8.2, 8.3, 8.4_
