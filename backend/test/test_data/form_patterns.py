"""Test data: Diverse form patterns for testing form analysis"""

FORM_TEST_CASES = [
    {
        "name": "minimal_form",
        "description": "Basic contact form with minimal markup",
        "html": """<form>
            <input name="name" type="text">
            <input name="email" type="email">
            <button type="submit">Send</button>
        </form>""",
        "expected_fields": 2,
        "expected_purposes": ["name", "email"],
        "difficulty": "easy",
    },
    {
        "name": "labeled_form",
        "description": "Form with proper labels and IDs",
        "html": """<form>
            <label for="product">Product Name</label>
            <input id="product" type="text">
            <label for="url">Website</label>
            <input id="url" type="url">
            <button>Submit</button>
        </form>""",
        "expected_fields": 2,
        "expected_purposes": ["name", "url"],
        "difficulty": "easy",
    },
    {
        "name": "complex_saas_form",
        "description": "Full SaaS directory submission form",
        "html": """<form id="saas-submit">
            <div class="form-group">
                <label>App/Tool Name</label>
                <input class="form-control" name="app_name" required>
            </div>
            <div class="form-group">
                <label>Homepage URL</label>
                <input type="url" name="site_url" placeholder="https://example.com">
            </div>
            <div class="form-group">
                <label>Contact Email</label>
                <input type="email" name="contact">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea name="desc" rows="5"></textarea>
            </div>
            <div class="form-group">
                <label>Category</label>
                <select name="cat">
                    <option>SaaS</option>
                    <option>Productivity</option>
                    <option>Marketing</option>
                </select>
            </div>
            <div class="form-group">
                <label>Logo Upload</label>
                <input type="file" name="logo" accept="image/*">
            </div>
            <button type="submit" class="btn btn-primary">Add to Directory</button>
        </form>""",
        "expected_fields": 6,
        "expected_purposes": [
            "name",
            "url",
            "email",
            "description",
            "category",
            "logo",
        ],
        "difficulty": "medium",
    },
    {
        "name": "react_style_form",
        "description": "Modern React-style form with data attributes",
        "html": """<form>
            <div data-field="name">
                <input id="startup-name" placeholder="Your startup name">
            </div>
            <div data-field="website">
                <input id="startup-url" placeholder="https://yoursite.com">
            </div>
            <button id="submit-btn">Submit Startup</button>
        </form>""",
        "expected_fields": 2,
        "expected_purposes": ["name", "url"],
        "difficulty": "medium",
    },
    {
        "name": "form_with_noise",
        "description": "Form with hidden fields and honeypots to ignore",
        "html": """<form>
            <input type="hidden" name="csrf" value="token123">
            <input type="hidden" name="form_id" value="submit_form">
            <div>
                <label>Product Name</label>
                <input name="product" type="text">
            </div>
            <div>
                <label>Website</label>
                <input name="url" type="url">
            </div>
            <input type="text" style="display:none" name="honeypot">
            <button>Submit Product</button>
        </form>""",
        "expected_fields": 2,
        "expected_purposes": ["name", "url"],
        "difficulty": "medium",
    },
    {
        "name": "ambiguous_labels",
        "description": "Form with unclear/generic labels",
        "html": """<form>
            <input name="field1" placeholder="Enter text here">
            <input name="field2" placeholder="Your link">
            <input name="field3" placeholder="Contact information">
            <textarea name="field4"></textarea>
            <button>Submit</button>
        </form>""",
        "expected_fields": 4,
        "expected_purposes": ["other", "url", "email", "description"],
        "difficulty": "hard",
    },
    {
        "name": "bootstrap_form",
        "description": "Bootstrap-styled form",
        "html": """<form class="needs-validation">
            <div class="mb-3">
                <label for="businessName" class="form-label">Business Name</label>
                <input type="text" class="form-control" id="businessName" required>
            </div>
            <div class="mb-3">
                <label for="businessWebsite" class="form-label">Website URL</label>
                <input type="url" class="form-control" id="businessWebsite">
            </div>
            <div class="mb-3">
                <label for="businessEmail" class="form-label">Email</label>
                <input type="email" class="form-control" id="businessEmail" required>
            </div>
            <button class="btn btn-primary" type="submit">Submit</button>
        </form>""",
        "expected_fields": 3,
        "expected_purposes": ["name", "url", "email"],
        "difficulty": "easy",
    },
]


def get_test_case(name: str) -> dict:
    """Get a specific test case by name"""
    for case in FORM_TEST_CASES:
        if case["name"] == name:
            return case
    return None


def get_test_cases_by_difficulty(difficulty: str) -> list:
    """Get all test cases of a specific difficulty"""
    return [case for case in FORM_TEST_CASES if case["difficulty"] == difficulty]
