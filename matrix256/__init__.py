"""matrix256 — reproducible fingerprints for optical discs and filesystem trees.

The active algorithm version lives in ``matrix256.v1``: a SHA-256 over a
canonical serialization of the (path, size) records of every regular file
under the walk root. See ``SPEC.md`` for the normative specification.

Importing code addresses the algorithm explicitly:

    from matrix256 import v1
    digest = v1.fingerprint(mountpoint)

The package exposes nothing at the top level so future versions can be
added as sibling submodules (``matrix256.v2``, …) without a "current"
default that would silently change behavior.
"""

# Copyright 2026 wolfy <wolfy@shitwolfymakes.com>
# SPDX-License-Identifier: Apache-2.0
