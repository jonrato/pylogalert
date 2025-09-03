# Timezone configuration

By default, `pylogalert` timestamps (`ts`) are emitted in **UTC**, ISO-8601 format, with a `Z` suffix.  
You can switch to local time with `tz_utc=False`.

---

## Default (UTC)

```python
import pylogalert as log

log.configure(service="orders", env="prod")

log.info("utc_example")
````

Output (excerpt):

```bash
{"ts":"2025-09-02T23:59:59Z","level":"INFO","event":"utc_example",...}
```

Notes:

- Always ends with "Z" to indicate UTC.

- Safe for distributed systems, log collectors, and correlation across services.

## Local time

Set tz_utc=False to emit local timestamps instead:

```python
log.configure(service="orders", env="dev", tz_utc=False)
log.info("local_example")
```

Output (example if localtime=America/Sao_Paulo):
```json
{"ts":"2025-09-02T20:59:59","level":"INFO","event":"local_example",...}
```

Differences:

- No Z suffix.

- Uses system localtime (time.localtime() under the hood).

## Comparing UTC vs local

UTC (default):

- ✅ portable across systems

- ✅ unambiguous correlation

- ✅ recommended for production

Local:

- Useful for quick dev/debugging when you want to match logs with your wall clock.

- Risk of confusion during DST changes or across hosts.

## Best practices

- Use UTC in production (the default).

- Only enable localtime (tz_utc=False) in dev/test environments if it helps readability.

- If you run services in multiple regions, stick to UTC — log pipelines and alerting tools expect it.

## Local quick test

```python
from io import StringIO
import json
import pylogalert as log

s = StringIO()
log.configure(service="t", env="test", stream=s, tz_utc=False)

log.info("demo")
line = json.loads(s.getvalue().strip().splitlines()[-1])
print(line["ts"])   # e.g., "2025-09-02T20:59:59"
````
