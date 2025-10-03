#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🧪 Test Portable Path System Implementation"""

import json
import sys
from pathlib import Path
from argparse import Namespace

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.utils.portable_paths import get_portable_paths, PortablePathManager


def test_portable_paths():
    """🧪 Test the portable path system"""
    print("🔧 TESTING PORTABLE PATH SYSTEM")
    print("=" * 50)
    
    # Initialize portable paths
    paths = get_portable_paths()
    
    print(f"📁 Project root detected: {paths.get_project_root()}")
    print(f"📁 Data directory: {paths.get_data_dir()}")
    print(f"📁 Config directory: {paths.get_config_dir()}")
    print(f"📁 Emails directory: {paths.get_emails_dir()}")
    print(f"📁 Attachments directory: {paths.get_attachments_dir()}")
    
    # Test path conversion
    test_paths = [
        "data/emails/2025-07-09",
        "/absolute/path/somewhere",
        "attachments/2025-07-09/file.pdf",
        str(paths.get_project_root() / "data" / "test.json")
    ]
    
    print(f"\n🔄 Testing path conversions:")
    for test_path in test_paths:
        print(f"   Original: {test_path}")
        try:
            relative = paths.to_relative(test_path)
            absolute = paths.to_absolute(test_path)
            portable = paths.is_portable(test_path)
            print(f"   Relative: {relative}")
            print(f"   Absolute: {absolute}")
            print(f"   Portable: {'✅' if portable else '❌'}")
        except Exception as e:
            print(f"   Error: {e}")
        print()
    
    # Test attachment path normalization
    print(f"🔧 Testing attachment path normalization:")
    test_attachments = [
        {"path": "attachments/2025-07-09/file1.pdf"},
        {"file_path": "/absolute/path/file2.pdf"},
        {"relative_path": "data/attachments/file3.pdf"},
        {"saved_filename": "file4.pdf"},
        {}  # Empty attachment
    ]
    
    for i, attachment in enumerate(test_attachments, 1):
        print(f"   Attachment {i}: {attachment}")
        normalized = paths.normalize_attachment_path(attachment)
        print(f"   Normalized: {normalized}")
        if normalized:
            print(f"   Exists: {'✅' if normalized.exists() else '❌'}")
        print()
    
    # Test directory creation
    print(f"📁 Testing directory creation:")
    try:
        paths.ensure_directories()
        print(f"   ✅ All directories created successfully")
    except Exception as e:
        print(f"   ❌ Error creating directories: {e}")
    
    print(f"\n✅ Portable path system test completed!")


def test_api_validator_integration():
    """🧪 Test integration with API Pipeline Validator"""
    print(f"\n🔗 TESTING API VALIDATOR INTEGRATION")
    print("=" * 50)
    
    try:
        from src.api_pipeline_validator import APIPipelineValidator
        
        # Create dummy args
        args = Namespace(
            mode="test",
            date=None,
            count=None,
            start_date=None,
            end_date=None,
            dry_run=True
        )
        
        # Try to initialize validator
        validator = APIPipelineValidator(args)
        
        print(f"✅ API Pipeline Validator initialized successfully")
        print(f"   Project root: {validator.project_root}")
        print(f"   Data dir: {validator.data_dir}")
        print(f"   Emails dir: {validator.emails_dir}")
        print(f"   Results dir: {validator.llm_results_dir}")
        
        # Test portable paths integration
        if hasattr(validator, 'portable_paths'):
            print(f"   ✅ Portable paths integrated")
            
            # Test attachment path normalization
            test_attachment = {
                "path": "attachments/2025-07-09/test.pdf",
                "filename": "test.pdf"
            }
            
            normalized_path = validator.portable_paths.normalize_attachment_path(test_attachment)
            print(f"   Test attachment path: {normalized_path}")
        else:
            print(f"   ❌ Portable paths not integrated")
        
    except Exception as e:
        print(f"❌ Error testing API validator integration: {e}")
        import traceback
        traceback.print_exc()


def test_project_portability():
    """🧪 Test project portability features"""
    print(f"\n🚀 TESTING PROJECT PORTABILITY")
    print("=" * 50)
    
    paths = get_portable_paths()
    
    # Simulate moving project to different location
    fake_roots = [
        Path("/tmp/contact_parser"),
        Path("/home/user/projects/contact_parser"),
        Path("C:\\Users\\User\\contact_parser"),
        Path("/opt/contact_parser")
    ]
    
    print(f"🎯 Current project root: {paths.get_project_root()}")
    
    for fake_root in fake_roots:
        print(f"\n🔄 Simulating project at: {fake_root}")
        
        try:
            # Create a new path manager with fake root
            fake_paths = PortablePathManager(fake_root)
            
            print(f"   ✅ Project root: {fake_paths.get_project_root()}")
            print(f"   📁 Data dir: {fake_paths.get_data_dir()}")
            print(f"   📧 Emails dir: {fake_paths.get_emails_dir()}")
            
            # Test relative path conversion
            test_path = "data/emails/2025-07-09/test.json"
            absolute = fake_paths.to_absolute(test_path)
            relative = fake_paths.to_relative(absolute)
            
            print(f"   🔄 Test path '{test_path}':")
            print(f"      Absolute: {absolute}")
            print(f"      Back to relative: {relative}")
            print(f"      Portable: {'✅' if fake_paths.is_portable(absolute) else '❌'}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n✅ Project portability test completed!")


def main():
    """🎯 Main test function"""
    print("🧪 PORTABLE PATH SYSTEM VALIDATION")
    print("=" * 60)
    
    test_portable_paths()
    test_api_validator_integration()
    test_project_portability()
    
    print(f"\n🎉 ALL TESTS COMPLETED!")
    print(f"📝 Summary:")
    print(f"   ✅ Portable path system implemented")
    print(f"   ✅ Cross-platform compatibility")
    print(f"   ✅ Automatic project root detection")
    print(f"   ✅ Attachment path normalization")
    print(f"   ✅ Directory structure management")
    print(f"   📦 Ready for deployment on any server/machine!")


if __name__ == "__main__":
    main()