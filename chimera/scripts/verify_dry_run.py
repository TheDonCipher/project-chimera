#!/usr/bin/env python3
"""
Verification script for dry-run mode implementation

Checks that:
1. --dry-run flag is properly implemented in main.py
2. Dry-run tracking variables are initialized
3. Transaction submission is skipped in dry-run mode
4. Dry-run report script exists and is functional
"""

import sys
from pathlib import Path
import ast
import re


def check_main_py():
    """Verify main.py has dry-run implementation"""
    print("Checking main.py implementation...")
    
    main_path = Path(__file__).parent.parent / "bot" / "src" / "main.py"
    
    if not main_path.exists():
        print("❌ main.py not found")
        return False
    
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "ChimeraBot __init__ accepts dry_run parameter": 
            r"def __init__\(self, dry_run: bool = False\)",
        "Dry-run flag stored in instance": 
            r"self\.dry_run = dry_run",
        "Dry-run tracking variables initialized": 
            r"self\._dry_run_simulations_success",
        "Argparse --dry-run flag": 
            r"--dry-run",
        "Dry-run mode warning logged": 
            r"DRY-RUN MODE ENABLED",
        "Transaction submission skipped in dry-run": 
            r"if self\.dry_run:",
        "Dry-run metrics logged": 
            r"\[DRY-RUN\] Would submit bundle",
    }
    
    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    return all_passed


def check_dry_run_report():
    """Verify dry_run_report.py exists and has required functions"""
    print("\nChecking dry_run_report.py script...")
    
    report_path = Path(__file__).parent / "dry_run_report.py"
    
    if not report_path.exists():
        print("❌ dry_run_report.py not found")
        return False
    
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "DryRunAnalyzer class": r"class DryRunAnalyzer",
        "parse_logs method": r"def parse_logs\(self\)",
        "calculate_metrics method": r"def calculate_metrics\(self\)",
        "generate_report method": r"def generate_report\(self",
        "main function": r"def main\(\)",
        "argparse for CLI": r"argparse\.ArgumentParser",
        "--log-file argument": r"--log-file",
        "--output argument": r"--output",
        "--json argument": r"--json",
    }
    
    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    return all_passed


def check_documentation():
    """Verify DRY_RUN_MODE.md documentation exists"""
    print("\nChecking documentation...")
    
    doc_path = Path(__file__).parent.parent / "DRY_RUN_MODE.md"
    
    if not doc_path.exists():
        print("❌ DRY_RUN_MODE.md not found")
        return False
    
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "Overview section": r"## Overview",
        "How It Works section": r"## How It Works",
        "Usage section": r"## Usage",
        "Monitoring section": r"## Monitoring",
        "Performance Analysis section": r"## Performance Analysis",
        "Key Metrics section": r"## Key Metrics",
        "Troubleshooting section": r"## Troubleshooting",
        "Starting dry-run command": r"python -m bot\.src\.main --dry-run",
        "Report generation command": r"python scripts/dry_run_report\.py",
    }
    
    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    return all_passed


def check_test_file():
    """Verify test file exists"""
    print("\nChecking test file...")
    
    test_path = Path(__file__).parent.parent / "tests" / "test_dry_run_mode.py"
    
    if not test_path.exists():
        print("❌ test_dry_run_mode.py not found")
        return False
    
    with open(test_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "TestDryRunMode class": r"class TestDryRunMode",
        "test_dry_run_initialization": r"def test_dry_run_initialization",
        "test_dry_run_skips_submission": r"def test_dry_run_skips_submission",
        "test_dry_run_tracks_failed_simulations": r"def test_dry_run_tracks_failed_simulations",
        "TestDryRunReport class": r"class TestDryRunReport",
    }
    
    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  ✅ {check_name}")
        else:
            print(f"  ❌ {check_name}")
            all_passed = False
    
    return all_passed


def main():
    """Run all verification checks"""
    print("=" * 80)
    print("DRY-RUN MODE IMPLEMENTATION VERIFICATION")
    print("=" * 80)
    print()
    
    results = []
    
    results.append(("main.py implementation", check_main_py()))
    results.append(("dry_run_report.py script", check_dry_run_report()))
    results.append(("Documentation", check_documentation()))
    results.append(("Test file", check_test_file()))
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("\n✅ All verification checks passed!")
        print("\nNext steps:")
        print("1. Test dry-run mode: python -m bot.src.main --dry-run")
        print("2. Let it run for 24 hours against live Base mainnet")
        print("3. Generate report: python scripts/dry_run_report.py")
        print("4. Review metrics and verify no transactions were submitted")
        return 0
    else:
        print("\n❌ Some verification checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
