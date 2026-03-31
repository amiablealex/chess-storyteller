"""Google (Gemini) LLM provider."""

import google.generativeai as genai
from providers import LLMProvider, register_provider


@register_provider("google")
class GoogleProvider(LLMProvider):

    @property
    def provider_name(self) -> str:
        return "google"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            ),
        )
        response = model.generate_content(user_prompt)
        return response.text
