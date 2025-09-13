# Contributing

Contributions are welcome! Follow the steps below to get a local dev setup and submit improvements.

## Development setup
```bash
# clone your fork
git clone https://github.com/<your-username>/pylogalert.git
cd pylogalert


# install in editable mode with dev extras
pip install -e .[dev]
```
Dev extras typically include linters (ruff), type checking (mypy), and pytest.

## Running tests

```bash
pytest -q
```
Covered areas:

- JSON logging basics

- Exception logging with stack trace

- Redaction (keys + regex)

- Sampling suppression

- EMERGENCY always emitted

- Context isolation

- Notifier dedupe / rate‑limit / retries

## Code style

- Lint: ruff

- Types: mypy

Run checks:
```bash
ruff check .
mypy .
```

## Pull requests

1. Fork the repo & create a branch.

2. Keep commits focused (one feature/fix per PR).

3. Add/update tests where relevant.

4. Ensure `pytest`, `ruff`, and `mypy` pass.

5. Submit PR with a clear description.

## Philosophy for contributors

- API surface should stay small and clear.
- Features must preserve safety guarantees (no crash on notifier failure, EMERGENCY never dropped).
- Documentation/examples matter as much as code.

Thanks for contributing 💜