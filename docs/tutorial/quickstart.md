# Quickstart

This tutorial will get you started with **pylogalert** in just a few minutes.  
We will configure the logger, add context, log structured events, capture exceptions, and emit an EMERGENCY alert.

---

## 1. Install

```bash
pip install pylogalert
# optional extras:
pip install pylogalert[ses]
```

## 2. Configure
Use log.configure() to set up the logger for your service:

```bash
import pylogalert as log

log.configure(
    service="orders",
    env="prod",
    level="INFO",
    redact_keys={"password"},            # redact sensitive keys
    redact_regexes=[r"\b\d{11}\b"],      # redact CPFs (Brazilian ID numbers)
)
```

## 3. Add context
You can attach request- or task-level context using log.set_context().
These fields will automatically appear in all logs until you clear them.

```bash
log.set_context(request_id="r-001", user_id=42)
```

## 4. Log events
Log a simple event using log.info(). Any extra fields become structured JSON keys.
```bash
log.info("user_login", email="alice@example.com", password="s3cr3t")

```

## 5. Log exceptions
Use log.exception() to capture structured exception details (exc_type, exc_message, stack).
```bash
try:
    {}["x"]
except KeyError:
    log.exception("lookup_failed", foo=123)

```

## 6. Emit an EMERGENCY alert
The EMERGENCY level is never sampled and can trigger external notifications (Slack, SES, ...).
```bash
log.emergency("payment_outage", region="us-east-1")
```

## 7. Example output
Logs are emitted as one JSON object per line:
```bash
{"ts":"2025-09-02T23:59:59Z","level":"INFO","service":"orders","env":"prod","event":"user_login","request_id":"r-001","user_id":42,"email":"alice@example.com","password":"***REDACTED***"}
{"ts":"2025-09-02T23:59:59Z","level":"ERROR","service":"orders","env":"prod","event":"lookup_failed","request_id":"r-001","user_id":42,"foo":123,"exc_type":"KeyError","exc_message":"'x'","stack":"Traceback (most recent call last): ..."}
{"ts":"2025-09-02T23:59:59Z","level":"EMERGENCY","service":"orders","env":"prod","event":"payment_outage","request_id":"r-001","user_id":42,"region":"us-east-1"}

```

Next steps

Learn how to redact PII: Redaction

Reduce log noise with sampling: Sampling

Trigger Slack or SES notifications: EMERGENCY & Channels