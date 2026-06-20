"""Content Router: detect content type and route to the optimal compression strategy.

Implements a detector chain (Text → Code → Diff → Log → Search → Command → SmartCrusher),
mirroring Firefly's pkg/headroom/compression/router.go design.
"""

import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Strategy:
    """A compression strategy with its detector and compressor."""

    name: str
    detect: Callable[[str], float]  # returns confidence 0.0-1.0
    compress: Callable[[str], tuple[str, float]]  # returns (compressed, saved_ratio)


class ContentRouter:
    """Route content through the most appropriate compression strategy."""

    def __init__(self, min_confidence: float = 0.3):
        self._strategies: list[Strategy] = []
        self._min_confidence = min_confidence

    def register(self, strategy: Strategy):
        self._strategies.append(strategy)

    def route(self, content: str) -> Strategy | None:
        """Find the best matching strategy for the given content."""
        best_strategy = None
        best_score = 0.0

        for strategy in self._strategies:
            score = strategy.detect(content)
            if score > best_score and score >= self._min_confidence:
                best_score = score
                best_strategy = strategy

        return best_strategy

    def compress(self, content: str) -> tuple[str, str, float]:
        """Compress content using the best matching strategy.

        Returns (compressed_content, strategy_name, saved_ratio).
        """
        strategy = self.route(content)
        if strategy is None:
            return content, "pass", 0.0

        compressed, ratio = strategy.compress(content)
        return compressed, strategy.name, ratio


# ── Built-in detection functions ──

def detect_diff(content: str) -> float:
    """Git diff: lines starting with +/-/@@."""
    lines = content.split("\n")[:50]
    diff_lines = sum(1 for l in lines if l.startswith(("+", "-", "@@")))
    ratio = diff_lines / max(len(lines), 1)
    return 0.9 if ratio > 0.3 else ratio * 0.5


def compress_diff(content: str) -> tuple[str, float]:
    """Git diff: keep +/- lines, drop context lines."""
    lines = content.split("\n")
    kept = [l for l in lines if l.startswith(("+", "-", "@@", "diff", "index", "---", "+++"))]
    compressed = "\n".join(kept)
    saved = 1.0 - (len(compressed) / max(len(content), 1))
    return compressed, saved


def detect_code(content: str) -> float:
    """Source code: contains language keywords."""
    code_patterns = [
        r"\b(def|class|import|from|return|if __name__)\b",
        r"\b(fn|pub|impl|struct|enum|let mut)\b",
        r"\b(function|const|let|var|export|interface)\b",
        r"\b(int|float|void|string|bool)\b.*\(",
        r"->\s*(\w+|<)",
    ]
    score = sum(1 for p in code_patterns if re.search(p, content[:1000]))
    return min(1.0, score / 3)


def compress_code(content: str) -> tuple[str, float]:
    """Source code: keep signatures, trim function bodies."""
    lines = content.split("\n")
    kept: list[str] = []
    brace_depth = 0
    in_body = False

    for line in lines:
        if re.match(r"^\s*(def |class |fn |pub |func |function |interface |type |const |let )", line):
            kept.append(line)
            brace_depth = line.count("{") - line.count("}")
            in_body = brace_depth > 0
            continue
        if in_body:
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                kept.append(line)
                in_body = False
            continue
        kept.append(line)

    compressed = "\n".join(kept)
    saved = 1.0 - (len(compressed) / max(len(content), 1))
    return compressed, saved


def detect_log(content: str) -> float:
    """Log output: contains timestamps, log levels, stack traces."""
    log_patterns = [
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}",
        r"\b(ERROR|WARN|INFO|DEBUG|TRACE)\b",
        r"\b(at |traceback|error|exception)\b",
    ]
    score = sum(1 for p in log_patterns if re.search(p, content[:2000], re.IGNORECASE))
    return min(1.0, score / 2)


def compress_log(content: str) -> tuple[str, float]:
    """Log output: keep ERROR/WARN, fold duplicate INFO lines."""
    lines = content.split("\n")
    kept: list[str] = []
    seen_lines: set[str] = set()

    for line in lines:
        if re.search(r"\b(ERROR|WARN|FATAL|TRACE|CRASH)\b", line, re.IGNORECASE):
            kept.append(line)
        elif re.search(r"\b(INFO|DEBUG)\b", line, re.IGNORECASE):
            folded = re.sub(r"\d+", "N", line)
            if folded not in seen_lines:
                seen_lines.add(folded)
                kept.append(line)

    compressed = "\n".join(kept)
    saved = 1.0 - (len(compressed) / max(len(content), 1))
    return compressed, saved


def detect_search(content: str) -> float:
    """Search/grep results: lines with file:line format."""
    search_pattern = re.compile(r"^[\w./\\-]+:\d+:")
    score_lines = sum(1 for l in content.split("\n")[:30] if search_pattern.match(l))
    return 0.8 if score_lines > 5 else score_lines / 10


def compress_search(content: str) -> tuple[str, float]:
    """Search results: keep file paths and line numbers, trim surrounding."""
    lines = content.split("\n")
    kept = [l for l in lines if re.match(r"^[\w./\\-]+:\d+:|^─|^└|^\d+\)", l)]
    compressed = "\n".join(kept)
    saved = 1.0 - (len(compressed) / max(len(content), 1))
    return compressed, saved


def detect_command(content: str) -> float:
    """Shell command output: contains shell prompt, command prefix."""
    cmd_patterns = [r"^\$ ", r"^❯ ", r"^λ ", r"^PS>", r"^\[.*\]\$", r"exit code"]
    if content.strip() == content and len(content.split("\n")) > 3:
        return 0.0  # probably not a command
    score = sum(1 for p in cmd_patterns if re.match(p, content, re.MULTILINE))
    return min(0.7, score * 0.3)


def compress_command(content: str) -> tuple[str, float]:
    """Shell output: keep stderr, fold repeated stdout."""
    lines = content.split("\n")
    kept: list[str] = []
    stdout_count = 0

    for line in lines:
        if re.match(r"^(Error|error|fatal|warning|panic|thread)", line):
            kept.append(line)
        elif re.match(r"^\$ ", line) or re.match(r"^❯ ", line):
            kept.append(line)
            stdout_count = 0
        else:
            stdout_count += 1
            if stdout_count <= 3:
                kept.append(line)

    if stdout_count > 3:
        kept.append(f"... [{stdout_count - 3} more lines suppressed]")

    compressed = "\n".join(kept)
    saved = 1.0 - (len(compressed) / max(len(content), 1))
    return compressed, saved


def detect_text(content: str) -> float:
    """Generic text: catch-all at low confidence."""
    return 0.1  # lowest priority, only used when nothing else matches


def compress_text(content: str) -> tuple[str, float]:
    """Generic text: remove stop words, keep first/last paragraphs."""
    paragraphs = content.split("\n\n")
    if len(paragraphs) <= 3:
        return content, 0.0

    # Keep first 2 and last 1 paragraph
    kept = paragraphs[:2] + paragraphs[-1:]
    compressed = "\n\n".join(kept)
    saved = 1.0 - (len(compressed) / max(len(content), 1))
    return compressed, saved


def create_default_router() -> ContentRouter:
    """Create a ContentRouter with all built-in strategies registered."""
    router = ContentRouter()
    router.register(Strategy("diff", detect_diff, compress_diff))
    router.register(Strategy("code", detect_code, compress_code))
    router.register(Strategy("log", detect_log, compress_log))
    router.register(Strategy("search", detect_search, compress_search))
    router.register(Strategy("command", detect_command, compress_command))
    router.register(Strategy("text", detect_text, compress_text))
    return router
