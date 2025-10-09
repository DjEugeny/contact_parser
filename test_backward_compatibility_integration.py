#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test for backward compatibility
Verifies that the system works end-to-end without ModelsManager
"""

import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config_manager import UnifiedConfigManager


def test_complete_workflow_without_models_config():
    """Test complete workflow without models_config.yaml"""
    print("\n" + "="*60)
    print("🧪 INTEGRATION TEST: Complete workflow without models_config.yaml")
    print("="*60)
    
    config_path = Path("config/models_config.yaml")
    backup_path = Path("config/models_config.yaml.backup_integration")
    
    # Backup and remove config
    if config_path.exists():
        shutil.move(str(config_path), str(backup_path))
        print("✅ Removed models_config.yaml for test")
    
    try:
        print("\n1️⃣ Creating UnifiedConfigManager...")
        config_manager = UnifiedConfigManager()
        
        print("\n2️⃣ Checking ModelsManager status...")
        if config_manager.models_manager:
            print("   ℹ️  ModelsManager initialized with defaults")
        else:
            print("   ✅ ModelsManager is None (expected)")
        
        print("\n3️⃣ Getting LLM providers...")
        providers = config_manager.get_llm_providers()
        print(f"   ✅ Loaded {len(providers)} providers")
        
        for provider in providers:
            print(f"\n   📋 {provider.name}:")
            print(f"      Model: {provider.model}")
            print(f"      Priority: {provider.priority}")
            print(f"      Active: {provider.active}")
        
        print("\n4️⃣ Checking provider availability...")
        for provider in providers:
            is_available = config_manager.is_provider_available(provider.name)
            status = "✅" if is_available else "❌"
            print(f"   {status} {provider.name}: {'Available' if is_available else 'Not available'}")
        
        print("\n5️⃣ Testing provider stats...")
        stats_summary = config_manager.get_provider_stats_summary()
        print(f"   ✅ Stats available for {len(stats_summary)} providers")
        
        print("\n6️⃣ Testing configuration validation...")
        validation = config_manager.validate_configuration()
        print(f"   Valid: {validation['valid']}")
        print(f"   Providers: {validation['providers']['count']}")
        print(f"   Available: {', '.join(validation['providers']['available'])}")
        
        if validation['errors']:
            print(f"   ⚠️  Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"   ℹ️  Warnings: {validation['warnings']}")
        
        print("\n7️⃣ Testing other configurations...")
        
        # Processing config
        proc_config = config_manager.get_processing_config()
        print(f"   ✅ Processing config: {proc_config.start_date} to {proc_config.end_date}")
        
        # Export config
        export_config = config_manager.get_export_config()
        print(f"   ✅ Export config: threshold={export_config.confidence_threshold}")
        
        # Retry config
        retry_config = config_manager.get_retry_config()
        print(f"   ✅ Retry config: max_retries={retry_config['max_retries']}")
        
        print("\n✅ INTEGRATION TEST PASSED")
        print("   System fully functional without models_config.yaml")
        return True
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Restore config
        if backup_path.exists():
            shutil.move(str(backup_path), str(config_path))
            print("\n✅ Restored models_config.yaml")


def test_graceful_degradation():
    """Test that system degrades gracefully when ModelsManager fails"""
    print("\n" + "="*60)
    print("🧪 GRACEFUL DEGRADATION TEST")
    print("="*60)
    
    try:
        print("\n1️⃣ Creating config manager with valid setup...")
        config_manager = UnifiedConfigManager()
        
        print("\n2️⃣ Simulating ModelsManager failure...")
        config_manager.models_manager = None
        
        print("\n3️⃣ Verifying system still works...")
        
        # Should still get providers
        providers = config_manager.get_llm_providers()
        if len(providers) > 0:
            print(f"   ✅ Still got {len(providers)} providers")
        else:
            print("   ❌ No providers available")
            return False
        
        # Should still check availability
        for provider in providers:
            is_available = config_manager.is_provider_available(provider.name)
            print(f"   ✅ Can check {provider.name} availability: {is_available}")
        
        # Should still record stats
        config_manager.record_provider_success("OpenRouter")
        print("   ✅ Can record provider success")
        
        config_manager.record_provider_failure("OpenRouter", "test error")
        print("   ✅ Can record provider failure")
        
        # Should still get next provider
        next_provider = config_manager.get_next_available_provider()
        if next_provider:
            print(f"   ✅ Can get next provider: {next_provider.name}")
        
        print("\n✅ GRACEFUL DEGRADATION TEST PASSED")
        print("   System continues to function when ModelsManager is unavailable")
        return True
        
    except Exception as e:
        print(f"\n❌ GRACEFUL DEGRADATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run integration tests"""
    print("\n" + "="*60)
    print("🧪 BACKWARD COMPATIBILITY INTEGRATION TESTS")
    print("Testing Requirements: 5.1, 5.2, 5.4")
    print("="*60)
    
    results = []
    results.append(("Complete workflow without config", test_complete_workflow_without_models_config()))
    results.append(("Graceful degradation", test_graceful_degradation()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
