import pylogalert as log

log.configure(service="checkout-api", env="dev")
log.set_context(request_id="req-123", user_id=42)

log.info("order_created", order_id=777, value=129.90)

try:
    1/0
except:
    log.exception("unexpected_error", order_id=777)
