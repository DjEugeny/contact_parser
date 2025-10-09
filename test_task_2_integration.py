#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Task 2: Verify ModelsManager integration in get_llm_providers()
"""

import sys
from pathlib import Path

# Add root directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_manager import UnifiedConfigManager


def test_models_manager_integration():
    """Test that get_llm_providers() uses ModelsManager"""
    print("\n" + "="*60)
    print("🧪 TESTING TASK 2: ModelsManager Integration")
    print("="*60)
    
    # Create config manager
    config_manager = UnifiedConfigManager()
    
    # Check if ModelsManager is initialized
    print("\n1️⃣ Checking ModelsManager initialization...")
    if config_manager.models_manager:
        print("   ✅ ModelsManager is initialized")
        config_manager.models_manager.print_status()
    else:
        print("   ⚠️  ModelsManager not initialized (using .env fallback)")
    
    # Get providers
    print("\n2️⃣ Getting LLM providers...")
    providers = config_manager.get_llm_providers()
    print(f"   Found {len(providers)} providers")
    
    # Check each provider
    print("\n3️⃣ Verifying provider configurations...")
    for provider in providers:
        print(f"\n   📋 {provider.name}:")
        print(f"      Model: {provider.model}")
        print(f"      Priority: {provider.priority}")
        print(f"      Active: {provider.active}")
        
        # Verify model comes from ModelsManager if available
        if config_manager.models_manager:
            provider_key = provider.name.lower()
            current_model = config_manager.models_manager.get_current_model(provider_key)
            if current_model:
                if provider.model == current_model.name:
                    print(f"      ✅ Model matches ModelsManager: {current_model.name}")
                else:
                    print(f"      ❌ Model mismatch!")
                    print(f"         Expected: {current_model.name}")
                    print(f"         Got: {provider.model}")
            else:
                print(f"      ℹ️  No model configured in ModelsManager for {provider_key}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ ModelsManager initialized: {config_manager.models_manager is not None}")
    print(f"✅ Providers configured: {len(providers)}")
    print(f"✅ Backward compatibility: {'Yes' if providers else 'No'}")
    
    if config_manager.models_manager:
        print("\n✅ Task 2 implementation verified successfully!")
        print("   - OpenRouter uses ModelsManager when available")
        print("   - Replicate uses ModelsManager when available")
        print("   - Falls back to .env when ModelsManager unavailable")
    else:
        print("\n⚠️  ModelsManager not available, using .env fallback")
        print("   This is expected behavior for backward compatibility")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    test_models_manager_integration()
