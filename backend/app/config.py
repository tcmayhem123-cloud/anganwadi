"""
Application Configuration Settings.
Loads configuration from environment or sets secure production defaults.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Anganwadi / ICDS Child Growth Monitoring System (ACGMS)"
    VERSION: str = "1.0.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "acgms-secure-secret-key-pec-chandigarh-24106011")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for field operation
    LOCKOUT_MAX_ATTEMPTS: int = 5          # FR-AUTH-03
    LOCKOUT_DURATION_MINUTES: int = 15     # FR-AUTH-03
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./acgms.db")
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")

    # Business rule thresholds
    N_RECOVERY_CONSECUTIVE_MONTHS: int = 2  # FR-SM-03 / T13
    MAM_TO_NORMAL_CONSECUTIVE_MONTHS: int = 1 # T8

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
