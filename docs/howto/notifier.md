# Advanced Notifier (fan‑out, rate‑limit, dedupe, retries)

This guide is aligned 1:1 with the code you shared `(_core.py, notify.py, notify_slack.py, notify_ses.py)`.

- Notifications are triggered only on EMERGENCY level and only when you pass a Notifier via the _notify= argument.

- EMERGENCY is never sampled (always emitted).

- Notifier performs fan‑out to multiple channels with rate‑limit (token bucket), deduplication by hash, and constant backoff retries.

## 1) When to use the Notifier

Outages, security incidents, irrecoverable corruption, on‑call pager triggers.

By design, only `EMERGENCY` level triggers notifications.

## 2) Quick setup (Slack + SES fan‑out)

```python
from pylogalert import (
configure, set_context, emergency,
Notifier, slack_webhook, ses_email,
)


configure(
service="checkout-api",
env="prod",
level="INFO",
tz_utc=True,
redact_keys=["password", "secret"],
sample={"debug": 0.1, "info": 1.0}, # sample keys are lowercase
)


slack = slack_webhook(
webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ",
text_template=lambda p: f"🚨 [{p['service']}/{p['env']}] {p['event']} (level={p['level']})"
)


email = ses_email(
sender="alerts@mycompany.com",
to=["oncall@mycompany.com"],
region="us-east-1",
)


notifier = Notifier(
channels=[slack, email],
rate_limit=("6/min", 3), # (rate, capacity)
dedupe_window=60.0, # seconds
retries=(3, 0.5), # (extra attempts, constant backoff in s)
)


set_context(request_id="r-42", user_id="u-9")


emergency(
"Cart checkout failing across region sa-east-1",
region="sa-east-1", error_rate=0.97,
_notify=notifier,
)
```

### Payload sent

Constructed in `_core.py` and redacted before sending:

```python
{
"ts": "2025-09-13T16:04:55Z",
"level": "EMERGENCY",
"service": "checkout-api",
"env": "prod",
"event": "Cart checkout failing across region sa-east-1",
"request_id": "r-42",
"user_id": "u-9",
"region": "sa-east-1",
"error_rate": 0.97
}
```

## 3) Notifier semantics (from `notify.py`)

- Rate‑limit: `rate_limit=(rate_str, capacity)`

    - `rate_str`: "N/sec", "N/min" or "N/hour" (internally → min interval per token)

    - `capacity` (int): bucket size (allows short bursts)

- Dedup: `dedupe_window` in seconds

    - SHA‑256 hash of the serialized payload (already redacted). If it repeats within the window, it is suppressed

- Retries: `retries=(retries, backoff_seconds)`

    - `retries`: number of extra attempts beyond the first

    - `backoff_seconds`: constant delay between attempts

- Thread safety: gating is protected by a `Lock`; channels are invoked outside the lock

## 4) Available channels
### Slack (Incoming Webhook)
```python
from pylogalert import slack_webhook
slack = slack_webhook(
webhook_url="https://hooks.slack.com/services/...",
text_template=lambda p: f":rotating_light: {p['event']} | svc={p['service']} env={p['env']}"
)
```
- Without `text_template`, the payload JSON is stringified and sent.

### Amazon SES (email)
```python
from pylogalert import ses_email
email = ses_email(
sender="alerts@mycompany.com",
to=["oncall@mycompany.com"],
region="us-east-1",
)
```

- Requires extra: `pip install pylogalert[ses]`.

- Subject: `[LEVEL] EVENT (service/env)`; body: indented JSON payload.

## 5) Best practices

- Only `EMERGENCY` notifies (with `_notify=`). For other levels, adapt the core if needed.

- Keep the `event` stable for an incident, and put volatile details in `extra` → dedupe works better.

- Slack: more permissive rate limits; Email: larger `dedupe_window` and more conservative rate limits.

- Avoid PII in payloads; rely on global redaction.

## 6) Testing (fake channel)

```python
from pylogalert import Notifier, emergency


sent = []


def fake(payload):
    sent.append(payload)


notifier = Notifier(channels=[fake], rate_limit=("100/min", 10), dedupe_window=0.0)


emergency("boom", x=1, _notify=notifier)
emergency("boom", x=2, _notify=notifier)


assert len(sent) == 2
assert sent[0]["level"] == "EMERGENCY"
```