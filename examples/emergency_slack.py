import os
import pylogalert as log
from pylogalert.notify import Notifier
from pylogalert.notify_slack import slack_webhook

WEBHOOK = os.environ["SLACK_WEBHOOK"]
notifier = Notifier(
    channels=[slack_webhook(WEBHOOK)],
    rate_limit=("6/min", 5),
    dedupe_window=60,
    retries=(2, 2.0),
)

log.configure(service="billing", env="prod", color=True)
log.emergency("charge_failed_invariant", invoice="inv_123", amount=199.0, _notify=notifier)
