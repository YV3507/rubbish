"""Tests for Headroom Content Router."""

import pytest

from app.headroom.router import (
    ContentRouter,
    create_default_router,
    detect_diff,
    detect_code,
    detect_log,
    detect_search,
    compress_code,
    compress_diff,
)


def test_create_default_router():
    """Default router has all strategies registered."""
    router = create_default_router()
    assert len(router._strategies) >= 5


def test_route_diff():
    """Diff content is routed to diff strategy."""
    router = create_default_router()
    diff_content = """diff --git a/file.py b/file.py
index abc..def 100644
--- a/file.py
+++ b/file.py
@@ -1,5 +1,6 @@
-old line
+new line
 context line
-more old
+more new"""
    strategy = router.route(diff_content)
    assert strategy is not None
    assert strategy.name == "diff"


def test_route_code():
    """Python code is routed to code strategy."""
    router = create_default_router()
    code = """def hello():
    print("world")

class Test:
    def foo(self):
        return 42
"""
    strategy = router.route(code)
    assert strategy is not None
    assert strategy.name == "code"


def test_compress_code_preserves_signatures():
    """Code compression keeps function/class signatures."""
    code = (
        "def hello():\n"
        "    print('a')\n"
        "    print('b')\n"
        "    print('c')\n"
        "\n"
        "def world():\n"
        "    return 42\n"
    )
    compressed, ratio = compress_code(code)
    assert "def hello():" in compressed
    assert "def world():" in compressed
    assert ratio >= 0  # compression ratio depends on input size


def test_route_log():
    """Log content is routed to log strategy."""
    router = create_default_router()
    log = """2024-01-01 12:00:00 ERROR connection timeout
2024-01-01 12:00:01 INFO retrying...
2024-01-01 12:00:02 WARN slow query detected"""
    strategy = router.route(log)
    assert strategy is not None
    assert strategy.name == "log"


def test_detect_diff_confidence():
    """detect_diff returns high confidence for diff-like content."""
    diff = "+added line\n-removed line\n@@ -1,2 +1,3 @@\nnormal line"
    confidence = detect_diff(diff)
    assert confidence > 0.3


def test_detect_code_confidence():
    """detect_code returns confidence for code-like content."""
    code = "def function(arg):\n    return arg * 2"
    confidence = detect_code(code)
    assert confidence > 0


def test_detect_search_confidence():
    """detect_search identifies grep/search results."""
    search = "file.py:42:def foo():\nfile.py:100:class Bar:\nother.py:1:import os"
    confidence = detect_search(search)
    assert confidence > 0


def test_compress_diff():
    """Diff compression preserves +/- lines."""
    diff = "+added\n-removed\n context\n+another\n-more"
    compressed, ratio = compress_diff(diff)
    assert "+added" in compressed
    assert "-removed" in compressed
    assert ratio > 0
