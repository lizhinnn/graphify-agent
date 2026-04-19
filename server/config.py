from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv


# 手动加载 .env 文件，确保其优先级高于系统环境变量
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path, override=True)


class Settings(BaseSettings):
    """应用配置类"""
    # API 配置
    API_KEY: str = "your_api_key_here"
    BASE_URL: str = "http://localhost:8000"
    
    # LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    
    # 存储路径
    UPLOADS_DIR: str = "storage/uploads"
    GRAPHS_DIR: str = "storage/graphs"
    DB_DIR: str = "storage/db"
    
    class Config:
        case_sensitive = True
        extra = "ignore"


# 创建全局配置实例
settings = Settings()

# 启动时检查必要的配置
if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.strip() == "":
    raise ValueError("OPENAI_API_KEY is required in .env file. Please set it to your OpenAI API key.")

