# Ollama Model Comparison for HTML Form Analysis

## Task Requirements

Our form reader needs to:
1. **Parse HTML structure** - Understand form elements, inputs, labels
2. **Extract field properties** - Type, name, ID, placeholder, required status
3. **Infer field purpose** - Determine if field is for name, email, URL, description, etc.
4. **Generate structured JSON** - Return consistent, valid JSON format
5. **Handle CSS selectors** - Create accurate selectors for automation

## Model Recommendations

### 🏆 **qwen2.5:7b** (RECOMMENDED)

**Best for: HTML form analysis and structured output**

**Pros:**
- ✅ Excellent at structured JSON output (critical for our use case)
- ✅ Strong understanding of technical content (HTML, CSS)
- ✅ Good at inferring field purposes from context
- ✅ Fast inference (~4GB RAM)
- ✅ Reliable field extraction

**Cons:**
- ⚠️ Slightly larger than llama3.2 (but worth it for accuracy)

**Use when:** You want the best balance of accuracy and speed

**Pull command:** `ollama pull qwen2.5:7b`

---

### 🥈 **deepseek-coder:6.7b**

**Best for: Technical tasks and code analysis**

**Pros:**
- ✅ Designed specifically for technical/code tasks
- ✅ Excellent with HTML/CSS/structured data
- ✅ Strong JSON generation
- ✅ Fast and efficient (~4GB RAM)

**Cons:**
- ⚠️ May be overkill (designed for coding, not just analysis)

**Use when:** You want maximum technical accuracy

**Pull command:** `ollama pull deepseek-coder:6.7b`

---

### 🥉 **llama3.2:3b**

**Best for: Fast testing and low-resource environments**

**Pros:**
- ✅ Very fast inference
- ✅ Low memory usage (~2GB RAM)
- ✅ Good structured output (decent JSON)
- ✅ Quick responses

**Cons:**
- ⚠️ Less accurate field extraction
- ⚠️ May miss some form fields
- ⚠️ Struggles with complex forms

**Use when:** You have limited RAM or need very fast responses

**Pull command:** `ollama pull llama3.2:3b`

---

### **mistral:7b**

**Best for: Balanced quality and speed**

**Pros:**
- ✅ Good balance of quality and speed
- ✅ Decent structured output
- ✅ Reliable performance

**Cons:**
- ⚠️ Not specialized for technical tasks
- ⚠️ May not be as accurate as qwen2.5

**Use when:** You want a general-purpose model

**Pull command:** `ollama pull mistral:7b`

---

### **llama3:8b**

**Best for: Maximum quality (overkill for this task)**

**Pros:**
- ✅ Highest quality output
- ✅ Best understanding of context

**Cons:**
- ❌ Slower inference
- ❌ Higher memory usage (~7GB RAM)
- ❌ Overkill for structured extraction tasks

**Use when:** You have powerful hardware and want maximum accuracy

**Pull command:** `ollama pull llama3:8b`

---

## Performance Comparison

| Model | RAM | Speed | JSON Quality | HTML Understanding | Field Extraction | Overall Score |
|-------|-----|-------|--------------|-------------------|------------------|---------------|
| **qwen2.5:7b** | 4GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **9.5/10** |
| **deepseek-coder:6.7b** | 4GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **9/10** |
| **llama3.2:3b** | 2GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | **7/10** |
| **mistral:7b** | 4GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **8/10** |
| **llama3:8b** | 7GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **8.5/10** |

## Recommendation

**For production use:** **qwen2.5:7b**
- Best balance of accuracy and speed
- Excellent structured output
- Reliable field extraction

**For testing/development:** **llama3.2:3b**
- Fast iteration
- Low resource usage
- Good enough for testing

## Quick Start

1. Pull the recommended model:
   ```bash
   ollama pull qwen2.5:7b
   ```

2. Update your `.env`:
   ```env
   LLM_MODEL=qwen2.5:7b
   ```

3. Test it:
   ```bash
   ollama run qwen2.5:7b "Analyze this form and return JSON: <form><input name='email'/><input name='name'/></form>"
   ```

## Switching Models

You can easily switch models by:
1. Pulling a different model: `ollama pull <model-name>`
2. Updating `.env`: `LLM_MODEL=<model-name>`
3. Restarting the backend

No code changes needed!
