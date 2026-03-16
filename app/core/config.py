from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_API_KEY: str
    SPRING_API_BASE_URL: str
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 20
    CHAT_LOG_DB_PATH: str = "./data/chatbot_logs.db"
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = 60
    CHAT_RATE_LIMIT_MAX_REQUESTS: int = 12
    
    # Watsonx 추가
    WATSONX_API_KEY: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_URL: str = "https://us-south.ml.cloud.ibm.com"
    WATSONX_MODEL_ID: str = "ibm/granite-4-h-small"
    WATSONX_TIMEOUT_SECONDS: int = 20

    class Config:
        env_file = ".env"
        extra = "ignore"
        
        


settings = Settings()
