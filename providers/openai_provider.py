"""OpenAI (GPT) LLM provider."""

from openai import OpenAI
from providers import LLMProvider, register_provider


@register_provider("openai")
class OpenAIProvider(LLMProvider):

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
