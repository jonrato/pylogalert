# Exceptions (structured stack traces)

`pylogalert` provides a convenience method `log.exception(event, **fields)` that captures **structured exception details**:
- `exc_type` (e.g., `KeyError`)
- `exc_message` (stringified exception)
- `stack` (full traceback string)

All of these are merged into the JSON log line together with your custom fields and the current context.

---

## Basic usage

```python
import pylogalert as log

log.configure(service="orders", env="prod")

try:
    {}["missing"]
except KeyError:
    log.exception("lookup_failed", route="/orders/1", foo=123)
```
Example JSON (excerpt):
```json
{
  "level": "ERROR",
  "event": "lookup_failed",
  "route": "/orders/1",
  "foo": 123,
  "exc_type": "KeyError",
  "exc_message": "'missing'",
  "stack": "Traceback (most recent call last):\n  ..."
}
```

Notes:

- log.exception(...) logs at ERROR level by design.

- Context fields set via log.set_context(...) are included automatically.

## Equivalent form via _exc_info=True

Under the hood, log.exception(event, **fields) is equivalent to:
```python
log.error("lookup_failed", _exc_info=True, route="/orders/1")
```
You can use this form if you want to keep a single call style for all levels.

## Attach more metadata

Any keyword arguments become structured JSON fields:

```python
try:
    1 / 0
except ZeroDivisionError:
    log.exception("calc_error", order_id=999, stage="invoice")
```

## Async / concurrent code

pylogalert uses ContextVar for context, so exception logs in concurrent tasks won’t leak context between requests:

```python
import asyncio, pylogalert as log

log.configure(service="orders", env="test")

async def handler(name):
    log.set_context(request_id=name)
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        log.exception("handler_failed")

asyncio.run(asyncio.gather(handler("r1"), handler("r2")))
```
Each task’s request_id is isolated.


## Redaction and exception fields

Redaction applies to the entire emitted payload, including stack and any custom fields:

-- Keys in redact_keys are replaced by ***REDACTED***.

-- redact_regexes are applied to strings, so matches inside the stack string will be masked too.

```python
log.configure(
    service="t", env="test",
    redact_keys={"token"},
    redact_regexes=[r"\b\d{11}\b"]  # mask 11-digit sequences in strings (incl. stack)
)
```
Redaction is best-effort. Choose sensible keys/patterns that match your compliance needs (GDPR/LGPD, PCI, HIPAA).

## Local quick test

```python
from io import StringIO
import json
import pylogalert as log

s = StringIO()
log.configure(service="t", env="test", stream=s)

try:
    {}["x"]
except KeyError:
    log.exception("explode", foo=123)

line = s.getvalue().strip().splitlines()[-1]
data = json.loads(line)
assert data["event"] == "explode"
assert data["exc_type"] == "KeyError"
assert "stack" in data and "KeyError" in data["stack"]
```

## Best practices

- Use log.exception(...) only in exception handlers. For non-exception error states, prefer log.error(...).

- Avoid logging the same exception multiple times (e.g., re-raise after logging). Log once at the boundary where you can add meaningful context.

- For expected control-flow errors (e.g., validation), don’t use exception logs; use WARNING or INFO with structured fields instead.

- In highly sensitive environments, prefer key-based redaction for known fields and a targeted regex set for stack masking to balance safety and readability.