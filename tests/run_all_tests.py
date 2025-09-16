#!/usr/bin/env python3
"""
Test runner script for Better-Bahn comprehensive testing.

Runs all test categories and provides summary reports.
"""

import unittest
import sys
import os
import subprocess
import time

def run_test_category(category_name, test_file, timeout=60):
    """Run a specific test category and return results."""
    print(f"\n{'='*60}")
    print(f"Running {category_name} Tests")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', test_file, '-v'],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Duration: {duration:.2f}s")
        print(f"Exit code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return {
            'category': category_name,
            'success': result.returncode == 0,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"⚠️ Test category {category_name} timed out after {timeout}s")
        return {
            'category': category_name,
            'success': False,
            'duration': timeout,
            'stdout': '',
            'stderr': f'Timeout after {timeout}s'
        }
    except Exception as e:
        print(f"❌ Error running {category_name}: {e}")
        return {
            'category': category_name,
            'success': False,
            'duration': 0,
            'stdout': '',
            'stderr': str(e)
        }

def main():
    """Run all test categories and provide summary."""
    print("🧪 Better-Bahn Comprehensive Test Suite")
    print("=" * 60)
    
    test_categories = [
        ("Unit Tests - Masterdata Loader", "tests/test_masterdata_loader.py"),
        ("Unit Tests - Realtime Client", "tests/test_realtime_client.py"),
        ("Unit Tests - Merge Logic", "tests/test_merge_logic.py"),
        ("Property-Based Tests", "tests/test_property_based.py"),
        ("Performance Tests", "tests/test_performance.py"),
        ("Manual QA Tests", "tests/test_manual_qa.py"),
    ]
    
    results = []
    
    for category_name, test_file in test_categories:
        if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), test_file)):
            result = run_test_category(category_name, test_file)
            results.append(result)
        else:
            print(f"⚠️ Test file not found: {test_file}")
    
    # Summary Report
    print(f"\n{'='*60}")
    print("TEST SUMMARY REPORT")
    print(f"{'='*60}")
    
    total_duration = sum(r['duration'] for r in results)
    passed_categories = sum(1 for r in results if r['success'])
    total_categories = len(results)
    
    print(f"Total test categories: {total_categories}")
    print(f"Passed: {passed_categories}")
    print(f"Failed: {total_categories - passed_categories}")
    print(f"Total duration: {total_duration:.2f}s")
    print()
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} {result['category']} ({result['duration']:.2f}s)")
        if not result['success'] and result['stderr']:
            print(f"    Error: {result['stderr'][:100]}...")
    
    print(f"\n{'='*60}")
    
    if passed_categories == total_categories:
        print("🎉 All test categories passed!")
        return 0
    else:
        print(f"⚠️ {total_categories - passed_categories} test categories failed")
        return 1

if __name__ == '__main__':
    exit(main())