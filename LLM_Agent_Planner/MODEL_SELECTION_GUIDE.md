# Model Selection Guide

## Overview
The IMRT planning agent now supports multiple LLM models from both OpenAI and Anthropic, including the latest GPT-5 and Claude 4.5 series, allowing you to choose the best model for your needs.

## Top Recommended Models for Agentic Work (Updated November 2025)

### OpenAI Models (GPT-5 Series - Latest)
1. **gpt-5.1** ⭐ NEW - Latest with improved reasoning and warmer personality (November 2025)
2. **gpt-5** ⭐ NEW - Multimodal with advanced reasoning capabilities (August 2025)
3. **gpt-4o** (default) - Reliable balance of speed and capability for function calling
4. **gpt-4o-mini** - Faster and more cost-effective, good for most cases
5. **gpt-4-turbo** - Strong reasoning and reliable function calling

### Anthropic Models (Claude 4.5/4.1 Series - Latest)
1. **claude-sonnet-4-5-20250929** ⭐ NEW - Excellent for coding and agentic tasks (September 2025)
2. **claude-opus-4-1-20250805** ⭐ NEW - Most capable for complex reasoning (August 2025)
3. **claude-haiku-4-5-20251001** ⭐ NEW - Fast and efficient for simpler tasks (October 2025)
4. **claude-3-5-sonnet-latest** - Previous generation, proven performance
5. **claude-3-5-sonnet-20241022** - Specific stable version with excellent capabilities

## Installation

### OpenAI (default)
```bash
pip install openai
export OPENAI_API_KEY="your-key-here"
```

### Anthropic (optional)
```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage Examples

### Command Line
```python
# Default (gpt-4o)
python test_agent_planning.py

# Or import and call with specific model
from test_agent_planning import main, print_supported_models

# Print all available models
print_supported_models()

# Use latest OpenAI models
main(model="gpt-5.1")      # Latest GPT-5.1 (Nov 2025)
main(model="gpt-5")        # GPT-5 (Aug 2025)
main(model="gpt-4o-mini")  # Cost-effective option

# Use latest Anthropic models
main(model="claude-sonnet-4-5-20250929")  # Latest Sonnet (Sep 2025)
main(model="claude-opus-4-1-20250805")    # Latest Opus (Aug 2025)
main(model="claude-haiku-4-5-20251001")   # Latest Haiku (Oct 2025)
```

### Programmatic Usage
```python
from test_agent_planning import IMRTPlanningAgent, TreatmentConfiguration

# Create treatment configuration
config = TreatmentConfiguration(
    cancer_site="head_and_neck",
    prescription_dose=70.0,
    num_fractions=35,
    treatment_technique="IMRT"
)

# Initialize agent with specific model
agent = IMRTPlanningAgent(
    matrad_path="~/matRad",
    treatment_config=config,
    model="gpt-5.1"  # or "gpt-5", "claude-sonnet-4-5-20250929", etc.
)

# Run planning session
results = agent.run_planning_session("HandN.mat", max_iterations=200)
```

## Model Selection Guidelines

**Choose gpt-5.1** ⭐ NEW when:
- You want the absolute latest from OpenAI (Nov 2025)
- You need improved reasoning with a more natural conversational style
- You want the best performance for complex agentic tasks
- You're working on cutting-edge applications

**Choose gpt-5** ⭐ NEW when:
- You want advanced multimodal capabilities (Aug 2025)
- You need state-of-the-art reasoning performance
- You're willing to use the latest technology
- Cost is not the primary concern

**Choose gpt-4o** (default) when:
- You need reliable, proven function calling
- You want good speed/cost balance
- You prefer stable, well-tested models
- This is the recommended safe default

**Choose gpt-4o-mini** when:
- You need faster responses
- Cost is a primary concern
- The planning task is relatively straightforward
- You want good performance at lower cost

**Choose claude-sonnet-4-5-20250929** ⭐ NEW when:
- You want the latest Sonnet from Anthropic (Sep 2025)
- You need excellent coding and agentic capabilities
- You want a model that maintains focus on complex multi-step tasks
- You prefer Anthropic's approach to AI alignment

**Choose claude-opus-4-1-20250805** ⭐ NEW when:
- You need the absolute best reasoning capability from Anthropic
- The planning task is very complex
- You want the most capable model for critical applications
- Speed is not the primary concern

**Choose claude-haiku-4-5-20251001** ⭐ NEW when:
- You need fast responses with good quality
- Cost efficiency is important
- The task is relatively straightforward
- You want the latest fast model from Anthropic

**Choose claude-3-5-sonnet-latest** when:
- You prefer a proven, stable Anthropic model
- You want excellent performance without bleeding-edge risk
- You need strong long-context capabilities

**Choose gpt-4-turbo** or **claude-3-opus** when:
- You want previous-generation models with proven track records
- You need reliable performance for production systems
- You prefer well-documented, stable APIs

## Implementation Details

The code automatically:
- Detects which provider to use based on model name
- Converts between OpenAI and Anthropic API formats
- Validates model availability and API keys
- Falls back gracefully if a model is not in the supported list

## What's New in Latest Models (2025 Releases)

### GPT-5.1 (November 2025)
- **Key Features**: Improved reasoning, warmer personality, two modes (Instant and Thinking)
- **Best For**: Complex agentic tasks requiring nuanced reasoning
- **Improvements**: Enhanced conversational quality over GPT-5

### GPT-5 (August 2025)
- **Key Features**: Multimodal capabilities, advanced reasoning, state-of-the-art benchmarks
- **Best For**: Tasks requiring vision + text reasoning
- **Improvements**: Major leap in reasoning capabilities from GPT-4 series

### Claude Sonnet 4.5 (September 29, 2025)
- **Model ID**: `claude-sonnet-4-5-20250929`
- **Key Features**: Excellent coding, maintains focus for extended periods (30+ hours on complex tasks)
- **Best For**: Autonomous coding, complex multi-step planning, agentic workflows
- **Improvements**: Substantial gains in reasoning, math, and sustained attention

### Claude Opus 4.1 (August 5, 2025)
- **Model ID**: `claude-opus-4-1-20250805`
- **Key Features**: Most capable Anthropic model, enhanced alignment, reduced problematic behaviors
- **Best For**: Critical applications requiring best possible reasoning
- **Improvements**: Superior performance on complex reasoning tasks vs Opus 3

### Claude Haiku 4.5 (October 1, 2025)
- **Model ID**: `claude-haiku-4-5-20251001`
- **Key Features**: Fast and efficient, excellent for simpler tasks with quick responses
- **Best For**: Cost-effective applications, rapid prototyping, straightforward planning
- **Improvements**: Speed and cost efficiency while maintaining quality

## Notes

- The default model is `gpt-4o` for stability and reliability in production
- All latest models (GPT-5 series and Claude 4.5 series) support function calling/tool use
- Model responses are normalized internally, so the code works identically regardless of provider
- You can add custom models by modifying the `SUPPORTED_MODELS` dictionary in the code
- Latest models may have different pricing - check provider documentation
- API availability may vary by region and access tier

