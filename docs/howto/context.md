# Context (request / task fields)

With `pylogalert`, you can attach **context fields** (e.g., `request_id`, `user_id`) that are automatically merged into all subsequent logs in the same execution flow.  
This is implemented using Python’s `ContextVar`, which makes it **async-safe**: each request/task can have its own context without interfering with others.

---

## Basic usage

```python
import pylogalert as log

log.configure(service="orders", env="prod")

# attach context
log.set_context(request_id="abc123", user_id=42)

# all logs now include these fields
log.info("user_login", ip="1.2.3.4")
log.error("db_error", detail="timeout")
````
Output (excerpt):
```bash
{"event":"user_login","request_id":"abc123","user_id":42,"ip":"1.2.3.4",...}
{"event":"db_error","request_id":"abc123","user_id":42,"detail":"timeout",...}
```

## Updating context

You can call set_context() multiple times; new keys overwrite, others persist.
```python
log.set_context(request_id="xyz789")   # overrides only request_id
log.info("order_created", order_id=555)
```
Output:
```bash
{"event":"order_created","request_id":"xyz789","user_id":42,"order_id":555,...}
```

## Clearing context

To reset and remove all context fields, call:

```python
log.clear_context()
log.info("no_context_here")
```
Output:
```bash
{"event":"no_context_here",...}
```

## Retrieving context manually

You can read the current context (dict) with log.get_context().
```python
ctx = log.get_context()
print(ctx)
# {"request_id": "xyz789", "user_id": 42}
```

## Async-safety

Because pylogalert uses ContextVar, context is isolated per task/coroutine.
Each concurrent request can safely set its own fields.

Example with asyncio:

```python
import asyncio
import pylogalert as log

log.configure(service="orders", env="test")

async def handler(name):
    log.set_context(request_id=name)
    log.info("start")
    await asyncio.sleep(0.1)
    log.info("end")

asyncio.run(asyncio.gather(handler("r1"), handler("r2")))
```
Each task keeps its own request_id without collisions.

## Best practices

Always set a stable request ID (trace ID, correlation ID) at the entry point of each request.

Consider adding user_id, tenant_id, or job_id if relevant for observability.

Remember to call clear_context() when reusing worker threads or tasks across requests (e.g., in long-lived workers).

Combine with extra_static (in configure()) for truly global metadata (e.g., region, service_version).

## Quick test

```python
from io import StringIO
import json
import pylogalert as log

s = StringIO()
log.configure(service="t", env="test", stream=s)

log.set_context(req="1")
log.info("first")
log.clear_context()
log.info("second")

lines = s.getvalue().strip().splitlines()
print(json.loads(lines[0])["req"])   # => "1"
print("req" in json.loads(lines[1])) # => False
```