from langchain_core.language_models import BaseChatModel

from app.config import settings


def get_llm() -> BaseChatModel:
    provider = settings.llm_provider.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(api_key=settings.groq_api_key, model="llama-3.3-70b-versatile", max_tokens=8192)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(api_key=settings.openai_api_key, model="gpt-4o", max_tokens=8192)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(api_key=settings.anthropic_api_key, model="claude-sonnet-4-5-20250929", max_tokens=8192)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
