#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test for Task 8: Model Fallback Logging with Providers
Tests that providers correctly log model switches through ModelsManager
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.models_manager import ModelsManager


def test_provider_fallback_integration():
    """Test that ModelsManager logging works correctly with multiple scenarios"""
    
    print("\n" + "="*60)
    print("🧪 TASK 8: COMPREHENSIVE LOGGING TEST")
    print("="*60)
    
    # Initialize ModelsManager
    print("\n1️⃣ Initializing ModelsManager...")
    manager = ModelsManager()
    print("   ✅ ModelsManager initialized")
    
    # Show initial model status
    print("\n2️⃣ Initial Model Configuration:")
    manager.print_status()
    
    # Verify log file configuration
    print("\n3️⃣ Verifying Log Configuration...")
    log_file = Path("data/logs/model_fallback.log")
    print(f"   Log file path: {log_file}")
    print(f"   Log directory exists: {log_file.parent.exists()}")
    
    # Clear log file for clean test
    if log_file.exists():
        log_file.unlink()
        print("   Cleared existing log file")
    
    # Test multiple error scenarios
    print("\n4️⃣ Testing Multiple Error Scenarios...")
    print("-" * 60)
    
    test_scenarios = [
        ('openrouter', '404', 'Model not found'),
        ('openrouter', '429', 'Rate limit exceeded'),
        ('replicate', 'data policy', 'Data policy violation'),
        ('replicate', '404', 'Model unavailable')
    ]
    
    switches_count = 0
    
    for provider, error_code, description in test_scenarios:
        print(f"\n   Testing {provider} with '{error_code}' error...")
        initial_model = manager.get_current_model(provider)
        
        # Trigger 3 errors to cause switch
        for i in range(3):
            switched = manager.report_error(provider, f'{error_code} {description}')
            if switched:
                switches_count += 1
                new_model = manager.get_current_model(provider)
                print(f"   ✅ Switched from {initial_model.name} to {new_model.name}")
                break
    
    # Show final status
    print("\n5️⃣ Final Model Status:")
    manager.print_status()
    
    # Verify log file
    print("\n6️⃣ Verifying Log File Contents...")
    print("-" * 60)
    
    if not log_file.exists():
        print("   ❌ FAILED: Log file not created")
        return False
    
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    print(f"   ✅ Log file exists")
    print(f"   Log file size: {len(log_content)} bytes")
    print(f"   Number of switches logged: {log_content.count('Timestamp:')}")
    
    # Verify all required fields
    required_fields = {
        'Timestamp:': 'ISO format timestamp',
        'Provider:': 'Provider name (openrouter/replicate)',
        'Old Model:': 'Previous model name with priority',
        'New Model:': 'New model name with priority',
        'Reason:': 'Reason for switch'
    }
    
    print("\n   Checking required fields:")
    all_fields_present = True
    for field, description in required_fields.items():
        present = field in log_content
        status = "✅" if present else "❌"
        print(f"      {status} {field} ({description})")
        if not present:
            all_fields_present = False
    
    # Display log content
    print("\n7️⃣ Complete Log File Contents:")
    print("-" * 60)
    print(log_content)
    print("-" * 60)
    
    # Verify log entry format
    print("\n8️⃣ Verifying Log Entry Format...")
    
    # Check for ISO timestamp format
    import re
    timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+'
    timestamps = re.findall(timestamp_pattern, log_content)
    print(f"   ✅ Found {len(timestamps)} valid ISO timestamps")
    
    # Check for provider names
    providers_logged = log_content.count('Provider: openrouter') + log_content.count('Provider: replicate')
    print(f"   ✅ Found {providers_logged} provider entries")
    
    # Check for priority information
    priority_mentions = log_content.count('priority')
    print(f"   ✅ Found {priority_mentions} priority mentions")
    
    # Summary
    print("\n9️⃣ Test Summary:")
    print("-" * 60)
    
    checks = {
        "ModelsManager initialized": True,
        "Log file created": log_file.exists(),
        "All required fields present": all_fields_present,
        "Model switches occurred": switches_count > 0,
        "Timestamps in ISO format": len(timestamps) > 0,
        "Provider names logged": providers_logged > 0,
        "Priority information included": priority_mentions > 0,
        "Reason field populated": 'Reason: Max retries exceeded' in log_content
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ COMPREHENSIVE LOGGING TEST PASSED")
        print("   All requirements for Task 8 verified:")
        print("   - Model errors trigger automatic switching ✅")
        print("   - Switches logged to data/logs/model_fallback.log ✅")
        print("   - Log entries contain all required fields ✅")
    else:
        print("❌ COMPREHENSIVE LOGGING TEST FAILED")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    try:
        success = test_provider_fallback_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
