# Test Files

This directory contains test files for validating the GENIE OPS automation system.

## test_form.html

A simple HTML form that mimics a typical directory submission page. It includes:

- **Product Name** field (text input)
- **Website URL** field (URL input)
- **Contact Email** field (email input)
- **Description** field (textarea)
- **Category** field (select dropdown)
- **Logo** field (file upload)
- **Submit** button

### How to Use

1. **Start a local web server** to serve the HTML file:
   ```bash
   # Using Python 3
   cd backend/test
   python -m http.server 8080
   
   # Or using Node.js (if you have http-server installed)
   npx http-server -p 8080
   ```

2. **Access the form** in your browser:
   ```
   http://localhost:8080/test_form.html
   ```

3. **Test the automation** by:
   - Creating a SaaS entry in the frontend
   - Creating a Directory entry with URL: `http://localhost:8080/test_form.html`
   - Starting a submission job
   - The automation should fill and submit the form

### Expected Behavior

When the automation runs:
- It should detect the form on the page
- Extract all form fields using DOM inspection
- Map SaaS data to form fields:
  - `name` → Product Name
  - `url` → Website URL
  - `contact_email` → Contact Email
  - `description` → Description
  - `category` → Category
  - `logo_path` → Logo (if provided)
- Fill all fields
- Click the Submit button
- Detect the success message

### Testing Different Scenarios

You can modify `test_form.html` to test:
- Different field names/IDs
- Required vs optional fields
- Different input types
- Modal forms
- Multi-step forms
- CAPTCHA (add a placeholder)

### Notes

- The form uses client-side JavaScript to show success/error messages
- No actual backend processing is required for testing
- The form data is logged to the browser console for inspection
