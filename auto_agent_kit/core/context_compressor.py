"""
AutoAgentKit - Context Compressor
==================================
Incremental context compression with instruction re-injection.
Based on the battle-tested enhanced_context_compressor pattern.

Usage:
    compressor = ContextCompressor(max_tokens=4000)
    compressed = compressor.compress(raw_text, key_instructions="...")
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CompressionState:
    """Tracks compression state across multiple rounds."""
    total_original_chars: int = 0
    total_compressed_chars: int = 0
    compression_rounds: int = 0
    last_summary: str = ""
    summaries: List[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        if self.total_original_chars == 0:
            return 1.0
        return self.total_compressed_chars / max(self.total_original_chars, 1)

    def record(self, original: str, compressed: str):
        self.total_original_chars += len(original)
        self.total_compressed_chars += len(compressed)
        self.compression_rounds += 1
        self.last_summary = compressed
        self.summaries.append(compressed)


class ContextCompressor:
    """
    Incremental context compressor with instruction re-injection.

    Features:
    - Structured segment summarization (goal, decisions, files, errors, next)
    - Incremental compression (only summarize new segments)
    - Instruction re-injection at compression boundaries
    - Configurable token budget and reserve
    """

    SEGMENT_HEADERS = [
        "goal", "decision", "decision point", "progress",
        "file", "files modified", "error", "blocker",
        "next step", "next action", "context", "summary",
        "key", "note", "lesson", "learning",
    ]

    def __init__(
        self,
        max_tokens: int = 4000,
        reserve_tokens: int = 1000,
        recent_turns_preserve: int = 3,
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.recent_turns_preserve = recent_turns_preserve
        self.state = CompressionState()
        self._instructions: List[str] = []

    def set_instructions(self, *instructions: str):
        """Set key instructions to re-inject after compression."""
        self._instructions = list(instructions)

    def compress(
        self,
        text: str,
        key_instructions: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """
        Compress text if it exceeds the token budget.

        Args:
            text: Raw text to compress
            key_instructions: Instructions to re-inject after compression
            force: Force compression even if under budget

        Returns:
            Compressed text
        """
        estimated_tokens = len(text) // 4  # rough estimate

        if not force and estimated_tokens < self.max_tokens - self.reserve_tokens:
            return text

        if key_instructions:
            self.set_instructions(key_instructions)

        # Structured compression
        segments = self._split_segments(text)
        compressed_parts = []

        for header, content in segments:
            compressed = self._summarize_segment(header, content)
            compressed_parts.append(f"[{header}]: {compressed}")

        # Preserve recent turns
        recent = self._extract_recent_turns(text)
        if recent:
            compressed_parts.append(f"[recent]: {recent}")

        # Re-inject instructions
        if self._instructions:
            inj = " | ".join(self._instructions)
            compressed_parts.append(f"[instructions]: {inj}")

        result = "\n".join(compressed_parts)
        self.state.record(text, result)
        return result

    def _split_segments(self, text: str) -> List[Tuple[str, str]]:
        """Split text into structured segments."""
        lines = text.split("\n")
        segments: List[Tuple[str, str]] = []
        current_header = "general"
        current_content: List[str] = []

        for line in lines:
            stripped = line.strip().lower().rstrip(":")
            # Also strip colon that may appear after header word
            # e.g. "goal: Build a thing" -> "goal" after splitting on ':'
            first_word = stripped.split(":")[0].strip() if ":" in stripped else stripped
            # Check if line starts with a known segment header
            matched_header = None
            for h in self.SEGMENT_HEADERS:
                if stripped == h or stripped.startswith(h + " ") or first_word == h:
                    matched_header = h
                    break
            if matched_header:
                if current_content:
                    segments.append((current_header, "\n".join(current_content)))
                current_header = matched_header
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            segments.append((current_header, "\n".join(current_content)))

        return segments

    def _summarize_segment(self, header: str, content: str) -> str:
        """Summarize a single segment."""
        if len(content) < 200:
            return content.strip()

        lines = content.strip().split("\n")
        # Keep first and last lines, summarize middle
        if len(lines) <= 4:
            return content.strip()

        first = lines[0].strip()
        last = lines[-1].strip()
        middle_count = len(lines) - 2

        return f"{first} (...{middle_count} lines...) {last}"

    def _extract_recent_turns(self, text: str) -> str:
        """Extract the most recent conversation turns."""
        lines = text.split("\n")
        if len(lines) <= self.recent_turns_preserve * 2:
            return ""

        recent = lines[-(self.recent_turns_preserve * 2):]
        return "\n".join(recent)

    def get_state(self) -> dict:
        """Get compression state as dict."""
        return {
            "total_original_chars": self.state.total_original_chars,
            "total_compressed_chars": self.state.total_compressed_chars,
            "compression_ratio": round(self.state.ratio, 3),
            "compression_rounds": self.state.compression_rounds,
        }

    def reset(self):
        """Reset compression state."""
        self.state = CompressionState()
        self._instructions = []
