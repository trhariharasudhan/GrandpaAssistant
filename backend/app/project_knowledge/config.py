from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_EXTENSIONS = frozenset(
    {
        ".py",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
    }
)

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)

MAX_CONTEXT_RESULTS = 5
MAX_CONTEXT_TOTAL_CHARS = 6000
MAX_CONTEXT_BLOCK_CHARS = 1500
CONTEXT_HEADER = "PROJECT KNOWLEDGE CONTEXT"
CONTEXT_SNIPPET_SEPARATOR = "\n---\n"

IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".codex",
        ".python311",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "coverage",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "runtime",
        "logs",
        "reference",
        "system_prompts_leaks",
    }
)


@dataclass(frozen=True)
class ProjectKnowledgeLimits:
    max_file_size_bytes: int = 512 * 1024
    max_scan_files: int = 5000
    max_directory_depth: int = 12
    max_line_count_bytes: int = 256 * 1024
    max_read_bytes: int = 200_000
    max_chunk_chars: int = 2000
    chunk_overlap_chars: int = 200
    max_chunks_per_file: int = 50
    binary_detection_bytes: int = 4096
    min_token_length: int = 2
    max_query_chars: int = 500
    max_search_results: int = 10
    max_result_snippet_chars: int = 500
    max_context_results: int = MAX_CONTEXT_RESULTS
    max_context_total_chars: int = MAX_CONTEXT_TOTAL_CHARS
    max_context_block_chars: int = MAX_CONTEXT_BLOCK_CHARS


DEFAULT_LIMITS = ProjectKnowledgeLimits()
