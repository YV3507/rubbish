"""AutoPlan: two-stage planning requirement detection.

Stage 1 → Heuristic scoring (cheap keyword match, fast path for simple requests)
Stage 2 → LLM classifier (only for borderline cases, 3-second timeout)

Reference: Firefly pkg/autoplan/
"""

import asyncio
import re
from typing import AsyncGenerator

from app.config import config


class AutoPlanDetector:
    """Detect whether user input requires a planning step before execution.

    Score interpretation:
        0-1  → No plan needed (simple request)
        2    → Borderline, invoke LLM classifier
        3-4  → Plan required (complex request)
    """

    def __init__(self, llm_classifier=None):
        self._threshold = config.autoplan_heuristic_threshold
        self._classifier_timeout = config.autoplan_classifier_timeout_sec
        self._llm = llm_classifier

        # Keywords grouped by weight
        self._high_weight = {
            "refactor", "redesign", "architect", "migrate", "rewrite",
            "restructure", "overhaul", "reorganize",
        }
        self._medium_weight = {
            "implement", "design", "create", "build", "develop", "add",
            "change", "update", "modify", "improve",
        }
        self._low_weight = {
            "plan", "what", "how", "approach", "strategy", "step",
            "analyze", "investigate", "explore",
        }

    def heuristic_score(self, user_input: str) -> int:
        """Score user input from 0 (simple) to 4 (complex)."""
        text = user_input.lower()
        score = 0

        # Length heuristic: longer inputs tend to be more complex
        if len(text) > 500:
            score += 1
        if len(text) > 1500:
            score += 1

        # Code references suggest multi-file changes
        if re.search(r"(file|class|function|module|component).*(create|change|edit|refactor)", text):
            score += 1

        # Multiple file paths suggest cross-cutting changes
        file_refs = re.findall(r"[\w./\\-]+\.[a-z]+", text)
        if len(set(file_refs)) > 2:
            score += 1

        # Keyword matching
        words = set(re.findall(r"\b[a-z]+\b", text))
        high = self._high_weight & words
        medium = self._medium_weight & words
        low = self._low_weight & words

        score += len(high) * 2
        score += len(medium)
        score += len(low) // 2

        # Normalize to 0-4
        return min(4, score)

    async def needs_plan(self, user_input: str) -> tuple[bool, str]:
        """Determine if the input needs planning.

        Returns (needs_plan, reason).
        """
        heuristic = self.heuristic_score(user_input)

        if heuristic <= 1:
            return False, f"heuristic: score={heuristic} (simple request)"
        elif heuristic >= 3:
            return True, f"heuristic: score={heuristic} (complex request)"
        else:
            # Borderline (score=2): use LLM classifier
            if self._llm is None:
                return False, f"heuristic: score={heuristic} (no LLM classifier, conservative skip)"
            return await self._classify(user_input)

    async def _classify(self, user_input: str) -> tuple[bool, str]:
        """LLM-based classifier for borderline cases."""
        try:
            result = await asyncio.wait_for(
                self._llm.summarize(
                    f"Does the following request require a multi-step plan before execution? "
                    f"Answer only YES or NO.\n\n{user_input}"
                ),
                timeout=self._classifier_timeout,
            )
            is_plan = "yes" in result.lower()
            return is_plan, f"llm_classifier: {'plan needed' if is_plan else 'no plan needed'}"
        except asyncio.TimeoutError:
            # Fallback to heuristic on timeout
            fallback = self.heuristic_score(user_input) >= 2
            return fallback, f"llm_fallback: classifier timed out, heuristic={fallback}"
