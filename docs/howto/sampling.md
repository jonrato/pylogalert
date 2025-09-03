# Sampling (reducing log noise and cost)

`pylogalert` supports **per-level sampling** to reduce volume and cost while keeping high-value signals.
You configure it via the `sample` map in `log.configure(...)`.

- Keys are **lowercase levels**: `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"`, `"emergency"`.
- Values are **probabilities** in `[0.0, 1.0]`.
- **EMERGENCY is never sampled** (always emitted), regardless of the configured value.

Under the hood, a UUID4-based draw decides if a record is emitted (`<= p`) or suppressed.

---

## Configure per-level sampling

```python
import pylogalert as log

log.configure(
    service="orders",
    env="prod",
    level="INFO",                 # logger threshold
    sample={
        "debug": 0.05,            # keep ~5% of DEBUG
        "info": 0.20,             # keep ~20% of INFO
        "warning": 1.0,           # keep all WARNING
        "error": 1.0,             # keep all ERROR
        # "emergency": any value here is ignored; EMERGENCY is always emitted
    },
)
```

Notes:

- The logger threshold (level="INFO") still applies first.
If the threshold is INFO, DEBUG won’t be considered at all (sampling or not).

- Sampling is statistical, not deterministic. Over many events, proportions converge to the configured probabilities.

## Suppress a level entirely

Set a level probability to 0.0 to drop all events of that level:

```python
log.configure(service="t", env="test", sample={"info": 0.0})
log.info("will_not_emit", x=1)   # suppressed
```
This pattern is useful in tests, noisy dev tools, or to mute irrelevant INFO in hot paths.

## Keep all for specific levels

Set a level to 1.0 to keep all events:

```python
log.configure(service="t", env="test", sample={"warning": 1.0, "error": 1.0})
log.warning("always_kept")
log.error("always_kept_too")
```

## EMERGENCY is never sampled

EMERGENCY is always emitted, regardless of the sample map:

```python
log.configure(service="t", env="test", sample={"emergency": 0.0, "info": 0.0})
log.emergency("must_emit")   # will be emitted (never sampled)
```

If you need to throttle notifications for EMERGENCY (e.g., alert channels), combine it with the Notifier’s rate_limit and dedupe_window. Sampling won’t help here by design.

```python
from pylogalert.notify import Notifier
from pylogalert.notify_slack import slack_webhook

notify = Notifier(
    channels=[slack_webhook("https://hooks.slack.com/services/XXX/YYY/ZZZ")],
    rate_limit=("6/min", 3),       # up to 6 per minute, burst 3
    dedupe_window=30,              # suppress identical payloads for 30s
)

log.emergency("payment_outage", region="us-east-1", _notify=notify)
```

## Choosing probabilities (guidelines)

- DEBUG: 0.01–0.10 in production to retain a sample for diagnostics.

- INFO: 0.05–0.50 depending on traffic and cost constraints.

- WARNING/ERROR: usually 1.0. Consider partial sampling only if extremely chatty.

- CRITICAL/EMERGENCY: always 1.0 (EMERGENCY is enforced by the library).

## Performance considerations

Sampling happens before formatting/serialization whenever possible (it avoids unnecessary JSON building).

It uses a fast UUID4-based check. There is no central RNG state (thread-safe).

If a level is muted (0.0) or below the logger threshold, the overhead is negligible.

## Local quick test

Use StringIO to verify suppression vs. emission:

```python
from io import StringIO
import json
import pylogalert as log

s = StringIO()
log.configure(service="t", env="test", stream=s, sample={"info": 0.0, "error": 1.0})

log.info("suppressed_info", a=1)
log.error("kept_error", b=2)

lines = s.getvalue().strip().splitlines()
assert len(lines) == 1
print(json.loads(lines[0])["event"])   # => "kept_error"
```

## FAQ

Q: Why do I still see some INFO even with sample={"info": 0.1}?
Because sampling is probabilistic; about 10% are kept over time. For total suppression, set 0.0.

Q: Can I sample by field (e.g., per user_id)?
Not natively. A common pattern is to encode variability in the event (e.g., only log if hash(user_id) % 10 == 0) and keep a low per-level sample for safety.

Q: Can I sample EMERGENCY?
No. EMERGENCY is intentionally never sampled; use Notifier’s rate_limit and dedupe_window to control alert floods.