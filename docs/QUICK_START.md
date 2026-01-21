# Quick Start Guide

## 1. Start Ollama Service

Make sure Ollama is running. On Windows, Ollama usually runs as a service automatically, but you can verify:

```bash
# Check if Ollama is running (should return model list)
# If ollama command not found, Ollama might be running as a service
# Try accessing: http://localhost:11434
```

If Ollama isn't running, start it:
- **Windows**: Usually runs automatically, or start from Start Menu
- **Manual**: Open terminal and run `ollama serve` (if in PATH)

## 2. Verify Model is Installed

The model `llama3.2:3b` should already be downloaded. You can verify by:
- Opening Ollama UI (if installed) or
- Checking the backend logs when it starts

## 3. Configure Backend

The backend is already configured to use `llama3.2:3b`. If you need to change it, edit `backend/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:3b
LLM_TEMPERATURE=0.1
```

## 4. Start the Backend

```bash
cd backend

# Activate virtual environment (if not already active)
# Windows:
venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

## 5. Test the Connection

The backend will automatically test the Ollama connection on startup. Check the logs for:
```
Ollama client initialized. Model: llama3.2:3b, Base URL: http://localhost:11434
```

## 6. Start the Frontend

In a new terminal:

```bash
cd frontend

# Install dependencies (if not already installed)
npm install --legacy-peer-deps

# Start dev server
npm run dev
```

## 7. Test Form Analysis

1. Open the frontend at `http://localhost:5173`
2. Add a SaaS product
3. Start a submission job
4. The system will automatically:
   - Navigate to the directory
   - Analyze the form with Ollama
   - Extract form fields
   - Fill and submit the form

## Troubleshooting

### Ollama Connection Error

**Error**: `Failed to initialize Ollama client`

**Solution**:
1. Make sure Ollama is running
2. Check if `http://localhost:11434` is accessible
3. Verify the model is installed: The backend will try to use it automatically

### Model Not Found

**Error**: Model `llama3.2:3b` not found

**Solution**:
- The model should already be downloaded
- If not, Ollama will download it automatically on first use
- Or manually: `ollama pull llama3.2:3b`

### Slow Responses

**Solution**:
- `llama3.2:3b` is already the fastest option
- For better accuracy, consider upgrading to `qwen2.5:7b` (requires more RAM)

## Next Steps

1. ✅ Ollama installed
2. ✅ Model downloaded (llama3.2:3b)
3. ⏭️ Start backend server
4. ⏭️ Start frontend
5. ⏭️ Test form submission

You're ready to go! 🚀
