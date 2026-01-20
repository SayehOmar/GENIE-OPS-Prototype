# Ollama Setup Guide

## Installation

1. **Install Ollama** (if not already installed):
   - Windows: Download from <https://ollama.com/download>
   - Or use: `winget install Ollama.Ollama`

2. **Start Ollama Service**:

   ```bash
   ollama serve
   ```

   This starts the Ollama server on `http://localhost:11434`

3. **Pull a Model** (recommended for HTML form analysis):

   ```bash
   # BEST FOR HTML FORM ANALYSIS - Recommended
   ollama pull qwen2.5:7b        # Excellent structured JSON output, great for technical tasks
   
   # Alternative options:
   ollama pull llama3.2:3b        # Fast, good for structured tasks, ~2GB RAM
   ollama pull deepseek-coder:6.7b # Excellent for technical/structured tasks
   ollama pull mistral:7b         # Good balance, ~4GB RAM
   ollama pull llama3:8b          # Best quality but slower, ~7GB RAM
   ```

## Recommended Models for HTML Form Analysis

### 🏆 **Best Choice: qwen2.5:7b**

- ✅ **Excellent structured JSON output** - Critical for form analysis
- ✅ **Great at technical content** - Understands HTML/CSS well
- ✅ **Fast inference** - ~4GB RAM, good speed
- ✅ **Reliable field extraction** - Good at inferring field purposes
- **Pull it**: `ollama pull qwen2.5:7b`

### 🥈 **Second Choice: deepseek-coder:6.7b**

- ✅ **Designed for technical tasks** - Excellent with code/HTML
- ✅ **Strong structured output** - Good JSON generation
- ✅ **Fast and efficient** - ~4GB RAM
- **Pull it**: `ollama pull deepseek-coder:6.7b`

### 🥉 **Third Choice: llama3.2:3b**

- ✅ **Very fast** - ~2GB RAM, quick responses
- ✅ **Good structured output** - Decent JSON generation
- ⚠️ **Less accurate** - May miss some form fields
- **Pull it**: `ollama pull llama3.2:3b`

### Other Options

- **mistral:7b** - Balanced, ~4GB RAM, good quality
- **llama3:8b** - Best quality but slower, ~7GB RAM (overkill for this task)

## Configuration

Update your `.env` file in the `backend/` directory:

```env
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b  # Recommended for HTML form analysis
LLM_TEMPERATURE=0.1   # Low temperature for consistent structured output
LLM_USE_OPENAI_COMPATIBLE=True
```

### Why These Settings?

- **qwen2.5:7b**: Best balance of accuracy and speed for HTML form analysis
- **Temperature 0.1**: Low temperature ensures consistent, structured JSON output
- **OpenAI Compatible**: Uses standard API format for compatibility

## Testing

Test if Ollama is working and can handle structured output:

```bash
# Test basic functionality
ollama run qwen2.5:7b "Analyze this HTML form: <form><input name='email' type='email'/><input name='name' type='text'/></form> and return JSON with field information"

# Or test JSON output capability
ollama run qwen2.5:7b "Return a JSON object with fields: name, email, url"
```

### Test Form Analysis

You can test the form reader directly by running the backend and making a test API call, or check the logs when processing a submission.

## Troubleshooting

- **Connection Error**: Make sure `ollama serve` is running
- **Model Not Found**: Pull the model first with `ollama pull <model-name>`
- **Out of Memory**: Use a smaller model (llama3.2 instead of llama3)
- **Slow Responses**: Try a smaller/faster model or reduce HTML content size

## Free & Local

✅ **100% Free** - No API costs
✅ **Runs Locally** - No internet required (after initial model download)
✅ **Privacy** - All data stays on your machine
✅ **No Rate Limits** - Use as much as you want
