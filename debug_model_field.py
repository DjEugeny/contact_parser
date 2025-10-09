#!/usr/bin/env python3
"""Debug script to check if model field is present in extractor output"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from src.core.extractor_factory import ExtractorFactory
from src.config.config_manager import UnifiedConfigManager

# Initialize config and extractor
config_manager = UnifiedConfigManager()
extractor = ExtractorFactory.create_extractor(
    test_mode=False,
    config_manager=config_manager
)

# Load a real email
email_file = Path("data/emails/2025-07-23/email_001_20250723_20250723_dna-technology_ru_bd220144.json")
with open(email_file) as f:
    email_data = json.load(f)

# Prepare text
subject = email_data.get('subject', '')
body = email_data.get('body', '')
combined_text = f"Subject: {subject}\n\n{body}"

# Extract
print("🔍 Extracting data...")
result = extractor.extract_all_data(combined_text[:5000], {})  # Limit text for speed

# Check for model field
print("\n📊 Checking result fields:")
print(f"  provider_used: {result.get('provider_used', 'NOT_FOUND')}")
print(f"  model: {result.get('model', 'NOT_FOUND')}")
print(f"  processing_time: {result.get('processing_time', 'NOT_FOUND')}")

# List all keys
print(f"\n📋 All keys in result:")
for key in sorted(result.keys()):
    if key not in ['organizations', 'contacts', 'interactions', 'commercial_offers', 'raw_llm_result', 'original_response']:
        print(f"  - {key}")
