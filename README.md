# matrix256-py

Python reference implementation of [**matrix256v1**](https://github.com/shitwolfymakes/matrix256) — a SHA-256 fingerprint over the (path, size) records of a rooted filesystem tree.

Stdlib only, Python 3.10+. One of several language implementations of the same normative spec; every implementation must produce byte-identical digests on the same input.

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
