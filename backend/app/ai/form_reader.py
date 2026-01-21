"""
LLM logic for form reading and understanding (BRAIN)
Uses Ollama (local LLM) to analyze forms and extract field information
"""
import json
import re
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.utils.logger import logger

# Make Ollama import optional - backend can run without it
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama module not found. AI form reading features will be disabled.")


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
            logger.warning("Ollama not available. FormReader initialized but AI features disabled.")
            return
            
        try:
            # Test connection
            self.client = ollama.Client(host=self.base_url)
            logger.info(f"Ollama client initialized. Model: {self.model}, Base URL: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            logger.warning("Make sure Ollama is running: ollama serve")
            self.client = None
    
    def _extract_form_html(self, html_content: str) -> str:
        """
        Extract only the form-related HTML to reduce token usage
        """
        # Find form tags
        form_pattern = r'<form[^>]*>.*?</form>'
        matches = re.findall(form_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            # Return the first (or largest) form found
            return max(matches, key=len)
        
        # If no form tag found, look for input fields
        input_pattern = r'<input[^>]*>'
        inputs = re.findall(input_pattern, html_content, re.IGNORECASE)
        if inputs:
            return '\n'.join(inputs[:20])  # Limit to first 20 inputs
        
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
                "error": "Ollama not available. Start Ollama with: ollama serve"
            }
        
        try:
            # Extract form HTML to reduce token usage
            form_html = self._extract_form_html(html_content)
            
            logger.info(f"Analyzing form with {self.model} (HTML length: {len(form_html)} chars)")
            
            # Create prompt for LLM
            prompt = self._create_analysis_prompt(form_html)
            
            # Call Ollama API
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing HTML forms and extracting structured field information. Always respond with valid JSON only, no additional text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": self.temperature,
                }
            )
            
            # Parse response
            result_text = response['message']['content']
            
            # Clean response - remove markdown code blocks if present
            result_text = self._clean_json_response(result_text)
            
            result = json.loads(result_text)
            
            logger.info(f"Form analysis complete. Found {len(result.get('fields', []))} fields")
            
            # Validate and structure response
            return self._validate_analysis_result(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama JSON response: {e}")
            logger.debug(f"Response was: {result_text[:500] if 'result_text' in locals() else 'N/A'}")
            return {
                "fields": [],
                "submit_button": None,
                "form_structure": {},
                "error": f"Failed to parse LLM response: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Form analysis failed: {str(e)}")
            return {
                "fields": [],
                "submit_button": None,
                "form_structure": {},
                "error": str(e)
            }
    
    def _clean_json_response(self, text: str) -> str:
        """
        Clean JSON response from LLM (remove markdown code blocks, etc.)
        """
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # Try to extract JSON if wrapped in other text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text
    
    def _create_analysis_prompt(self, form_html: str) -> str:
        """
        Create the prompt for LLM form analysis
        """
        return f"""Analyze this HTML form and extract all form fields with their properties.

HTML Form:
{form_html}

Extract the following information for each form field:
1. Field type (text, email, url, textarea, select, file, checkbox, radio, etc.)
2. Field name/ID attribute
3. Label text (if available)
4. Placeholder text
5. CSS selector (prefer ID, then name, then other attributes)
6. Whether field is required
7. Field purpose (name, email, url, description, category, logo, etc.) - infer from label/placeholder/name

Also identify:
- Submit button selector
- Form container selector

Return ONLY a JSON object with this structure (no additional text):
{{
    "fields": [
        {{
            "selector": "string (CSS selector)",
            "type": "string (input type)",
            "name": "string (name/id attribute)",
            "label": "string (label text if found)",
            "placeholder": "string (placeholder text)",
            "required": boolean,
            "purpose": "string (inferred purpose: name, email, url, description, category, logo, other)",
            "options": ["array of options if select/radio"]
        }}
    ],
    "submit_button": {{
        "selector": "string (CSS selector for submit button)",
        "text": "string (button text)"
    }},
    "form_selector": "string (CSS selector for form container)"
}}

Focus on fields that might be used for SaaS directory submissions:
- Name/Title
- URL/Website
- Email
- Description
- Category
- Logo/Image upload
- Tags
- Company name

Be thorough and extract ALL form fields, even if their purpose is unclear."""
    
    def _validate_analysis_result(self, result: dict) -> dict:
        """
        Validate and normalize the LLM analysis result
        """
        validated = {
            "fields": [],
            "submit_button": None,
            "form_selector": result.get("form_selector", "form"),
            "form_structure": result
        }
        
        # Validate fields
        for field in result.get("fields", []):
            if "selector" in field and field["selector"]:
                validated["fields"].append({
                    "selector": field.get("selector", ""),
                    "type": field.get("type", "text"),
                    "name": field.get("name", ""),
                    "label": field.get("label", ""),
                    "placeholder": field.get("placeholder", ""),
                    "required": field.get("required", False),
                    "purpose": field.get("purpose", "other"),
                    "options": field.get("options", [])
                })
        
        # Validate submit button
        submit_info = result.get("submit_button", {})
        if submit_info and submit_info.get("selector"):
            validated["submit_button"] = {
                "selector": submit_info.get("selector", ""),
                "text": submit_info.get("text", "Submit")
            }
        
        return validated
    
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
                        "content": "You are an expert at mapping data to form fields. Always respond with valid JSON only, no additional text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": self.temperature,
                }
            )
            
            result_text = response['message']['content']
            result_text = self._clean_json_response(result_text)
            mapping = json.loads(result_text)
            
            logger.info(f"Data mapping complete. Mapped {len(mapping.get('field_mappings', {}))} fields")
            
            return mapping.get("field_mappings", {})
            
        except Exception as e:
            logger.error(f"Data mapping failed: {str(e)}")
            # Fallback to simple mapping
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
        Fallback simple mapping based on field purpose
        """
        mapping = {}
        field_purpose_map = {
            "name": saas_data.get("name", ""),
            "url": saas_data.get("url", ""),
            "email": saas_data.get("contact_email", ""),
            "description": saas_data.get("description", ""),
            "category": saas_data.get("category", ""),
            "logo": saas_data.get("logo_path", "")
        }
        
        for field in form_structure.get("fields", []):
            purpose = field.get("purpose", "").lower()
            selector = field.get("selector", "")
            
            if purpose in field_purpose_map and field_purpose_map[purpose]:
                mapping[selector] = field_purpose_map[purpose]
        
        return mapping
