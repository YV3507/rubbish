"""Tests for AutoPlan two-stage planning detection."""

import pytest

from app.autoplan.detector import AutoPlanDetector


def test_heuristic_simple_request():
    """Simple requests get low scores."""
    detector = AutoPlanDetector()
    score = detector.heuristic_score("what is 2+2?")
    assert score <= 1


def test_heuristic_complex_request():
    """Complex multi-file refactoring requests get high scores."""
    detector = AutoPlanDetector()
    score = detector.heuristic_score(
        "Refactor the authentication module to use OAuth2. "
        "We need to update auth.py, create a new tokens.py, "
        "and modify the middleware in app/middleware/auth.py"
    )
    assert score >= 2
    assert score <= 4


def test_heuristic_keyword_detection():
    """Keywords like 'refactor' and 'redesign' increase score."""
    detector = AutoPlanDetector()
    score = detector.heuristic_score("refactor the entire codebase architecture")
    assert score >= 2  # 'refactor' gives +2; <=4 chars gives no length bonus


@pytest.mark.asyncio
async def test_needs_plan_simple():
    """Simple request → no plan needed."""
    detector = AutoPlanDetector()
    needed, reason = await detector.needs_plan("hello world")
    assert not needed


@pytest.mark.asyncio
async def test_needs_plan_complex():
    """Complex request → plan needed."""
    detector = AutoPlanDetector()
    needed, reason = await detector.needs_plan(
        "Refactor the entire API layer from REST to GraphQL. "
        "Migrate all routes, update schema definitions, "
        "and modify the frontend data fetching layer."
    )
    assert needed
