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
    
    # AI/LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4"
    
    # Automation
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
