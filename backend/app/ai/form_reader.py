"""
LLM logic for form reading and understanding (BRAIN)
Uses Ollama (local LLM) to analyze forms and extract field information
"""

import json
import os
import re
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.utils.logger import logger
from app.automation.field_classifier import FieldPurposeClassifier

# Make Ollama import optional - backend can run without it
try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning(
        "Ollama module not found. AI form reading features will be disabled."
    )


class FormReader:
    """
    AI-powered form reader using Ollama (local LLM)
    Analyzes HTML forms and extracts field information for automation
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.use_openai_compatible = settings.LLM_USE_OPENAI_COMPATIBLE
        self.client = None

        # Initialize Ollama client only if available
        if not OLLAMA_AVAILABLE:
            logger.warning(
                "Ollama not available. FormReader initialized but AI features disabled."
            )
            return

        try:
            # Test connection
            self.client = ollama.Client(host=self.base_url)
            logger.info(
                f"Ollama client initialized. Model: {self.model}, Base URL: {self.base_url}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            logger.warning("Make sure Ollama is running: ollama serve")
            self.client = None

    def _extract_form_html(self, html_content: str) -> str:
        """
        Extract only the form-related HTML to reduce token usage
        """
        # Find form tags
        form_pattern = r"<form[^>]*>.*?</form>"
        matches = re.findall(form_pattern, html_content, re.DOTALL | re.IGNORECASE)

        if matches:
            # Return the first (or largest) form found
            return max(matches, key=len)

        # If no form tag found, look for input fields
        input_pattern = r"<input[^>]*>"
        inputs = re.findall(input_pattern, html_content, re.IGNORECASE)
        if inputs:
            return "\n".join(inputs[:20])  # Limit to first 20 inputs

        # Fallback: return a portion of HTML
        return html_content[:5000]  # Limit to 5000 chars

    async def analyze_form(self, html_content: str) -> dict:
        """
        Analyze form HTML and extract field information using Ollama
        Returns structured form data with field types, labels, selectors, etc.
        """
        if not self.client:
            logger.error("Ollama client not initialized. Make sure Ollama is running.")
            return {
                "fields": [],
                "submit_button": None,
                "form_structure": {},
                "error": "Ollama not available. Start Ollama with: ollama serve",
            }

        try:
            # Extract form HTML to reduce token usage
            form_html = self._extract_form_html(html_content)

            logger.info(
                f"Analyzing form with {self.model} (HTML length: {len(form_html)} chars)"
            )

            # Create prompt for LLM
            prompt = self._create_analysis_prompt(form_html)

            # Call Ollama API
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing HTML forms and extracting structured field information. Always respond with valid JSON only, no additional text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": self.temperature,
                },
            )

            # Parse response
            result_text = response["message"]["content"]

            # Clean response - remove markdown code blocks if present
            result_text = self._clean_json_response(result_text)

            result = json.loads(result_text)

            logger.info(
                f"Form analysis complete. Found {len(result.get('fields', []))} fields"
            )

            # Validate and structure response
            return self._validate_analysis_result(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama JSON response: {e}")
            logger.debug(
                f"Response was: {result_text[:500] if 'result_text' in locals() else 'N/A'}"
            )
            return {
                "fields": [],
                "submit_button": None,
                "form_structure": {},
                "error": f"Failed to parse LLM response: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Form analysis failed: {str(e)}")
            return {
                "fields": [],
                "submit_button": None,
                "form_structure": {},
                "error": str(e),
            }

    def _clean_json_response(self, text: str) -> str:
        """
        Clean JSON response from LLM, removing markdown code blocks and extra text
        Enhanced to handle common LLM JSON formatting issues
        """
        import re

        original_text = text  # Keep for debugging

        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Find JSON object boundaries (look for outermost braces)
        start_idx = text.find("{")
        end_idx = text.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx : end_idx + 1]
        else:
            # Try to find JSON in the text using regex
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
            if json_match:
                text = json_match.group(0)

        # Remove common prefixes/suffixes
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        # Fix common JSON issues
        # Remove trailing commas before closing braces/brackets
        text = re.sub(r",(\s*[}\]])", r"\1", text)

        # Remove any text before the first { or after the last }
        text = re.sub(r"^[^{]*", "", text)
        text = re.sub(r"[^}]*$", "", text)

        # Fix common quote issues (unescaped quotes in strings)
        # This is a simple fix - may need refinement
        lines = text.split("\n")
        fixed_lines = []
        for line in lines:
            # Don't fix lines that are already properly quoted
            if re.match(r'^\s*"[^"]+":\s*"[^"]*"\s*,?\s*$', line):
                fixed_lines.append(line)
            elif re.match(r'^\s*"[^"]+":\s*\[', line):
                fixed_lines.append(line)
            elif re.match(r'^\s*"[^"]+":\s*\{', line):
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        text = "\n".join(fixed_lines)

        # Log if significant cleaning was done
        if len(original_text) - len(text) > 100:
            logger.debug(
                f"Cleaned JSON response: removed {len(original_text) - len(text)} characters"
            )

        return text.strip()

    def _create_analysis_prompt(self, form_html: str) -> str:
        """
        Create the prompt for LLM form analysis with few-shot examples
        """

        few_shot_examples = """Here are examples of correct form analysis:

