# API Reference — pylogalert
Runtime‑friendly structured logging with JSON output, ContextVar context, built‑in redaction, level sampling, and an `EMERGENCY` level that can trigger external notifications via a `Notifier`.

This reference reflects the code you shared (`_core.py, notify.py, notify_slack.py, notify_ses.py`).

## Top‑level functions
`configure(service, *, env=None, level=None, stream=None, redact_keys=(), redact_regexes=(), sample=None, tz_utc=True, extra_static=None, color=None)`

Configure the global logging behavior and JSON formatter.

### Parameters

`service: str` — Service name included in every log line.

`env: Optional[str]` — Environment tag (default: `APP_ENV` or `"dev"`).

`level: Optional[str]` — Minimum log level (e.g. `"INFO"`).

`stream: IO` — Output stream (default: `sys.stdout`).

`redact_keys: Iterable[str]` — Keys whose values are replaced with `***REDACTED***` recursively.

`redact_regexes: Iterable[str]` — Regex patterns applied to strings (global substitution to `***REDACTED***`).

`sample: Optional[Dict[str, float]]` — Per‑level sampling probabilities. Keys are lowercase (e.g. `{"debug": 0.1, "info": 1.0}`). `EMERGENCY` is never sampled.

`tz_utc: bool` — If `True`, timestamps are UTC with `Z`. Otherwise local time.

`extra_static: Optional[Dict[str, Any]]` — Static fields merged into every JSON log.

`color: Optional[bool]` — Force ANSI colors on/off. If `None`, respects `LOG_PRETTY` env var or TTY detection.

### Notes

- Replaces all handlers of the internal logger and installs a JSON logging.Formatter.

- Level names include built‑in levels and custom EMERGENCY (numeric 60).

## Context helpers

- `set_context(**kv) -> None` — Merge key‑values into a ContextVar used by the formatter and notifier payload.

- `get_context() -> Dict[str, Any]` — Return current context dict.

- `clear_context() -> None` — Clear context for the current task/thread.

Context is task‑local (safe under async and threads).

## Logging functions

All functions accept a mandatory `event: str` and arbitrary structured fields as `**fields`. Fields are merged into the JSON log line after     service`, `env`, timestamp and context.

- `debug(event: str, **fields) -> None`

- `info(event: str, **fields) -> None`

- `warn(event: str, **fields) -> None`

- `warning(event: str, **fields) -> None (alias of warn)`

- `error(event: str, **fields) -> None`

- `critical(event: str, **fields) -> None`

- `exception(event: str, **fields) -> None` — Logs at `ERROR` level with structured exception fields. Pass `_exc_info=True` implicitly (handled by the helper).

- `emergency(event: str, **fields) -> None` — Logs at custom `EMERGENCY` (60). Never sampled.

### Special private fields (filtered before JSON output):

- `_exc_info: bool` — When present/true in low‑level calls, attaches exc_type, exc_message, stack to the JSON.

- `_notify: Notifier` — Only respected by EMERGENCY. If provided, the logger builds a redacted payload and calls Notifier.send(payload).

### Sampling

- Deterministic per‑call decision via pseudo‑random UUID hashing. Keys in `sample` must be lowercase (`"debug"`, `"info"`, ...). Missing key → emit.

`EMERGENCY` bypasses sampling.


## Notifier & channels

### `class Notifier`
Fan‑out sender with token‑bucket rate limiting, deduplication and constant‑delay retries.

```python
Notifier(
*,
channels: Iterable[Callable[[Dict[str, Any]], None]],
rate_limit: Optional[tuple[str, int]] = None,
dedupe_window: Optional[float] = None,
retries: tuple[int, float] = (0, 1.0),
)
```

#### Parameters

- `channels` — Callables receiving a redacted payload dict.

- `rate_limit` — `(rate_str, capacity)`; `rate_str` is `"N/sec" | "N/min" | "N/hour"`. Internally converted into a minimum token interval; capacity allows short bursts.

- `dedupe_window` — Seconds. If the SHA‑256 of the serialized payload matches the previous send within this window, the notification is suppressed.

- `retries` — `(retries, backoff_seconds)`. Number of extra attempts and a constant sleep between attempts.

### Methods
 - `send(payload: Dict[str, Any]) -> None` — Applies dedupe/rate‑limit gating and, if allowed, calls each channel. Failures are retried; final failure is swallowed (logging should not crash the app).

### Threading

Rate/dedupe gating is protected by a lock. Channel invocations happen outside the lock.


### Channels
`slack_webhook(webhook_url: str, *, text_template: Optional[Callable[[Dict[str, Any]], str]] = None) -> Channel`

Creates a Slack Incoming Webhook channel.

- `text_template(payload) -> str` (optional). If omitted, the payload dict is stringified and sent as text prefixed with `:rotating_light:`.

- Network timeout is ~5s (via `urllib.request.urlopen`). Exceptions bubble to `Notifier` to trigger retries.

#### Example

```python
slack = slack_webhook(
webhook_url="https://hooks.slack.com/services/...",
text_template=lambda p: f"🚨 {p['event']} | svc={p['service']} env={p['env']}"
)
```

`
ses_email(*, sender: str, to: Iterable[str], region: str) -> Channel
`

Creates an Amazon SES email channel using `boto3`.

- Requires extra: `pip install pylogalert[ses]`.

- Subject format: `[LEVEL] EVENT (service/env)`.

- Body: pretty‑printed JSON of the payload.

#### Example
```python
email = ses_email(
sender="alerts@mycompany.com",
to=["oncall@mycompany.com"],
region="us-east-1",
)
```

## JSON output schema
Each log line is a single JSON object (optionally ANSI‑colored for TTY). Canonical fields:


- `ts: str` — ISO timestamp (UTC Z if tz_utc=True).

- `level: str` — One of `DEBUG|INFO|WARNING|ERROR|CRITICAL|EMERGENCY`.

- `service: str`, `env: str` — Values from configuration.

- `event: str` — Message/event string.

- `...context` — All keys from `get_context()` are merged at top level.

- `...extra_fields` — Any additional `**fields` passed to the logging call.

- (optional) `exc_type`, `exc_message`, `stack` — Present when `_exc_info=True` / `exception()`.

#### Redaction

- Keys present in `redact_keys` are replaced by `***REDACTED***` recursively.

- For strings, each regex in `redact_regexes` is applied globally; matches are replaced by `***REDACTED***`.

#### Color
 - When enabled (TTY or `LOG_PRETTY=1` or `color=True`), the whole JSON line is wrapped in an ANSI color chosen per level.

## Custom level: `EMERGENCY``

- Numeric value: 60 (via `logging.addLevelName`).

- Never sampled; intended to trigger human‑visible notifications via `_notify=Notifier`.

