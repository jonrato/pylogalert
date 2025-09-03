# EMERGENCY & Channels (Slack, SES)

The **EMERGENCY** level is designed for **high-severity incidents**.  
It is **never sampled** (always emitted), and can **optionally** trigger external channels (Slack, SES, …) via the `_notify` field.

- Logs still go to the configured stream as JSON.
- When `_notify` is provided, a **redacted** payload is also sent to the channel(s).
- Channel failures **never crash** your app; errors are swallowed on purpose.

---

## Basic EMERGENCY (no channel)

```python
import pylogalert as log

log.configure(service="orders", env="prod")
log.emergency("payment_outage", region="us-east-1")
```
This emits a JSON line with level=EMERGENCY. No external notification is sent.

## Slack (Incoming Webhook)

Use slack_webhook(url) to create a channel callable.
```python
import pylogalert as log
from pylogalert.notify_slack import slack_webhook

log.configure(service="orders", env="prod")

notify = slack_webhook("https://hooks.slack.com/services/XXX/YYY/ZZZ")

log.emergency(
    "payment_outage",
    region="us-east-1",
    shard="A",
    _notify=notify,               # channel callable
)
```
Custom message text

You can format a custom Slack text using text_template(payload) -> str.
```python
notify = slack_webhook(
    "https://hooks.slack.com/services/XXX/YYY/ZZZ",
    text_template=lambda p: (
        f":rotating_light: {p['event']} on {p['service']}/{p['env']} "
        f"(ts={p['ts']}, region={p.get('region','?')})"
    ),
)
```

## Amazon SES (email)

Requires the optional extra: pip install pylogalert[ses]

```python
import pylogalert as log
from pylogalert.notify_ses import ses_email

log.configure(service="orders", env="prod")

notify = ses_email(
    sender="alerts@company.com",
    to=["oncall@company.com", "eng@company.com"],
    region="us-east-1",
)

log.emergency(
    "db_unreachable",
    endpoint="orders-db.cluster-xyz",
    _notify=notify,
)
```

SES will send an email with a subject like:

```bash
[EMERGENCY] db_unreachable (orders/prod)
```
and a pretty-printed JSON body of the (redacted) payload.

## Combining channels with Notifier (rate limit, dedupe, retries)

For production-grade alerting, wrap one or more channels with Notifier.
This gives you token-bucket rate limiting, deduplication, and retries.

```python
import pylogalert as log
from pylogalert.notify import Notifier
from pylogalert.notify_slack import slack_webhook
from pylogalert.notify_ses import ses_email

log.configure(service="orders", env="prod")

slack = slack_webhook("https://hooks.slack.com/services/XXX/YYY/ZZZ")
ses = ses_email(sender="alerts@company.com", to=["oncall@company.com"], region="us-east-1")

notify = Notifier(
    channels=[slack, ses],
    rate_limit=("6/min", 3),   # up to 6 sends per minute, burst capacity 3
    dedupe_window=30,          # suppress identical payloads for 30 seconds
    retries=(2, 2.0),          # 2 retries with 2s backoff (per send attempt)
)

log.emergency("payment_outage", region="us-east-1", _notify=notify)
```

How it works:

- rate_limit=("6/min", 3) → token bucket; refills at 6 per minute, holds up to 3 tokens for bursts.

- dedupe_window=30 → if the redacted payload hashes equal within 30s, skip duplicates.

- retries=(2, 2.0) → if a channel raises, try again up to 2 times with 2s intervals.

- Channel calls happen outside the internal lock to avoid blocking other threads.

## Redaction & safety

- The notification payload is redacted using the same rules as log lines
(keys in redact_keys, strings matching redact_regexes).

- Channel exceptions are caught — alerts should never take down your service.

- Keep your webhook URLs and credentials in env vars or a secret manager.

## Recommended patterns

- Use Slack for fast on-call visibility and SES for audit/email trails.

- Always wrap channels with a Notifier in production to prevent floods.

- If you need per-tenant or per-feature throttling, include a stable discriminator in the payload (e.g., tenant_id, feature) so dedupe/rate-limit work as intended.

## Local smoke test (no network)

You can stub a channel to validate _notify flow:
```python
import pylogalert as log
from pylogalert.notify import Notifier

sent = []
def fake_channel(payload):
    sent.append(payload)

notify = Notifier(channels=[fake_channel], rate_limit=("1/sec", 1), dedupe_window=2)

log.configure(service="t", env="test")
log.emergency("inv_broken", account_id=1, _notify=notify)
log.emergency("inv_broken", account_id=1, _notify=notify)  # deduped
```
sent will contain exactly one redacted payload for the first call.