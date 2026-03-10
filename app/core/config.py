# app/core/config.py
# 환경 설정 관리

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_API_KEY: str
    CHROMA_DIR: str = "./chroma_data"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()