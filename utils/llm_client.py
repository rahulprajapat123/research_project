"""
LLM client - unified interface for OpenAI, Anthropic, Azure OpenAI
"""
from typing import Optional
import openai
import anthropic
from config import get_settings

settings = get_settings()


class LLMClient:
    """Unified LLM client supporting multiple providers"""
    
    def __init__(self):
        self.provider = settings.llm_provider
        self.client = None
        if self.provider not in {"openai", "anthropic"}:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def complete(
        self,
        prompt: str,
        temperature: float = None,
        max_tokens: int = None,
        model: str = None
    ) -> str:
        """
        Generate completion from prompt
        
        Returns the response text
        """
        temperature = temperature or settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens
        model = model or settings.llm_model
        client = self._get_client()
        
        if self.provider == "openai":
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a research analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        
        elif self.provider == "anthropic":
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _get_client(self):
        if self.client is not None:
            return self.client

        if self.provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when llm_provider=openai")
            self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            return self.client

        if self.provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when llm_provider=anthropic")
            self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            return self.client

        raise ValueError(f"Unsupported provider: {self.provider}")
