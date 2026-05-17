from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Floor Plan Intelligence"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_HERE_CHANGE_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database (Neon / PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://neondb_owner:npg_rq5ew8LkpVEC@ep-proud-wildflower-ap44fblg-pooler.c-7.us-east-1.aws.neon.tech/3d_floor"

    class Config:
        env_file = ".env"

settings = Settings()
