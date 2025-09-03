# Colorized output (TTY / dev mode)

`pylogalert` can optionally colorize log lines for **human-friendly development**.  
Color is applied at the **formatter** stage if a TTY is detected, or you can force it with `color=True` or via the env var `LOG_PRETTY=1`.

---

## Automatic detection

If `color` is not set explicitly:
- If the log `stream` has `.isatty()` returning `True` (e.g., your terminal), color is enabled.
- Otherwise (e.g., redirected to a file, container logs), plain JSON is used.

---

## Forcing color on / off

You can override detection with either:

### Explicit flag
```python
import pylogalert as log

log.configure(service="orders", env="dev", color=True)   # force colors
log.info("user_login", user_id=1)
```

### Environment variable
```bash
export LOG_PRETTY=1   # force enable
export LOG_PRETTY=0   # force disable
```

### Example output

```json
# Without color (plain JSON):
{"ts":"2025-09-02T23:59:59Z","level":"INFO","service":"orders","env":"dev","event":"user_login","user_id":1}

# With color in TTY (simplified illustration):
\033[36m{"ts":"...","level":"INFO","event":"user_login","user_id":1}\033[0m
```

### Colors by level:

- DEBUG: gray

- INFO: cyan

- WARNING: yellow

- ERROR: red

- CRITICAL: magenta

- EMERGENCY: red background

## When to use

- Enable color in development for easier scanning.

- Disable in production log pipelines (default) — most log collectors expect plain JSON.

## Local quick test
```python
from io import StringIO
import pylogalert as log

s = StringIO()
log.configure(service="t", env="test", stream=s, color=True)
log.warning("colored_warning")

out = s.getvalue()
print(out)   # includes ANSI codes for yellow
```

## Best practices

- Keep color disabled in production to avoid polluting JSON log pipelines.

- Use LOG_PRETTY=1 locally to toggle without touching code.

- Remember: color is a display aid only — the underlying JSON structure is unchanged.