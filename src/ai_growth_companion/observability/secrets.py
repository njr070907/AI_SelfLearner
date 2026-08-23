"""Small deterministic secret scanner used as a blocking Sprint 0 guard."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretFinding:
    rule: str
    line: int


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "credentialed-url",
        re.compile(r"https?://[^\s/:]+:[^\s/@]+@[^\s/]+", re.IGNORECASE),
    ),
)


def find_secrets(text: str) -> tuple[SecretFinding, ...]:
    """Return locations and rule names without echoing the candidate secret."""
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(SecretFinding(rule=rule, line=line_number))
    return tuple(findings)
