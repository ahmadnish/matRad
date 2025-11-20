# Updated Models Summary - November 2025

## ✅ Latest Models Added

### OpenAI (GPT-5 Series)
✨ **NEW** Models Added:
- **gpt-5.1** - Latest release (November 2025)
  - Improved reasoning with warmer personality
  - Features Instant and Thinking modes
  
- **gpt-5** - Major release (August 2025)
  - Multimodal capabilities
  - Advanced reasoning, state-of-the-art performance

### Anthropic (Claude 4.5 Series)
✨ **NEW** Models Added:
- **claude-sonnet-4.5** - Latest Sonnet (September 2025)
  - Excellent for coding and agentic tasks
  - Maintains focus for 30+ hours on complex tasks
  - Substantial gains in reasoning and math
  
- **claude-opus-4.5** - Latest Opus (September 2025)
  - Most capable Anthropic model
  - Enhanced alignment and reasoning
  - Best for critical applications

### Legacy Models (Still Supported)
- gpt-4o (default - stable and reliable)
- gpt-4o-mini (cost-effective)
- gpt-4-turbo
- claude-3-5-sonnet-latest
- claude-3-5-sonnet-20241022
- claude-3-opus-20240229

## Quick Usage

```python
from test_agent_planning import main, print_supported_models

# Show all models
print_supported_models()

# Use latest OpenAI model
main(model="gpt-5.1")

# Use latest Anthropic model
main(model="claude-sonnet-4.5")

# Use default stable model
main()  # Uses gpt-4o
```

## Files Updated
1. ✅ `test_agent_planning.py` - Added all new models
2. ✅ `MODEL_SELECTION_GUIDE.md` - Updated with detailed guidance
3. ✅ No breaking changes - backward compatible

## Total Models Supported
- **10 models** total (5 OpenAI + 5 Anthropic)
- **4 NEW models** added (2 OpenAI GPT-5 + 2 Anthropic Claude 4.5)
- Default remains `gpt-4o` for stability

## Next Steps
- Test with `gpt-5.1` for cutting-edge performance
- Try `claude-sonnet-4.5` for complex agentic tasks
- Use `gpt-4o` for production stability

