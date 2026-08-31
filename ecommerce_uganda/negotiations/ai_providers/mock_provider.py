from .base import AIProvider


class MockProvider(AIProvider):
    """
    Deterministic stand-in for testing the negotiation engine without a
    live Ollama instance — including deliberately misbehaving in ways a
    real small model might, so the safety-validation layer gets exercised
    properly rather than only ever seeing well-formed input.
    """

    def __init__(self, fixed_response=None):
        self.fixed_response = fixed_response

    def negotiate(self, system_context: str, conversation_history: list) -> dict:
        if self.fixed_response is not None:
            return self.fixed_response
        # Default: a plausible-looking but generic counter, roughly
        # splitting the difference — good enough for exercising the
        # normal (non-adversarial) path in tests.
        return {
            "decision": "COUNTER",
            "price": 0,
            "confidence": 0.5,
            "reason_code": "default_counter",
            "message": "Let's meet somewhere in the middle.",
        }
