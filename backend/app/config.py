from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    llm_provider: str = "groq"

    narrator_voice_id: str = "pNInz6obpgDQGcFmaJgB"
    character_male_voice_id: str = "ErXwobaYiN019PkySvjV"
    character_female_voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    character_child_voice_id: str = "jBpfuIE2acCO8z3wKNLl"

    class Config:
        env_file = ".env"


settings = Settings()
