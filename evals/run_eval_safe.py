#!/usr/bin/env python3
"""
Safe evaluation runner that prevents asyncio recursion issues by using subprocess isolation.
This version is designed to terminate cleanly without the recursion error.
"""

import subprocess
import sys
import os
import time
from datetime import datetime

def run_evaluation_safe(config_path: str) -> bool:
    """Run evaluation in a subprocess to prevent asyncio recursion"""
    print(f"[SAFE] Starting safe evaluation at {datetime.now()}")
    print(f"[SAFE] Config: {config_path}")
    
    if not os.path.exists(config_path):
        print(f"[SAFE] Config file not found: {config_path}")
        return False
    
    start_time = time.time()
    
    try:
        # Run the evaluation framework in a subprocess
        cmd = [sys.executable, "evals/eval_framework.py", config_path]
        print(f"[SAFE] Executing: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=os.getcwd(),
            capture_output=False,  # Let output go to console directly
            timeout=1800,  # 30 minutes timeout
            check=False
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"[SAFE] ✅ Evaluation completed successfully in {duration:.2f} seconds")
            return True
        else:
            print(f"[SAFE] ❌ Evaluation failed with exit code {result.returncode} after {duration:.2f} seconds")
            return False
            
    except subprocess.TimeoutExpired:
        print("[SAFE] ❌ Evaluation timed out after 30 minutes")
        return False
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"[SAFE] ❌ Evaluation failed after {duration:.2f} seconds with error: {e}")
        return False

def main():
    """Main entry point for safe evaluation"""
    if len(sys.argv) < 2:
        print("Usage: python run_eval_safe.py <config_file>")
        print("Example: python run_eval_safe.py evals/test_configs/minigames_comparison.json")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    print("[SAFE] Running evaluation with subprocess isolation to prevent asyncio recursion...")
    
    try:
        success = run_evaluation_safe(config_path)
        
        if success:
            print("[SAFE] 🎉 Evaluation completed successfully!")
            sys.exit(0)
        else:
            print("[SAFE] 💥 Evaluation failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n[SAFE] Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[SAFE] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 