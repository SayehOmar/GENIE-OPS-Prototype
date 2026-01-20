"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "GENIE OPS"
    DEBUG: bool = True
    
    # Database
    # PostgreSQL connection string format: postgresql://user:password@localhost/dbname
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/genie_ops"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Storage
    STORAGE_PATH: str = "./storage"
    LOGOS_PATH: str = "./storage/logos"
    
    # AI/LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:7b"  # Recommended: qwen2.5:7b for HTML form analysis
    # Alternatives: llama3.2:3b (fast), deepseek-coder:6.7b (technical), mistral:7b (balanced)
    LLM_TEMPERATURE: float = 0.1  # Low temperature for consistent structured output
    LLM_USE_OPENAI_COMPATIBLE: bool = True  # Use OpenAI-compatible endpoint
    
    # Automation
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000
    
    # Workflow Manager
    WORKFLOW_MAX_CONCURRENT: int = 3  # Max concurrent submissions
    WORKFLOW_BATCH_SIZE: int = 10  # Batch size for processing
    WORKFLOW_PROCESSING_INTERVAL: int = 30  # Seconds between processing cycles
    WORKFLOW_MAX_RETRIES: int = 3  # Max retry attempts per submission
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
