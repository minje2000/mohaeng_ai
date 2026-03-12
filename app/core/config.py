from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_API_KEY: str
    SPRING_API_BASE_URL: str = "http://localhost:8080"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 20
    CHROMA_DIR: str = "./chroma_data"
    
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