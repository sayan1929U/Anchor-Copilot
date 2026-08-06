# ANCHOR — Career Sustainability Copilot

A multi-agent RAG system that helps Gen Z and Millennial employees navigate financial pressure, career growth, skills, AI readiness, recognition, belonging, and early-career onboarding, grounded in real findings from Deloitte's 2026 Global Gen Z & Millennial Survey (22,595 respondents, 44 countries), not generic advice.

Built by **Sayan Dey**, B.Tech CSE (AI & ML), Brainware University.
Live repo: [github.com/sayan1929U/Anchor-Copilot](https://github.com/sayan1929U/Anchor-Copilot)

---

## Why this exists

Deloitte's own research frames this generation's story as a shift from "career acceleration" to "career sustainability" — employees are ambitious but anxious, sequencing stability and well-being ahead of speed. Most workplace AI tools are either a single generic chatbot or a search box over an HR wiki. ANCHOR is neither: it's a **multi-agent system** where each domain (pay, promotion, skills, AI anxiety, burnout, belonging, onboarding) has its own specialist agent, its own retrieval scope, and its own grounding checks and every agent answers only from retrieved company policy and primary research, never from memory alone.

---

## Architecture

```
Employee message (authenticated via JWT)
        │
        ▼
┌─────────────────────┐
│  Crisis Guardrail    │──── if triggered ──► Crisis resource message (bypasses everything below)
│  (regex, fail-closed)│
└──────────┬───────────┘
           │ not triggered
           ▼
┌─────────────────────┐
│ Orchestrator Agent   │  Groq/Llama 3.3 70B — classifies into 1 of 7 intents
│ (intent classifier)  │
└──────────┬───────────┘
           ▼
┌─────────────────────────────────────────────────────────┐
│  7 Specialist Agents (stability, pathways, skills,        │
│  ai_fluency, recognition, belonging, early_careers)        │
│                                                             │
│  Each: retrieve_chunks(category) → pgvector cosine search  │
│        → grounded generation → AgentResponse                │
└──────────┬──────────────────────────────────────────────┘
           ▼
┌─────────────────────┐
│ Hallucination Check   │  Deterministic claim-extraction (NOT an LLM judge)
│ (fail-open)           │  Verifies every number/named entity in the reply
└──────────┬───────────┘  actually appears in retrieved context
           ▼
┌─────────────────────┐
│ Manager Nudge Layer   │  Selective (3 of 7 intents) — recognition, pathways, early_careers
└──────────┬───────────┘
           ▼
┌─────────────────────┐
│ Audit Log + Reply     │  Every decision logged with a reason string
└──────────────────────┘
```

**Shared Vector Store:** PostgreSQL + `pgvector`, populated from two sources per category — hand-authored company policy docs (`data/policy_docs/*.md`) and the actual Deloitte 2026 survey PDFs (global + India country report), chunked, embedded locally via `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim), and tagged by category. Retrieval reserves at least one slot for a policy-doc chunk so the much larger research corpus can't crowd out company-specific answers (see [Known Issues & Fixes](#known-issues-we-found-and-fixed) below).

---

## The 7 specialist agents

| Agent | Domain | Deloitte chapter it maps to |
|---|---|---|
| **Stability** | Pay, cost of living, financial hardship policy | The 'Maybe Later' Reality: Financial Pressure |
| **Pathways** | Promotion, leadership, career growth | Leadership, Reconsidered |
| **Skills** | Learning, upskilling, certifications | Continuous Learning & Adaptability |
| **AI-Fluency** | AI tools, readiness, job-security concerns | AI and the Readiness Gap |
| **Recognition** | Wellbeing, burnout, being seen at work | Well-being as Infrastructure |
| **Belonging** | Purpose, culture, connection | The Ideal Workplace |
| **Early-Careers** | Onboarding, first 90 days | The Future They're Preparing For |

---

## Security & Authentication

- **JWT-based auth** — email + bcrypt-hashed password, tokens signed with `HS256`. Employee identity is derived **entirely from the verified token**, never from client-supplied input — an earlier version of this API trusted `employee_id` in the request body, which meant anyone could impersonate anyone. Fixed before deployment.
- **RBAC**: two roles, `employee` and `manager`. Manager-only endpoints (`/audit/*`, `/analytics/*`) are enforced server-side via a FastAPI dependency, not just hidden in the UI.
- **Rate limiting**: 20 requests/minute per IP on `/chat` via `slowapi`.
- **CORS**: locked to the deployed frontend origin, not wildcard.
- **Tokens stored in-memory in the frontend**, not `localStorage` — a deliberate tradeoff (refresh requires re-login) to reduce the blast radius of a hypothetical XSS finding.
- **Multi-key Groq rotation**: the client automatically fails over across up to 3 API keys on `RateLimitError`, so a single account's free-tier quota doesn't take down the whole system.

---

## Adversarial / Red-Team Testing

`tests/security/run_adversarial_eval.py` runs 15 real attack prompts against the live orchestrator — prompt injection, jailbreak attempts, role confusion, cross-session data leakage, system-prompt extraction, harmful-advice boundary testing, and both false-positive and true-positive crisis-detection checks.

**Current result: 15/15 (100%)**

Worth being honest about how that number was reached: the first version of this suite reported 14/15, flagging a response that echoed the literal string `<system>` because an attack prompt asked the model to wrap its reply in those tags. On inspection, the agent hadn't leaked anything — it just complied with a formatting request. That was a flaw in the **test's** design (checking for superficial string echoes rather than actual system-prompt content), not a real vulnerability. The check was rewritten to test for verbatim excerpts of the real system prompts instead, and the suite now passes cleanly. 15 cases is a solid foundation, not an exhaustive audit — a production system would want 40-50+ cases with more phrasing diversity per category.

---

## Evaluation — the numbers, and how they got here

`tests/eval/run_eval.py` runs 21 labeled test cases across all 7 categories and reports intent accuracy, source-grounding rate, guardrail block rate, and latency.

**Current result:**
```
Intent accuracy:         95.2%
Source grounding rate:   95.2%
Guardrail block rate:    0.0%
Avg latency per request: 2.16s
```

### The guardrail story (the most important engineering narrative in this project)

The hallucination guardrail went through three real iterations, each measured, not guessed:

1. **LLM-judge, single-word verdict** — 28.6% false-positive block rate (correct answers incorrectly flagged as ungrounded).
2. **LLM-judge with few-shot examples** — made it *worse* (47.6%). This was the important signal: two failed attempts at the same underlying approach meant the approach itself was wrong, not the prompt wording.
3. **Deterministic claim-extraction** — regex-extracts numbers and named entities from the response, checks each against the retrieved context verbatim. **0% false positives**, and roughly halved average latency by removing an entire LLM call from the pipeline.

### Known issues we found and fixed

- **Citation self-reference false positives**: after ingesting the real Deloitte PDFs, the checker began flagging responses that cited the *report's own title* or *publication year* (e.g. "the 2026 Gen Z and Millennial Survey") as unsupported claims, since those exact strings didn't always appear in the specific 3 retrieved chunks. Fixed by excluding citation-keyword phrases and bare 4-digit years from claim extraction.
- **Retrieval imbalance after PDF ingestion**: adding ~100 research-PDF chunks against ~15 policy-doc chunks caused the larger corpus to statistically crowd out company-specific policy answers — grounding rate dropped from 95.2% to 76.2%. Fixed by reserving at least one retrieval slot specifically for a policy-doc match before filling the rest from the full corpus.

---

## Analytics Dashboard

Manager-only, backed by 7 SQL-aggregated endpoints (`/api/v1/analytics/*`) — message volume, intent distribution, guardrail action breakdown, grounding-rate trend, nudges by type, active employees, multi-turn conversation rate. **No raw message text or per-user logs are ever sent to an LLM for analysis** — every number is computed with `GROUP BY`/`COUNT`/`AVG` in Postgres first, and the frontend renders pre-aggregated results via Chart.js. This was a deliberate architectural choice to avoid the failure mode of dumping raw logs into an LLM context window for "insights."

---

## Tech stack & why

| Choice | Alternative considered | Why this one |
|---|---|---|
| **Groq (Llama 3.3 70B)** | OpenAI, Anthropic | Free tier + genuinely fast inference matters when a single request chains 2-3 LLM calls (classify → generate → [grounding check, now deterministic]) |
| **pgvector** | Pinecone, Weaviate | No new infra — reuses the Postgres instance already running; a defensible "I understand what a vector store actually is" choice over a managed SaaS |
| **sentence-transformers (local)** | OpenAI embeddings API | Zero API cost, zero rate limits, works offline |
| **Deterministic hallucination check** | LLM-as-judge | Measured 28-47% false-positive rate with an LLM judge across two prompting strategies; a rule-based claim-extraction check eliminated the noise and cut latency |
| **In-memory JWT storage (frontend)** | localStorage | Reduces XSS blast radius at the cost of requiring re-login on refresh |

---

## Known limitations (stated honestly, not hidden)

- **No verification that ingested documents are true** — the grounding check verifies a claim is *in the source*, not that the source is *correct*. The system trusts its own knowledge base completely.
- **No CI/CD yet** — the eval and adversarial suites run manually, not on every push.
- **Not load-tested** — no data on behavior under concurrent traffic.
- **15-case adversarial suite** is a foundation, not an exhaustive security audit.
- **No MFA/OAuth** — plain email+password JWT auth only; reasonable for current scale, a real roadmap item before any genuine multi-tenant production use.

---

## API Reference

```
POST /api/v1/auth/register     { full_name, email, password } → JWT
POST /api/v1/auth/login        { email, password }             → JWT

POST /api/v1/chat/             (Bearer token required)
  { message, session_id? }
  → { intent, agent, reply, sources, session_id }
  Omit session_id to start a new conversation; include it to continue one with memory.

GET  /api/v1/audit/logs        (manager only)
GET  /api/v1/audit/nudges      (manager only)
GET  /api/v1/analytics/*       (manager only) — 7 aggregated metrics endpoints
```

---

## Running locally

```bash
docker compose up -d                    # Postgres + pgvector
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.core.ingest                # company policy docs
python -m app.core.ingest_pdf_research   # Deloitte research PDFs
uvicorn app.main:app --reload
```

Requires a `.env` (see `.env.example`) with `DATABASE_URL`, `SECRET_KEY`, and `GROQ_API_KEY_1` (up to `_3` for rotation).

**Run the test suites:**
```bash
python -m tests.eval.run_eval
python -m tests.security.run_adversarial_eval
```

---

## Roadmap

- [ ] CI/CD — run both eval suites automatically on every push
- [ ] Live deployment (Render: FastAPI + managed Postgres/pgvector)
- [ ] Expanded adversarial suite (40-50+ cases)
- [ ] Re-ranking / query expansion in retrieval
- [ ] Source-truthfulness verification, not just grounding-in-source