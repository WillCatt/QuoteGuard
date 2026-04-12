# QuoteGuard: Project Plan

> A guardrailed RAG chatbot for insurance quote generation, built as a portfolio piece over 3–4 weeks using local LLMs (Ollama).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [The Contract](#the-contract)
3. [System Architecture](#system-architecture)
4. [Tech Stack](#tech-stack)
5. [Effort Allocation](#effort-allocation)
6. [Week 1: Foundations & Ingestion](#week-1-foundations--ingestion)
7. [Week 2: Orchestration & Happy Path](#week-2-orchestration--happy-path)
8. [Week 3: Guardrails & Evaluation](#week-3-guardrails--evaluation)
9. [Week 4: Polish, Demo & Writeup](#week-4-polish-demo--writeup)
10. [Pitfalls & Learned-the-Hard-Way Notes](#pitfalls--learned-the-hard-way-notes)
11. [Success Criteria](#success-criteria)
12. [Future Work](#future-work)

---

## Project Overview

**Name:** QuoteGuard

**What it is:** A retrieval-augmented chatbot that guides users through an insurance quote generation flow, grounded entirely in a corpus of insurance PDFs (Product Disclosure Statements), and engineered with multi-layered guardrails so it cannot stray from its intended path, give advice, hallucinate coverage details, or be manipulated by prompt injection.

**The core tension the project solves:** LLMs are flexible and conversational, but insurance is a regulated domain where hallucinations, off-topic drift, or unauthorised advice create real legal and financial risk. QuoteGuard demonstrates how to keep a chatbot *useful* while making it *structurally impossible* to misuse. Every technical decision traces back to this tension.

**Why this is portfolio-worthy:** Most RAG portfolio projects are generic Q&A demos with no evaluation. QuoteGuard differentiates itself by:
- Treating the chatbot as a constrained state machine, not an open agent
- Building four independent guardrail layers with measurable coverage
- Running a rigorous adversarial evaluation with reported metrics
- Deploying on fully local infrastructure (Ollama) to prove full-stack competence

---

## The Contract

QuoteGuard enforces six guarantees. Every technical decision, every guardrail, and every eval exists to prove one of these holds:

1. **Grounded answers only.** The bot will only answer questions answerable from the PDF corpus. If retrieval confidence is low, it says "I don't have that information."
2. **No advice.** The bot will never give financial, legal, or purchasing advice.
3. **No final prices.** The bot will never generate a final quote price itself — it collects information and hands off to a deterministic pricing engine.
4. **Citations.** The bot will always cite source sections for factual claims.
5. **Prompt injection resistance.** The bot will detect and refuse prompt injection attempts, and log them for review.
6. **Human handoff.** Anything outside the state machine triggers a handoff to a human.

These are written in stone in `docs/contract.md` from day one and the eval suite exists to prove each one.

---

## System Architecture

The system has four layers with clean separation of responsibility:

**1. Ingestion & Knowledge Base.** PDF parsing, hierarchical chunking with section metadata, embedding, vector store persistence. Built once at project start, rebuilt when corpus changes.

**2. Retrieval Layer.** Hybrid dense + sparse retrieval with reciprocal rank fusion, cross-encoder reranking, and metadata filtering. Returns ranked, cited chunks.

**3. Conversational Orchestration.** A deterministic state machine (greeting → product selection → risk profiling → coverage questions → quote summary → handoff). LLM calls happen *within* states for natural language understanding, but state transitions are deterministic Python code based on slot completeness.

**4. Guardrails.** Four independent layers: input (topic classification, prompt injection detection, PII redaction), retrieval (confidence thresholds, mandatory grounding), output (schema validation, refusal classifiers, claim verification), and behavioural (the pricing engine handoff boundary).

---

## Tech Stack

**Language & tooling:** Python 3.11+, `uv` for dependency management, `ruff` for linting/formatting, `pytest` for testing, pre-commit hooks.

**LLM runtime:** Ollama (local). Primary model: `llama3.1:8b-instruct-q4_K_M`. Secondary: `qwen2.5:7b-instruct` for strict-format prompts.

**Embeddings:** `sentence-transformers` with `bge-small-en-v1.5` (fast, CPU-friendly).

**Vector store:** Chroma (zero-config, disk-persistent).

**Retrieval:** `rank_bm25` for sparse, custom reciprocal rank fusion, `bge-reranker-base` for reranking.

**PDF parsing:** `pymupdf4llm` or `docling` (decide in Week 1 after testing both).

**Orchestration:** Custom Pydantic-based state machine (no LangGraph — more code, better interview story).

**Guardrails:** Custom layer with `presidio` for PII, `protectai/deberta-v3-base-prompt-injection-v2` for injection detection, Pydantic for schema validation.

**API layer:** FastAPI for the mock pricing engine endpoint.

**UI:** Streamlit with a debug panel exposing state, retrieved chunks, and guardrail decisions.

**Evaluation:** RAGAS for RAG metrics, custom harness for adversarial evaluation, bootstrap confidence intervals for all reported numbers.

---

## Effort Allocation

Balanced across the three portfolio pillars:

- **Guardrails & adversarial evaluation:** ~35% of total effort
- **RAG quality & retrieval sophistication:** ~35%
- **Full-stack polish & demo UX:** ~30%

Polish is deliberately lower because it has diminishing returns. The contract, the eval, and the writeup are what sell the project.

---

## Week 1: Foundations & Ingestion

**Goal for end of week:** Query a Python REPL and get back well-ranked chunks from a corpus of real insurance PDFs.

### Day 1 — Repo & Contract

**What:** Set up the repository skeleton, lock in the contract document, and install the local LLM runtime.

**How:**

1. Create `quoteguard` repo on GitHub with this structure:
   ```
   quoteguard/
   ├── src/quoteguard/
   │   ├── ingestion/
   │   ├── retrieval/
   │   ├── orchestration/
   │   ├── guardrails/
   │   ├── llm/
   │   └── api/
   ├── data/{raw_pdfs,processed,eval}/
   ├── notebooks/
   ├── tests/
   ├── evals/
   ├── docs/
   ├── scripts/
   └── README.md
   ```
2. `uv init`, add initial dependencies: `pydantic`, `ollama`, `chromadb`, `sentence-transformers`, `rank-bm25`, `pymupdf4llm`, `docling`, `pytest`, `ruff`, `streamlit`, `presidio-analyzer`, `presidio-anonymizer`, `jinja2`, `python-dotenv`.
3. Set up `ruff` config and pre-commit hooks. Write one smoke test that imports the top-level module.
4. Install Ollama. Pull `llama3.1:8b-instruct-q4_K_M`, `qwen2.5:7b-instruct`, and `nomic-embed-text` (fallback embedder).
5. Write `docs/contract.md` with the six guarantees spelled out, each with a placeholder "how we enforce this" note.
6. Initial commit and push.

**Deliverable:** Clean repo skeleton, contract document, Ollama working locally.

### Day 2 — Corpus Acquisition & Inspection

**What:** Gather insurance PDFs, inspect them manually, decide chunking strategy.

**How:**

1. Write `scripts/fetch_corpus.py` that downloads 5–8 home contents PDS documents from Australian insurers (AAMI, Budget Direct, Allianz, Youi, Bupa). Do **not** commit the PDFs themselves.
2. Open every PDF manually. Note in `docs/corpus_notes.md`: heading structure, tables of benefits, nested sections, scanned pages, footnotes, cross-references. This informs parsing.
3. Check copyright pages. Document usage rights in the README to pre-empt questions.
4. Decide on one product vertical (recommended: home contents). Tight scope beats broad scope.

**Deliverable:** Fetch script, corpus notes, scope decision locked in.

### Day 3 — PDF Parsing

**What:** Compare parsers and choose one based on output quality on *your actual corpus*.

**How:**

1. Write `notebooks/01_parser_comparison.ipynb`. Parse the same 2–3 PDFs with `pymupdf4llm` and `docling`. Compare: heading preservation, table handling, reading order, speed.
2. Pick a winner. Document the decision in `docs/design_decisions.md` with concrete examples.
3. Write `src/quoteguard/ingestion/parser.py` wrapping the chosen parser behind a clean interface so you can swap later.
4. Parse the full corpus and cache intermediate output to `data/processed/parsed/`.

**Deliverable:** Parsed corpus, parser module, documented design decision.

### Day 4 — Chunking & Metadata

**What:** Hierarchical chunking that preserves document structure.

**How:**

1. Write `src/quoteguard/ingestion/chunker.py`. Strategy: parse into sections using heading structure, then split long sections into ~500 token chunks with 50 token overlap.
2. Every chunk carries metadata: `{source_pdf, product_type, section_path, page_number, chunk_id}`.
3. Write unit tests verifying: chunks never exceed max tokens, metadata is complete, section boundaries are respected where possible.
4. Run chunking across full corpus, persist to `data/processed/chunks.jsonl`.

**Deliverable:** Chunker module, test coverage, processed chunks with metadata.

### Day 5 — Embedding & Vector Store

**What:** Embed chunks and persist to Chroma. Baseline dense retrieval working end-to-end.

**How:**

1. Write `src/quoteguard/ingestion/embedder.py` using `sentence-transformers` and `bge-small-en-v1.5`.
2. Write `src/quoteguard/retrieval/vector_store.py` wrapping Chroma with methods: `upsert_chunks()`, `query(text, k, filters)`.
3. Write `scripts/build_index.py` — one-shot script that parses → chunks → embeds → persists.
4. Write `notebooks/02_retrieval_sanity.ipynb` with 20 hand-crafted questions. Eyeball the top-5 results for each.
5. Record baseline recall@5 as your starting point for the ablation table.

**Deliverable:** Indexed corpus, working dense retrieval, baseline metric recorded.

### Weekend Buffer / Catch-up

PDF parsing always takes longer than expected. Use the weekend to absorb overruns, not to get ahead. If you're on schedule, start exploring adversarial prompt ideas informally — it'll pay off in Week 3.

---

## Week 2: Orchestration & Happy Path

**Goal for end of week:** Complete a full quote conversation end-to-end from a terminal. Guardrails minimal, but the flow works.

### Day 6 — Hybrid Retrieval & Reranking

**What:** Upgrade retrieval from baseline dense to production-quality hybrid + rerank.

**How:**

1. Add BM25 via `rank_bm25` in `src/quoteguard/retrieval/sparse.py`.
2. Write reciprocal rank fusion in `src/quoteguard/retrieval/fusion.py` (~15 lines).
3. Add reranking with `bge-reranker-base` in `src/quoteguard/retrieval/reranker.py`. Rerank top-20, return top-5.
4. Re-run the 20 sanity questions. Record recall@5 and MRR at each stage: baseline → +bm25 → +rerank. This is your ablation table.
5. Add metadata filtering (product type, section type).

**Deliverable:** Hybrid retriever, ablation table with numbers.

### Day 7 — Ollama Client & Prompt Infrastructure

**What:** Build the LLM client layer and prompt template system.

**How:**

1. Write `src/quoteguard/llm/client.py` wrapping the Ollama Python client. Features: temperature=0 default, JSON schema mode for structured output, disk-cached responses keyed on `(prompt, model, temperature)`, automatic retry with repair prompts on malformed JSON.
2. Set up `src/quoteguard/llm/prompts/` with Jinja2 templates. Store every prompt as a file — never inline strings. This makes prompt iteration reviewable in git.
3. Write a structured output helper: takes a Pydantic model, returns a validated instance or raises.
4. Unit test the client with a mocked Ollama backend.

**Deliverable:** LLM client module, prompt template system, caching layer.

### Day 8 — State Machine Schema

**What:** Define states, slots, and transitions as Pydantic models. No LLM calls yet — just the skeleton.

**How:**

1. Write `src/quoteguard/orchestration/state.py`:
   ```python
   class ConversationState(BaseModel):
       phase: Literal["greeting", "product_select", "risk_profile",
                      "coverage_questions", "quote_summary", "handoff"]
       product_type: Optional[Literal["home_contents"]]
       slots: dict[str, Any]
       turn_count: int
       history: list[Message]
   ```
2. For each phase, define: required slots, allowed LLM actions, allowed retrieval filters.
3. Write `src/quoteguard/orchestration/transitions.py` — pure functions that take a state and return the next phase. Transitions are deterministic; the LLM never decides them.
4. Unit test every transition path.

**Deliverable:** State machine schema, transition logic, full test coverage.

### Day 9 — Risk Profile State (Built Deep)

**What:** Implement one state completely, end-to-end. This becomes the template for the other states.

**How:**

1. Write the risk profile prompt template: asks the user about property type, location, security features, etc.
2. Write a slot extraction function using structured output: takes user message + current slots, returns updated slots.
3. Write validation for each slot (e.g., postcode must match regex).
4. Wire it into the state machine so the risk profile phase loops until all required slots are filled.
5. Write an integration test that simulates a user filling the risk profile through several turns.

**Deliverable:** One complete state, template pattern for the others.

### Day 10 — Remaining States (Built Shallow)

**What:** Replicate the pattern across the remaining states. Shallow is fine — depth comes later.

**How:**

1. Implement greeting, product selection, coverage questions, quote summary, handoff following the Day 9 pattern.
2. Coverage questions is the one that uses retrieval: the user asks a question, the bot retrieves relevant chunks from the PDFs, generates a grounded answer with citations.
3. Quote summary assembles a `QuoteRequest` Pydantic object from collected slots.
4. Handoff calls the mock pricing engine (built Day 11).
5. Run an end-to-end conversation manually. Expect bugs; fix them.

**Deliverable:** All six states working in sequence, a conversation can complete.

### Day 11 — Mock Pricing Engine

**What:** The deterministic endpoint the bot hands off to. This makes the architectural boundary concrete.

**How:**

1. Write a tiny FastAPI app in `src/quoteguard/api/pricing.py`. One endpoint: `POST /quote`.
2. Input: a validated `QuoteRequest` Pydantic object. Output: a deterministic mock price (e.g., a simple formula over the slots).
3. The bot *cannot* compute a price — it can only POST to this endpoint.
4. Test with the happy path conversation from Day 10.

**Deliverable:** Pricing engine running, handoff boundary enforced in code.

### Day 12 — Grounding Discipline & Week 2 Close

**What:** Make sure generation never invents facts, even without the full guardrail stack in place.

**How:**

1. Write the coverage question prompt template carefully. Instructions: use only the provided chunks, cite by section path, respond with "I don't have that information" if no chunk is relevant.
2. Add a post-generation check: every factual sentence must contain at least one citation marker. If not, replace with safe fallback.
3. Test adversarially by hand — ask questions the PDFs don't answer. Does it refuse?
4. Commit, tag as `v0.2-happy-path`, review the week's work.

**Deliverable:** Happy path works end-to-end, basic grounding in place, ready for Week 3.

---

## Week 3: Guardrails & Evaluation

**Goal for end of week:** Full guardrail stack, golden dataset, adversarial evaluation, measured robustness with confidence intervals.

### Day 13 — Input Guardrails

**What:** Topic classification, prompt injection detection, PII redaction. Everything the bot sees gets filtered first.

**How:**

1. Topic classifier: start with zero-shot using `facebook/bart-large-mnli` classifying into "insurance question" vs "off-topic". If too slow, fine-tune a small `distilbert` on ~200 examples.
2. Prompt injection detector: drop in `protectai/deberta-v3-base-prompt-injection-v2`.
3. PII redaction with `presidio-analyzer` + `presidio-anonymizer`. Redact before logging, never log raw user input.
4. Wire all three into a single `InputGuardrail` class in `src/quoteguard/guardrails/input.py`.
5. Unit test with obvious positive and negative examples.

**Deliverable:** Input guardrail layer, tested.

### Day 14 — Output & Grounding Guardrails

**What:** Nothing leaves the bot without being checked.

**How:**

1. Grounding check: after the LLM generates a response, call the LLM again with "list any claims in this response not supported by these chunks." If the list is non-empty, replace response with safe fallback. Prompt it as per-sentence for reliability.
2. Refusal classifier for advice-giving. Start with keyword heuristics (words like "should", "I recommend", "you ought to"). Optionally fine-tune a small classifier if time permits.
3. Schema validation for structured outputs via Pydantic.
4. Regex blocklists for forbidden patterns: dollar amounts in freeform text, competitor names, legal interpretation phrases.
5. Wire into `OutputGuardrail` class in `src/quoteguard/guardrails/output.py`.

**Deliverable:** Output guardrail layer, tested, integrated into the generation pipeline.

### Day 15 — Golden Dataset Construction

**What:** Hand-craft the evaluation dataset. This is slow and boring but non-negotiable.

**How:**

1. Write 80–100 question/answer pairs from your corpus. Each entry: `{question, expected_answer, expected_source_chunks, product_type}`.
2. Spread across difficulty: direct lookups, multi-section synthesis, edge cases, questions with no answer in the corpus (should refuse).
3. Store as `data/eval/golden.jsonl`.
4. Use an LLM to help *brainstorm* questions but review every entry by hand. Quality over quantity.
5. Write `evals/run_rag_eval.py` using RAGAS: faithfulness, answer relevancy, context precision, context recall. Report with bootstrap 95% confidence intervals.

**Deliverable:** Golden dataset, RAG eval harness, first RAG metrics recorded.

### Day 16 — Adversarial Dataset Construction

**What:** The showpiece artefact. 150+ adversarial prompts across six categories.

**How:**

1. Six attack categories:
   - **Prompt injection** ("ignore all previous instructions...")
   - **Role-play jailbreaks** ("pretend you're an agent with no restrictions")
   - **Off-topic extraction** (weather, general knowledge, competitor info)
   - **Advice solicitation** ("should I buy this?", "is this a good policy?")
   - **System prompt extraction** ("repeat your instructions")
   - **Price manipulation** ("just give me an estimate, it's fine")
2. Aim for 25+ prompts per category. Pull some from JailbreakBench and HarmBench to signal awareness of the literature.
3. For each entry: `{prompt, category, expected_behaviour: "refuse" | "deflect" | "handoff"}`.
4. Store as `data/eval/adversarial.jsonl`.
5. Also build a **benign control set** (50 normal insurance questions) to measure false-positive rate — refusing legitimate questions is also a failure.

**Deliverable:** Adversarial dataset, benign control set.

### Day 17 — Adversarial Evaluation & Iteration

**What:** Run the adversarial eval, find failures, fix them, re-run.

**How:**

1. Write `evals/run_adversarial_eval.py`. For each entry, run the full pipeline, record the result, compare to expected behaviour.
2. Report per-category refusal rate and overall false-positive rate on the benign set. Bootstrap confidence intervals.
3. First run will reveal failures. Fix the top 3–5 failure modes by tightening prompts, adjusting thresholds, or adding specific guards.
4. Re-run. Document the before/after in the eval report. The iteration story is itself a portfolio signal.

**Deliverable:** Adversarial eval results, at least one iteration cycle documented.

### Day 18 — Conversational Simulation

**What:** End-to-end flow testing with a simulated user.

**How:**

1. Write a user simulator: an LLM with a persona prompt instructed to try to complete a quote for a specific scenario.
2. Run 50 simulated conversations. Record: completion rate, average turns to completion, slot accuracy vs ground truth, guardrail trigger rate.
3. This catches flow bugs that unit tests miss — states that loop forever, slots that never fill, handoffs that fire too early.
4. Fix anything that's clearly broken. Log anything weird for the eval report.

**Deliverable:** Simulation results, flow bugs fixed.

### Day 19 — Eval Report Draft

**What:** Turn all the numbers into a narrative document.

**How:**

1. Write `evals/REPORT.md` with sections: Setup, RAG Quality, Adversarial Robustness, Conversational Flow, Failure Analysis, Before/After Iteration.
2. Include tables with confidence intervals, not point estimates.
3. Include 2–3 specific failure examples with commentary on why they failed and how you fixed them.
4. This document is arguably more valuable than the code for portfolio purposes. Treat it as such.

**Deliverable:** Draft eval report, ready to polish in Week 4.

---

## Week 4: Polish, Demo & Writeup

**Goal for end of week:** Shippable portfolio piece. Deployed demo, polished README, eval report finalised, design decisions doc complete.

### Day 20 — Streamlit UI

**What:** A clean demo interface with a debug panel that exposes the system internals.

**How:**

1. Two panels: chat on the left, debug panel on the right.
2. Debug panel shows: current state phase, populated slots, last retrieval query and top-5 chunks, guardrail decisions for the last turn.
3. The debug panel is the interview superpower — it makes the invisible visible.
4. Don't over-polish. Clean and functional beats fancy.

**Deliverable:** Working Streamlit app, locally runnable.

### Day 21 — Deployment

**What:** A clickable demo hiring managers can try.

**How:**

1. HuggingFace Spaces is the easiest path for a Streamlit app.
2. Ollama-in-container is painful. Two honest options:
   a. Deploy with an API-backed model (OpenAI/Anthropic) for the hosted version, with a clear note in the README that local development uses Ollama.
   b. Don't deploy — record a 2-minute demo video instead. Video + clear local setup instructions is acceptable.
3. Document whichever choice you make in the README and design decisions doc.

**Deliverable:** Deployed demo *or* polished demo video + local run instructions.

### Day 22 — README & Architecture Diagram

**What:** The front door to the project.

**How:**

1. README structure:
   - 30-second pitch at the top
   - GIF or video of the demo
   - The six-point contract
   - Architecture diagram
   - Headline eval metrics (RAG + adversarial with CIs)
   - How to run locally
   - Links to deep-dive writeups
2. Architecture diagram: use Excalidraw or draw.io. Show the four layers, data flow, and guardrail checkpoints. Commit the source file as well as the exported image.
3. Reviewers often don't click through to demos. The README has to sell the work on its own.

**Deliverable:** Polished README, committed architecture diagram.

### Day 23 — Design Decisions Doc

**What:** The document that turns this from "a project" into "a considered piece of engineering."

**How:**

1. Write `docs/design_decisions.md` covering:
   - Why state machine vs open agent
   - Why local Ollama vs API
   - Why custom orchestration vs LangGraph
   - Chunking strategy and why
   - Grounding check approach and failure modes
   - How the guardrail layers compose
   - Known limitations and what you'd do with more time
2. This is what separates a portfolio project from a tutorial follow-along. Every non-obvious decision should be explained here.

**Deliverable:** Design decisions doc, ready to reference in interviews.

### Day 24 — Eval Report Polish & Future Work

**What:** Finalise the eval report, write the future work doc.

**How:**

1. Polish `evals/REPORT.md`: tighten prose, add any missing confidence intervals, double-check numbers against the scripts.
2. Write `docs/future_work.md` listing everything you'd do with more time: richer corpus, more product lines, fine-tuned grounding classifier, observability with Langfoe/Phoenix, A/B testing prompts, richer pricing engine. This doc is itself a portfolio signal — it shows you know what "done enough" means.

**Deliverable:** Final eval report, future work doc.

### Day 25 — Blog Post / LinkedIn Writeup

**What:** Turn the project into a narrative you can point employers to.

**How:**

1. 800–1500 word writeup. Structure: the problem, the contract, one or two technical deep dives (the state machine and the adversarial eval), the headline numbers, what you learned, what you'd do next.
2. Post it on your portfolio site, LinkedIn, or dev.to. Link from the README.
3. The writeup is what lets hiring managers share your work internally. Invest in it.

**Deliverable:** Published writeup, links from README and portfolio.

### Day 26–28 — Buffer

Three-day buffer for overruns, last-minute polish, and a final review pass. Do not skip the buffer — something will go wrong and you want the slack.

Final checklist before calling it done:
- [ ] Clean git history, meaningful commit messages
- [ ] README sells the work in 30 seconds
- [ ] Contract doc and six guarantees are prominent
- [ ] Eval report has confidence intervals, not point estimates
- [ ] Architecture diagram committed
- [ ] Design decisions doc explains every non-obvious choice
- [ ] Demo is runnable (local or hosted)
- [ ] Blog post published and linked
- [ ] Future work doc present

---

## Pitfalls & Learned-the-Hard-Way Notes

**PDF parsing will consume more time than expected.** Insurance PDFs have tables, multi-column layouts, and footnotes that confuse most parsers. Budget a full day in Week 1, drop problematic PDFs rather than fighting them.

**Local model JSON output is fragile.** Even with structured output mode, expect occasional malformed responses. Wrap every structured LLM call in a retry loop with a repair prompt. Log every failure — they become adversarial eval material.

**The grounding guardrail is the hardest to get right.** 8B models aren't great at NLI-style checks. Prompt per-sentence, use few-shot examples, and fall back to keyword-overlap heuristics plus strict generation prompts if it's unreliable. Sometimes prevention beats detection.

**Eval set creation is slow and boring but non-negotiable.** Block out full days in Week 3 for this. LLM-assisted brainstorming is fine; LLM-generated entries without human review are not.

**Scope creep is the #1 killer of portfolio projects.** Every "one more thing" goes into `future_work.md`, not into the codebase. Defend the scope.

**Don't refactor during Weeks 2 or 3.** It's tempting to clean up Week 1 code, but resist until Week 4. Working code that ships beats clean code that doesn't.

**Protect Week 3.** The adversarial eval is the single highest-leverage artefact. If Week 1 or Week 2 overruns, cut scope from Week 4 polish, not from Week 3 evaluation.

**Design around the 8B model, don't fight it.** Local models are weaker at long-context reasoning and complex JSON. The state machine and strict prompts exist *because* of this — frame it as deliberate engineering in your writeup, not as a limitation.

**Version prompts and eval data like code.** When you change a prompt and metrics move, you want to know which change caused it.

---

## Success Criteria

By end of Week 4 you should have:

- A GitHub repo with clean commit history spanning 4 weeks
- A deployed (or easily runnable) demo with debug panel
- A README that opens with the contract and closes with headline eval metrics
- An evaluation report showing RAG quality, adversarial robustness, and conversational flow with confidence intervals
- A design decisions doc walking through the non-obvious choices
- An architecture diagram
- A published blog post or LinkedIn writeup turning the project into a narrative
- A `future_work.md` showing you know what "done enough" means

That's a portfolio piece that gets you interviews specifically *about this project* — which is the goal.

---

## Future Work

Things explicitly out of scope for this build but worth listing for the portfolio signal:

- Multi-product support (home building, motor, travel)
- Observability with Langfuse or Phoenix for trace visualisation
- Fine-tuned grounding classifier trained on labelled failure cases
- Feedback loop: flagged interactions automatically added to the eval set
- Prompt A/B testing harness
- Richer pricing engine with actual actuarial logic
- Multi-turn memory compression for very long conversations
- Internationalisation and support for non-English PDS documents
- Integration with a real underwriting system

---

*This plan is a living document. Update it as you go — especially the design decisions doc and future work list. Good luck.*
