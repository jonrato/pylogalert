import pylogalert as log

log.configure(
    service="auth",
    env="prod",
    redact_keys=["email", "token"],
    redact_regexes=[r"\b\d{3}\.\d{3}\.\d{3}\-\d{2}\b"],  # CPF
    color=True,
)

log.info("login", email="ana@example.com", token="XYZ", ok=True)
log.info("profile_update", note="cpf=123.456.789-09 atualizado")
