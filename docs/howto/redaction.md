# Redaction (masking PII)

`pylogalert` can redact sensitive data **before** it hits your sinks or alert channels.  
There are two complementary mechanisms:

- **By key**: any JSON field whose key is in `redact_keys` is replaced with `***REDACTED***`.
- **By regex**: any **string** matching one of `redact_regexes` patterns is masked in-place.

Redaction is **recursive**: it walks dicts and lists and applies the rules to nested structures.  
Regex-based redaction only applies to **strings**.

---

## Configure redaction

```python
import pylogalert as log

log.configure(
    service="orders",
    env="prod",
    level="INFO",
    # redact by key:
    redact_keys={"password", "token", "secret"},
    # redact by regex (example: Brazilian CPF with punctuation):
    redact_regexes=[r"\b\d{3}\.\d{3}\.\d{3}\-\d{2}\b"],
)
```
## Redaction by key

Any field whose key is listed in redact_keys becomes ***REDACTED***.

### Before
```bash
log.info("user_login", email="alice@example.com", password="s3cr3t", ok=True)
```
### After (JSON)
```bash
{"event":"user_login","email":"alice@example.com","password":"***REDACTED***","ok":true,...}
```

Notes:

- Key comparison is exact (case-sensitive).

- Works at any depth (nested dicts/lists are traversed).

## Redaction by regex (strings)

Any string field is scanned with all patterns in redact_regexes.
Matches are replaced by ***REDACTED*** inside the string.

### Before
```bash
log.info("profile_update", note="cpf=123.456.789-09 ok")
```
### After (JSON)
```bash
{"event":"profile_update","note":"cpf=***REDACTED*** ok",...}
```

Tips:

- Add multiple patterns for different identifiers (e.g., phone, card PAN).

- Prefer anchored tokens (e.g., \b) to avoid over-redaction.

## Nested structures & lists

Redaction recurses into dicts and lists automatically.

```python
payload = {
    "customer": {
        "email": "bob@example.com",
        "password": "p@ss",
        "notes": ["cpf=123.456.789-09", "vip user"],
    },
    "items": [
        {"sku": "A1", "token": "abc"},
        {"sku": "B2", "token": "def"},
    ],
}

log.info("checkout", data=payload)
```

### After (JSON excerpt)

```json
{
  "event": "checkout",
  "data": {
    "customer": {
      "email": "bob@example.com",
      "password": "***REDACTED***",
      "notes": ["cpf=***REDACTED***", "vip user"]
    },
    "items": [
      {"sku": "A1", "token": "***REDACTED***"},
      {"sku": "B2", "token": "***REDACTED***"}
    ]
  }
}

```

## Interaction between key- and regex-based redaction

If a field’s key is in redact_keys, the entire value is replaced by ***REDACTED***, regardless of regex.

If not, but the value is a string, each regex is applied in sequence to that string.

Non-string values (e.g., numbers, booleans) are unaffected by redact_regexes.


## Recommended patterns

Common sensitive tokens (examples — adapt to your locale):

```python
log.configure(
    service="orders",
    env="prod",
    redact_keys={"password", "token", "secret", "ssn", "cpf", "pan"},
    redact_regexes=[
        r"\b\d{3}\.\d{3}\.\d{3}\-\d{2}\b",   # CPF with punctuation
        r"\b\d{11}\b",                       # CPF digits only
        r"\b(?:\d[ -]*?){13,19}\b",          # card-like sequences (broad)
        r"[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}",  # JWT-ish
        r"[A-Za-z0-9\-_]{32,}",              # generic secrets/tokens
    ],
)
```
Keep patterns precise to avoid masking legitimate data. Test them with real-like payloads.

## Performance tips

Prefer key-based redaction for known fields (cheaper than regex).

Keep regex list focused; avoid very heavy patterns.

Compile cost is handled by configure() (patterns are precompiled once).

## Safety notes

Redaction runs inside the formatter and notifier payload building.
That means both the log line and EMERGENCY notification payloads are redacted.

Redaction is best-effort. You are responsible for choosing sensible keys/patterns for your domain and legal requirements (GDPR/LGPD, PCI, HIPAA, …).

## Quick test locally

Use StringIO to inspect the last JSON line:
```python
from io import StringIO
import json
import pylogalert as log

s = StringIO()
log.configure(service="t", env="test", stream=s, redact_keys={"password"}, redact_regexes=[r"\b\d{11}\b"])

log.info("demo", password="s3cr3t", note="cpf=12345678901 ok")

line = s.getvalue().strip().splitlines()[-1]
print(json.loads(line))
# => "password": "***REDACTED***", "note": "cpf=***REDACTED*** ok"

```