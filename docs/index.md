# pylogalert

**JSON-structured logging for Python — async-safe, with built-in PII redaction, per-level sampling, and an EMERGENCY level that can trigger external notifications (Slack, SES, ...).**

---

## Features

- **JSON logs** per line (ready for ELK, Loki, DataDog, etc.)
- **Async-safe context** using `ContextVar`
- **PII redaction** by key (`redact_keys`) or regex (`redact_regexes`)
- **Sampling** by log level to reduce noise and cost
- **EMERGENCY level**: never sampled, can trigger notifications
- **Optional colorized output** (TTY/dev, `LOG_PRETTY=1`)
- **Timezone aware** (UTC by default, local optional)
- **Integrates seamlessly** with Python’s `logging` module

---

## Installation

```bash
pip install pylogalert
# optional extras:
pip install pylogalert[ses]    # Amazon SES notification channel
```

## Short example

```bash
from pylogalert import configure, set_context, info, exception, emergency

configure(
    service="orders",
    env="prod",
    level="INFO",
    redact_keys={"password"},
    redact_regexes=[r"\b\d{11}\b"],  # redact CPFs
)

set_context(request_id="abc123", user_id=42)

info("user_login", email="alice@example.com", password="s3cr3t")

try:
    1/0
except ZeroDivisionError:
    exception("calc_error")

emergency("payment_outage", region="us-east-1")

```
Typical JSON output (1 log line):

```bash
{"ts":"2025-09-02T23:59:59Z","level":"INFO","service":"orders","env":"prod","event":"user_login","request_id":"abc123","user_id":42,"email":"alice@example.com","password":"***REDACTED***"}

```

Next steps

Get started in 5 minutes: Quickstart

Practical guides: see How-to
 for redaction, sampling, context handling, exceptions, and more

API Reference: Reference