"""Anthropic (Claude) LLM provider."""

import anthropic
from providers import LLMProvider, register_provider


@register_provider("anthropic")
class AnthropicProvider(LLMProvider):

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
