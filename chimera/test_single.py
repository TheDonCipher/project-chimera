#!/usr/bin/env python3
"""Run a single test"""
import sys
import os
os.chdir(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))
from test_integration import test_daily_volume_limit_enforcement

if __name__ == '__main__':
    result = test_daily_volume_limit_enforcement()
    sys.exit(0 if result else 1)
