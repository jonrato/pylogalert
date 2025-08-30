from __future__ import annotations
import json
import logging, os, re, sys, uuid, time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional
from contextvars import ContextVar

# ---------- State/Config ----------
_ctx: ContextVar[Dict[str, Any]] = ContextVar("_ctx", default={})

@dataclass
class Config:
    service: str = "app"
    env: str = os.getenv("APP_ENV", "dev")
    level: str = os.getenv("LOG_LEVEL", "INFO")
    stream: Any = sys.stdout
    redact_keys: set[str] = field(default_factory=set)
    redact_patterns: list[re.Pattern] = field(default_factory=list)
    sample: Dict[str, float] = field(default_factory=dict)
    tz_utc: bool = True
    extra_static: Dict[str, Any] = field(default_factory=dict)
    color: Optional[bool] = None

_config = Config()
_logger = logging.getLogger("pylogalert")
_logger.propagate = False

EMERGENCY_LEVEL_NUM = 60
logging.addLevelName(EMERGENCY_LEVEL_NUM, "EMERGENCY")

# ---------- Helpers ----------
def _iso_ts() -> str:
    t = time.gmtime() if _config.tz_utc else time.localtime()
    return time.strftime("%Y-%m-%dT%H:%M:%S", t) + ("Z" if _config.tz_utc else "")

def set_context(**kv) -> None:
    _ctx.set({**get_context(), **kv})

def get_context() -> Dict[str, Any]:
    return _ctx.get()

def clear_context() -> None:
    _ctx.set({})

def _redact(obj: Any):
    from typing import Mapping
    if isinstance(obj, Mapping):
        out = {}
        for k, v in obj.items():
            out[k] = "***REDACTED***" if k in _config.redact_keys else _redact(v)
        return out
    if isinstance(obj, str) and _config.redact_patterns:
        s = obj
        for pat in _config.redact_patterns:
            s = pat.sub("***REDACTED***", s)
        return s
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj

def _env_bool(name: str) -> Optional[bool]:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return None

def _color_enabled() -> bool:
    if _config.color is not None:
        return _config.color
    env = _env_bool("LOG_PRETTY")
    if env is not None:
        return env
    return bool(getattr(_config.stream, "isatty", lambda: False)())

# ---------- Formatter JSON ----------
class JsonFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[37m",     # gray
        "INFO": "\033[36m",      # cyan
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[35m",  # magenta
        "EMERGENCY": "\033[41m", # red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {
            "ts": _iso_ts(),
            "level": record.levelname,
            "service": _config.service,
            "env": _config.env,
            "event": getattr(record, "event", record.getMessage()),
            **_config.extra_static,
        }
        data.update(get_context())
        extra = getattr(record, "extra_fields", {})
        data.update(extra)
        if record.exc_info:
            data["exc_type"] = str(record.exc_info[0].__name__)
            data["exc_message"] = str(record.exc_info[1])
            data["stack"] = self.formatException(record.exc_info)

        text = json.dumps(_redact(data), ensure_ascii=False)
        if _color_enabled():
            color = self.COLORS.get(record.levelname, "")
            return f"{color}{text}{self.RESET}"
        return text


# ---------- Settings ----------
def configure(
    service: str,
    env: Optional[str] = None,
    level: Optional[str] = None,
    stream: Any = None,
    redact_keys: Iterable[str] = (),
    redact_regexes: Iterable[str] = (),
    sample: Optional[Dict[str, float]] = None,
    tz_utc: bool = True,
    extra_static: Optional[Dict[str, Any]] = None,
    color: Optional[bool] = None,
) -> None:
    _config.service = service
    if env: _config.env = env
    if level: _config.level = level
    if stream: _config.stream = stream

    _config.sample = sample if sample is not None else {}

    _config.tz_utc = tz_utc
    if extra_static: _config.extra_static = extra_static
    if color is not None: _config.color = color

    _config.redact_keys = set(redact_keys)
    _config.redact_patterns = [re.compile(p) for p in redact_regexes]

    _logger.handlers.clear()
    handler = logging.StreamHandler(_config.stream)
    handler.setFormatter(JsonFormatter())
    _logger.addHandler(handler)
    _logger.setLevel(getattr(logging, _config.level.upper(), logging.INFO))
    

def _should_sample(level: str) -> bool:
    # EMERGENCY is never sampled (always emits)
    if level.upper() == "EMERGENCY":
        return True
    p = _config.sample.get(level.lower())
    if p is None:
        return True
    # pseudorandom sampling via UUID
    return int(uuid.uuid4().hex[:8], 16) / 0xFFFFFFFF <= p

def _log(level: str, event: str, **fields):
    if not _should_sample(level):
        return

    # remove notifier from fields to not go to JSON
    notify = fields.pop("_notify", None)
    exc = fields.pop("_exc_info", False)

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "EMERGENCY": EMERGENCY_LEVEL_NUM,
    }

    _logger.log(
        level_map[level.upper()],
        event,
        extra={"event": event, "extra_fields": fields},
        exc_info=exc,
    )

    # notification triggering outside the formatter
    if level.upper() == "EMERGENCY" and notify:
        payload = {
            "ts": _iso_ts(),
            "level": "EMERGENCY",
            "service": _config.service,
            "env": _config.env,
            "event": event,
            **get_context(),
            **fields,
        }
        payload = _redact(payload)
        try:
            notify.send(payload)
        except Exception:
            # don't crash the application if the channel fails
            pass

def debug(event: str, **fields): _log("DEBUG", event, **fields)
def info(event: str, **fields): _log("INFO", event, **fields)
def warn(event: str, **fields): _log("WARNING", event, **fields)
def warning(event: str, **fields): warn(event, **fields)
def error(event: str, **fields): _log("ERROR", event, **fields)
def critical(event: str, **fields): _log("CRITICAL", event, **fields)
def exception(event: str, **fields): _log("ERROR", event, _exc_info=True, **fields)
def emergency(event: str, **fields): _log("EMERGENCY", event, **fields)
