#!/usr/bin/env python3
"""
Comprehensive test runner for ChromaDB Vector Database Integration

This script runs all unit tests with detailed reporting and coverage analysis.
"""
import sys
import os
import unittest
import time
from io import StringIO

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_test_module(module_name, test_class_name):
    """Run tests for a specific module and return results"""
    print(f"\n{'='*60}")
    print(f"Running tests for {module_name}")
    print(f"{'='*60}")
    
    # Import the test module
    try:
        module = __import__(f"ChromaDB.tests.{module_name}", fromlist=[test_class_name])
        test_class = getattr(module, test_class_name)
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return False, 0, 0
    except AttributeError as e:
        print(f"❌ Failed to find test class {test_class_name}: {e}")
        return False, 0, 0
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    
    # Run tests with detailed output
    stream = StringIO()
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=2,
        buffer=True
    )
    
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Print results
    output = stream.getvalue()
    print(output)
    
    # Summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    success = total_tests - failures - errors - skipped
    
    print(f"\n📊 {module_name} Results:")
    print(f"   ✅ Passed: {success}")
    print(f"   ❌ Failed: {failures}")
    print(f"   💥 Errors: {errors}")
    print(f"   ⏭️  Skipped: {skipped}")
    print(f"   ⏱️  Time: {end_time - start_time:.2f}s")
    
    # Print failure details
    if result.failures:
        print(f"\n❌ Failures in {module_name}:")
        for test, traceback in result.failures:
            # Extract meaningful error message
            if 'AssertionError:' in traceback:
                error_msg = traceback.split('AssertionError:')[-1].strip()
            else:
                error_msg = traceback.split('\n')[-1] if traceback.split('\n') else traceback
            print(f"   • {test}: {error_msg}")
    
    if result.errors:
        print(f"\n💥 Errors in {module_name}:")
        for test, traceback in result.errors:
            # Extract meaningful error message from traceback
            traceback_lines = traceback.split('\n')
            if len(traceback_lines) >= 2:
                error_msg = traceback_lines[-2].strip()
            elif len(traceback_lines) >= 1:
                error_msg = traceback_lines[-1].strip()
            else:
                error_msg = "Unknown error"
            print(f"   • {test}: {error_msg}")
    
    return result.wasSuccessful(), total_tests, success

