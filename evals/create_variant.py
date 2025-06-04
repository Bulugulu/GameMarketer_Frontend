#!/usr/bin/env python3
"""
Utility script to help create new system prompt variants.
"""

import os
import sys
import argparse
from datetime import datetime

def create_variant_from_baseline(variant_name: str, description: str = ""):
    """Create a new variant by copying the baseline prompt."""
    baseline_path = "evals/baseline_prompt.txt"
    variant_path = f"evals/prompts/{variant_name}.txt"
    
    # Create prompts directory if it doesn't exist
    os.makedirs("evals/prompts", exist_ok=True)
    
    # Check if baseline exists
    if not os.path.exists(baseline_path):
        print(f"Error: Baseline prompt not found at {baseline_path}")
        return False
    
    # Check if variant already exists
    if os.path.exists(variant_path):
        response = input(f"Variant '{variant_name}' already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    # Copy baseline to new variant
    with open(baseline_path, 'r') as f:
        baseline_content = f.read()
    
    # Add header comment
    header = f"""// System Prompt Variant: {variant_name}
// Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
// Description: {description}
// 
// Instructions: Modify this prompt as needed for your variant.
// Remove this header comment when done.

"""
    
    with open(variant_path, 'w') as f:
        f.write(header + baseline_content)
    
    print(f"✅ Created new variant: {variant_path}")
    print(f"📝 Edit the file to make your changes")
    return True

def create_test_config(config_name: str, variant_name: str, description: str = ""):
    """Create a new test configuration that includes the variant."""
    config_path = f"evals/test_configs/{config_name}.json"
    
    # Create test_configs directory if it doesn't exist
    os.makedirs("evals/test_configs", exist_ok=True)
    
    # Check if config already exists
    if os.path.exists(config_path):
        response = input(f"Config '{config_name}' already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    # Create config template
    config_content = f'''{{
  "name": "{config_name.title()} Test Suite",
  "description": "{description}",
  "runs_per_variant": 3,
  "tests": [
    {{
      "name": "example_test",
      "description": "Example test - modify as needed",
      "steps": [
        "hi",
        "your test question here"
      ],
      "correct_features": [
        "feature-id-here"
      ],
      "expected_behaviors": {{
        "should_produce_screenshots": true,
        "min_relevance_score": 0.6
      }}
    }}
  ],
  "variants": [
    {{
      "name": "baseline",
      "path": "evals/baseline_prompt.txt",
      "description": "The current production system prompt"
    }},
    {{
      "name": "{variant_name}",
      "path": "evals/prompts/{variant_name}.txt",
      "description": "{description}"
    }}
  ]
}}'''
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Created test config: {config_path}")
    print(f"📝 Edit the file to customize your tests")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create new system prompt variants and test configurations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_variant.py my_variant                              # Create variant only
  python create_variant.py my_variant --config my_test            # Create variant + test config
  python create_variant.py my_variant --desc "Improved prompting" # Add description
        """
    )
    
    parser.add_argument(
        'variant_name',
        help='Name for the new variant (will create prompts/VARIANT_NAME.txt)'
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Also create a test configuration with this name'
    )
    
    parser.add_argument(
        '--description', '--desc', '-d',
        default="",
        help='Description of the variant/test'
    )
    
    args = parser.parse_args()
    
    print(f"Creating variant: {args.variant_name}")
    
    # Create the variant
    if not create_variant_from_baseline(args.variant_name, args.description):
        sys.exit(1)
    
    # Create test config if requested
    if args.config:
        print(f"\nCreating test config: {args.config}")
        if not create_test_config(args.config, args.variant_name, args.description):
            sys.exit(1)
    
    print(f"\n🎉 Setup complete!")
    
    if args.config:
        print(f"\nNext steps:")
        print(f"1. Edit evals/prompts/{args.variant_name}.txt to modify the system prompt")
        print(f"2. Edit evals/test_configs/{args.config}.json to customize your tests")
        print(f"3. Run: python run_eval.py {args.config}")
    else:
        print(f"\nNext steps:")
        print(f"1. Edit evals/prompts/{args.variant_name}.txt to modify the system prompt")
        print(f"2. Add the variant to an existing test config or create one with --config")

if __name__ == "__main__":
    main() 