# Archivo autogenerado por sync_env.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Entorno(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    
    ENV: str
    URL_SGC: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASS: str
    WEBHOOK_DISCORD: str

# Instancia global lista para ser importada
env = Entorno()
