# Prompt: gap_generation (version v1)

# Prompt: gap_generation (version v1)

STATUS: implemented — used by rios/gap_engine/generator.py.

The actual runtime template is `gap_generation_prompt.txt` in this same
folder. This .md file documents the rules it enforces; keep both in sync
when editing.

Every prompt file here is versioned by folder (v1/, v2/, ...). When a
ResearchGapCandidate is generated, its `prompt_version` field records
which folder produced it — this is what makes generation reproducible.

Rules this prompt enforces (per project principles):
- The model may ONLY use facts present in the retrieved evidence excerpts
  provided in context. No outside knowledge.
- Every gap must cite `supporting_paper_ids` that were actually retrieved —
  and the code (not the model) re-verifies this after generation, dropping
  any candidate that cites an unknown paper_id.
- Vague gaps (e.g. "no one studied region X") are explicitly disallowed;
  the prompt requires methodological, empirical, theoretical, or policy
  justification instead.
- Output must be valid JSON matching `ResearchGapCandidate` (see
  src/rios/core/schemas.py) so it can be parsed without regex.

