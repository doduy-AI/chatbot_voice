from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.middleware.cors import CORSMiddleware

class Settings(BaseSettings):
    API_VERSION : str = "/api/v1"
    VOICE_NAM : str = "VOICE_NAM"
    VOICE_NU : str = "VOICE_NU"
    VOICE_TEST : str = "VOICE_TEST"
    VOICE_ID_NAM : str = "VOICE_ID_NAM"
    VOICE_ID_NU : str = "VOICE_ID_NU"
    TEXT_VOICE_NAM : str = "TEXT_VOICE_NAM"
    TEXT_VOICE_NU : str = "TEXT_VOICE_NU"
    PORT : int = "PORT"
    DEVICE : str = "DEVICE"
    HOST : str = "HOST"
    API_GEMINI : str = "API_GEMINI"
    PROJECT_NAME : str = "PROJECT_NAME"
    URL_LLM : str = "URL_LLM"
    model_config = SettingsConfigDict(env_file=".env",env_file_encoding='utf-8')


def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # Cho phép tất cả các nguồn
        allow_credentials=True,
        allow_methods=["*"],          # Cho phép tất cả các phương thức (GET, POST,...)
        allow_headers=["*"],          # Cho phép tất cả các headers
    )
settings = Settings()