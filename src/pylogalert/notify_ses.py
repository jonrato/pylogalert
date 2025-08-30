from __future__ import annotations
import json
from typing import Iterable, Dict, Any
try:
    import boto3
except ImportError as e:
    raise ImportError("pylogalert[ses] extra is required to use SES channels. Install with: pip install pylogalert[ses]") from e

def ses_email(*, sender: str, to: Iterable[str], region: str):
    """
    Returns the channel (payload) that sends email via Amazon SES (SendEmail).
    """
    ses = boto3.client("ses", region_name=region)
    to = list(to)

    def channel(payload: Dict[str, Any]) -> None:
        subject = f"[{payload.get('level','ALERT')}] {payload.get('event','event')} ({payload.get('service')}/{payload.get('env')})"
        body = json.dumps(payload, indent=2, ensure_ascii=False)

        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": to},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
    return channel
