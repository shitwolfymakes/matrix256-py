# matrix256-py

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/matrix256.svg)](https://pypi.org/project/matrix256/)
[![Python versions](https://img.shields.io/pypi/pyversions/matrix256.svg)](https://pypi.org/project/matrix256/)
[![Downloads](https://img.shields.io/pypi/dm/matrix256.svg)](https://pypi.org/project/matrix256/)
[![Conformance](https://github.com/shitwolfymakes/matrix256-py/actions/workflows/conformance.yml/badge.svg)](https://github.com/shitwolfymakes/matrix256-py/actions/workflows/conformance.yml)
[![Lint](https://github.com/shitwolfymakes/matrix256-py/actions/workflows/lint.yml/badge.svg)](https://github.com/shitwolfymakes/matrix256-py/actions/workflows/lint.yml)

Python reference implementation of [**matrix256v1**](https://github.com/shitwolfymakes/matrix256) — a SHA-256 fingerprint over the (path, size) records of a rooted filesystem tree.

Zero runtime dependencies — stdlib only, Python 3.10+. One of several language implementations of the same normative spec; every implementation must produce byte-identical digests on the same input.

The project's only dev dependency is `ruff` (declared under `[dependency-groups.dev]` in [`pyproject.toml`](pyproject.toml)) — used to enforce the [library discipline](#library-discipline) below. Dev deps are not installed when consumers `pip install matrix256` or `uv add matrix256`; they only land in a contributor's environment via `uv sync --group dev`.

## Library discipline

The library promise is: **a consumer's process must never break because of code in this package.** The rules below are enforced by `ruff` (CI runs `uv run ruff check .` on every push); a few rows are intent rules that still require code review.

| Category | What's guarded | Enforced by |
|---|---|---|
| Exception discipline | No `assert` in library code (stripped under `python -O`), no bare `except:`, no `sys.exit`. Failures raise specific, typed exceptions — `OSError` from filesystem calls is propagated unchanged per spec §3. | `S101`, `E722`, `BLE001`, `TID251` (banned-api on `sys.exit`) |
| Output discipline | No `print(...)`, no `logging` configuration, no writes to `sys.stdout` / `sys.stderr` from library code. A fingerprint call has no business producing output. | `T201`, `T203` (in `T20`); `logging`/direct `sys.stdout` writes are intent rules |
| Total functions | Where reasonable, public functions are made total by construction. `_utf8_encode` substitutes U+FFFD for any lone surrogate so no caller can hand it a string that triggers `UnicodeEncodeError`. | code review |
| Side effects at import | No top-level work beyond imports and the `VERSION` constant. Importing the package never touches the filesystem, the network, or `os.environ`. | code review |
| Documentation | Every public class and function carries a `"""..."""` docstring. Public API stays self-describing. | `D100`–`D104` |

Tests under [`tests/`](tests/) are exempt via `[tool.ruff.lint.per-file-ignores]` — they use `assert`, `print`, and `sys.exit` freely, as Python's testing idiom expects.

```
uv sync --group dev    # install ruff into a contributor venv
uv run ruff check .    # run the discipline checks
```

## Usage

```python
from matrix256 import v1

digest = v1.fingerprint("/media/user/DISC")
```

The package exposes nothing at the top level. Future algorithm versions will be added as sibling submodules (`matrix256.v2`, …) so callers always address an explicit version.

## Conformance

This implementation's Tier-1 conformance test is the synthetic fixture suite at [`tests/generate_fixtures.py`](tests/generate_fixtures.py). The script constructs each fixture in a temporary directory, runs `matrix256.v1.fingerprint` against it, and verifies the produced digest against the canonical value published in the spec repo's [`conformance_fixtures.json`](https://github.com/shitwolfymakes/matrix256/blob/main/conformance_fixtures.json) (human-readable companion: [`CONFORMANCE_FIXTURES.md`](https://github.com/shitwolfymakes/matrix256/blob/main/CONFORMANCE_FIXTURES.md)). The suite has no external data dependency and runs on every commit in CI.

```
python tests/generate_fixtures.py                      # run all fixtures
python tests/generate_fixtures.py --fixture 14         # one fixture
python tests/generate_fixtures.py --range 1-10         # a range
python tests/generate_fixtures.py --generate           # emit JSON for the spec repo
```

By default the runner expects the spec repo to be cloned alongside this one as `../matrix256/`. Override with `--fixtures PATH`. Platform-incompatible fixtures (e.g. case-sensitive sort on a case-insensitive filesystem, surrogate-escape paths off Linux) are reported as skips rather than failures.

The script doubles as the canonical fixture generator: implementers in other languages should mirror its construction logic in their own runner so all language implementations agree on the on-disk state under test.

## See also (in the [spec repo](https://github.com/shitwolfymakes/matrix256))

- `SPEC.md` — normative algorithm
- `RATIONALE.md` — design rationale
- `IMPLEMENTERS.md` — practical guidance (encoding, mount handling, bridge discs)
- `CORPUS.md` — known-good digests across real discs
- `CONFORMANCE_FIXTURES.md` / `conformance_fixtures.json` — Tier-1 synthetic fixture suite

## License

Licensed under the [Apache License, Version 2.0](LICENSE). Apache 2.0 grants an explicit patent license to users and includes a patent-retaliation clause that terminates those rights for anyone who sues a contributor over the licensed work.
