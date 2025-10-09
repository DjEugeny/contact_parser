#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Task 2: Verify ModelsManager logging
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.models_manager import ModelsManager

# Configure logging to see the output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_model_logging():
    """Test that get_current_model logs the model selection"""
    print("\n" + "="*60)
    print("TEST: ModelsManager Logging")
    print("="*60)
    
    # Create manager
    manager = ModelsManager()
    
    print("\n📝 Testing OpenRouter model logging...")
    openrouter_model = manager.get_current_model('openrouter')
    if openrouter_model:
        print(f"✅ OpenRouter model retrieved: {openrouter_model.name}")
        print(f"   Priority: {openrouter_model.priority}")
    else:
        print("❌ No OpenRouter model available")
    
    print("\n📝 Testing Replicate model logging...")
    replicate_model = manager.get_current_model('replicate')
    if replicate_model:
        print(f"✅ Replicate model retrieved: {replicate_model.name}")
        print(f"   Priority: {replicate_model.priority}")
    else:
        print("❌ No Replicate model available")
    
    print("\n📝 Testing multiple calls (should log each time)...")
    for i in range(3):
        print(f"\n   Call {i+1}:")
        manager.get_current_model('openrouter')
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETED")
    print("="*60)
    print("\nExpected behavior:")
    print("- Each call to get_current_model should log with 🎯 emoji")
    print("- Log should include provider, model name, and priority")
    print("- Format: '🎯 ModelsManager: {Provider} использует модель {model} (priority {priority})'")
    print("\n")

if __name__ == "__main__":
    test_model_logging()
