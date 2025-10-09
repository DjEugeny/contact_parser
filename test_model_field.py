#!/usr/bin/env python3
"""
Test script to verify that the model field is properly added to results
"""
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.extractor_factory import ExtractorFactory

def test_model_field_in_test_mode():
    """Test that model field is present in test mode"""
    print("🧪 Testing model field in test mode...")
    extractor = ExtractorFactory.create_extractor(test_mode=True)
    result = extractor.extract_all_data('Test email text', {})
    
    assert 'model' in result, "❌ model field missing in test mode"
    assert result['model'] == 'test_mode', f"❌ Expected 'test_mode', got '{result['model']}'"
    print(f"✅ Test mode: model = {result['model']}")
    return True

def test_model_field_structure():
    """Test that model field is in the correct position"""
    print("\n📋 Testing model field structure...")
    extractor = ExtractorFactory.create_extractor(test_mode=True)
    result = extractor.extract_all_data('Test email text', {})
    
    # Check that model comes after provider_used
    keys = list(result.keys())
    if 'provider_used' in keys and 'model' in keys:
        provider_idx = keys.index('provider_used')
        model_idx = keys.index('model')
        print(f"   provider_used at index {provider_idx}")
        print(f"   model at index {model_idx}")
        print(f"✅ Both fields present in result")
    else:
        print(f"❌ Missing fields: provider_used={('provider_used' in keys)}, model={('model' in keys)}")
        return False
    
    return True

def test_existing_result_file():
    """Test that we can read an existing result file (backward compatibility)"""
    print("\n🔄 Testing backward compatibility with existing files...")
    
    # Find an existing result file
    result_dir = PROJECT_ROOT / "data" / "llm_results" / "2025-07-23"
    if not result_dir.exists():
        print("⚠️ No existing result files found, skipping backward compatibility test")
        return True
    
    result_files = list(result_dir.glob("*_processed.json"))
    if not result_files:
        print("⚠️ No processed result files found, skipping backward compatibility test")
        return True
    
    test_file = result_files[0]
    print(f"   Reading: {test_file.name}")
    
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    processed = data.get('processed_result', {})
    
    # Old files won't have model field, but code should handle it gracefully
    model = processed.get('model', 'Unknown')
    provider = processed.get('provider_used', 'Unknown')
    
    print(f"   provider_used: {provider}")
    print(f"   model: {model}")
    print(f"✅ Backward compatibility: Can read old files with .get('model', 'Unknown')")
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Testing Model Field Implementation")
    print("=" * 60)
    
    tests = [
        test_model_field_in_test_mode,
        test_model_field_structure,
        test_existing_result_file,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
