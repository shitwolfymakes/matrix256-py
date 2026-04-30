"""matrix256v1 — reference implementation of the filesystem-walk fingerprint.

Every regular file under the walk root contributes one (relative-path,
size) record to a SHA-256 hash. The walk and serialization logic here
must stay in lockstep with the normative spec in SPEC.md. If one
changes, the other must too.
"""

# Copyright 2026 wolfy <wolfy@shitwolfymakes.com>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import os
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

VERSION = "1"


@dataclass(frozen=True)
class Entry:
    """A regular file selected for v1 fingerprinting.

    `path` is the absolute path on the host, retained for callers that
    need to inspect or display entries; it is not part of the digest.
    `relative` is the NFC-normalized, forward-slash, root-relative path
    that gets UTF-8-encoded into the hash input. `size` is bytes per
    filesystem metadata.
    """

    path: Path
    relative: str
    size: int


_FFFD = "\ufffd"  # Unicode replacement character; spec §2.2.


def _is_lone_surrogate(c: str) -> bool:
    """True when `c` is a single character in the UTF-16 surrogate block
    (U+D800-U+DFFF). Lone surrogates have no UTF-8 representation, so spec
    §2.2 directs the v1 pipeline to replace each one with U+FFFD before
    encoding."""
    return 0xD800 <= ord(c) <= 0xDFFF


def _utf8_encode(s: str) -> bytes:
    """UTF-8 encode `s` after replacing each lone surrogate with U+FFFD.

    The usual source of lone surrogates in v1 input is Python's
    `surrogateescape` error handler: when the filesystem returns a path
    byte that doesn't decode as UTF-8, Python smuggles the byte into the
    string as a code point in U+DC80-U+DCFF so the path can round-trip
    back to the kernel. Those code points cannot be UTF-8 encoded. The
    replacement covers the full surrogate block (not just the
    surrogateescape range), so the function is total — any lone surrogate
    from any source yields stable hash bytes instead of UnicodeEncodeError.
    """
    cleaned = "".join(_FFFD if _is_lone_surrogate(c) else c for c in s)
    return cleaned.encode("utf-8")


def _scan(root: Path, current: Path) -> Iterator[Entry]:
    """Yield an Entry for every regular file under `current`, recursing into
    subdirectories.

    `root` is the original walk root and stays constant across recursive
    calls so `Entry.relative` is always computed against it, not against
    the subdirectory currently being scanned. `current` advances on each
    recursion.

    Filtering matches spec §2.1: symbolic links (file, directory, dangling)
    are skipped before any further inspection — neither followed nor
    emitted. Devices, sockets, FIFOs, and any other non-file entries are
    likewise skipped. Directories are not emitted; they participate only
    as recursion targets.

    Internal helper for `walk`, which materializes and sorts the result.
    """
    with os.scandir(current) as it:
        for de in it:
            if de.is_symlink():
                continue
            if de.is_dir(follow_symlinks=False):
                yield from _scan(root, Path(de.path))
                continue
            if not de.is_file(follow_symlinks=False):
                continue
            full = Path(de.path)
            relative = unicodedata.normalize(
                "NFC", full.relative_to(root).as_posix()
            )
            yield Entry(
                path=full,
                relative=relative,
                size=de.stat(follow_symlinks=False).st_size,
            )


def walk(root: Path) -> list[Entry]:
    """Collect every regular file under `root`, sorted by UTF-8 path bytes.

    Directories are skipped (their existence is implied by the relative
    paths of contained files), as are symbolic links (not followed, not
    emitted) and other non-file entries (devices, sockets, FIFOs). Raises
    OSError on any metadata failure — matrix256v1 is all-or-nothing per
    spec §3.
    """
    root = Path(root)
    entries = list(_scan(root, root))
    entries.sort(key=lambda e: _utf8_encode(e.relative))
    return entries


def fingerprint(root: Path) -> str:
    """Compute the matrix256v1 digest of the filesystem rooted at `root`.

    Walks the tree, sorts the entries by UTF-8 path bytes (spec §2.4),
    builds the per-entry serialization (`<path-bytes> 0x00 <size-ascii>
    0x0A`, spec §2.5) into a single buffer, then SHA-256s the whole thing
    (spec §2.6). Returns 64 lowercase hex digits. Raises OSError if any
    directory or file metadata can't be read — matrix256v1 is
    all-or-nothing per spec §3.

    Building the buffer fully before hashing mirrors the spec literally.
    Feeding records into SHA-256 incrementally is an implementer's choice
    and produces identical digests, but the explicit form here is easier
    to verify against the spec.
    """
    serialized = bytearray()
    for e in walk(Path(root)):
        serialized += _utf8_encode(e.relative)
        serialized.append(0x00)
        serialized += str(e.size).encode("ascii")
        serialized.append(0x0A)
    return hashlib.sha256(serialized).hexdigest()
