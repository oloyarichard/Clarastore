import json

import requests
from django.conf import settings

from .base import AIProvider, AIProviderError


class OllamaProvider(AIProvider):
    """
    Calls a self-hosted Ollama instance over its local HTTP API. Uses
    /api/chat (not /api/generate) specifically so conversation_history
    can be passed as real chat turns — this is what gives the AI actual
    negotiation memory (spec section 9) instead of re-explaining the
    whole situation from scratch on every offer.
    """

    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = getattr(settings, 'OLLAMA_MODEL', 'phi4-mini')

    def negotiate(self, system_context: str, conversation_history: list) -> dict:
        messages = [{"role": "system", "content": system_context}] + conversation_history

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.7},
                },
                # Local CPU inference is slow (~10-25s typical for a short
                # exchange), and longer negotiations with more context to
                # process — or a machine under memory/swap pressure — can
                # take considerably longer. 45s proved too tight in real
                # testing (a genuine, in-progress response was cut off at
                # exactly that mark). 120s gives real headroom while still
                # bounding worst-case wait time to something reasonable.
                timeout=120,
            )
        except requests.RequestException as e:
            raise AIProviderError(f"Could not reach Ollama: {e}")

        if resp.status_code != 200:
            raise AIProviderError(f"Ollama returned {resp.status_code}: {resp.text[:300]}")

        try:
            raw_content = resp.json()["message"]["content"]
        except (KeyError, ValueError) as e:
            raise AIProviderError(f"Unexpected Ollama response shape: {e}")

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            # Even with format=json, a small local model can occasionally
            # wrap its output in stray text — this is exactly the kind of
            # thing the caller must treat as untrustworthy, not crash on.
            raise AIProviderError(f"AI did not return valid JSON: {raw_content[:300]}")

        if not isinstance(parsed, dict):
            raise AIProviderError(f"AI JSON was not an object: {raw_content[:300]}")

        return parsed
