"""Scan repository text files for high-confidence credential patterns."""

import subprocess
import sys
from pathlib import Path

from ai_growth_companion.observability.secrets import find_secrets


def repository_files() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
    )
    return tuple(Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item)


def main() -> None:
    paths = repository_files()
    findings: list[str] = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for finding in find_secrets(content):
            findings.append(f"{path.as_posix()}:{finding.line} [{finding.rule}]")

    if findings:
        print("Potential secrets detected; values are intentionally not printed:")
        print("\n".join(findings))
        sys.exit(1)
    print(f"Secret scan passed: {len(paths)} repository files checked")


if __name__ == "__main__":
    main()
