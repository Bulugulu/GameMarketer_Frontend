# Agent Evaluation System

This automated evaluation system tests different system prompt variants and measures their performance on predefined test cases.

## Overview

The system automatically:
1. Runs the agent with predetermined questions using different system prompt variants
2. Measures various performance metrics (screenshot production, relevance scores, correct feature identification)
3. Produces detailed reports comparing variant performance

## Quick Start

To run the minigames test:

```bash
cd evals
python run_eval.py minigames
```

## File Structure

```
evals/
├── README.md                     # This file
├── eval_framework.py             # Main evaluation framework
├── run_eval.py                   # Easy-to-use runner script
├── baseline_prompt.txt           # Current production system prompt
├── test_configs/                 # Test configuration files
│   └── minigames_test.json      # Minigames test configuration
├── prompts/                      # System prompt variants
└── reports/                      # Generated evaluation reports
```

## Usage

### Basic Usage

```bash
# Run the minigames test with default settings
python run_eval.py minigames

# Run with custom number of iterations
python run_eval.py minigames --runs 5

# Run with verbose output
python run_eval.py minigames --verbose

# Run with custom output name
python run_eval.py minigames --output my_experiment

# Run the ChatGPT scoring test (requires OPENAI_API_KEY)
python run_eval.py chatgpt_scoring_test
```

### Using Custom Configurations

```bash
# Run with a custom config file
python run_eval.py path/to/custom_config.json
```

## Test Configuration Format

Test configurations are JSON files that define:

```json
{
  "name": "Test Suite Name",
  "description": "Description of what this test suite evaluates",
  "runs_per_variant": 3,
  "tests": [
    {
      "name": "test_name",
      "description": "What this specific test does",
      "steps": [
        "First message to send",
        "Second message to send"
      ],
      "correct_features": [
        "feature-id-1",
        "feature-id-2"
      ],
      "expected_behaviors": {
        "should_produce_screenshots": true,
        "min_relevance_score": 0.6,
        "calculate_retrieval_rate": false,
        "use_chatgpt_scoring": false,
        "min_chatgpt_score": 0.7
      }
    }
  ],
  "variants": [
    {
      "name": "variant_name",
      "path": "path/to/prompt.txt",
      "description": "Description of this variant"
    }
  ]
}
```

## Metrics Measured

The system automatically measures:

- **Screenshot Production**: Whether the agent produced screenshots
- **Screenshot Count**: Number of screenshots retrieved
- **Average Relevance Scores**: For both features and screenshots
- **Correct Feature Identification**: How many of the expected features were found
- **Execution Time**: How long each test run took
- **Error Rate**: Percentage of failed runs
- **ChatGPT Relevance Scoring**: AI-powered evaluation of response relevance (optional)

### ChatGPT Scoring Feature

The framework now includes an optional ChatGPT-based scoring system that evaluates how relevant and helpful the agent's responses are to the user's questions. This provides an objective, AI-powered assessment of response quality.

**Key Features:**
- Uses GPT-4 to score responses on a 0.0-1.0 scale
- Provides detailed rationale for each score
- Enforces JSON output format for reliable parsing
- Evaluates responses based on directness, helpfulness, and relevance

**To enable ChatGPT scoring**, add this to your test configuration:

```json
{
  "expected_behaviors": {
    "use_chatgpt_scoring": true,
    "min_chatgpt_score": 0.7
  }
}
```

**Requirements:**
- Set the `OPENAI_API_KEY` environment variable
- Ensure the `openai` Python package is installed

**Sample output:**
```
ChatGPT Scoring Success Rate: 100.00%
Avg ChatGPT Relevance Score: 0.847
```

## Creating New System Prompt Variants

1. Create a new `.txt` file in the `prompts/` directory
2. Add the full system prompt text (without Python code wrapper)
3. Add a variant entry to your test configuration:

```json
{
  "name": "my_new_variant",
  "path": "evals/prompts/my_new_variant.txt",
  "description": "Description of changes made"
}
```

## Report Output

The system generates two types of reports:

### 1. Detailed JSON Report
Contains complete data for all runs, including:
- Individual run results
- Raw agent responses
- Developer notes
- Full configuration

### 2. Summary Text Report
Human-readable summary with:
- Success rates
- Average metrics
- Comparison across variants

## Example Report Output

```
EVALUATION SUMMARY REPORT
==================================================

Evaluation Date: 2024-01-15T10:30:00
Total Variants: 2
Total Tests: 1
Runs per Variant: 3

VARIANT: baseline
----------------------------------------

  Test: minigames_conversation
    Success Rate: 3/3
    Screenshot Production Rate: 100.00%
    Avg Screenshots: 25.3
    Avg Screenshot Relevance: 0.847
    Avg Feature Relevance: 0.923
    Avg Correct Features Found: 1.0
    Avg Execution Time: 12.45s
    ChatGPT Scoring Success Rate: 100.00%
    Avg ChatGPT Relevance Score: 0.847
```

## Adding New Tests

1. Create a new test configuration file in `test_configs/`
2. Define your conversation steps and expected outcomes
3. Run with: `python run_eval.py your_test_name`

## Advanced Features

### Custom Metric Extraction

The framework uses regex patterns to extract metrics from agent responses. You can modify `extract_metrics_from_response()` in `eval_framework.py` to add custom metrics.

### Parallel Execution

The framework runs tests sequentially but could be extended for parallel execution across variants.

### Database Integration

The system works with your existing agent tools and database connections.

## Troubleshooting

### Common Issues

1. **"Configuration file not found"**: Check that your test config exists in `test_configs/`
2. **"Error calling Agents SDK"**: Ensure your OpenAI API key is properly configured
3. **Path errors**: Make sure all prompt file paths in configs are correct

### Debug Mode

Run with `--verbose` to see detailed information about:
- Configuration loading
- Test execution
- Error stack traces

```bash
python run_eval.py minigames --verbose
```

## Future Enhancements

Potential improvements:
- A/B testing statistical significance
- Performance benchmarking
- Integration with CI/CD pipelines
- Web dashboard for results visualization
- Cost tracking for API usage 