def run_integration_tests():
    """Run integration tests that test multiple components together"""
    print(f"\n{'='*60}")
    print("Running Integration Tests")
    print(f"{'='*60}")
    
    # Integration test: Test that all components work together
    try:
        from ChromaDB import GameDataSearchInterface, ChromaDBManager
        from ChromaDB.feature_embeddings_generator import FeatureEmbeddingsGenerator
        from ChromaDB.screenshot_embeddings_generator import ScreenshotEmbeddingsGenerator
        
        print("✅ All modules import successfully")
        
        # Test that classes can be instantiated (with mocking)
        from unittest.mock import patch, MagicMock
        
        # Mock environment variables properly
        env_vars = {
            'PG_USER': 'test_user',
            'PG_PASSWORD': 'test_password', 
            'PG_HOST': 'localhost',
            'PG_PORT': '5432',
            'PG_DATABASE': 'test_db',
            'OPENAI_API_KEY': 'test_openai_key'
        }
        
        # Test FeatureEmbeddingsGenerator
        with patch('ChromaDB.database_connection.pg8000.dbapi.connect'):
            with patch('ChromaDB.database_connection.load_dotenv'):
                with patch('ChromaDB.database_connection.os.getenv') as mock_db_getenv:
                    with patch('ChromaDB.feature_embeddings_generator.OpenAI'):
                        with patch('ChromaDB.feature_embeddings_generator.os.getenv') as mock_openai_getenv:
                            mock_db_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)
                            mock_openai_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)
                            generator = FeatureEmbeddingsGenerator()
                            print("✅ FeatureEmbeddingsGenerator can be instantiated")
        
        # Test ScreenshotEmbeddingsGenerator  
        with patch('ChromaDB.database_connection.pg8000.dbapi.connect'):
            with patch('ChromaDB.database_connection.load_dotenv'):
                with patch('ChromaDB.database_connection.os.getenv') as mock_db_getenv:
                    with patch('ChromaDB.screenshot_embeddings_generator.OpenAI'):
                        with patch('ChromaDB.screenshot_embeddings_generator.os.getenv') as mock_openai_getenv:
                            mock_db_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)
                            mock_openai_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)
                            generator = ScreenshotEmbeddingsGenerator()
                            print("✅ ScreenshotEmbeddingsGenerator can be instantiated")
        
        # Test ChromaDBManager
        with patch('ChromaDB.chromadb_manager.chromadb.PersistentClient'):
            manager = ChromaDBManager(use_openai_embeddings=False)
            print("✅ ChromaDBManager can be instantiated")
        
        # Test GameDataSearchInterface
        with patch('ChromaDB.vector_search_interface.ChromaDBManager'):
            interface = GameDataSearchInterface()
            print("✅ GameDataSearchInterface can be instantiated")
        
        # Test basic method calls work
        with patch('ChromaDB.vector_search_interface.ChromaDBManager') as mock_manager:
            mock_vector_db = MagicMock()
            mock_manager.return_value = mock_vector_db
            mock_vector_db.search_features.return_value = []
            mock_vector_db.search_screenshots.return_value = []
            mock_vector_db.get_database_info.return_value = {'database_path': '/test', 'collections': []}
            
            interface = GameDataSearchInterface()
            
            # Test search methods work
            results = interface.search_game_features("test query")
            assert isinstance(results, list), "search_game_features should return a list"
            
            results = interface.search_game_screenshots("test query")
            assert isinstance(results, list), "search_game_screenshots should return a list"
            
            results = interface.search_all_game_content("test query")
            assert isinstance(results, dict), "search_all_game_content should return a dict"
            assert 'features' in results and 'screenshots' in results, "Result should have features and screenshots keys"
            
            stats = interface.get_database_stats()
            assert isinstance(stats, dict), "get_database_stats should return a dict"
            
            print("✅ All search interface methods work correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test runner function"""
    print("🧪 ChromaDB Vector Database Integration - Unit Test Suite")
    print("=" * 60)
    
    start_time = time.time()
    
    # Define test modules to run
    test_modules = [
        ("test_database_connection", "TestDatabaseConnection"),
        ("test_feature_embeddings_generator", "TestFeatureEmbeddingsGenerator"),
        ("test_screenshot_embeddings_generator", "TestScreenshotEmbeddingsGenerator"),
        ("test_chromadb_manager", "TestChromaDBManager"),
        ("test_vector_search_interface", "TestGameDataSearchInterface"),
    ]
    
    # Track overall results
    total_modules = len(test_modules)
    successful_modules = 0
    total_tests_run = 0
    total_tests_passed = 0
    
    # Run each test module
    for module_name, class_name in test_modules:
        success, tests_run, tests_passed = run_test_module(module_name, class_name)
        
        if success:
            successful_modules += 1
        
        total_tests_run += tests_run
        total_tests_passed += tests_passed
    
    # Run integration tests
    print(f"\n{'='*60}")
    integration_success = run_integration_tests()
    if integration_success:
        print("✅ Integration tests passed")
    else:
        print("❌ Integration tests failed")
    
    # Overall summary
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n{'🎯 OVERALL TEST RESULTS':=^60}")
    print(f"Modules tested: {successful_modules}/{total_modules}")
    print(f"Tests run: {total_tests_run}")
    print(f"Tests passed: {total_tests_passed}")
    print(f"Success rate: {(total_tests_passed/total_tests_run)*100:.1f}%" if total_tests_run > 0 else "No tests run")
    print(f"Total time: {total_time:.2f}s")
    print(f"Integration tests: {'✅ Passed' if integration_success else '❌ Failed'}")
    
    # Determine overall success
    all_unit_tests_passed = successful_modules == total_modules
    overall_success = all_unit_tests_passed and integration_success
    
    if overall_success:
        print(f"\n🎉 ALL TESTS PASSED! 🎉")
        print("The ChromaDB integration is ready for use.")
    else:
        print(f"\n⚠️ SOME TESTS FAILED")
        if not all_unit_tests_passed:
            print(f"   • {total_modules - successful_modules} unit test modules failed")
        if not integration_success:
            print("   • Integration tests failed")
        print("Please review the failures above before using the system.")
    
    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)

def run_specific_test(test_name):
    """Run a specific test module"""
    test_mapping = {
        'db': ("test_database_connection", "TestDatabaseConnection"),
        'features': ("test_feature_embeddings_generator", "TestFeatureEmbeddingsGenerator"),
        'screenshots': ("test_screenshot_embeddings_generator", "TestScreenshotEmbeddingsGenerator"),
        'chromadb': ("test_chromadb_manager", "TestChromaDBManager"),
        'interface': ("test_vector_search_interface", "TestGameDataSearchInterface"),
    }
    
    if test_name in test_mapping:
        module_name, class_name = test_mapping[test_name]
        success, tests_run, tests_passed = run_test_module(module_name, class_name)
        
        if success:
            print(f"\n✅ {test_name} tests passed!")
        else:
            print(f"\n❌ {test_name} tests failed!")
            
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown test: {test_name}")
        print(f"Available tests: {', '.join(test_mapping.keys())}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run ChromaDB unit tests")
    parser.add_argument("--test", "-t", help="Run specific test module", 
                       choices=['db', 'features', 'screenshots', 'chromadb', 'interface'])
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.test:
        run_specific_test(args.test)
    else:
        main() 