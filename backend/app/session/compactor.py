"""Compactor: token budget compression — summarize oldest messages when over budget.

Configurable via config.session_token_budget / session_tokens_per_char.
"""

from app.config import config
from app.session.session import Entry, Session


class Compactor:
    """Summarize older messages to keep within token budget."""

    def __init__(self, llm_provider=None):
        self._llm = llm_provider
        self._token_budget = config.session_token_budget
        self._tokens_per_char = config.session_tokens_per_char

    async def compact(self, session: Session):
        """Compact session by summarizing oldest messages."""
        total_chars = sum(len(str(e.content)) for e in session.entries)
        total_tokens = total_chars // self._tokens_per_char

        if total_tokens <= self._token_budget:
            return

        budget_chars = self._token_budget * self._tokens_per_char
        running = 0
        keep_from = 0

        for i in range(len(session.entries) - 1, -1, -1):
            char_len = len(str(session.entries[i].content))
            if running + char_len > budget_chars:
                keep_from = i + 1
                break
            running += char_len

        if keep_from > 1 and self._llm:
            to_summarize = session.entries[:keep_from]
            summary_text = "\n".join(str(e.content) for e in to_summarize)
            summary = await self._llm.summarize(summary_text)
            session.entries = [
                Entry(role="system", content=f"[Summary of earlier conversation]: {summary}"),
                *(session.entries[keep_from:]),
            ]
