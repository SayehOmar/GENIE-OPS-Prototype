# Testing Guide for Submission Workflow

This guide explains how to test the GENIE OPS submission workflow using Playwright and AI (Ollama).

## Table of Contents

1. [Why Playwright over Selenium?](#why-playwright-over-selenium)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Test Scenarios](#test-scenarios)
5. [Running Tests](#running-tests)
6. [Expected Outputs](#expected-outputs)
7. [Troubleshooting](#troubleshooting)
8. [Performance Benchmarks](#performance-benchmarks)

## Why Playwright over Selenium?

**Playwright is the better choice for this project because:**

1. **Already Integrated**: The codebase uses Playwright (`backend/app/automation/browser.py`)
2. **Better Performance**: Faster execution, better async support
3. **Auto-waiting**: Built-in smart waiting for elements (no manual waits needed)
4. **Modern API**: Cleaner, more intuitive API than Selenium
5. **Better Debugging**: Built-in tracing, screenshots, video recording
6. **Cross-browser**: Supports Chromium, Firefox, WebKit out of the box
7. **Network Control**: Can intercept/modify network requests (useful for testing)
8. **Mobile Emulation**: Built-in device emulation for responsive testing

**Selenium drawbacks for this use case:**
- Slower execution
- Requires WebDriver management (ChromeDriver, GeckoDriver, etc.)
- More verbose code
- Less reliable waiting mechanisms
- Older API design

## Prerequisites

### 1. Install Dependencies

```bash
# Install pytest and async support
pip install pytest pytest-asyncio

# Ensure Playwright browsers are installed
playwright install chromium
```

### 2. Start Ollama (for AI Testing)

```bash
# Start Ollama server
ollama serve

# In another terminal, verify model is available:
ollama list

# If llama3.2:3b is not installed:
ollama pull llama3.2:3b
```

**Note**: AI tests will be skipped if Ollama is not running. DOM fallback tests will still work.

### 3. Start Test Server

```bash
# Navigate to test directory
cd test

# Start HTTP server on port 8080
python -m http.server 8080

# Keep this terminal open - the server must be running during tests
```

### 4. Verify Backend is Running

- Backend API should be running on `http://localhost:8000`
- Database should be connected (PostgreSQL)
- Check backend logs for any errors

## Quick Start

### Run All Tests

```bash
# From project root
pytest backend/test/test_submission.py -v
```

### Run Specific Test Categories

```bash
# Test with AI (Ollama must be running)
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_full_workflow_with_ai -v

# Test without AI (DOM fallback)
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_full_workflow_without_ai -v

# Test form detection only
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_form_detection -v

# Run with browser visible (headless=False)
pytest backend/test/test_submission.py -v -s --headless=false
```

### Run with Screenshots

Screenshots are automatically saved to `backend/storage/screenshots/` during tests. To view them:

```bash
# On Windows
start backend/storage/screenshots

# On Linux/Mac
open backend/storage/screenshots
```

## Test Scenarios

### 1. Test with AI (Ollama)

**Purpose**: Verify AI-powered form analysis works correctly.

**Requirements**:
- Ollama server running
- Model `llama3.2:3b` (or configured model) available

**What it tests**:
- Form HTML extraction
- AI form analysis
- Field mapping with AI
- Form filling and submission

**Run**:
```bash
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_ai_form_extraction -v
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_full_workflow_with_ai -v
```

### 2. Test without AI (DOM Fallback)

**Purpose**: Verify DOM-based extraction works when AI is unavailable.

**Requirements**:
- No Ollama needed
- Test server running

**What it tests**:
- DOM form field extraction
- Fallback field mapping
- Form filling and submission

**Run**:
```bash
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_dom_form_extraction -v
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_full_workflow_without_ai -v
```

### 3. Test Individual Components

**Form Detection**:
```bash
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_form_detection -v
```

**Field Mapping**:
```bash
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_field_mapping -v
```

**Form Filling**:
```bash
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_form_filling -v
```

**Form Submission**:
```bash
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_form_submission -v
```

### 4. Test Edge Cases

**Error Handling**:
```bash
# Invalid URL
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_error_handling_invalid_url -v

# Missing form
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_error_handling_missing_form -v
```

**CAPTCHA Detection**:
```bash
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_captcha_detection -v
```

## Running Tests

### Basic Commands

```bash
# Run all tests with verbose output
pytest backend/test/test_submission.py -v

# Run with print statements visible
pytest backend/test/test_submission.py -v -s

# Run specific test
pytest backend/test/test_submission.py::TestSubmissionWorkflow::test_form_detection -v

# Run with coverage (if pytest-cov installed)
pytest backend/test/test_submission.py --cov=app --cov-report=html
```

### Advanced Options

```bash
# Run tests in parallel (if pytest-xdist installed)
pytest backend/test/test_submission.py -n auto

# Stop on first failure
pytest backend/test/test_submission.py -x

# Show local variables on failure
pytest backend/test/test_submission.py -l

# Run only tests matching pattern
pytest backend/test/test_submission.py -k "form" -v
```

## Expected Outputs

### Successful Test Run

```
backend/test/test_submission.py::TestSubmissionWorkflow::test_form_detection PASSED
backend/test/test_submission.py::TestSubmissionWorkflow::test_dom_form_extraction PASSED
backend/test/test_submission.py::TestSubmissionWorkflow::test_field_mapping PASSED
backend/test/test_submission.py::TestSubmissionWorkflow::test_form_filling PASSED
backend/test/test_submission.py::TestSubmissionWorkflow::test_form_submission PASSED
backend/test/test_submission.py::TestSubmissionWorkflow::test_full_workflow_without_ai PASSED
backend/test/test_submission.py::TestSubmissionWorkflow::test_captcha_detection PASSED
backend/test/test_submission.py::TestSubmissionWorkflow::test_screenshot_capture PASSED

======================== 8 passed in 15.23s ========================
```

### Expected Form Extraction Results

**DOM Extraction** (without AI):
- Form fields extracted: **6 fields**
  - `product_name` (text input)
  - `website_url` (URL input)
  - `contact_email` (email input)
  - `description` (textarea)
  - `category` (select dropdown)
  - `logo` (file input)

**AI Extraction** (with Ollama):
- Form fields extracted: **6 fields** (similar structure)
- Additional metadata from AI analysis
- Better field purpose inference

### Expected Workflow Results

**Successful Submission**:
```json
{
  "status": "success",
  "message": "Submission successful (detected: success)",
  "fields_filled": 5,
  "total_fields": 5,
  "form_structure": { ... },
  "fill_errors": []
}
```

**Fields Mapped**:
- Name → `#product_name`
- URL → `#website_url`
- Email → `#contact_email`
- Description → `#description`
- Category → `#category`

## Troubleshooting

### Common Issues

#### 1. "Connection refused" to test server

**Problem**: Test server not running on port 8080.

**Solution**:
```bash
cd test
python -m http.server 8080
```

#### 2. "Ollama not available" warnings

**Problem**: Ollama server not running or model not installed.

**Solution**:
```bash
# Start Ollama
ollama serve

# Install model
ollama pull llama3.2:3b

# Verify
ollama list
```

**Note**: AI tests will be skipped automatically. DOM fallback tests will still run.

#### 3. "Element not found" errors

**Problem**: Form selectors changed or page structure different.

**Solution**:
- Check `test/test_form.html` matches expected structure
- Verify test server is serving the correct file
- Check browser screenshots in `backend/storage/screenshots/`

#### 4. Playwright browser not found

**Problem**: Playwright browsers not installed.

**Solution**:
```bash
playwright install chromium
```

#### 5. Import errors

**Problem**: Python path not set correctly.

**Solution**:
```bash
# Run from project root
cd /path/to/GENIE-OPS-Prototype
pytest backend/test/test_submission.py -v
```

### Debug Mode

Run tests with browser visible to see what's happening:

```bash
# Set headless=False in config or use environment variable
export PLAYWRIGHT_HEADLESS=false  # Linux/Mac
set PLAYWRIGHT_HEADLESS=false     # Windows

pytest backend/test/test_submission.py -v -s
```

### View Screenshots

Screenshots are saved to `backend/storage/screenshots/`:

```bash
# List screenshots
ls -la backend/storage/screenshots/

# View latest screenshot
# On Windows
start backend/storage/screenshots/test_workflow_dom.png

# On Linux/Mac
open backend/storage/screenshots/test_workflow_dom.png
```

### Check Logs

Enable verbose logging:

```bash
# Set log level
export LOG_LEVEL=DEBUG  # Linux/Mac
set LOG_LEVEL=DEBUG     # Windows

pytest backend/test/test_submission.py -v -s
```

## Performance Benchmarks

### Expected Performance

**DOM Extraction** (without AI):
- Form extraction: **< 1 second**
- Field mapping: **< 0.5 seconds**
- Form filling: **1-2 seconds**
- Form submission: **1-2 seconds**
- **Total**: **3-5 seconds**

**AI Extraction** (with Ollama):
- Form extraction: **< 1 second**
- AI analysis: **2-5 seconds** (depends on model)
- Field mapping: **< 0.5 seconds**
- Form filling: **1-2 seconds**
- Form submission: **1-2 seconds**
- **Total**: **5-10 seconds**

### Optimization Tips

1. **Use DOM fallback for faster tests**: DOM extraction is faster than AI
2. **Run tests in parallel**: Use `pytest-xdist` for parallel execution
3. **Cache form structures**: Reuse extracted form structures when possible
4. **Use headless mode**: Faster than visible browser

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Test Submission Workflow

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-asyncio
          playwright install chromium
      - name: Start test server
        run: |
          cd test && python -m http.server 8080 &
      - name: Run tests
        run: |
          pytest backend/test/test_submission.py -v
```

## Next Steps

1. **Add more test forms**: Create variations of test forms to test edge cases
2. **Test real directories**: Test against actual directory websites (with permission)
3. **Performance testing**: Measure and optimize submission times
4. **Error scenario testing**: Test more error conditions
5. **Integration testing**: Test with full database and API integration

## Additional Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ollama Documentation](https://ollama.ai/docs)
- [Project Documentation](../docs/)