EXAMPLE 1 - Simple Contact Form:
HTML:
<form>
  <input type="text" name="full_name" placeholder="Your name">
  <input type="email" name="email_address">
  <textarea name="msg">Message</textarea>
  <button type="submit">Send</button>
</form>

CORRECT OUTPUT:
{
  "fields": [
    {
      "selector": "[name='full_name']",
      "type": "text",
      "name": "full_name",
      "label": "",
      "placeholder": "Your name",
      "required": false,
      "purpose": "name",
      "options": []
    },
    {
      "selector": "[name='email_address']",
      "type": "email",
      "name": "email_address",
      "label": "",
      "placeholder": "",
      "required": false,
      "purpose": "email",
      "options": []
    },
    {
      "selector": "[name='msg']",
      "type": "textarea",
      "name": "msg",
      "label": "",
      "placeholder": "Message",
      "required": false,
      "purpose": "description",
      "options": []
    }
  ],
  "submit_button": {
    "selector": "button[type='submit']",
    "text": "Send"
  },
  "form_selector": "form"
}

EXAMPLE 2 - Product Submission:
HTML:
<form id="productForm">
  <label for="pname">Product Title</label>
  <input id="pname" type="text" required>
  <label for="site">Website</label>
  <input id="site" type="url">
  <select name="category">
    <option>SaaS</option>
    <option>Marketing</option>
  </select>
  <input type="submit" value="Submit">
</form>

CORRECT OUTPUT:
{
  "fields": [
    {
      "selector": "#pname",
      "type": "text",
      "name": "",
      "label": "Product Title",
      "placeholder": "",
      "required": true,
      "purpose": "name",
      "options": []
    },
    {
      "selector": "#site",
      "type": "url",
      "name": "",
      "label": "Website",
      "placeholder": "",
      "required": false,
      "purpose": "url",
      "options": []
    },
    {
      "selector": "[name='category']",
      "type": "select",
      "name": "category",
      "label": "",
      "placeholder": "",
      "required": false,
      "purpose": "category",
      "options": ["SaaS", "Marketing"]
    }
  ],
  "submit_button": {
    "selector": "input[type='submit']",
    "text": "Submit"
  },
  "form_selector": "#productForm"
}
"""

        # Get classification hints from rule-based classifier
        classification_hints = FieldPurposeClassifier.get_classification_hints()

        return f"""{few_shot_examples}

NOW ANALYZE THIS FORM:

HTML Form:
{form_html}

