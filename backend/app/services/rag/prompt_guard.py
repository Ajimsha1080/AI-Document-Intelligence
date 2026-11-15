import re
import logging
from typing import Tuple

logger = logging.getLogger("prompt_guard")

# Patterns commonly used in prompt injection / delimiter escaping
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(an\s+unrestricted|a\s+different|in\s+dan\s+mode)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?guidelines", re.IGNORECASE),
    re.compile(r"print\s+(the\s+)?(secret|password|api\s*key|auth\s*token)", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
    re.compile(r"###\s*system", re.IGNORECASE),
    re.compile(r"###\s*instruction", re.IGNORECASE),
]

def check_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Scans query or untrusted text for adversarial prompt injection patterns.
    Returns (is_suspicious, reason).
    """
    if not text:
        return False, ""

    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            reason = f"Potential injection pattern detected: '{match.group(0)}'"
            logger.warning(f"Sovereign Prompt Guard: {reason}")
            return True, reason

    return False, ""

def sanitize_untrusted_text(text: str) -> str:
    """
    Sanitizes untrusted document text so it cannot break LLM/RAG context frames.
    Neutralizes markdown codeblock escapes and system instruction delimiters.
    """
    if not text:
        return ""

    sanitized = text.replace("```", "'''")
    sanitized = re.sub(r"<\|[^|>]*\|>", "", sanitized)
    sanitized = re.sub(r"###\s*(System|Instruction|Assistant)", r"[\1]", sanitized, flags=re.IGNORECASE)
    return sanitized.strip()
