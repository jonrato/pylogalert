from __future__ import annotations
import json
from typing import Callable, Dict, Any, Optional
from urllib import request

def slack_webhook(webhook_url: str, *, text_template: Optional[Callable[[Dict[str, Any]], str]] = None):
    """
    Returns a channel (payload) that publishes to Slack via Incoming Webhook.
    - webhook_url: URL generated in Slack
    - text_template(payload) -> str: Optional; formats a string from the payload
    """
    def channel(payload: Dict[str, Any]) -> None:
        text = text_template(payload) if text_template else f":rotating_light: {payload}"
        body = json.dumps({"text": text}).encode("utf-8")
        req = request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=5) as resp:
            _ = resp.read()
    return channel
