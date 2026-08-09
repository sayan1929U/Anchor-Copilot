# ANCHOR — Career Sustainability Copilot
### Full Project Summary & Technical Retrospective

**Live application:** [https://anchor-copilot-11.onrender.com](https://anchor-copilot-11.onrender.com)
**Repository:** [github.com/sayan1929U/Anchor-Copilot](https://github.com/sayan1929U/Anchor-Copilot)
**Author:** Sayan Dey — B.Tech CSE (AI & ML), Brainware University
**Research foundation:** Deloitte Global 2026 Gen Z & Millennial Survey (22,595 respondents, 44 countries)

---

## 1. What ANCHOR Is

ANCHOR is a multi-agent Retrieval-Augmented Generation (RAG) system that helps Gen Z and Millennial employees navigate seven real workplace pressures — financial stability, career growth, skills, AI readiness, recognition, belonging, and early-career onboarding — each handled by its own specialist AI agent, each grounded only in retrieved company policy and primary Deloitte research, never in unverified model memory.

It is not a single chatbot with a big prompt. It is a **routed, multi-agent system with independent retrieval scopes, deterministic safety checks, authenticated multi-tenant sessions, and a manager-facing analytics layer**, built end-to-end from a FastAPI backend to a deployed, publicly accessible frontend.

---

## 2. Explicit clarification: No LangChain / No LangGraph

This was a deliberate architectural decision made at the start of the build, not an omission. **No agent framework (LangChain, LangGraph, CrewAI, AutoGen, etc.) is used anywhere in this codebase.** Every part of the pipeline — intent classification, routing, retrieval, grounding verification, guardrails — is hand-implemented directly against:
- The **Groq SDK** (`groq` Python package) for LLM calls
- **SQLAlchemy** for all database access, including vector search via `pgvector`'s SQLAlchemy integration
- Plain Python control flow (`if`/`dict` dispatch) for orchestration logic

**Why this choice was made:** frameworks like LangChain abstract away exactly the mechanics that were the point of building this — intent routing, prompt assembly, retrieval scoring, and guardrail logic. Hand-rolling them means every decision in the pipeline is visible, debuggable, and explainable line-by-line, which is both a better learning outcome and a stronger technical interview story ("I can walk you through exactly how routing works" vs. "the framework handles that").

---

## 3. Core Algorithms & Techniques Actually Used

| Component | Technique |
|---|---|
| **Intent classification** | Prompt-engineered LLM call (Groq/Llama 3.3 70B) constrained to 7 fixed labels, with a defensive substring-fallback parser for non-conforming output |
| **Retrieval** | **Cosine similarity search** over 384-dimensional sentence embeddings, computed natively by `pgvector`'s `<=>` operator inside PostgreSQL |
| **Embeddings** | `sentence-transformers` (`all-MiniLM-L6-v2`), run **locally**, zero API cost |
| **Retrieval balancing** | A reserved-slot algorithm: at least 1 of top-k retrieval results is guaranteed from company-policy sources before filling remaining slots from the full corpus (prevents a larger research corpus from statistically crowding out policy-specific answers) |
| **Grounding / hallucination check** | **Deterministic claim-extraction**, not an LLM judge — regex extracts numeric values and capitalized multi-word phrases from a generated response, then verifies each literal string is present in the retrieved source context |
| **Crisis detection guardrail** | Regex pattern matching against a conservative, fail-closed keyword list |
| **Authentication** | **JWT (HS256)** signed tokens; **bcrypt** password hashing (cost-factor default) |
| **Rate limiting** | Sliding-window IP-based limiting via `slowapi` |
| **Manager nudge logic** | Rule-based mapping table (intent → nudge type), deliberately not ML-based, for predictable/auditable behavior |
| **Chunking** | Paragraph-boundary text splitting with a max-character soft limit (400–500 chars), merging short paragraphs to avoid over-fragmenting policy documents |
| **PDF ingestion** | Page-by-page text extraction (`pypdf`) with chapter-header pattern detection to auto-tag chunks by category, carrying the last-detected category forward across pages that don't repeat the header |

---

## 4. Architecture

```
Employee message (JWT-authenticated)
        │
        ▼
Crisis Guardrail (regex, fail-closed) ──if triggered──► Crisis resource message, bypasses all else
        │ not triggered
        ▼
Orchestrator Agent — Groq/Llama 3.3 70B intent classifier → 1 of 7 labels
        │
        ▼
Specialist Agent (1 of 7) ──► retrieve_chunks() [pgvector cosine search, reserved-slot balancing]
        │                              │
        │◄─────────────────────────────
        ▼
Grounded generation (LLM call with retrieved context injected as system prompt)
        │
        ▼
Hallucination Check — deterministic claim extraction (fail-open on API error)
        │
        ▼
Manager Nudge Layer — selective, 3 of 7 intents (recognition, pathways, early_careers)
        │
        ▼
Audit Log (every decision + reason string) + Reply to employee
```

**Shared Vector Store:** PostgreSQL + `pgvector` extension. Populated from two sources per category: hand-authored company policy markdown files, and the real Deloitte 2026 survey PDFs (global report + India country report), both chunked and embedded identically.

---

## 5. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| API framework | **FastAPI** | Async-capable, automatic OpenAPI docs, dependency-injection auth pattern |
| Database | **PostgreSQL + pgvector** | Single database for both relational data and vector search — no separate managed vector DB needed |
| ORM / migrations | **SQLAlchemy 2.0 + Alembic** | Type-safe queries, versioned schema migrations |
| LLM provider | **Groq (Llama 3.3 70B)** | Free tier, low latency (matters when one request chains 2+ LLM calls) |
| Embeddings | **sentence-transformers (local)** | Zero API cost, zero rate limits, offline-capable |
| Auth | **python-jose (JWT) + passlib/bcrypt** | Industry-standard token signing and password hashing |
| Rate limiting | **slowapi** | Lightweight IP-based limiter, FastAPI-native |
| PDF parsing | **pypdf** | Pure-Python, no external binary dependency |
| Frontend | **Vanilla HTML/CSS/JS** (no framework) | No build step, fully self-contained static files, deploys trivially |
| Charts | **Chart.js** (CDN) | Lightweight, no bundler required |
| Containerization | **Docker** (CPU-only PyTorch base) | Reproducible builds; avoids Render's native-build torch/GPU-wheel issues |
| CI/CD | **GitHub Actions** | Automated eval + adversarial suite on every push |
| Hosting | **Render** (Docker-based Web Service + PostgreSQL) | Free tier, GitHub-integrated auto-deploy |

---

## 6. Build History — Every Phase, In Order

### Phase 1 — Foundation
FastAPI skeleton, SQLAlchemy models (`Employee`, `ConversationSession`, `Message`, `AgentAuditLog`), Alembic migrations, Docker Compose for local Postgres+pgvector.
**Issues fixed:** nested nested `app/app` nested folder from a bad move; Windows venv-not-activated errors (recurring theme throughout the build); `psycopg2` → `psycopg` driver switch for Python 3.13 wheel compatibility; missing pgvector `CREATE EXTENSION` step; Alembic autogenerate omitting the `pgvector.sqlalchemy` import in generated migration files.

### Phase 2 — Orchestrator Agent
LLM-based intent classifier routing to 7 stub agents. Originally built against Gemini, then switched to **Groq** for genuinely free, low-latency inference — including a defensive fallback parser since Groq/Llama doesn't enforce output format as strictly as some alternatives.
**Issues fixed:** `bcrypt`/`passlib` version incompatibility (`bcrypt` 4.1+ removed the `__about__` attribute `passlib` 1.7.4 depends on — pinned to `bcrypt==4.0.1`); `httpx` version drift breaking the Groq SDK's internal `proxies` argument (pinned `httpx==0.27.2`); PowerShell `curl` alias vs real `curl.exe` confusion.

### Phase 3 — Specialist Agents
All 7 stub agents replaced with real Groq-backed generation, each with a distinct persona/system prompt.

### Phase 4 — Shared Vector Store (RAG Ingestion)
`pgvector` column added, local embedding pipeline (`sentence-transformers`), markdown chunking + ingestion script, retrieval function using cosine distance.

### Phase 5 — Grounded Response Generation
Retrieval wired directly into each specialist agent's prompt, with inline source citation requirements and per-source labeling.

### Phase 6 — Safety & Guardrail Layer
Crisis-detection guardrail (regex, fail-closed) and first-generation hallucination checker (LLM-judge based).
**Major finding, iterated over multiple sessions:** the LLM-judge hallucination checker had a **28.6% false-positive block rate**. A second attempt using few-shot examples made it *worse* (47.6%) — this was the key signal that the *approach* (LLM-as-judge for binary grounding verdicts) was fundamentally unreliable, not just the prompt wording. Replaced with a **deterministic claim-extraction algorithm**: 0% false positives, ~50% latency reduction from removing an entire LLM call per response.

### Phase 7 — Action Layer (Manager Nudges)
Rule-based nudge system triggering on 3 of 7 intents (recognition, pathways, early_careers), deliberately selective to avoid alert fatigue.

### Phase 8 — Audit Trail + Frontend
`AgentAuditLog`-backed `/audit/logs` and `/audit/nudges` endpoints; first full chat UI and manager dashboard (later substantially redesigned).
**Resilience hardening:** wrapped all Groq calls in `safe_groq_call()` with timeout/connection-error handling and a graceful fallback message, since an earlier unhandled `APITimeoutError` had crashed the whole endpoint.
**Data grounding upgrade:** ingested the actual Deloitte 2026 Global and India country-report PDFs (chapter-header detection auto-tags chunks by category), replacing hand-written placeholder statistics with real, cited survey data.
**Issues fixed:** a cross-platform text-encoding bug (Windows-saved files defaulting to cp1252, breaking strict UTF-8 reads); retrieval imbalance after PDF ingestion (grounding rate dropped from 95.2% → 76.2% because the much larger PDF corpus crowded out policy-doc chunks) — fixed via the reserved-slot retrieval algorithm; false-positive hallucination flags on the system's own citation text (e.g. flagging "2026 Gen Z and Millennial Survey" as an unsupported claim) — fixed by excluding citation-keyword phrases and bare 4-digit years from claim extraction.

### Phase 9 — Authentication & Session Security
JWT-based auth (register/login), bcrypt password hashing, role-based access control (`employee` / `manager`), rate limiting, CORS lockdown, full-screen login-gate frontend with in-memory (not `localStorage`) token storage to reduce XSS blast radius.
**Critical fix:** `employee_id` was previously trusted directly from client-supplied request body — meaning any caller could impersonate any employee. Identity is now derived exclusively from the verified JWT.
**Multi-key Groq rotation** added afterward: automatic failover across up to 3 Groq API keys on `RateLimitError`, so free-tier quota exhaustion on one key doesn't take down the system.
**Issues fixed:** two separate stale Groq client instances (`rag_engine.py`, `orchestrator.py`) still constructing clients from the old single-key config field after the multi-key refactor, causing `AttributeError` on boot — both migrated to the centralized `safe_groq_call`.

### Phase 10 — Adversarial / Red-Team Testing
15-case adversarial test suite covering prompt injection, jailbreak attempts, role confusion, cross-session data leakage, system-prompt extraction, harmful-advice boundaries, and both false-positive/true-positive crisis-detection checks.
**Result: 15/15 (100%).** Notably, the first version of this suite reported 14/15 — flagging a response that echoed the literal string `<system>` because an attack prompt requested that exact formatting. On inspection this was a **test design flaw** (checking for superficial string echoes rather than actual leaked system-prompt content), not a real vulnerability — the check was rewritten to test for verbatim excerpts of real internal prompts instead.

### Phase 11 — Analytics Dashboard
7 SQL-aggregated, manager-only endpoints (message volume, intent distribution, guardrail action breakdown, grounding-rate trend, nudges by type, active employees, multi-turn conversation rate), rendered via 5 Chart.js visualizations plus 4 summary stat cards. **No raw message text or per-user data is ever sent to an LLM** — every metric is computed in Postgres via `GROUP BY`/`COUNT` first.

### Phase 12 — README / Design Documentation
Comprehensive README covering architecture, real eval numbers, the full guardrail-iteration story, and explicitly stated known limitations (no source-truthfulness verification, no MFA, 15-case adversarial suite is a foundation not an exhaustive audit).

### Phase 13 — CI/CD + Deployment
**13a:** GitHub Actions workflow spinning up a fresh `pgvector`-enabled Postgres service container on every push, running migrations, seeding a test employee, ingesting documents, and running both the evaluation suite and adversarial suite — build **fails** (non-zero exit code) on any accuracy regression or security-case failure, not just prints a report.
**Issues fixed during CI setup:** the same encoding bug resurfacing on Linux runners (fixed at the source by making `ingest.py` try UTF-8 then fall back to cp1252); PDF ingestion script crashing when `data/research_pdfs/` (gitignored) doesn't exist in CI — now exits cleanly with an informational message; GitHub Actions secrets initially not configured at all (`GROQ_API_KEY_1/2/3` were never added as repository secrets, diagnosed via a temporary debug step printing secret *lengths* only).
**13b:** Deployment on **Render**, using a custom **Dockerfile** with an explicit CPU-only PyTorch install (`--index-url https://download.pytorch.org/whl/cpu`) to avoid Render's native Python build environment struggling with the default GPU-capable torch wheel.
**Issues fixed during deployment:** Render's free-tier "one active free database per account" limit required switching to a fresh database; `email-validator` package was installed ad-hoc locally during Phase 9 but never captured in `requirements.txt`, causing a clean Docker build to fail at runtime with `ImportError: email-validator is not installed` — added explicitly to `requirements.txt`.

---

## 7. Verified Results (not estimates)

```
Evaluation suite (21 labeled test cases, 7 categories):
  Intent accuracy:         95.2%
  Source grounding rate:   95.2%
  Guardrail block rate:    0.0%
  Avg latency per request: ~2.2s

Adversarial security suite (15 real attack prompts):
  Passed:                  15/15 (100%)

CI/CD:
  Automated on every push via GitHub Actions
  Build fails on any regression below threshold
```

---

## 8. Known, Honestly-Stated Limitations

- No verification that ingested source documents are *true* — the grounding check verifies a claim is *in the source*, not that the source is *correct*.
- 15-case adversarial suite is a solid foundation, not an exhaustive security audit.
- No load testing performed; behavior under concurrent production traffic is unverified.
- No MFA/OAuth — email+password JWT auth only.
- Render's free-tier web service cold-starts after 15 minutes of inactivity (~30–50s first response).

---

## 9. Roadmap

- [ ] Expand adversarial suite to 40–50+ cases with greater phrasing diversity
- [ ] Load testing with real concurrency numbers
- [ ] Retrieval re-ranking / query expansion
- [ ] Source-truthfulness verification layer, beyond in-source grounding
- [ ] Custom domain + MFA, if moved toward genuine multi-tenant production use
