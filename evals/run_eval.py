#!/usr/bin/env python3
"""
Runner script for the evaluation framework.
Makes it easy to run evaluations with different test configurations.
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import eval_framework
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval_framework import EvalFramework

def main():
    """Main entry point for the evaluation runner."""
    parser = argparse.ArgumentParser(
        description='Run automated evaluations on agent variants',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_eval.py minigames                    # Run minigames test with default config
  python run_eval.py minigames --runs 5          # Run minigames test with 5 runs per variant
  python run_eval.py custom_config.json          # Run with custom configuration file
  python run_eval.py minigames --output my_test  # Run with custom output name
        """
    )
    
    parser.add_argument(
        'config',
        help='Test configuration name (without .json) or path to config file'
    )
    
    parser.add_argument(
        '--runs', '-r',
        type=int,
        help='Number of runs per variant (overrides config file setting)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Custom output file name (without extension)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Determine config file path
    if args.config.endswith('.json'):
        config_path = args.config
    else:
        config_path = f"evals/test_configs/{args.config}.json"
    
    # Check if config file exists
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}")
        print("\nAvailable configurations:")
        config_dir = "evals/test_configs"
        if os.path.exists(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith('.json'):
                    print(f"  - {file[:-5]}")  # Remove .json extension
        else:
            print("  No configurations found")
        sys.exit(1)
    
    print(f"Running evaluation with config: {config_path}")
    
    # Run the evaluation with proper cleanup
    success = False
    try:
        asyncio.run(run_evaluation(config_path, args))
        success = True
    finally:
        # Force cleanup of any remaining event loop resources
        try:
            # Try to get the event loop in different ways
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None
            
            if loop and not loop.is_closed():
                # Cancel all tasks
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                except RuntimeError:
                    pass  # Tasks might be from a different loop
                
                # Close the loop
                try:
                    loop.close()
                except RuntimeError:
                    pass  # Loop might already be closed
        except:
            pass  # Ignore all cleanup errors
        
        # Force exit only on successful completion to ensure process terminates
        if success:
            os._exit(0)

async def run_evaluation(config_path: str, args):
    """Run the evaluation with the given configuration."""
    try:
        # Initialize framework
        framework = EvalFramework(config_path)
        
        # Override runs_per_variant if specified
        if args.runs:
            framework.config['runs_per_variant'] = args.runs
            print(f"Overriding runs per variant to: {args.runs}")
        
        if args.verbose:
            print(f"Configuration loaded:")
            print(f"  - Test suite: {framework.config['name']}")
            print(f"  - Number of tests: {len(framework.config['tests'])}")
            print(f"  - Number of variants: {len(framework.config['variants'])}")
            print(f"  - Runs per variant: {framework.config.get('runs_per_variant', 3)}")
        
        # Run evaluations
        await framework.run_all_evaluations()
        
        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.output:
            report_name = f"{args.output}_{timestamp}"
        else:
            config_name = Path(config_path).stem
            report_name = f"eval_report_{config_name}_{timestamp}"
        
        report_path = f"evals/reports/{report_name}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        framework.generate_report(report_path)
        
        print(f"\n✅ Evaluation completed successfully!")
        print(f"📊 Reports saved in: evals/reports/")
        
    except Exception as e:
        print(f"\n❌ Evaluation failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Cleanup: Cancel any remaining tasks and close connections
        try:
            # Get the current event loop
            loop = asyncio.get_event_loop()
            
            # Cancel all pending tasks
            pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
            if pending_tasks:
                print(f"[CLEANUP] Cancelling {len(pending_tasks)} pending tasks...")
                for task in pending_tasks:
                    task.cancel()
                
                # Wait for tasks to be cancelled
                await asyncio.gather(*pending_tasks, return_exceptions=True)
            
            # Give a moment for connections to close properly
            await asyncio.sleep(0.1)
            
        except Exception as cleanup_error:
            if args.verbose:
                print(f"[CLEANUP] Warning: Cleanup error: {cleanup_error}")
            pass

if __name__ == "__main__":
    main() 