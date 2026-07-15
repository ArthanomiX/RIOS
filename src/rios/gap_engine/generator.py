"""
Evidence-constrained research gap generation, using Google's official
`google-genai` SDK to call the Gemini API (free tier — Gemini 2.5 Flash by
default, no credit card required).

WHY this is the most safety-critical module in RIOS: this is the only place
an LLM is used to produce something a researcher might act on. Every design
choice here enforces the evidence-before-generation principle:

- The model only ever sees the retrieved/screened evidence chunks passed in
  — never asked to draw on its own training knowledge.
- Every candidate gap must cite `supporting_paper_ids`. Any candidate citing
  a paper_id that was NOT in the evidence we actually sent is REJECTED here,
  in code, before a person ever sees it. The model is not trusted to
  self-police this — we verify it ourselves.
- Every surviving candidate is tagged with prompt_version + model_version +
  a generation timestamp, satisfying the reproducibility requirement.
- Every candidate is created with review_status = PENDING. Nothing in this
  module ever marks a gap as accepted — only an explicit human action via
  rios.review.apply_review can do that.

WHY the official SDK instead of a raw REST call: Google has been rolling
out a newer API key format (prefixed "AQ." instead of the older "AIzaSy...")
that is inconsistently compatible with hand-rolled REST calls to the raw
generateContent endpoint. The official `google-genai` SDK is what Google
actively maintains to stay correct across exactly this kind of backend
change, so it's the more robust integration point for a project that has
to keep working with whatever key format a student's account is issued.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from rios.core.logging_setup import get_logger
from rios.core.schemas import Chunk, ResearchGapCandidate, ReviewStatus

logger = get_logger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


def _load_prompt_template(prompt_version: str) -> str:
    path = PROMPTS_DIR / prompt_version / "gap_generation_prompt.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _format_evidence(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[paper_id: {c.paper_id}] {c.text}" for c in chunks)


def _extract_json_array(raw_text: str) -> list[dict]:
    """The model is instructed to return raw JSON, but occasionally wraps it
    in markdown fences anyway — strip those defensively rather than crashing
    on a preventable formatting slip."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        first_line, _, rest = cleaned.partition("\n")
        cleaned = rest if first_line.strip().lower() in ("json", "") else cleaned
    return json.loads(cleaned.strip())


def generate_gap_candidates(
    chunks: list[Chunk],
    domain: str,
    api_key: str,
    max_gaps: int = 5,
    prompt_version: str = "v1",
    model: str = DEFAULT_MODEL,
) -> list[ResearchGapCandidate]:
    """Generate candidate research gaps from evidence chunks only.

    Raises ValueError for bad inputs (no chunks / no key), RuntimeError if
    the model's response can't be parsed as JSON or was blocked/empty.
    Returns only candidates that passed evidence validation — the caller
    should assume anything returned here is safe to show a human for
    review, but NOT safe to treat as already accepted.
    """
    if not chunks:
        raise ValueError("Cannot generate gaps from zero evidence chunks.")
    if not api_key:
        raise ValueError("Gemini API key is required for gap generation.")

    valid_paper_ids = {c.paper_id for c in chunks}
    template = _load_prompt_template(prompt_version)
    prompt = (
        template.replace("{{DOMAIN}}", domain)
        .replace("{{EVIDENCE}}", _format_evidence(chunks))
        .replace("{{MAX_GAPS}}", str(max_gaps))
    )

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=2000,
            ),
        )
    except Exception as exc:  # SDK raises its own exception types; treat all as a generation failure
        logger.error("Gemini API call failed: %s", exc)
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    raw_text = (response.text or "").strip()
    if not raw_text:
        block_reason = None
        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None:
            block_reason = getattr(feedback, "block_reason", None)
        raise RuntimeError(f"Gemini returned no usable text (blockReason={block_reason}).")

    try:
        raw_candidates = _extract_json_array(raw_text)
    except (json.JSONDecodeError, IndexError) as exc:
        logger.error("Failed to parse gap generation response as JSON: %s", exc)
        raise RuntimeError(
            "The model did not return valid JSON. Try again, or reduce the "
            "amount of evidence passed in."
        ) from exc

    accepted: list[ResearchGapCandidate] = []
    for raw in raw_candidates:
        cited_ids = set(raw.get("supporting_paper_ids", []))
        unknown_ids = cited_ids - valid_paper_ids

        if not cited_ids:
            logger.warning(
                "Dropping gap candidate with no supporting_paper_ids: %r",
                str(raw.get("description", ""))[:80],
            )
            continue
        if unknown_ids:
            logger.warning(
                "Dropping gap candidate citing paper_id(s) not in retrieved "
                "evidence (possible fabrication): %s", unknown_ids,
            )
            continue

        try:
            candidate = ResearchGapCandidate(
                gap_id=str(uuid.uuid4()),
                domain=domain,
                gap_type=raw.get("gap_type", "unspecified"),
                description=raw["description"],
                why_insufficient=raw["why_insufficient"],
                expected_contribution=raw["expected_contribution"],
                supporting_paper_ids=sorted(cited_ids),
                confidence_score=float(raw.get("confidence_score", 0.0)),
                prompt_version=prompt_version,
                model_version=model,
                generated_at=datetime.now(timezone.utc),
                review_status=ReviewStatus.PENDING,
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Dropping malformed gap candidate: %s", exc)
            continue

        accepted.append(candidate)

    logger.info(
        "Gap generation: %d candidates returned by model, %d passed evidence validation",
        len(raw_candidates), len(accepted),
    )
    return accepted
