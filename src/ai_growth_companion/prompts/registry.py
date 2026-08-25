"""Load immutable Prompt bundles and render bounded evaluation inputs."""

import hashlib
import json
from pathlib import Path
from string import Template
from typing import Literal, Self

from pydantic import Field, model_validator

from ai_growth_companion.providers.base import EvaluationRequest
from ai_growth_companion.schemas.diagnosis import StrictSchema

PromptVersion = Literal["evaluator-v0.1", "evaluator-v0.2"]


class PromptManifest(StrictSchema):
    """Metadata required for a reproducible Prompt release."""

    prompt_id: Literal["evaluation"]
    version: PromptVersion
    purpose: str = Field(min_length=1, max_length=500)
    input_schema: Literal["evaluation-request-v0.1"]
    output_schema: Literal["provider-observation-v0.1"]
    owner: str = Field(min_length=1, max_length=100)
    updated_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    evaluation_set: Literal["high-math-mastery-v0.1"]
    system_file: Literal["system.md"]
    user_file: Literal["user.md"]
    required_placeholders: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def placeholders_must_be_unique(self) -> Self:
        if len(self.required_placeholders) != len(set(self.required_placeholders)):
            raise ValueError("Prompt placeholders must be unique")
        return self


class PromptBundle(StrictSchema):
    """Validated Prompt source plus a content hash."""

    manifest: PromptManifest
    system_template: str = Field(min_length=1)
    user_template: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RenderedPrompt(StrictSchema):
    """Messages ready for a Provider adapter without exposing supplier SDK types."""

    prompt_version: PromptVersion
    prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    system_message: str = Field(min_length=1)
    user_message: str = Field(min_length=1)


class PromptRegistry:
    """Resolve known Prompt versions from package data and reject template drift."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).parent / "templates"

    def load_evaluation(self, version: str = "v0.1") -> PromptBundle:
        """Load a versioned evaluation Prompt bundle."""
        if version not in {"v0.1", "v0.2"}:
            raise ValueError(f"Unknown evaluation Prompt version: {version}")

        bundle_path = self.root / "evaluation" / version
        manifest_path = bundle_path / "manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        manifest = PromptManifest.model_validate_json(manifest_bytes)
        system_template = (bundle_path / manifest.system_file).read_text(encoding="utf-8")
        user_template = (bundle_path / manifest.user_file).read_text(encoding="utf-8")
        self._validate_templates(manifest, system_template, user_template)

        digest = hashlib.sha256()
        digest.update(manifest_bytes)
        digest.update(system_template.encode("utf-8"))
        digest.update(user_template.encode("utf-8"))
        return PromptBundle(
            manifest=manifest,
            system_template=system_template,
            user_template=user_template,
            sha256=digest.hexdigest(),
        )

    def render_evaluation(
        self,
        request: EvaluationRequest,
        *,
        version: str = "v0.1",
    ) -> RenderedPrompt:
        """Render one minimal JSON envelope while preserving learner text verbatim."""
        bundle = self.load_evaluation(version)
        envelope = {
            "request": {"language": "zh-CN", "task": "evaluate_explanation"},
            "knowledge_context": {
                "concept": request.concept,
                "coverage_points": list(request.coverage_points),
            },
            "interaction": {
                "question": request.question_text,
                "user_answer": request.answer_text,
            },
        }
        user_message = Template(bundle.user_template).substitute(
            evaluation_input_json=json.dumps(envelope, ensure_ascii=False, indent=2)
        )
        return RenderedPrompt(
            prompt_version=bundle.manifest.version,
            prompt_sha256=bundle.sha256,
            system_message=bundle.system_template,
            user_message=user_message,
        )

    @staticmethod
    def _validate_templates(
        manifest: PromptManifest,
        system_template: str,
        user_template: str,
    ) -> None:
        system = Template(system_template)
        user = Template(user_template)
        if not system.is_valid() or not user.is_valid():
            raise ValueError("Prompt template syntax is invalid")
        if system.get_identifiers():
            raise ValueError("System Prompt must not contain runtime placeholders")
        actual = set(user.get_identifiers())
        expected = set(manifest.required_placeholders)
        if actual != expected:
            raise ValueError("Prompt template placeholders do not match manifest")
