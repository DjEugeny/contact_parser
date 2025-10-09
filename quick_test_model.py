#!/usr/bin/env python3
"""Quick test to verify model field"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from src.api_pipeline_validator import APIPipelineValidator

# Create args
args = argparse.Namespace(
    mode='first1',
    date=None,
    count=1,
    start_date=None,
    end_date=None,
    dry_run=False
)

# Initialize validator
print("Initializing validator...")
validator = APIPipelineValidator(args)

# Process one email
email_file = "data/emails/2025-07-23/email_001_20250723_20250723_dna-technology_ru_bd220144.json"
print(f"\nProcessing {email_file}...")

result = validator.process_single_email(email_file=email_file, simplified=False)

if result:
    print(f"\n✅ Result received")
    print(f"   provider_used: {result.get('provider_used', 'NOT_FOUND')}")
    print(f"   model: {result.get('model', 'NOT_FOUND')}")
else:
    print("\n❌ No result")
