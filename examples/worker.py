import pylogalert as log, time

log.configure(service="reconciler", env="prod", color=True)
for job in range(3):
    log.set_context(job=job)
    log.info("start")
    time.sleep(0.1)
    log.info("done")
    log.clear_context()
