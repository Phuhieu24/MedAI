from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    APP_NAME: str = "MedAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/medai.db"

    ML_MODELS_DIR: str = str(BASE_DIR / "ml" / "versions")
    EXCEL_DATA_PATH: str = str(
        BASE_DIR.parent.parent
        / ".zenflow-attachments"
        / "79431e9e-da78-4740-a76a-277f6877140e.xlsx"
    )

    WEIGHTED_SCORE_WEIGHT: float = 0.40
    ML_SCORE_WEIGHT: float = 0.60

    FUZZY_MATCH_THRESHOLD: int = 75

    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    RAG_MAX_SOURCES: int = 8
    LLM_TRAINING_DIR: str = str(BASE_DIR / "data" / "llm_training")
    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = "openai_compatible"
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TIMEOUT_SECONDS: float = 8.0

    # ML Model Settings
    DIAGNOSIS_ENGINE: str = "xgboost"  # xgboost | llm
    ML_MODEL_TYPE: str = "xgboost"  # xgboost | ensemble (old)
    XGBOOST_N_ESTIMATORS: int = 200
    XGBOOST_MAX_DEPTH: int = 7
    XGBOOST_LEARNING_RATE: float = 0.1
    
    # Ollama Settings
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_TIMEOUT_SECONDS: float = 30.0
    
    # Vector DB Settings
    CHROMA_DB_PATH: str = str(BASE_DIR / "data" / "chroma")
    CHROMA_COLLECTION_NAME: str = "medical_data"
    
    # Explanation Settings
    LIME_ENABLED: bool = True
    LIME_NUM_SAMPLES: int = 1000

    class Config:
        env_file = ".env"


settings = Settings()
