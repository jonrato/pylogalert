import pylogalert as log
from pylogalert.notify import Notifier

def fake_channel(payload):
    print("ALERT >>>", payload)

notifier = Notifier(channels=[fake_channel], rate_limit=("1/min", 3), dedupe_window=60)

log.configure(service="ledger", env="prod")
log.set_context(request_id="r-9")

log.emergency("invariant_broken", account_id=1, balance=-50.0, _notify=notifier)
log.emergency("invariant_broken", account_id=1, balance=-250.0, _notify=notifier)
