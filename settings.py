from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"))

    db_url: str
    test_db_url: str
    secret_key: str
    algorithm: str = 'HS256'
    access_expire_minutes: int = 30
    refresh_expire_days: int = 15
    redis_host: str
    redis_port: int = 6379


settings =Settings() # type:ignore [call-arg]
