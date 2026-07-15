# RIOS — Research Intelligence Operating System

An evidence-based AI research advisor. RIOS retrieves real scholarly literature
(OpenAlex, Crossref, Semantic Scholar) and helps identify research gaps,
methodologies, and journal targets — with every output traceable back to
retrieved papers and reviewed by a human before it's finalized.

Built by **Suman_Econ (UAS-B)**.

## Project status

Module 1: project scaffolding + config + core schemas + Streamlit shell.
Literature retrieval, RAG, and gap-generation modules are added incrementally
in later modules.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in your API key(s)
streamlit run app/streamlit_app.py
```

## Repo structure

```
RIOS/
├── src/rios/          # all business logic (importable package)
│   ├── core/          # config loader, schemas, logging
│   ├── literature/    # OpenAlex / Crossref / Semantic Scholar clients
│   ├── ingestion/     # dedup, screening, structured extraction
│   ├── rag/           # chunking, embeddings, vector store, retrieval
│   ├── gap_engine/    # evidence synthesis, gap candidate generation
│   ├── methodology/   # methodology recommender + audit trail
│   ├── journals/      # journal matching / recommendation
│   ├── reports/       # docx / pdf / pptx / xlsx generators
│   └── review/        # human-in-the-loop accept/reject/edit history
├── app/streamlit_app.py  # UI only — no business logic here
├── prompts/v1/            # versioned prompt templates
├── config/                # YAML settings (human-edited, commented)
├── tests/                  # mirrors src/rios structure
├── data/                    # cache + vector store (gitignored contents)
└── outputs/                  # generated reports (gitignored contents)
```

## Deploying on Streamlit Community Cloud

1. Push this repo to GitHub (public repo — required for the free tier).
2. Go to share.streamlit.io → "New app" → pick this repo/branch.
3. Set **Main file path** to `app/streamlit_app.py`.
4. Under "Advanced settings → Secrets", add your API key(s), e.g.:
   ```toml
   GEMINI_API_KEY = "AIza..."
   ```
5. Deploy. The app sleeps after inactivity and wakes on next visit — fine for
   occasional use.

## Cost

Everything here is free (OpenAlex/Crossref/Semantic Scholar have no cost,
Streamlit Community Cloud is free for public repos). The only pay-as-you-go
cost is LLM API usage once generation modules are added — no subscription
required.
