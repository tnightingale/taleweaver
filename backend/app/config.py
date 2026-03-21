import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM Provider Configuration
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "groq"
    
    # Text-to-Speech Configuration
    elevenlabs_api_key: str = ""
    narrator_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    character_male_voice_id: str = "ErXwobaYiN019PkySvjV"
    character_female_voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    character_child_voice_id: str = "jBpfuIE2acCO8z3wKNLl"
    
    # Once Platform Variables (automatically provided by Once)
    secret_key_base: str = ""  # Unique identifier for cryptographic signing
    disable_ssl: bool = False  # Set to true if running without SSL
    
    # SMTP Configuration (provided by Once email settings)
    smtp_address: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    mailer_from_address: str = ""
    
    # Storage Paths
    storage_path: Path = Path(os.environ.get("STORAGE_PATH", "/storage"))
    jobs_path: Path = Path(os.environ.get("JOBS_PATH", "/storage/jobs"))
    music_path: Path = Path(os.environ.get("MUSIC_PATH", "/storage/music"))

    class Config:
        env_file = ".env"


settings = Settings()
