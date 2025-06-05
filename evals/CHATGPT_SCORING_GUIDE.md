# ChatGPT Scoring Feature Guide

This guide explains how to use the new ChatGPT-based scoring system in the evaluation framework.

## Overview

The ChatGPT scoring feature uses GPT-4 to evaluate how relevant and helpful your agent's responses are to user questions. This provides an objective, AI-powered assessment of response quality that goes beyond simple keyword matching.

## How It Works

1. **Conversation Parsing**: The system formats the conversation history between user and assistant
2. **ChatGPT Evaluation**: GPT-4 analyzes the conversation and scores the assistant's relevance (0.0-1.0)
3. **JSON Output**: The scorer returns a structured JSON response with score and rationale
4. **Integration**: Results are included in evaluation reports alongside other metrics

## Quick Start

### 1. Set Up API Key

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. Enable in Test Configuration

Add ChatGPT scoring to your test config:

```json
{
  "expected_behaviors": {
    "use_chatgpt_scoring": true,
    "min_chatgpt_score": 0.7
  }
}
```

### 3. Run the Test

```bash
python run_eval.py chatgpt_scoring_test
```

## Configuration Options

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `use_chatgpt_scoring` | Enable ChatGPT scoring | `false` | No |
| `min_chatgpt_score` | Minimum expected score (0.0-1.0) | Not enforced | No |

## Scoring Scale

- **0.9-1.0**: Perfect relevance, completely addresses the question
- **0.8-0.9**: Highly relevant, mostly addresses the question  
- **0.6-0.7**: Moderately relevant, partially addresses the question
- **0.4-0.5**: Somewhat relevant but missing key information
- **0.2-0.3**: Minimally relevant, tangentially relates to the question
- **0.0-0.1**: Not relevant, doesn't address the question

## Example Output

### Console Output
```
[EVAL] Running ChatGPT scoring evaluation...
[EVAL] ChatGPT scored conversation: 0.847
[EVAL] ChatGPT rationale: The assistant provides a comprehensive and helpful response that directly addresses...
```

### Report Output
```
ChatGPT Scoring Success Rate: 100.00%
Avg ChatGPT Relevance Score: 0.847
```

## Sample Test Configuration

```json
{
  "name": "ChatGPT Scoring Test Suite",
  "description": "Test suite with ChatGPT-based relevance scoring",
  "runs_per_variant": 3,
  "tests": [
    {
      "name": "minigames_with_scoring",
      "description": "Test minigames conversation with ChatGPT scoring",
      "steps": [
        "hi",
        "I'm interested in minigames. Can you show me what's available?"
      ],
      "correct_features": ["17", "1006", "1021"],
      "expected_behaviors": {
        "should_produce_screenshots": true,
        "use_chatgpt_scoring": true,
        "min_chatgpt_score": 0.7
      }
    }
  ],
  "variants": [
    {
      "name": "baseline",
      "path": "evals/baseline_prompt.txt",
      "description": "Current production prompt"
    }
  ]
}
```

## Testing the Feature

Use the included test script to verify ChatGPT scoring works:

```bash
cd evals
python test_chatgpt_scoring.py
```

This will run sample conversations through the scorer to verify functionality.

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```
   Error: OpenAI API key not found in environment variables
   ```
   **Solution**: Set the `OPENAI_API_KEY` environment variable

2. **JSON Parsing Error**
   ```
   Error: Failed to parse ChatGPT response as JSON
   ```
   **Solution**: This is usually temporary; retry the evaluation

3. **Invalid Score Format**
   ```
   Error: Score X is not between 0.0 and 1.0
   ```
   **Solution**: Usually indicates a ChatGPT response issue; retry

### Best Practices

1. **Use Specific Questions**: More specific user questions get more accurate scoring
2. **Multiple Runs**: Run tests multiple times as ChatGPT scoring can have variance
3. **Review Rationales**: Check the rationale field in detailed reports for insights
4. **Cost Awareness**: ChatGPT scoring adds API costs (typically $0.01-0.03 per test)

## Data Structure

### TestResult Fields
```python
chatgpt_relevance_score: Optional[float] = None      # Score 0.0-1.0
chatgpt_rationale: Optional[str] = None             # Explanation text
chatgpt_scoring_error: Optional[str] = None         # Error message if failed
```

### Aggregate Metrics
```python
chatgpt_scoring_success_rate: float    # % of successful scoring attempts
avg_chatgpt_relevance_score: float     # Average score across runs
```

## Integration with Existing Metrics

ChatGPT scoring complements existing evaluation metrics:

- **Screenshot Production**: Measures if agent retrieved relevant screenshots
- **Feature Identification**: Measures if correct features were found  
- **ChatGPT Scoring**: Measures overall response quality and relevance

Use all three together for comprehensive evaluation of agent performance.

## Advanced Usage

### Custom Evaluation Prompts

The evaluation prompt can be customized by modifying the `score_with_chatgpt` method in `eval_framework.py`. The current prompt evaluates:

1. How directly the response addresses the question
2. How helpful and informative the response is  
3. How well it provides actionable information
4. Overall relevance to user intent

### Batch Processing

For large-scale evaluations, consider:
- Setting appropriate API rate limits
- Adding retry logic for failed requests
- Monitoring API usage costs

## Cost Estimates

Approximate costs per evaluation run:
- **GPT-4**: ~$0.01-0.03 per conversation scored
- **Factors**: Conversation length, number of test runs, number of variants

For a typical test with 3 runs × 2 tests × 1 variant = 6 scoring calls ≈ $0.06-0.18 

**Requirements:**
- Set the `OPENAI_API_KEY` environment variable
- Ensure the `openai` Python package is installed  
- Uses GPT-4o model (supports JSON mode - older GPT-4 models do not) 