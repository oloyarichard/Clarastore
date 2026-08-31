from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Raised when the AI provider fails to respond or returns something
    fundamentally unusable — callers should treat this as REJECT, never
    as license to skip validation."""
    pass


class AIProvider(ABC):
    """
    Common interface for whatever negotiates on the AI's behalf. The rest
    of the system only ever talks to this interface, never to a specific
    provider's SDK/API directly — swapping Ollama for a hosted API later
    means writing one new class, not touching the negotiation engine.
    """

    @abstractmethod
    def negotiate(self, system_context: str, conversation_history: list) -> dict:
        """
        `system_context` — a rendered string containing the market/product
        context and the rules the AI should reason within (word choice,
        tone, explanation only — never final authority on price).

        `conversation_history` — a list of {"role": "user"|"assistant",
        "content": str} dicts, oldest first, so the model has real memory
        of the negotiation instead of restarting reasoning each turn.

        Returns a dict parsed from the model's JSON output. The caller
        (negotiations.services) is responsible for validating every field
        before trusting it — this method's only job is getting a response
        back, not deciding if it's safe.
        """
        raise NotImplementedError
