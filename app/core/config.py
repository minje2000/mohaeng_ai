from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_API_KEY: str
    SPRING_API_BASE_URL: str
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 20
    CHAT_LOG_DB_PATH: str = "./data/chatbot_logs.db"
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = 60
    CHAT_RATE_LIMIT_MAX_REQUESTS: int = 12

    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "mohaeng_rag"
    CHROMA_EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    CHROMA_TOP_K: int = 5
    CHROMA_FAQ_TOP_K: int = 2
    CHROMA_REINDEX_ON_BOOT: bool = False

    WATSONX_API_KEY: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_URL: str = "https://us-south.ml.cloud.ibm.com"
    WATSONX_MODEL_ID: str = "ibm/granite-4-h-small"
    WATSONX_TIMEOUT_SECONDS: int = 20

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
