"""
Pytest configuration and fixtures for submission workflow tests
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


# Event loop is handled by pytest-asyncio automatically
# No need to define it manually


@pytest.fixture
def test_saas_data():
    """Sample SaaS data for testing"""
    return {
        "name": "Test SaaS Product",
        "url": "https://example.com",
        "contact_email": "test@example.com",
        "description": "This is a test product for automation testing. It demonstrates the capabilities of the GENIE OPS system.",
        "category": "SaaS",
        "logo_path": None,
    }


@pytest.fixture
def test_form_url():
    """URL of the test form"""
    return "http://localhost:8080/test_form.html"


@pytest.fixture
def screenshot_dir():
    """Directory for test screenshots"""
    dir_path = Path(__file__).parent.parent / "storage" / "screenshots"
    dir_path.mkdir(parents=True, exist_ok=True)
    return str(dir_path)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test"""
    # Ensure storage directories exist
    os.makedirs("./storage/screenshots", exist_ok=True)
    os.makedirs("./storage/logos", exist_ok=True)

    yield

    # Cleanup after test (optional)
    # Can add cleanup logic here if needed


@pytest.fixture
def skip_if_ollama_unavailable():
    """Skip test if Ollama is not available"""
    try:
        from app.ai.form_reader import FormReader

        form_reader = FormReader()
        if not form_reader.client:
            pytest.skip("Ollama not available")
    except Exception as e:
        pytest.skip(f"Ollama initialization failed: {e}")


@pytest.fixture
def skip_if_test_server_unavailable():
    """Skip test if test server is not available"""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 8080))
        sock.close()
        if result != 0:
            pytest.skip("Test server not available on port 8080")
    except Exception:
        pytest.skip("Could not check test server availability")
