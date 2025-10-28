#!/usr/bin/env python3
"""Fix Unicode characters in test files for Windows compatibility"""

import sys

def fix_unicode_in_file(filepath):
    """Replace Unicode characters with ASCII equivalents"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace Unicode characters
    replacements = {
        '→': '->',
        '✓': '[OK]',
        '✗': '[FAIL]',
        '═': '=',
        '─': '-'
    }
    
    for unicode_char, ascii_char in replacements.items():
        content = content.replace(unicode_char, ascii_char)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed Unicode characters in {filepath}")

if __name__ == '__main__':
    import os
    os.chdir(os.path.dirname(__file__))
    fix_unicode_in_file('bot/test_integration.py')
