#!/usr/bin/env python3
"""
Test Data Cleanup Script

This script provides comprehensive cleanup of test data, temporary files,
and comparison results to ensure fresh test runs.

Usage:
    python scripts/clean_test_data.py                    # Clean everything
    python scripts/clean_test_data.py --baseline-only    # Clean only for baseline generation
    python scripts/clean_test_data.py --temp-only        # Clean only temp directory
    python scripts/clean_test_data.py --dry-run          # Show what would be cleaned
"""

import argparse
import sys
import os

# Add project root to path so we can import test utilities
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tests.utils import cleanup_utils


def main():
    parser = argparse.ArgumentParser(
        description="Clean test data and temporary files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/clean_test_data.py                    # Clean all test data
  python scripts/clean_test_data.py --baseline-only    # Clean for baseline generation
  python scripts/clean_test_data.py --temp-only        # Clean only temp files
  python scripts/clean_test_data.py --dry-run          # Show what would be cleaned
        """
    )
    
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Clean only files needed for fresh baseline generation (preserves existing baselines)"
    )
    
    parser.add_argument(
        "--temp-only",
        action="store_true",
        help="Clean only the tests/temp directory"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually cleaning"
    )
    
    args = parser.parse_args()
    
    print("🧹 Test Data Cleanup Script")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will actually be deleted")
        print("")
    
    try:
        if args.temp_only:
            print("📁 Cleaning temp directory only...")
            if args.dry_run:
                temp_dir = "tests/temp"
                if os.path.exists(temp_dir):
                    items = os.listdir(temp_dir)
                    print(f"Would clean {len(items)} items from {temp_dir}:")
                    for item in items:
                        print(f"  - {item}")
                else:
                    print(f"  - {temp_dir} doesn't exist")
            else:
                success, items = cleanup_utils.clean_temp_directory()
                if success:
                    print(f"✅ Cleaned {len(items)} items")
                    for item in items:
                        print(f"  - {item}")
                else:
                    print("❌ Failed to clean temp directory")
                    return 1
                    
        elif args.baseline_only:
            print("🎯 Cleaning for baseline generation...")
            if args.dry_run:
                print("Would clean:")
                print("  - tests/temp/ directory")
                print("  - tests/fixtures/expected_outputs/golden_files/comparison/")
                print("  - pytest cache files")
            else:
                success, items = cleanup_utils.clean_for_baseline_generation()
                if success:
                    print(f"✅ Baseline cleanup completed ({len(items)} items)")
                else:
                    print("❌ Baseline cleanup failed")
                    return 1
                    
        else:
            print("🧽 Comprehensive cleanup...")
            if args.dry_run:
                print("Would clean:")
                print("  - tests/temp/ directory")
                print("  - tests/fixtures/expected_outputs/golden_files/comparison/")
                print("  - pytest cache files")
                print("  - Python __pycache__ directories")
            else:
                success, items = cleanup_utils.clean_all_test_data()
                if success:
                    print(f"✅ Comprehensive cleanup completed ({len(items)} items)")
                else:
                    print("❌ Comprehensive cleanup failed")
                    return 1
        
        if not args.dry_run:
            print("")
            print("🎉 Cleanup completed successfully!")
            print("Ready for fresh test runs.")
        else:
            print("")
            print("🔍 Dry run completed. Use without --dry-run to actually clean files.")
        
        return 0
        
    except Exception as e:
        print(f"💥 Error during cleanup: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())