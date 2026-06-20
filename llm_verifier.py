"""
LLM Verifier — structured semantic triage over a context pack (not raw data).

Providers:
  - mock: deterministic summary from failed rules (no external API)
  - openai: structured JSON via Chat Completions API
  - none: disabled
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from llm_config import llm_model, llm_provider

logger = logging.getLogger("datalens.llm")

PROMPT_VERSION = "survey-v1"


class VerifiedIssue(BaseModel):
    issue_id: str
    rule_id: Optional[str] = None
    column: Optional[str] = None
    severity: Literal["critical", "warning", "info"] = "warning"
    title: str
    explanation: str
    evidence_refs: List[str] = Field(default_factory=list)
    suggested_action: Literal["fix", "document", "ignore", "manual_review"] = "manual_review"


class RejectedFalsePositive(BaseModel):
    candidate_id: str
    rule_id: Optional[str] = None
    reason: str


class VerificationResult(BaseModel):
    confirmed_issues: List[VerifiedIssue] = Field(default_factory=list)
    rejected_false_positives: List[RejectedFalsePositive] = Field(default_factory=list)
    verification_confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    model_id: str = "mock"
    prompt_version: str = PROMPT_VERSION
    summary: str = ""


def _mock_verify(context: Dict[str, Any]) -> VerificationResult:
    """Deterministic verifier for dev/tests — interprets the pack, no model call."""
    confirmed: List[VerifiedIssue] = []
    rejected: List[RejectedFalsePositive] = []

    for rule in context.get("rules_failed", []):
        rule_id = rule["rule_id"]
        samples = context.get("samples", {}).get(rule_id, [])
        evidence = [f"rule:{rule_id}", f"violations:{rule['violation_count']}"]
        if samples:
            evidence.append(f"sample_failures[0..{len(samples) - 1}]")

        action: Literal["fix", "document", "ignore", "manual_review"] = "manual_review"
        if rule_id == "no_duplicate_rows" and rule.get("violation_pct", 100) < 2:
            action = "fix"
        elif rule_id == "high_item_missingness":
            action = "document"

        confirmed.append(
            VerifiedIssue(
                issue_id=f"confirm_{rule_id}",
                rule_id=rule_id,
                severity=rule.get("severity", "warning"),
                title=rule["name"],
                explanation=(
                    f"Deterministic contract flagged {rule['violation_count']} violation(s) "
                    f"({rule['violation_pct']}%): {rule['message']}. "
                    "Review samples before treating as actionable."
                ),
                evidence_refs=evidence,
                suggested_action=action,
            )
        )

    for col in context.get("columns_of_interest", []):
        if col.get("mixed_type_pct", 0) > 10:
            confirmed.append(
                VerifiedIssue(
                    issue_id=f"mixed_{col['name']}",
                    column=col["name"],
                    severity="warning",
                    title=f"Mixed encoding in {col['name']}",
                    explanation=(
                        f"Column has {col['mixed_type_pct']}% non-numeric values in a numeric-leaning "
                        "column — common in survey Likert exports with text labels."
                    ),
                    evidence_refs=[
                        f"ColumnProfile.mixed_type_pct={col['mixed_type_pct']}",
                        f"top_values:{col.get('top_values', [])[:3]}",
                    ],
                    suggested_action="manual_review",
                )
            )

    if not confirmed and context.get("rules_passed_count", 0) > 0:
        rejected.append(
            RejectedFalsePositive(
                candidate_id="no_failed_rules",
                reason="All contract rules passed on analyzed data; no semantic flags to confirm.",
            )
        )

    summary_parts = [
        f"Reviewed {context.get('row_count_analyzed', 0)} rows",
        f"({context.get('total_row_count', 0)} total)",
    ]
    if context.get("is_sampled"):
        summary_parts.append("(sampled analysis — counts may differ on full data)")

    return VerificationResult(
        confirmed_issues=confirmed,
        rejected_false_positives=rejected,
        verification_confidence=0.65 if context.get("is_sampled") else 0.85,
        model_id="mock-deterministic",
        summary=" ".join(summary_parts) + f". {len(confirmed)} issue(s) to review.",
    )


def _openai_verify(context: Dict[str, Any]) -> VerificationResult:
    import os

    import httpx

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    system = (
        "You are a data quality verifier for survey research datasets. "
        "You receive a JSON context pack with deterministic profiler results — "
        "rule pass/fail counts, capped sample rows, and column summaries. "
        "You do NOT have the full dataset. Confirm real issues, reject false positives, "
        "and cite evidence_refs from the pack only. Return JSON matching the schema."
    )
    user = json.dumps(context, default=str)

    schema = VerificationResult.model_json_schema()
    payload = {
        "model": llm_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "verification_result",
                "schema": schema,
                "strict": True,
            },
        },
    }

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        body = resp.json()

    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    parsed["model_id"] = body.get("model", llm_model())
    parsed["prompt_version"] = PROMPT_VERSION
    return VerificationResult.model_validate(parsed)


def verify_context_pack(context: Dict[str, Any]) -> VerificationResult:
    provider = llm_provider()
    if provider == "none":
        raise ValueError("LLM verification is disabled (DATALENS_LLM_PROVIDER=none)")
    if provider == "openai":
        try:
            return _openai_verify(context)
        except Exception as exc:
            logger.warning("OpenAI verify failed, falling back to mock: %s", exc)
            result = _mock_verify(context)
            result.summary = f"(OpenAI unavailable: {exc}) " + result.summary
            return result
    return _mock_verify(context)


def verification_to_dict(result: VerificationResult) -> Dict[str, Any]:
    return result.model_dump()
