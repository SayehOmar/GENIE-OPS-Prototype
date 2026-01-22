"""Rule-based field purpose classifier
Helps identify form field purposes without needing LLM
"""

import re
from typing import Dict, List, Optional
from app.utils.logger import logger


class FieldPurposeClassifier:
    """
    Rule-based classifier to determine form field purposes
    Uses keyword matching and regex patterns
    """
    
    PURPOSE_KEYWORDS = {
        "name": [
            r'\bname\b', r'\btitle\b', r'\bproduct\b', r'\bapp\b', r'\btool\b',
            r'\bcompany\b', r'\bbusiness\b', r'\bbrand\b', r'\bstartup\b',
            r'product.?name', r'app.?name', r'company.?name', r'business.?name',
            r'tool.?name', r'service.?name', r'project.?name'
        ],
        "url": [
            r'\burl\b', r'\bwebsite\b', r'\bsite\b', r'\blink\b', r'\bhomepage\b',
            r'\bdomain\b', r'\bweb\b', r'web.?site', r'home.?page', r'site.?url',
            r'website.?url', r'landing.?page'
        ],
        "email": [
            r'\bemail\b', r'\be-mail\b', r'\bmail\b', r'\bcontact\b',
            r'contact.?email', r'email.?address', r'your.?email'
        ],
        "description": [
            r'\bdescription\b', r'\bdesc\b', r'\babout\b', r'\bdetails\b',
            r'\binfo\b', r'\binformation\b', r'\bsummary\b', r'\bpitch\b',
            r'\boverview\b', r'tell.?us', r'describe', r'what.?does'
        ],
        "category": [
            r'\bcategory\b', r'\bcategories\b', r'\btag\b', r'\btags\b',
            r'\btype\b', r'\bindustry\b', r'\bniche\b', r'\bsector\b',
            r'select.?category', r'choose.?category'
        ],
        "logo": [
            r'\blogo\b', r'\bimage\b', r'\bicon\b', r'\bpicture\b',
            r'\bphoto\b', r'\bavatar\b', r'\bthumbnail\b',
            r'upload.?logo', r'upload.?image', r'company.?logo'
        ]
    }
    
    @classmethod
    def classify(cls, field_text: str, field_type: str = "") -> str:
        """
        Classify field purpose based on text analysis
        
        Args:
            field_text: Combined text from name, label, placeholder, id
            field_type: HTML input type (email, url, file, etc.)
        
        Returns:
            Purpose string: name, url, email, description, category, logo, other
        """
        field_text_lower = field_text.lower()
        
        # Type-based shortcuts (high confidence)
        if field_type == "email":
            return "email"
        if field_type == "url":
            return "url"
        if field_type == "file":
            return "logo"
        
        # Score each purpose based on keyword matches
        scores = {}
        for purpose, patterns in cls.PURPOSE_KEYWORDS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, field_text_lower)
                score += len(matches)
            scores[purpose] = score
        
        # Return purpose with highest score
        max_score = max(scores.values())
        if max_score > 0:
            best_purpose = max(scores, key=scores.get)
            logger.debug(f"Classified '{field_text[:30]}' as '{best_purpose}' (score: {max_score})")
            return best_purpose
        
        return "other"
    
    @classmethod
    def classify_fields(cls, fields: List[Dict]) -> List[Dict]:
        """
        Classify multiple fields at once
        
        Args:
            fields: List of field dicts with selector, type, name, label, placeholder
        
        Returns:
            Same fields list with 'purpose' added/updated
        """
        for field in fields:
            field_text = f"{field.get('name', '')} {field.get('label', '')} {field.get('placeholder', '')}"
            field_type = field.get('type', '')
            
            purpose = cls.classify(field_text, field_type)
            field['purpose'] = purpose
        
        return fields
    
    @classmethod
    def get_classification_hints(cls) -> str:
        """
        Generate prompt hints for LLM based on classification rules
        """
        hints = []
        for purpose, patterns in cls.PURPOSE_KEYWORDS.items():
            # Get first 5 keywords for each purpose
            keywords = [p.replace(r'\b', '').replace('\\', '').replace('.?', ' ') 
                       for p in patterns[:5]]
            hints.append(f"  - {purpose}: {', '.join(keywords)}")
        
        return "\n".join(hints)
