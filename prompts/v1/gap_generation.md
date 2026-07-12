# Prompt: gap_generation (version v1)

STATUS: placeholder — wired up in the gap_engine module.

Every prompt file here is versioned by folder (v1/, v2/, ...). When a
ResearchGapCandidate is generated, its `prompt_version` field must record
which folder produced it — this is what makes generation reproducible.

Rules this prompt must enforce when implemented (per project principles):
- The model may ONLY use facts present in the retrieved paper excerpts
  provided in context. No outside knowledge.
- Every gap must cite `supporting_paper_ids` that were actually retrieved.
- Reject vague gaps (e.g. "no one studied region X"); require methodological,
  empirical, theoretical, or policy justification.
- Output must be valid JSON matching `ResearchGapCandidate` (see
  src/rios/core/schemas.py) so it can be parsed without regex.
