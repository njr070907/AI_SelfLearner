"""Validate the canonical Sprint 1 golden set and summarize review status."""

from collections import Counter
from pathlib import Path

from ai_growth_companion.evaluation.golden_set import ReviewStatus, load_golden_set

DEFAULT_GOLDEN_SET = Path("evals/golden/high_math_v0.1.json")


def main() -> int:
    """Fail on schema/provenance errors and print a concise human-review summary."""
    golden_set = load_golden_set(DEFAULT_GOLDEN_SET)
    scenarios = Counter(case.scenario.value for case in golden_set.cases)
    reviews = Counter(case.human_review.status.value for case in golden_set.cases)

    print(f"Validated: {golden_set.dataset_id}")
    print(f"Cases: {len(golden_set.cases)} across 5 concepts")
    print(f"Scenarios: {dict(sorted(scenarios.items()))}")
    print(f"Human review: {dict(sorted(reviews.items()))}")

    if all(case.human_review.status is ReviewStatus.APPROVED for case in golden_set.cases):
        print("Status: structurally valid and human-approved")
    else:
        print("Status: structurally valid; human review is still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
