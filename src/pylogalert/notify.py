from __future__ import annotations
import hashlib
import json
import threading
import time
from typing import Callable, Dict, Any, Iterable, Optional

Channel = Callable[[Dict[str, Any]], None]

def _parse_rate(rate: str) -> float:
    """
    Converte '1/sec', '6/min', '120/hour' em intervalo mínimo (segundos) entre envios.
    Ex.: '1/sec' -> 1.0s; '6/min' -> 10s; '120/hour' -> 30s.
    """
    num, per = rate.split("/")
    n = float(num)
    per = per.strip().lower()
    if per in ("s", "sec", "second", "seconds"):
        base = 1.0
    elif per in ("m", "min", "minute", "minutes"):
        base = 60.0
    elif per in ("h", "hour", "hours"):
        base = 3600.0
    else:
        raise ValueError(f"Unrecognized rate unit: {per}")
    if n <= 0:
        raise ValueError("Rate must be > 0")
    return base / n

def _stable_hash(payload: Dict[str, Any]) -> str:
    # deterministic hash of the redacted/serialized payload
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

class Notifier:
    """
    Sends payloads to one or more channels (callables).
    Features:
    - rate_limit: ('6/min', capacity) → minimum interval + simple bucket
    - dedupe_window: N seconds (does not send if hash equals recently viewed)
    - retries: (retries, backoff_seconds)
    """
    def __init__(
        self,
        *,
        channels: Iterable[Channel],
        rate_limit: Optional[tuple[str, int]] = None,
        dedupe_window: Optional[float] = None,
        retries: tuple[int, float] = (0, 1.0),
    ) -> None:
        self._channels = list(channels)
        self._lock = threading.Lock()

        self._min_interval = None
        self._capacity = 1
        self._tokens = 1.0
        self._last_refill = time.time()
        if rate_limit:
            rate, capacity = rate_limit
            self._min_interval = _parse_rate(rate)
            self._capacity = max(1, int(capacity))
            self._tokens = float(self._capacity)

        self._dedupe_window = float(dedupe_window) if dedupe_window else 0.0
        self._last_hash: Optional[str] = None
        self._last_hash_ts: float = 0.0

        self._retries = int(retries[0])
        self._backoff = float(retries[1])

    # ---- internals ---------------------------------------------------------
    def _refill(self) -> None:
        if self._min_interval is None:
            return
        now = time.time()
        delta = now - self._last_refill
        if delta <= 0:
            return
        add = delta / self._min_interval
        self._tokens = min(self._capacity, self._tokens + add)
        self._last_refill = now

    def _consume(self) -> bool:
        if self._min_interval is None:
            return True
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def _is_dupe(self, payload: Dict[str, Any]) -> bool:
        if self._dedupe_window <= 0:
            return False
        h = _stable_hash(payload)
        now = time.time()
        if self._last_hash == h and (now - self._last_hash_ts) < self._dedupe_window:
            return True
        self._last_hash, self._last_hash_ts = h, now
        return False

    # ---- public API --------------------------------------------------------
    def send(self, payload: Dict[str, Any]) -> None:
        """
        Sends to all channels, respecting rate limits, dedupe, and retries.
        """
        with self._lock:
            if self._is_dupe(payload):
                return
            if not self._consume():
                return

        # outside the lock to not block other sends while calling the channel
        attempts = self._retries + 1
        for i in range(attempts):
            try:
                for ch in self._channels:
                    ch(payload)
                return
            except Exception:
                if i == attempts - 1:
                    return
                time.sleep(self._backoff)
