# pylogalert

**Lean JSON logging** for Python with **async-safe contextvars**, **PII redaction**, **sampling**, and **EMERGENCY alerts** (Slack, SES).  
Designed for production services and framework integration (FastAPI, Django).

---

## 🚀 Installation

```bash
pip install pylogalert
# optional extras
pip install pylogalert[ses]   # enable AWS SES email notifications
```

## 🔑 Features

- Structured JSON logs (NDJSON, one log per line).

- Context propagation: async-safe via contextvars.

- PII Redaction: hide sensitive keys or regex patterns.

- Sampling: reduce noise and cost (info: 0.1, debug: 0.01).

- New log level: EMERGENCY (≥ CRITICAL).

- Exception logging: automatic exc_type, exc_message, and stack.

- Notifications: plugable notifier system with:

- Slack Webhook (built-in)

- AWS SES email (optional extra [ses])

- Rate limiting, deduplication, retries

- Framework integration: ready to plug into FastAPI middleware or Django logging config.

- Zero mandatory deps (stdlib only).

## 📖 Usage

### Basic logging
```bash
import pylogalert as log

log.configure(service="checkout-api", env="prod")

log.set_context(request_id="req-123")
log.info("order_created", user_id=42, order_id=777, value=129.9)

try:
    1/0
except:
    log.exception("unexpected_error", user_id=42, order_id=777)

```

Output (colorized if LOG_PRETTY=1 or stream.isatty()):

```bash
{"ts":"2025-08-29T12:00:00Z","level":"INFO","service":"checkout-api","env":"prod","event":"order_created","request_id":"req-123","user_id":42,"order_id":777,"value":129.9}
{"ts":"2025-08-29T12:00:00Z","level":"ERROR","service":"checkout-api","env":"prod","event":"unexpected_error","request_id":"req-123","user_id":42,"order_id":777,"exc_type":"ZeroDivisionError","exc_message":"division by zero","stack":"Traceback ..."}

```

### PII redaction
```bash
log.configure(service="auth", env="prod",
              redact_keys=["password", "token"],
              redact_regexes=[r"\b\d{3}\.\d{3}\.\d{3}\-\d{2}\b"])  # hide CPF

log.info("user_login", email="a@x.com", password="secret123")
````
Output:
```bash
{"event":"user_login","email":"a@x.com","password":"***REDACTED***"}
```

### Emergency alerts (Slack)
```bash
import pylogalert as log
from pylogalert.notify import Notifier
from pylogalert.notify_slack import slack_webhook

slack = slack_webhook("https://hooks.slack.com/services/XXX/YYY/ZZZ")

notifier = Notifier(
    channels=[slack],
    rate_limit=("6/min", 5),
    dedupe_window=60,
    retries=(2, 2.0),
)

log.configure(service="billing", env="prod")
log.emergency("payment_failed", invoice="inv-001", amount=199.0, _notify=notifier)
````

### Emergency alerts (AWS SES)

```bash
import pylogalert as log
from pylogalert.notify import Notifier
from pylogalert.notify_ses import ses_email  # requires: pip install pylogalert[ses]

notifier = Notifier(
    channels=[ses_email(sender="alerts@mydomain.com", to=["ops@mydomain.com"])],
    rate_limit=("1/min", 1),
)

log.configure(service="checkout", env="prod")
log.emergency("critical_invariant_broken", account_id=123, _notify=notifier)
````

## ⚙️ Environment variables
- LOG_LEVEL: default log level (default: INFO)

- APP_ENV: environment tag (default: dev)

- LOG_PRETTY: enable colors (1, true, yes)

## 📦 Project status

- 0.1.0 – first release

- Semantic Versioning (SemVer)

- MIT licensed

## 🛠 Development
```bash
git clone https://github.com/jonrato/pylogalert.git
cd pylogalert
python3 -m venv venv && source venv/bin/activate
pip install -e ".[all]"   # install with extras
pytest -q
```