from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str = "5432"
    DB_NAME: str

    KIS_APP_KEY: str
    KIS_APP_SECRET: str
    KIS_CANO: str
    KIS_ACNT_PRDT_CD: str
    KIS_BASE_URL: str = "https://openapi.koreainvestment.com:9443"

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
