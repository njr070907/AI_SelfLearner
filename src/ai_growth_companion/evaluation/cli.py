"""CLI for free previews, Fake baselines, and explicitly approved real evaluations."""

import argparse
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ai_growth_companion.config import Settings
from ai_growth_companion.evaluation.golden_set import GoldenCase, load_golden_set
from ai_growth_companion.evaluation.run_models import EvaluationMode
from ai_growth_companion.evaluation.runner import (
    ProviderFactory,
    run_golden_evaluation,
    save_evaluation_run,
)
from ai_growth_companion.prompts.registry import PromptRegistry
from ai_growth_companion.providers.base import EvaluationRequest
from ai_growth_companion.providers.fake import FakeLLMProvider, FakeScenario
from ai_growth_companion.providers.openai_evaluation import OpenAIEvaluationProvider

DEFAULT_DATASET = Path("evals/golden/high_math_v0.1.json")
DEFAULT_FAKE_OUTPUT = Path("evals/runs/fake-pipeline-v0.1.json")


def fake_provider_for_case(case: GoldenCase) -> FakeLLMProvider:
    """Select the deterministic Fake path matching a golden scenario."""
    return FakeLLMProvider(FakeScenario(case.scenario.value))


def bounded_int(minimum: int, maximum: int) -> Callable[[str], int]:
    """Create a compact argparse integer validator without a huge choices listing."""

    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError("must be an integer") from error
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return number

    return parse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-cases", type=int, choices=range(1, 21))
    parser.add_argument(
        "--provider",
        choices=("fake", "openai"),
        default="fake",
        help="Fake is free and default; openai performs real paid network calls.",
    )
    parser.add_argument(
        "--model",
        help="Exact OpenAI model name; required for a real run unless LLM_MODEL is set.",
    )
    parser.add_argument("--timeout-seconds", type=bounded_int(1, 120), default=30)
    parser.add_argument(
        "--max-output-tokens",
        type=bounded_int(100, 5000),
        default=1200,
    )
    parser.add_argument(
        "--confirm-paid-calls",
        action="store_true",
        help="Required acknowledgement that a real OpenAI run can incur API charges.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and validate every Prompt without calling any Provider or writing results.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Execute a zero-cost preview, Fake baseline, or explicitly approved real run."""
    args = parse_args(argv)
    golden_set = load_golden_set(args.dataset)
    max_cases = args.max_cases or (1 if args.provider == "openai" else 20)
    if args.dry_run:
        registry = PromptRegistry()
        rendered_characters = 0
        for case in golden_set.cases[:max_cases]:
            rendered = registry.render_evaluation(
                EvaluationRequest(
                    concept=case.concept,
                    question_text=case.question_text,
                    coverage_points=tuple(case.coverage_points),
                    answer_text=case.learner_answer,
                )
            )
            rendered_characters += len(rendered.system_message) + len(rendered.user_message)
        print(f"Dry run validated {max_cases} Prompt envelopes")
        print(f"Rendered characters: {rendered_characters}")
        print("Provider calls: 0; estimated cost: $0")
        return 0

    if args.provider == "openai":
        if not args.confirm_paid_calls:
            raise SystemExit(
                "Real Provider run blocked: pass --confirm-paid-calls after approving API fees."
            )
        settings = Settings()
        api_key = settings.llm_api_key.get_secret_value().strip() if settings.llm_api_key else ""
        if not api_key:
            raise SystemExit("Real Provider run blocked: set LLM_API_KEY in the environment.")
        model = (args.model or settings.llm_model).strip()
        if not model or model.lower().startswith("fake"):
            raise SystemExit(
                "Real Provider run blocked: pass --model with an exact non-Fake model name."
            )
        provider = OpenAIEvaluationProvider(
            api_key=api_key,
            model=model,
            timeout_seconds=args.timeout_seconds,
            max_output_tokens=args.max_output_tokens,
        )

        def openai_provider_for_case(_case: GoldenCase) -> OpenAIEvaluationProvider:
            return provider

        provider_factory: ProviderFactory = openai_provider_for_case
        mode = EvaluationMode.REAL_PROVIDER
        paid_calls_allowed = True
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"openai-evaluator-v0.1-{timestamp}"
        output = args.output or Path(f"evals/runs/{run_id}.json")
    else:
        if args.confirm_paid_calls:
            raise SystemExit("--confirm-paid-calls is only valid with --provider openai.")
        provider_factory = fake_provider_for_case
        mode = EvaluationMode.FAKE_PIPELINE
        paid_calls_allowed = False
        run_id = "fake-pipeline-v0.1"
        output = args.output or DEFAULT_FAKE_OUTPUT

    run = run_golden_evaluation(
        golden_set,
        provider_factory=provider_factory,
        mode=mode,
        max_cases=max_cases,
        paid_calls_allowed=paid_calls_allowed,
        run_id=run_id,
    )
    save_evaluation_run(run, output)
    print(f"Run: {run.run_id}")
    print(f"Cases: {run.summary.succeeded_cases}/{run.summary.total_cases} succeeded")
    print(
        f"Automatic checks: {run.summary.automatic_passed_cases}/{run.summary.total_cases} passed"
    )
    print(f"Human semantic review required: {run.summary.human_review_required_cases}")
    print(f"Input/output tokens: {run.summary.input_tokens}/{run.summary.output_tokens}")
    if mode is EvaluationMode.FAKE_PIPELINE:
        print(f"Provider calls were deterministic and free; results saved to {output}")
    else:
        print(f"Real paid Provider calls completed with zero retries; results saved to {output}")
    return 0 if run.summary.failed_cases == 0 else 1
