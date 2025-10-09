#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Task 8: Model Fallback Logging
Tests automatic model switching and verifies logging functionality
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.models_manager import ModelsManager


def test_model_fallback_logging():
    """Test model fallback logging functionality"""
    
    print("\n" + "="*60)
    print("🧪 TASK 8: MODEL FALLBACK LOGGING TEST")
    print("="*60)
    
    # Initialize ModelsManager
    print("\n1️⃣ Initializing ModelsManager...")
    manager = ModelsManager()
    
    # Show initial status
    print("\n2️⃣ Initial Model Status:")
    manager.print_status()
    
    # Get log file path
    log_file = Path("data/logs/model_fallback.log")
    
    # Clear existing log file for clean test
    if log_file.exists():
        print(f"\n3️⃣ Clearing existing log file: {log_file}")
        log_file.unlink()
    
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n4️⃣ Testing OpenRouter Model Fallback...")
    print("-" * 60)
    
    # Get initial model
    initial_or_model = manager.get_current_model('openrouter')
    print(f"   Initial OpenRouter model: {initial_or_model.name}")
    
    # Trigger errors to cause model switch (need 3 errors based on config)
    print("\n   Triggering errors to test automatic switching...")
    for i in range(3):
        print(f"   ❌ Error {i+1}/3: Simulating '404' error")
        switched = manager.report_error('openrouter', '404 model not found')
        if switched:
            new_model = manager.get_current_model('openrouter')
            print(f"   ✅ Switched to: {new_model.name}")
            break
    
    # Check if switch occurred
    current_or_model = manager.get_current_model('openrouter')
    if current_or_model.name != initial_or_model.name:
        print(f"\n   ✅ Model switch successful!")
        print(f"      Old: {initial_or_model.name}")
        print(f"      New: {current_or_model.name}")
    else:
        print(f"\n   ⚠️  No model switch occurred")
    
    print("\n5️⃣ Testing Replicate Model Fallback...")
    print("-" * 60)
    
    # Get initial model
    initial_rep_model = manager.get_current_model('replicate')
    print(f"   Initial Replicate model: {initial_rep_model.name}")
    
    # Trigger errors to cause model switch
    print("\n   Triggering errors to test automatic switching...")
    for i in range(3):
        print(f"   ❌ Error {i+1}/3: Simulating '429' rate limit error")
        switched = manager.report_error('replicate', '429 rate limit exceeded')
        if switched:
            new_model = manager.get_current_model('replicate')
            print(f"   ✅ Switched to: {new_model.name}")
            break
    
    # Check if switch occurred
    current_rep_model = manager.get_current_model('replicate')
    if current_rep_model.name != initial_rep_model.name:
        print(f"\n   ✅ Model switch successful!")
        print(f"      Old: {initial_rep_model.name}")
        print(f"      New: {current_rep_model.name}")
    else:
        print(f"\n   ⚠️  No model switch occurred")
    
    # Show final status
    print("\n6️⃣ Final Model Status:")
    manager.print_status()
    
    # Verify log file exists and contains expected entries
    print("\n7️⃣ Verifying Log File...")
    print("-" * 60)
    
    if not log_file.exists():
        print(f"   ❌ FAILED: Log file not found at {log_file}")
        return False
    
    print(f"   ✅ Log file exists: {log_file}")
    
    # Read and verify log contents
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    print(f"\n   Log file size: {len(log_content)} bytes")
    
    # Check for required fields in log entries
    required_fields = ['Timestamp:', 'Provider:', 'Old Model:', 'New Model:', 'Reason:']
    missing_fields = []
    
    for field in required_fields:
        if field not in log_content:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"   ❌ FAILED: Missing required fields in log: {missing_fields}")
        return False
    
    print(f"   ✅ All required fields present in log")
    
    # Display log content
    print("\n8️⃣ Log File Contents:")
    print("-" * 60)
    print(log_content)
    print("-" * 60)
    
    # Verify specific requirements
    print("\n9️⃣ Verification Summary:")
    print("-" * 60)
    
    checks = {
        "Log file created": log_file.exists(),
        "Contains timestamp": "Timestamp:" in log_content,
        "Contains provider": "Provider:" in log_content,
        "Contains old model": "Old Model:" in log_content,
        "Contains new model": "New Model:" in log_content,
        "Contains reason": "Reason:" in log_content,
        "Model switch occurred": (current_or_model.name != initial_or_model.name or 
                                  current_rep_model.name != initial_rep_model.name)
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ TASK 8 TEST PASSED: All requirements verified")
    else:
        print("❌ TASK 8 TEST FAILED: Some requirements not met")
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    try:
        success = test_model_fallback_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
