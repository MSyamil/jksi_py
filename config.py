import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # AI Models
    # Available options: gemini-1.5-flash, gemini-1.5-pro, gpt-4o, gpt-4o-mini
    DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "gemini") # 'gemini' or 'openai'
    DEFAULT_MODEL = os.getenv("AI_MODEL", "gemini-3.1-flash-lite")
    
    # Browser Settings
    HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "15000")) # ms
    SLOW_MO = int(os.getenv("SLOW_MO", "500")) # ms between actions to make them visible
    
    # Application Config
    TARGET_URL = "https://www.saucedemo.com/"

    @classmethod
    def update_keys(cls, gemini_key: str = None, openai_key: str = None, provider: str = None, model: str = None):
        """Helper to dynamically update configuration at runtime (e.g., from Streamlit UI)"""
        if gemini_key is not None:
            cls.GEMINI_API_KEY = gemini_key
            os.environ["GEMINI_API_KEY"] = gemini_key
        if openai_key is not None:
            cls.OPENAI_API_KEY = openai_key
            os.environ["OPENAI_API_KEY"] = openai_key
        if provider is not None:
            cls.DEFAULT_PROVIDER = provider
        if model is not None:
            cls.DEFAULT_MODEL = model

    @classmethod
    def get_active_key(cls) -> str:
        if cls.DEFAULT_PROVIDER == "gemini":
            return cls.GEMINI_API_KEY
        return cls.OPENAI_API_KEY
