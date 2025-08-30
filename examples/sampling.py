import pylogalert as log

log.configure(service="worker", env="prod", sample={"debug": 0.0, "info": 0.1}, color=True)
for i in range(100):
    log.info("heartbeat", i=i)