IMPORTANT RULES:
1. IGNORE hidden fields (type="hidden") - they are not user-fillable
2. Prefer ID selectors (#id) over name ([name=""]) over class
3. For purpose inference, look at: label text > placeholder > name attribute
4. Purpose keywords:
{classification_hints}
5. Return ONLY valid JSON, no markdown, no extra text
6. If multiple submit buttons exist, pick the primary one

Extract all form fields and return JSON with this exact structure:
{{
    "fields": [...],
    "submit_button": {{...}},
    "form_selector": "..."
}}"""

    def _validate_analysis_result(self, result: dict) -> dict:
        """
        Validate and normalize the LLM analysis result
        """
        validated = {
            "fields": [],
            "submit_button": None,
            "form_selector": result.get("form_selector", "form"),
            "form_structure": result,
        }

        # Validate fields
        for field in result.get("fields", []):
            if "selector" in field and field["selector"]:
                validated["fields"].append(
                    {
                        "selector": field.get("selector", ""),
                        "type": field.get("type", "text"),
                        "name": field.get("name", ""),
                        "label": field.get("label", ""),
                        "placeholder": field.get("placeholder", ""),
                        "required": field.get("required", False),
                        "purpose": field.get("purpose", "other"),
                        "options": field.get("options", []),
                    }
                )

        # Validate submit button
        submit_info = result.get("submit_button", {})
        if submit_info and submit_info.get("selector"):
            validated["submit_button"] = {
                "selector": submit_info.get("selector", ""),
                "text": submit_info.get("text", "Submit"),
            }

        return validated

    async def analyze_form_hybrid(
        self, html_content: str, use_llm: bool = True
    ) -> dict:
        """
        Hybrid approach: DOM extraction + rule-based classification + optional LLM enhancement

        Args:
            html_content: HTML content to analyze
            use_llm: Whether to use LLM for complex forms (default: True)

        Returns:
            Form structure dict
        """
        logger.info("Starting hybrid form analysis")

        # Step 1: Always start with DOM extraction (fast, reliable)
        from app.automation.browser import BrowserAutomation
        from urllib.parse import quote

        browser = BrowserAutomation()

        try:
            await browser.start()
            # Use data URI for DOM extraction (encode HTML properly)
            # Playwright supports data URLs
            encoded_html = quote(html_content)
            data_url = f"data:text/html;charset=utf-8,{encoded_html}"
            await browser.navigate(data_url)
            dom_result = await browser.extract_form_fields_dom()
            await browser.close()
        except Exception as e:
            logger.error(f"DOM extraction failed: {e}")
            try:
                await browser.close()
            except:
                pass
            dom_result = {"fields": [], "submit_button": None, "form_selector": "form"}

        if not dom_result.get("fields"):
            logger.warning("No fields found in DOM extraction")
            return dom_result

        # Step 2: Enhance with rule-based classification
        fields = dom_result.get("fields", [])
        fields = FieldPurposeClassifier.classify_fields(fields)
        dom_result["fields"] = fields

        logger.info(f"Rule-based classification complete. Found {len(fields)} fields")

        # Step 3: Determine if LLM is needed
        if not use_llm or not self.client:
            logger.info("Using rule-based classification only")
            return dom_result

        # Check form complexity
        is_complex = self._is_complex_form(dom_result)

        if not is_complex:
            logger.info("Simple form detected, skipping LLM analysis")
            return dom_result

        # Step 4: Use LLM for complex forms
        logger.info("Complex form detected, using LLM for enhancement")
        try:
            llm_result = await self.analyze_form(html_content)

            if llm_result.get("error"):
                logger.warning("LLM analysis failed, using rule-based result")
                return dom_result

            # Merge results (prefer LLM for complex cases)
            return self._merge_results(dom_result, llm_result)

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return dom_result

    def _is_complex_form(self, form_data: dict) -> bool:
        """
        Determine if form is complex enough to warrant LLM analysis

        Args:
            form_data: Form structure from DOM extraction

        Returns:
            True if form is complex, False otherwise
        """
        fields = form_data.get("fields", [])

        # Complex if many fields
        if len(fields) > 8:
            logger.debug(f"Complex form: {len(fields)} fields > 8")
            return True

        # Complex if many fields have unclear purpose
        unclear_count = sum(1 for f in fields if f.get("purpose") == "other")
        unclear_ratio = unclear_count / len(fields) if fields else 0

        if unclear_ratio > 0.3:
            logger.debug(f"Complex form: {unclear_ratio*100:.1f}% fields unclear")
            return True

        # Complex if has unusual field types
        field_types = [f.get("type", "") for f in fields]
        unusual_types = [
            "color",
            "range",
            "date",
            "time",
            "datetime-local",
            "month",
            "week",
        ]
        has_unusual = any(t in unusual_types for t in field_types)

        if has_unusual:
            logger.debug("Complex form: contains unusual field types")
            return True

        return False

    def _merge_results(self, dom_result: dict, llm_result: dict) -> dict:
        """
        Merge DOM and LLM results intelligently

        Args:
            dom_result: Result from DOM extraction
            llm_result: Result from LLM analysis

        Returns:
            Merged result
        """
        # Start with DOM result (more reliable structure)
        merged = dom_result.copy()

        # Update purposes from LLM if they seem better
        llm_fields = {f.get("selector"): f for f in llm_result.get("fields", [])}

        for field in merged.get("fields", []):
            selector = field.get("selector")
            if selector in llm_fields:
                llm_field = llm_fields[selector]
                # Update purpose if LLM found something better than "other"
                if (
                    field.get("purpose") == "other"
                    and llm_field.get("purpose") != "other"
                ):
                    field["purpose"] = llm_field.get("purpose")
                    logger.debug(
                        f"Updated {selector} purpose to {field['purpose']} from LLM"
                    )

        # Use LLM submit button if DOM didn't find one
        if not merged.get("submit_button") and llm_result.get("submit_button"):
            merged["submit_button"] = llm_result["submit_button"]

        return merged

    async def map_data_to_form(self, form_structure: dict, saas_data: dict) -> dict:
        """
        Map SaaS data to form fields using AI understanding
        Intelligently matches SaaS data fields to detected form fields
        """
        if not self.client:
            logger.error("Ollama client not initialized. Check Ollama connection.")
            return self._simple_field_mapping(form_structure, saas_data)

        try:
            fields = form_structure.get("fields", [])
            if not fields:
                logger.warning("No fields found in form structure")
                return {}

            logger.info(f"Mapping SaaS data to {len(fields)} form fields")

            # Create mapping prompt
            prompt = self._create_mapping_prompt(fields, saas_data)

            # Call Ollama API for intelligent mapping
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at mapping data to form fields. Always respond with valid JSON only, no additional text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": self.temperature,
                },
            )

            result_text = response["message"]["content"]
            result_text = self._clean_json_response(result_text)
            mapping = json.loads(result_text)

            logger.info(
                f"Data mapping complete. Mapped {len(mapping.get('field_mappings', {}))} fields"
            )

            return mapping.get("field_mappings", {})

        except json.JSONDecodeError as e:
            logger.error(f"Data mapping JSON parse failed: {str(e)}")
            if "result_text" in locals():
                logger.debug(
                    f"Failed JSON response (first 500 chars): {result_text[:500]}"
                )
            logger.info("Falling back to simple field mapping")
            return self._simple_field_mapping(form_structure, saas_data)
        except Exception as e:
            logger.error(f"Data mapping failed: {str(e)}")
            logger.info("Falling back to simple field mapping")
            return self._simple_field_mapping(form_structure, saas_data)

    def _create_mapping_prompt(self, fields: List[dict], saas_data: dict) -> str:
        """
        Create prompt for intelligent field mapping
        """
        fields_info = json.dumps(fields, indent=2)
        saas_info = json.dumps(saas_data, indent=2)

        return f"""Map the SaaS data to the form fields intelligently.

Available Form Fields:
{fields_info}

SaaS Data to Submit:
{saas_info}

For each form field, determine which SaaS data field should fill it based on:
- Field purpose (name, email, url, description, category, logo)
- Field label/placeholder text
- Field name/ID attribute
- Semantic similarity

Return ONLY a JSON object (no additional text):
{{
    "field_mappings": {{
        "selector1": "value1",
        "selector2": "value2",
        ...
    }},
    "unmapped_fields": ["list of selectors that couldn't be mapped"],
    "notes": "any important notes about the mapping"
}}

Important mappings:
- name/title fields → saas_data.name
- url/website fields → saas_data.url
- email fields → saas_data.contact_email
- description fields → saas_data.description
- category fields → saas_data.category
- logo/image upload fields → saas_data.logo_path (file path)

If a field can't be mapped, don't include it in field_mappings."""

    def _simple_field_mapping(self, form_structure: dict, saas_data: dict) -> dict:
        """
        Fallback simple mapping based on field purpose, name, label, and placeholder matching
        Uses flexible keyword matching instead of exact purpose matching
        """
        mapping = {}

        for field in form_structure.get("fields", []):
            purpose = field.get("purpose", "").lower()
            selector = field.get("selector", "")
            name = field.get("name", "").lower()
            label = field.get("label", "").lower()
            placeholder = field.get("placeholder", "").lower()

            # Combine all text for flexible matching
            field_text = f"{purpose} {name} {label} {placeholder}"

            # Skip if already mapped or no selector
            if selector in mapping or not selector:
                continue

            # Match name/title/product fields
            if any(
                keyword in field_text
                for keyword in [
                    "name",
                    "title",
                    "product",
                    "company",
                    "business",
                    "app",
                    "tool",
                    "startup",
                ]
            ):
                if saas_data.get("name"):
                    mapping[selector] = saas_data["name"]
                    logger.debug(f"Mapped {selector} to name field")
                    continue

            # Match URL/website fields
            if any(
                keyword in field_text
                for keyword in [
                    "url",
                    "website",
                    "site",
                    "link",
                    "homepage",
                    "domain",
                    "web",
                ]
            ):
                if saas_data.get("url"):
                    mapping[selector] = saas_data["url"]
                    logger.debug(f"Mapped {selector} to url field")
                    continue

            # Match email fields
            if any(keyword in field_text for keyword in ["email", "mail", "contact"]):
                if saas_data.get("contact_email"):
                    mapping[selector] = saas_data["contact_email"]
                    logger.debug(f"Mapped {selector} to email field")
                    continue

            # Match description fields
            if any(
                keyword in field_text
                for keyword in [
                    "description",
                    "desc",
                    "about",
                    "details",
                    "summary",
                    "info",
                    "pitch",
                ]
            ):
                if saas_data.get("description"):
                    mapping[selector] = saas_data["description"]
                    logger.debug(f"Mapped {selector} to description field")
                    continue

            # Match category/tag fields
            if any(
                keyword in field_text
                for keyword in ["category", "tag", "tags", "type", "industry", "niche"]
            ):
                if saas_data.get("category"):
                    mapping[selector] = saas_data["category"]
                    logger.debug(f"Mapped {selector} to category field")
                    continue

            # Match logo/image fields
            if any(
                keyword in field_text
                for keyword in ["logo", "image", "picture", "icon", "photo", "avatar"]
            ):
                if saas_data.get("logo_path"):
                    mapping[selector] = saas_data["logo_path"]
                    logger.debug(f"Mapped {selector} to logo field")
                    continue

        logger.info(f"Simple field mapping complete. Mapped {len(mapping)} fields")
        return mapping
