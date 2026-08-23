"""Run or safely preview the approved high-math golden evaluation set."""

import argparse
from pathlib import Path

from ai_growth_companion.evaluation.golden_set import GoldenCase, load_golden_set
from ai_growth_companion.evaluation.run_models import EvaluationMode
from ai_growth_companion.evaluation.runner import run_golden_evaluation, save_evaluation_run
from ai_growth_companion.prompts.registry import PromptRegistry
from ai_growth_companion.providers.base import EvaluationRequest
from ai_growth_companion.providers.fake import FakeLLMProvider, FakeScenario

DEFAULT_DATASET = Path("evals/golden/high_math_v0.1.json")
DEFAULT_OUTPUT = Path("evals/runs/fake-pipeline-v0.1.json")


def fake_provider_for_case(case: GoldenCase) -> FakeLLMProvider:
    """Select the deterministic Fake path matching a golden scenario."""
    return FakeLLMProvider(FakeScenario(case.scenario.value))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-cases", type=int, default=20, choices=range(1, 21))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and validate every Prompt without calling any Provider or writing results.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute a zero-cost dry run or deterministic fake-pipeline baseline."""
    args = parse_args()
    golden_set = load_golden_set(args.dataset)
    if args.dry_run:
        registry = PromptRegistry()
        rendered_characters = 0
        for case in golden_set.cases[: args.max_cases]:
            rendered = registry.render_evaluation(
                EvaluationRequest(
                    concept=case.concept,
                    question_text=case.question_text,
                    coverage_points=tuple(case.coverage_points),
                    answer_text=case.learner_answer,
                )
            )
            rendered_characters += len(rendered.system_message) + len(rendered.user_message)
        print(f"Dry run validated {args.max_cases} Prompt envelopes")
        print(f"Rendered characters: {rendered_characters}")
        print("Provider calls: 0; estimated cost: $0")
        return 0

    run = run_golden_evaluation(
        golden_set,
        provider_factory=fake_provider_for_case,
        mode=EvaluationMode.FAKE_PIPELINE,
        max_cases=args.max_cases,
        paid_calls_allowed=False,
        run_id="fake-pipeline-v0.1",
    )
    save_evaluation_run(run, args.output)
    print(f"Run: {run.run_id}")
    print(f"Cases: {run.summary.succeeded_cases}/{run.summary.total_cases} succeeded")
    print(
        f"Automatic checks: {run.summary.automatic_passed_cases}/{run.summary.total_cases} passed"
    )
    print(f"Human semantic review required: {run.summary.human_review_required_cases}")
    print(f"Provider calls were deterministic and free; results saved to {args.output}")
    return 0 if run.summary.failed_cases == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
