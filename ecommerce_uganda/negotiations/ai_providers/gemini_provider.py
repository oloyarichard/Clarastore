import json

import requests
from django.conf import settings

from .base import AIProvider, AIProviderError


class GeminiProvider(AIProvider):
    """
    Calls Google's Gemini API (generateContent). Same interface as
    OllamaProvider — the negotiation engine, floor validation, and every
    test built against it don't know or care which provider is actually
    answering. Swapping providers is exactly this file plus one setting,
    nothing else in the system changes.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', '')
        self.model = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')

    def negotiate(self, system_context: str, conversation_history: list) -> dict:
        if not self.api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured.")

        # Our conversation_history uses {"role": "user"|"assistant", ...}
        # — the same shape Ollama/OpenAI-style chat APIs use. Gemini uses
        # "model" instead of "assistant" for its own turns; everything
        # else about the shape is otherwise the same idea.
        contents = [
            {
                "role": "model" if turn["role"] == "assistant" else "user",
                "parts": [{"text": turn["content"]}],
            }
            for turn in conversation_history
        ]

        payload = {
            "systemInstruction": {"parts": [{"text": system_context}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json",
            },
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/{self.model}:generateContent",
                headers={
                    "x-goog-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                # Gemini is typically fast (well under Ollama's local
                # inference time), but a generous bound still matters —
                # a slow or rate-limited response should fail safe
                # rather than hang the customer's request indefinitely.
                timeout=30,
            )
        except requests.RequestException as e:
            raise AIProviderError(f"Could not reach Gemini: {e}")

        if resp.status_code == 429:
            # Rate-limited — this is exactly what the free-tier burst
            # limit look like in practice. Treated the same as any other
            # provider failure: fails safe to REJECT, never crashes the
            # customer's negotiation.
            raise AIProviderError("Gemini rate limit hit.")

        if resp.status_code != 200:
            raise AIProviderError(f"Gemini returned {resp.status_code}: {resp.text[:300]}")

        try:
            data = resp.json()
            raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError) as e:
            raise AIProviderError(f"Unexpected Gemini response shape: {e}")

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            raise AIProviderError(f"AI did not return valid JSON: {raw_content[:300]}")

        if not isinstance(parsed, dict):
            raise AIProviderError(f"AI JSON was not an object: {raw_content[:300]}")

        return parsed
