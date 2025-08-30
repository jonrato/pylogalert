import json
import time
from io import StringIO
import logging
import pylogalert as log
from pylogalert import _core as core


class ListHandler(logging.Handler):
    """In-memory handler to capture formatted messages."""

    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))


def _get_last_json(stream: StringIO):
    val = stream.getvalue().strip()
    assert val, "stream is empty"
    line = val.splitlines()[-1]
    return json.loads(line)


# -------------------------
# Basic logging
# -------------------------
def test_basic_log():
    s = StringIO()
    log.configure(service="t", env="test", stream=s)
    log.set_context(request_id="r1")
    log.info("evt", a=1)

    data = _get_last_json(s)
    assert data["event"] == "evt"
    assert data["a"] == 1
    assert data["request_id"] == "r1"


def test_exception():
    s = StringIO()
    log.configure(service="t", env="test", stream=s)
    log.set_context(request_id="r1")
    try:
        1 / 0
    except Exception:   # more explicit than bare except
        log.exception("boom", x=2)

    data = _get_last_json(s)
    assert data["event"] == "boom"
    assert data["exc_type"] == "ZeroDivisionError"


# -------------------------
# Redaction (by key)
# -------------------------
def test_redaction_by_key():
    s = StringIO()
    log.configure(service="t", env="test", stream=s, redact_keys=["email", "token"])
    log.info("user_login", email="a@x.com", token="abc", ok=True)

    data = _get_last_json(s)
    assert data["event"] == "user_login"
    assert data["ok"] is True
    assert data["email"] == "***REDACTED***"
    assert data["token"] == "***REDACTED***"


# -------------------------
# Redaction (by regex)
# -------------------------
def test_redaction_by_regex():
    s = StringIO()
    log.configure(
        service="t", env="test", stream=s, redact_regexes=[r"\b\d{3}\.\d{3}\.\d{3}\-\d{2}\b"]
    )
    log.info("user_update", note="cpf=123.456.789-09 ok")

    data = _get_last_json(s)
    assert data["event"] == "user_update"
    assert "***REDACTED***" in data["note"]


# -------------------------
# Sampling: suppress INFO (0.0)
# -------------------------
def test_sampling_suppresses_info():
    s = StringIO()
    log.configure(service="t", env="test", stream=s, sample={"info": 0.0})
    log.info("will_not_emit", x=1)
    assert s.getvalue().strip() == ""  # nothing emitted


# -------------------------
# Emergency ignores sampling
# -------------------------
def test_emergency_ignores_sampling():
    s = StringIO()
    log.configure(service="t", env="test", stream=s, sample={"info": 0.0, "emergency": 0.0})
    log.emergency("must_emit", invariant="balance>=0")

    data = _get_last_json(s)
    assert data["event"] == "must_emit"
    assert data["level"] == "EMERGENCY"


# -------------------------
# Context isolation
# -------------------------
def test_context_isolation():
    log.configure(service="t", env="test")

    logger = logging.getLogger("pylogalert")
    logger.handlers.clear()
    lh = ListHandler()
    lh.setFormatter(core.JsonFormatter())
    logger.addHandler(lh)
    logger.setLevel(logging.INFO)

    log.set_context(request_id="r1")
    log.info("first")
    log.clear_context()
    log.info("second")

    assert len(lh.messages) == 2, lh.messages

    first = json.loads(lh.messages[0])
    second = json.loads(lh.messages[1])

    assert first["event"] == "first" and first["request_id"] == "r1"
    assert second["event"] == "second" and "request_id" not in second


# -------------------------
# Exception: includes stack trace
# -------------------------
def test_exception_has_stack():
    s = StringIO()
    log.configure(service="t", env="test", stream=s)
    try:
        {}["x"]  # KeyError
    except Exception:   # more explicit than bare except
        log.exception("explode", foo=123)

    data = _get_last_json(s)
    assert data["event"] == "explode"
    assert data["exc_type"] == "KeyError"
    assert "stack" in data and "KeyError" in data["stack"]


# -------------------------
# Notifier: dedupe + rate limit (no network)
# -------------------------
def test_notifier_dedupe_and_rate_limit():
    sent = []

    def fake_channel(payload):
        sent.append(payload)

    from pylogalert.notify import Notifier

    notifier = Notifier(
        channels=[fake_channel], rate_limit=("1/sec", 1), dedupe_window=2, retries=(0, 1.0)
    )

    s = StringIO()
    log.configure(service="t", env="test", stream=s)

    log.emergency("inv_broken", account_id=1, _notify=notifier)
    log.emergency("inv_broken", account_id=1, _notify=notifier)

    time.sleep(1.1)
    log.emergency("inv_broken", account_id=2, _notify=notifier)

    assert len(sent) == 2
    assert sent[0]["event"] == "inv_broken" and sent[0]["account_id"] == 1
    assert sent[1]["event"] == "inv_broken" and sent[1]["account_id"] == 2
