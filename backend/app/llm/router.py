"""Smart Router: select model based on prompt length and complexity."""


class Router:
    """Route requests to fast or reasoning models based on complexity."""

    SHORT_THRESHOLD = 2000  # chars

    def __init__(self, fast_provider, reasoning_provider):
        self.fast = fast_provider
        self.reasoning = reasoning_provider

    def select(self, messages: list):
        """Pick provider based on message complexity."""
        total_length = sum(len(m.get("content", "")) for m in messages)
        if total_length < self.SHORT_THRESHOLD:
            return self.fast
        return self.reasoning
