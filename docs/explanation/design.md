# Explanation — Design and Concepts

This section gives the rationale behind pylogalert’s core features. Concise but enough to explain why each decision was made

## Structured JSON logs

- JSON makes logs easy to parse and index in ELK, Loki, DataDog, etc.

- Flat key‑value objects ensure compatibility and searchability.

## Context via ContextVar

- Unlike globals, `ContextVar` keeps request/task context isolated across threads and async tasks.

- Enables adding `request_id`, `user_id`, or trace fields without polluting global state.

## Built‑in redaction

- Sensitive data (passwords, credit cards) often leaks into logs.

- Redaction at the formatter level guarantees safety even if app code forgets.

- Supports `redact_keys` (exact match) and `redact_regexes` (patterns).

## Sampling

High‑volume debug/info logs can overload storage and budgets.

Per‑level sampling (`{"debug":0.1}`) reduces noise while keeping critical levels intact.

`EMERGENCY` is never sampled.

## Custom level: EMERGENCY

- Numeric level 60, above CRITICAL.

- Always emitted and can trigger external notifications.

- Separates log everything from wake up humans.

## Notifications
 
- Decoupled `Notifier` supports Slack, SES, or custom callables.

- Features: fan‑out, rate‑limit, dedupe, retries.

- Philosophy: logging should never crash the app if a channel fails.


## Philosophy

Favor safe defaults (UTC timestamps, JSON, redaction).

Keep the API minimal (`configure`, `context`, log functions).

Ensure operational guardrails: no PII leaks, no silent drops at EMERGENCY, no crash on notifier failure.