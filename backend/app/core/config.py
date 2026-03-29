from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "CamaraDOC"
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DEFAULT_ADMIN_EMAIL: str = "admin@camaradoc.local"
    DEFAULT_ADMIN_PASSWORD: str = "123456"

    STORAGE_ORIGINAL: str = "/storage/original"
    STORAGE_OCR: str = "/storage/ocr"
    STORAGE_TEMP: str = "/storage/temp"


settings = Settings()
