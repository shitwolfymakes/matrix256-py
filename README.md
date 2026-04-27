# matrix256-py

Python reference implementation of [**matrix256v1**](https://github.com/shitwolfymakes/matrix256) — a SHA-256 fingerprint over the (path, size) records of a rooted filesystem tree.

Stdlib only, Python 3.10+. One of several language implementations of the same normative spec; every implementation must produce byte-identical digests on the same input.

## Usage

```python
from matrix256 import v1

digest = v1.fingerprint("/media/user/DISC")
```

The package exposes nothing at the top level. Future algorithm versions will be added as sibling submodules (`matrix256.v2`, …) so callers always address an explicit version.

## See also (in the [spec repo](https://github.com/shitwolfymakes/matrix256))

- `SPEC.md` — normative algorithm
- `RATIONALE.md` — design rationale
- `IMPLEMENTERS.md` — practical guidance (encoding, mount handling, bridge discs)
- `CORPUS.md` — known-good digests across real discs
