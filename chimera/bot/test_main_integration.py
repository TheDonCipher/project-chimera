"""
Simple integration test for main bot orchestrator.

This test verifies that:
1. The main module can be imported
2. ChimeraBot class can be instantiated
3. Basic structure is correct
"""

import sys
from pathlib import Path

# Add parent directory to path to allow package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_import():
    """Test that main module can be imported"""
    try:
        from bot.src.main import ChimeraBot, main
        print("✓ Main module imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import main module: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bot_instantiation():
    """Test that ChimeraBot can be instantiated"""
    try:
        from bot.src.main import ChimeraBot
        bot = ChimeraBot()
        print("✓ ChimeraBot instantiated successfully")
        
        # Check that bot has required attributes
        assert hasattr(bot, 'logger'), "Bot missing logger attribute"
        assert hasattr(bot, 'initialize'), "Bot missing initialize method"
        assert hasattr(bot, 'start'), "Bot missing start method"
        assert hasattr(bot, 'stop'), "Bot missing stop method"
        assert hasattr(bot, 'main_event_loop'), "Bot missing main_event_loop method"
        assert hasattr(bot, 'monitoring_loop'), "Bot missing monitoring_loop method"
        
        print("✓ ChimeraBot has all required methods")
        return True
    except Exception as e:
        print(f"✗ Failed to instantiate ChimeraBot: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_module_structure():
    """Test that all required modules can be imported"""
    try:
        from bot.src.config import get_config
        from bot.src.database import init_database, init_redis
        from bot.src.state_engine import StateEngine
        from bot.src.opportunity_detector import OpportunityDetector
        from bot.src.execution_planner import ExecutionPlanner
        from bot.src.safety_controller import SafetyController
        from bot.src.types import SystemState, ChimeraError
        
        print("✓ All required modules can be imported")
        return True
    except Exception as e:
        print(f"✗ Failed to import required modules: {e}")
        import traceback
        traceback.print_exc()
        return False

def main_test():
    """Run all tests"""
    print("=" * 60)
    print("Testing Main Bot Orchestrator Integration")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_import),
        ("Module Structure Test", test_module_structure),
        ("Bot Instantiation Test", test_bot_instantiation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 60)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main_test())
