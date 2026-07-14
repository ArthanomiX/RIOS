"""
RIOS — Streamlit entry point.

WHY this file stays thin: it must not contain pipeline/business logic.
It only renders UI and calls functions imported from the `rios` package.
This keeps the logic unit-testable and lets us swap the UI framework later
without touching the pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Fallback path setup: ensures `import rios` works even if the package
# wasn't pip-installed (e.g. a fresh clone run before `pip install -e .`).
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st
import streamlit.components.v1 as components

from rios.core.config import get_secrets, get_settings
from rios.ingestion import ScreeningCriteria, dedup_papers, screen_papers
from rios.literature import search_openalex
from rios.rag import VectorStore, chunk_papers

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

st.subheader("4. What's still placeholder")
st.info(
    "You can now retrieve relevant passages from the screened literature, "
    "but nothing is yet synthesized into a research gap. Next: evidence-based "
    "gap generation with mandatory human review. Nothing here fabricates a "
    "research gap — by design, that logic doesn't exist yet."
)
