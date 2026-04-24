

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
  
    API_V1_STR:                  str = "/api/v1"
    DATABASE_URL:                str
    SECRET_KEY:                  str
    ALGORITHM:                   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database config
    DB_NAME: str
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: int

   
    TOGETHER_API_KEY: str

  
    HUGGINGFACE_API_KEY: str = ""

    # Twilio — sms_agent (SMS + Call)
    TWILIO_ACCOUNT_SID:  str = ""
    TWILIO_AUTH_TOKEN:   str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Gmail — email_agent
    EMAIL_USER: str = ""
    EMAIL_PASS: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )


settings = Settings()
