#!/usr/bin/env python3
"""
Simple test script to verify the evaluation framework properly terminates.
This can be used to test if the framework hangs or exits cleanly.
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add parent directory to path to import eval_framework
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.eval_framework import EvalFramework

async def test_termination():
    """Test that the evaluation framework terminates properly"""
    start_time = time.time()
    print(f"[TEST] Starting termination test at {datetime.now()}")
    
    try:
        # Use the minigames comparison config
        config_path = "evals/test_configs/minigames_comparison.json"
        
        if not os.path.exists(config_path):
            print(f"[TEST] Config file not found: {config_path}")
            return False
        
        framework = EvalFramework(config_path)
        
        # Run a single evaluation
        await framework.run_all_evaluations()
        
        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"evals/reports/test_termination_{timestamp}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        framework.generate_report(report_path)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"[TEST] Evaluation completed successfully in {duration:.2f} seconds")
        print(f"[TEST] Report saved to: {report_path}")
        
        return True
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"[TEST] Evaluation failed after {duration:.2f} seconds with error: {e}")
        return False

def main():
    """Main entry point for termination test"""
    print("[TEST] Testing evaluation framework termination...")
    
    try:
        result = asyncio.run(test_termination())
        
        if result:
            print("[TEST] ✅ Framework terminated properly!")
            sys.exit(0)
        else:
            print("[TEST] ❌ Framework test failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n[TEST] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[TEST] Test failed with unexpected error: {e}")
        sys.exit(1)
    finally:
        print("[TEST] Termination test complete, exiting...")

if __name__ == "__main__":
    main() 