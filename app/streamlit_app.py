"""
RIOS — Streamlit entry point.

WHY this file stays thin: it must not contain pipeline/business logic.
It only renders UI and calls functions imported from the `rios` package.
This keeps the logic unit-testable and lets us swap the UI framework later
without touching the pipeline.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Fallback path setup: ensures `import rios` works even if the package
# wasn't pip-installed (e.g. a fresh clone run before `pip install -e .`).
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st
import streamlit.components.v1 as components

# Streamlit Cloud secrets (set via the dashboard) live in st.secrets, not
# automatically in os.environ. pydantic-settings (used by rios.core.config)
# reads from os.environ / .env, so we bridge the values here, once, before
# any get_secrets() call — this lets the same Secrets class work identically
# locally (.env file) and on Streamlit Cloud (dashboard secrets).
try:
    for _key in ("GEMINI_API_KEY", "OPENALEX_MAILTO", "CROSSREF_MAILTO"):
        if _key in st.secrets and not os.environ.get(_key):
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass  # no secrets.toml present locally — fine, .env still works

from rios.core.config import get_secrets, get_settings
from rios.core.schemas import ReviewStatus
from rios.gap_engine import generate_gap_candidates
from rios.ingestion import ScreeningCriteria, dedup_papers, screen_papers
from rios.literature import search_openalex
from rios.rag import VectorStore, chunk_papers
from rios.review import apply_review

st.set_page_config(
    page_title="RIOS — Research Intelligence Operating System",
    page_icon="🧭",
    layout="wide",
)


def render_animated_credit(text: str = "Built by Suman_Econ (UAS-B)") -> None:
    """Render the credit line as a gradient heading where letters appear
    one after another, then the gradient keeps shifting continuously.
    Implemented as a standalone HTML component so the CSS keyframe
    animations run reliably (Streamlit's markdown sanitizer can strip
    <style>/<script> in some contexts; components.html does not).
    """
    letters_html = "".join(
        f'<span class="letter" style="animation-delay:{i * 0.06:.2f}s">'
        f'{"&nbsp;" if ch == " " else ch}</span>'
        for i, ch in enumerate(text)
    )

    html = f"""
    <style>
      .credit-wrap {{
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 6px 0 2px 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }}
      .credit-heading {{
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0.5px;
      }}
      .letter {{
        display: inline-block;
        opacity: 0;
        transform: translateY(10px);
        animation:
          reveal 0.5s ease forwards,
          shimmer 4s linear infinite;
        animation-fill-mode: forwards, forwards;
        background: linear-gradient(
          90deg,
          #ff6ec4, #7873f5, #4ade80, #38bdf8, #ff6ec4
        );
        background-size: 300% auto;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
      }}
      @keyframes reveal {{
        to {{ opacity: 1; transform: translateY(0); }}
      }}
      @keyframes shimmer {{
        0%   {{ background-position:   0% center; }}
        100% {{ background-position: 300% center; }}
      }}
    </style>
    <div class="credit-wrap">
      <div class="credit-heading">{letters_html}</div>
    </div>
    """
    components.html(html, height=50)


# ---------- Page content ----------

st.title("🧭 RIOS — Research Intelligence Operating System")
render_animated_credit()

st.divider()

settings = get_settings()

st.markdown(
    f"**{settings.app.name}** · v{settings.app.version} · "
    f"active prompt version: `{settings.prompts.active_version}`"
)

st.subheader("1. Select a research domain")
domain = st.selectbox("Domain", options=settings.domains, index=0)

st.subheader("2. Search real literature (OpenAlex)")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    keywords_input = st.text_input(
        "Keywords (comma-separated)", value=domain
    )
with col2:
    year_min = st.number_input(
        "From year", value=settings.literature_defaults.publication_year_min
    )
with col3:
    year_max = st.number_input(
        "To year", value=settings.literature_defaults.publication_year_max
    )

if st.button("Search OpenAlex", type="primary"):
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    secrets = get_secrets()
    with st.spinner("Querying OpenAlex..."):
        try:
            papers, strategy = search_openalex(
                keywords=keywords,
                year_min=int(year_min),
                year_max=int(year_max),
                max_results=25,
                mailto=secrets.openalex_mailto,
            )
        except RuntimeError as exc:
            st.error(f"Search failed: {exc}")
            papers, strategy = [], None

    if strategy:
        st.success(f"Retrieved {len(papers)} papers from OpenAlex.")

        deduped_papers, num_removed = dedup_papers(papers)
        if num_removed:
            st.caption(f"Removed {num_removed} duplicate record(s).")

        st.markdown("**Screening criteria**")
        require_abstract = st.checkbox("Require abstract present", value=True)
        min_citations = st.number_input("Minimum citation count", value=0, min_value=0)

        criteria = ScreeningCriteria(
            require_abstract=require_abstract,
            min_citation_count=int(min_citations),
        )
        included, excluded, decisions = screen_papers(deduped_papers, criteria)

        st.info(f"After screening: **{len(included)} included**, {len(excluded)} excluded.")

        with st.expander("Search strategy (reproducibility record)"):
            st.json(strategy.model_dump(mode="json"))

        with st.expander(f"Excluded papers and reasons ({len(excluded)})"):
            for paper, decision in zip(
                [p for p in deduped_papers if p.id not in {i.id for i in included}],
                [d for d in decisions if not d.included],
            ):
                st.markdown(f"- **{paper.title}** — {'; '.join(decision.reasons)}")

        for p in included:
            with st.container(border=True):
                st.markdown(f"**{p.title}** ({p.year or 'n.d.'})")
                st.caption(
                    f"{', '.join(p.authors[:4]) or 'Unknown authors'} · "
                    f"{p.journal or 'Unknown journal'} · "
                    f"{p.citation_count or 0} citations · "
                    f"{'Open Access' if p.open_access else 'Closed Access'}"
                )
                if p.abstract:
                    st.write(p.abstract[:400] + ("..." if len(p.abstract) > 400 else ""))

        # Persisted in session_state so it survives the rerun triggered by
        # widgets in section 3 below (Streamlit reruns the whole script on
        # every interaction — without this, "included" would vanish the
        # moment the user types a query).
        st.session_state["included_papers"] = included

st.subheader("3. Ask the retrieved evidence a question")

included_papers = st.session_state.get("included_papers")
if not included_papers:
    st.caption("Run a search and screen papers above first.")
else:
    query_text = st.text_input(
        "Query (e.g. 'what methodologies are used for price forecasting?')"
    )
    if query_text:
        chunks = chunk_papers(included_papers)
        store = VectorStore()
        store.build(chunks)
        results = store.query(query_text, top_k=5)

        if not results:
            st.warning("No relevant passages found in the retrieved literature.")
        else:
            papers_by_id = {p.id: p for p in included_papers}
            st.caption(
                f"Top {len(results)} matching passages — each is traceable to "
                "its source paper, nothing here is generated."
            )
            for r in results:
                source_paper = papers_by_id.get(r.chunk.paper_id)
                with st.container(border=True):
                    st.markdown(f"**Relevance: {r.score:.2f}**")
                    st.write(r.chunk.text)
                    if source_paper:
                        st.caption(f"Source: {source_paper.title} ({source_paper.year or 'n.d.'})")

st.subheader("4. Generate evidence-based research gap candidates")

secrets = get_secrets()
papers_by_id = {p.id: p for p in included_papers} if included_papers else {}

if not included_papers:
    st.caption("Run a search and screen papers above first.")
elif not secrets.gemini_api_key:
    st.warning(
        "No Gemini API key configured. Add `GEMINI_API_KEY` under "
        "your Streamlit app's **Settings → Secrets** (or in a local `.env` "
        "file) to enable this step. Get a free key (no credit card needed) "
        "at aistudio.google.com/apikey. Nothing is generated without it."
    )
else:
    max_gaps = st.slider("Max candidate gaps to generate", 1, 8, 5)
    if st.button("Generate candidate gaps", type="primary"):
        with st.spinner("Analyzing retrieved evidence — this calls the Gemini API..."):
            try:
                chunks_for_generation = chunk_papers(included_papers)
                candidates = generate_gap_candidates(
                    chunks_for_generation,
                    domain=domain,
                    api_key=secrets.gemini_api_key,
                    max_gaps=max_gaps,
                )
                st.session_state.setdefault("gap_candidates", {})
                for c in candidates:
                    st.session_state["gap_candidates"][c.gap_id] = c
                if not candidates:
                    st.info(
                        "The model did not return any gap it could support "
                        "from this evidence — try broadening the search above."
                    )
            except (ValueError, RuntimeError) as exc:
                st.error(f"Generation failed: {exc}")

gap_candidates = st.session_state.get("gap_candidates", {})
review_history = st.session_state.setdefault("review_history", [])

if gap_candidates:
    st.subheader("5. Human review — accept, modify, or reject each candidate")
    st.caption(
        "Nothing here is final until you decide. Every decision is logged "
        "below with a timestamp for the audit trail."
    )
    for gap_id, gap in list(gap_candidates.items()):
        with st.container(border=True):
            st.markdown(f"**[{gap.gap_type}] {gap.description}**")
            st.caption(
                f"Confidence: {gap.confidence_score:.2f} · "
                f"Prompt {gap.prompt_version} · Model {gap.model_version}"
            )
            st.write(f"**Why existing evidence is insufficient:** {gap.why_insufficient}")
            st.write(f"**Expected contribution:** {gap.expected_contribution}")
            supporting_titles = [
                papers_by_id[pid].title for pid in gap.supporting_paper_ids if pid in papers_by_id
            ]
            st.caption("Supporting papers: " + "; ".join(supporting_titles))

            if gap.review_status == ReviewStatus.PENDING:
                comment = st.text_input("Comment (optional)", key=f"comment_{gap_id}")
                c1, c2, c3 = st.columns(3)
                if c1.button("✅ Accept", key=f"accept_{gap_id}"):
                    updated, record = apply_review(gap, ReviewStatus.ACCEPTED, comment=comment)
                    gap_candidates[gap_id] = updated
                    review_history.append(record)
                    st.rerun()
                if c2.button("❌ Reject", key=f"reject_{gap_id}"):
                    updated, record = apply_review(gap, ReviewStatus.REJECTED, comment=comment)
                    gap_candidates[gap_id] = updated
                    review_history.append(record)
                    st.rerun()
                with c3.popover("✏️ Modify"):
                    new_desc = st.text_area(
                        "Edit description", value=gap.description, key=f"modify_text_{gap_id}"
                    )
                    if st.button("Save as modified", key=f"modify_save_{gap_id}"):
                        updated, record = apply_review(
                            gap, ReviewStatus.MODIFIED, comment=comment,
                            modified_description=new_desc,
                        )
                        gap_candidates[gap_id] = updated
                        review_history.append(record)
                        st.rerun()
            else:
                status_label = gap.review_status.value.upper()
                st.success(
                    f"Status: {status_label}"
                    + (f" — {gap.review_comment}" if gap.review_comment else "")
                )

    if review_history:
        with st.expander(f"Review history / audit trail ({len(review_history)} decisions)"):
            for r in review_history:
                st.caption(
                    f"{r.decided_at.strftime('%Y-%m-%d %H:%M UTC')} · "
                    f"{r.decision.value} · gap `{r.target_id[:8]}` · {r.reviewer}"
                    + (f" — {r.comment}" if r.comment else "")
                )

st.subheader("6. What's still placeholder")
st.info(
    "Accepted gaps are not yet turned into full research frameworks "
    "(titles, objectives, hypotheses, methodology recommendations, journal "
    "matches) or exported reports — those are the next modules."
)
