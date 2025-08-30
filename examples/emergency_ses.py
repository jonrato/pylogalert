import os
import pylogalert as log
from pylogalert.notify import Notifier
from pylogalert.notify_ses import ses_email

notifier = Notifier(
    channels=[ses_email(
        sender=os.environ["SES_FROM"],
        to=os.environ["SES_TO"].split(","),
        region=os.environ.get("AWS_REGION", "us-east-1"),
    )],
    rate_limit=("6/min", 10),
    dedupe_window=60,
    retries=(3, 2.0),
)

log.configure(service="billing", env="prod", color=False)
log.emergency("charge_failed_invariant", invoice="inv_123", amount=199.0, _notify=notifier)
