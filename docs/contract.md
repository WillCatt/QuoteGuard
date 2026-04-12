# QuoteGuard Contract

QuoteGuard exists to enforce six guarantees in a regulated domain. Every guardrail, prompt, retrieval check, and evaluation asset should trace back to one of these commitments.

## 1. Grounded Answers Only

The bot answers only from the PDF corpus. If retrieval confidence is below threshold, the system responds with a refusal or handoff instead of guessing.

How we enforce this:
- retrieval confidence thresholding
- citation requirements on factual responses
- post-generation grounding checks

## 2. No Advice

The bot may explain policy wording, but it cannot recommend products, legal positions, or purchase decisions.

How we enforce this:
- advice-seeking input detection
- output pattern checks for recommendation language
- deterministic refusal copy

## 3. No Final Prices

The bot collects data for a quote request and hands off to a deterministic pricing endpoint. It never invents or estimates a price in freeform chat.

How we enforce this:
- explicit behavioural boundary in orchestration
- output guardrail blocklists for freeform dollar amounts
- pricing calculation isolated in `api/pricing.py`

## 4. Citations

Factual claims must cite the document section and page reference where possible.

How we enforce this:
- retrieval chunks carry section metadata
- coverage-answer generation uses retrieval payloads only
- output checks reject unsupported factual text

## 5. Prompt Injection Resistance

Prompt injection, system prompt extraction, and jailbreak attempts must be refused and logged in redacted form.

How we enforce this:
- input guardrail pattern detection and classifier hook points
- audit logging with PII redaction
- adversarial evaluation dataset and reporting

## 6. Human Handoff

Anything outside the approved state machine or retrieval contract triggers a handoff to a human or downstream system.

How we enforce this:
- deterministic transition logic
- allowed-action maps per state
- explicit handoff state and refusal pathways
