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

3. **Pull a Model** (choose one based on your hardware):

   ```bash
   # Small, fast model (good for testing, ~2GB RAM)
   ollama pull llama3.2
   
   # Medium model (better quality, ~4GB RAM)
   ollama pull mistral
   
   # Large model (best quality, ~7GB RAM)
   ollama pull llama3
   ```

## Recommended Models

- **llama3.2** (default) - Fast, good for structured tasks, ~2GB RAM
- **mistral** - Good balance of speed and quality, ~4GB RAM
- **qwen2.5** - Excellent for structured output, ~2-4GB RAM
- **llama3** - Best quality but slower, ~7GB RAM

## Configuration

Update your `.env` file in the `backend/` directory:

```env
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
LLM_TEMPERATURE=0.1
LLM_USE_OPENAI_COMPATIBLE=True
```

## Testing

Test if Ollama is working:

```bash
ollama run llama3.2 "Hello, can you respond in JSON format?"
```

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
