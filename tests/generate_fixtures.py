#!/usr/bin/env python3
"""Tier-1 conformance runner for matrix256v1.

Constructs each synthetic fixture from the matrix256 spec repo's
``CONFORMANCE_FIXTURES.md`` in a fresh temporary directory, runs the
``matrix256.v1.fingerprint`` reference implementation against it, and
verifies the result matches the expected digest published in the spec
repo's ``conformance_fixtures.json`` companion.

Two roles in one script:

1. **Conformance test harness.** With expected digests loaded from the
   spec repo, every fixture is executed and its produced digest compared
   to the canonical value. A divergence is a regression in either this
   implementation or the spec.

2. **Canonical fixture generator.** With ``--generate``, the script
   constructs each fixture and emits the JSON block ready to paste into
   the spec repo's ``conformance_fixtures.json``. Implementers in other
   languages should treat the construction code in this file as the
   canonical reference where the markdown's prose is ambiguous.

Stdlib only, matching the package's no-deps convention.

Usage::

    python tests/generate_fixtures.py
    python tests/generate_fixtures.py --fixture 14
    python tests/generate_fixtures.py --range 1-10
    python tests/generate_fixtures.py --generate

By default the script reads ``conformance_fixtures.json`` from a sibling
checkout of the spec repo at ``../matrix256/`` relative to this repo's
root. Override with ``--fixtures PATH``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_FIXTURES_JSON = REPO_ROOT.parent / "matrix256" / "conformance_fixtures.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from matrix256 import v1  # noqa: E402


class SkipFixture(Exception):
    """Raised by a builder when the current platform can't host the fixture."""


@dataclass(frozen=True)
class Fixture:
    id: int
    name: str
    builder: Callable[[Path], None]
    requirements: tuple[str, ...] = field(default_factory=tuple)


# --- Builders -------------------------------------------------------------
#
# Each builder receives a fresh empty directory and constructs the fixture
# state in it. A SkipFixture exception means the platform can't host the
# fixture as written and the runner should report a skip rather than a fail.


def _b1_empty_dir(d: Path) -> None:
    return


def _b2_zero_byte_file(d: Path) -> None:
    (d / "a").write_bytes(b"")


def _b3_small_ascii_file(d: Path) -> None:
    (d / "hello.txt").write_bytes(b"hello\n")


def _b4_two_files(d: Path) -> None:
    (d / "a").write_bytes(b"")
    (d / "b").write_bytes(b"")


def _b5_case_sensitive_sort(d: Path) -> None:
    (d / "A").write_bytes(b"")
    try:
        (d / "a").write_bytes(b"")
    except OSError as e:
        raise SkipFixture(f"filesystem is case-insensitive ({e})") from e
    names = {p.name for p in d.iterdir()}
    if names != {"A", "a"}:
        raise SkipFixture("filesystem collapsed 'A' and 'a' (case-insensitive)")


def _b6_slash_vs_dash(d: Path) -> None:
    (d / "a-b").write_bytes(b"")
    (d / "a").mkdir()
    (d / "a" / "b").write_bytes(b"")


def _b7_nested_dirs(d: Path) -> None:
    nested = d / "dir1" / "dir2"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_bytes(b"")


def _b8_sibling_full_path_sort(d: Path) -> None:
    (d / "a").mkdir()
    (d / "a" / "z").write_bytes(b"")
    (d / "b").mkdir()
    (d / "b" / "a").write_bytes(b"")


def _b9_only_empty_subdir(d: Path) -> None:
    (d / "empty").mkdir()


def _b10_file_plus_empty_subdir(d: Path) -> None:
    (d / "hello.txt").write_bytes(b"hello\n")
    (d / "empty").mkdir()


def _b11_only_symlink(d: Path) -> None:
    try:
        (d / "link").symlink_to("nonexistent")
    except (OSError, NotImplementedError) as e:
        raise SkipFixture(f"symlinks not supported ({e})") from e


def _b12_symlink_alongside_file(d: Path) -> None:
    (d / "real.txt").write_bytes(b"x")
    try:
        (d / "link").symlink_to("real.txt")
    except (OSError, NotImplementedError) as e:
        raise SkipFixture(f"symlinks not supported ({e})") from e


def _b13_latin_diacritics_nfc(d: Path) -> None:
    name = unicodedata.normalize("NFC", "café.txt")
    (d / name).write_bytes(b"")


def _b14_latin_diacritics_nfd(d: Path) -> None:
    nfd_name = unicodedata.normalize("NFD", "café.txt")
    (d / nfd_name).write_bytes(b"")
    listed = next(d.iterdir()).name
    if listed != nfd_name:
        raise SkipFixture("filesystem auto-normalized the filename at write time")


def _b15_cyrillic(d: Path) -> None:
    (d / "привет.txt").write_bytes(b"")


def _b16_han(d: Path) -> None:
    (d / "你好.txt").write_bytes(b"")


def _b17_arabic(d: Path) -> None:
    (d / "مرحبا.txt").write_bytes(b"")


def _b18_emoji(d: Path) -> None:
    (d / "🎵.txt").write_bytes(b"")


def _b19_multi_script(d: Path) -> None:
    for name in ("ascii.txt", unicodedata.normalize("NFC", "café.txt"), "你好.txt", "🎵.txt"):
        (d / name).write_bytes(b"")


def _b20_size_boundaries(d: Path) -> None:
    sizes = [
        ("size_0000000", 0),
        ("size_0000001", 1),
        ("size_0000255", 255),
        ("size_0000256", 256),
        ("size_0065535", 65535),
        ("size_0065536", 65536),
        ("size_1000000", 1000000),
    ]
    for name, size in sizes:
        (d / name).write_bytes(b"\x00" * size)


def _b21_many_small_files(d: Path) -> None:
    for i in range(100):
        (d / f"f{i:03d}").write_bytes(b"")


def _b22_deeply_nested(d: Path) -> None:
    nested = d
    for letter in "abcdefghij":
        nested = nested / letter
    nested.mkdir(parents=True)
    (nested / "file.txt").write_bytes(b"")


def _b23_long_filename(d: Path) -> None:
    name = "a" * 200
    try:
        (d / name).write_bytes(b"")
    except OSError as e:
        raise SkipFixture(f"filesystem rejected 200-byte component ({e})") from e


def _b24_surrogate_escape(d: Path) -> None:
    if sys.platform != "linux":
        raise SkipFixture(f"non-UTF-8 filenames unsupported on {sys.platform}")
    raw_name = b"bad\xff.txt"
    path_bytes = os.fsencode(d) + b"/" + raw_name
    try:
        fd = os.open(path_bytes, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        os.close(fd)
    except OSError as e:
        raise SkipFixture(f"could not create non-UTF-8 filename ({e})") from e


def _b25_prefix_sort(d: Path) -> None:
    for name in ("foo", "foo.txt", "foobar"):
        (d / name).write_bytes(b"")


def _b26_content_irrelevance(d: Path) -> None:
    (d / "hello.txt").write_bytes(b"world!")


FIXTURES: tuple[Fixture, ...] = (
    Fixture(1, "empty directory", _b1_empty_dir),
    Fixture(2, "single zero-byte file", _b2_zero_byte_file),
    Fixture(3, "single small ASCII file", _b3_small_ascii_file),
    Fixture(4, "two files at root", _b4_two_files),
    Fixture(5, "case-sensitive sort", _b5_case_sensitive_sort, ("case_sensitive_fs",)),
    Fixture(6, "slash vs dash sort edge case", _b6_slash_vs_dash),
    Fixture(7, "nested directories", _b7_nested_dirs),
    Fixture(8, "sibling directories sort by full path", _b8_sibling_full_path_sort),
    Fixture(9, "only an empty subdirectory", _b9_only_empty_subdir),
    Fixture(10, "file plus an empty subdirectory", _b10_file_plus_empty_subdir),
    Fixture(11, "only a symlink", _b11_only_symlink, ("symlinks",)),
    Fixture(12, "symlink alongside a file", _b12_symlink_alongside_file, ("symlinks",)),
    Fixture(13, "Latin diacritics, NFC source", _b13_latin_diacritics_nfc),
    Fixture(
        14, "Latin diacritics, NFD source", _b14_latin_diacritics_nfd, ("byte_preserving_fs",)
    ),
    Fixture(15, "Cyrillic filename", _b15_cyrillic),
    Fixture(16, "Han filename", _b16_han),
    Fixture(17, "Arabic filename", _b17_arabic),
    Fixture(18, "emoji filename", _b18_emoji),
    Fixture(19, "multi-script directory", _b19_multi_script),
    Fixture(20, "size boundaries", _b20_size_boundaries),
    Fixture(21, "many small files", _b21_many_small_files),
    Fixture(22, "deeply nested file", _b22_deeply_nested),
    Fixture(23, "long filename", _b23_long_filename, ("long_component_names",)),
    Fixture(
        24,
        "surrogate-escape filename byte",
        _b24_surrogate_escape,
        ("non_utf8_filenames",),
    ),
    Fixture(25, "prefix and trailing-character sort", _b25_prefix_sort),
    Fixture(26, "content irrelevance (bit-rot tolerance)", _b26_content_irrelevance),
)


# --- Runner ---------------------------------------------------------------


def load_expected(path: Path) -> dict[int, str]:
    """Parse {fixture_id: expected_digest} out of the spec repo's JSON."""
    data = json.loads(path.read_text("utf-8"))
    return {int(f["id"]): f["expected_digest"] for f in data["fixtures"]}


def run_one(fix: Fixture) -> tuple[str, str | None]:
    """Construct fixture in a temp dir, hash, return (status, value).

    status ∈ {"digest", "skip"}. value is either the produced digest (for
    "digest") or the skip reason (for "skip"). Cleanup is unconditional —
    the temp dir is removed even on construction failure.
    """
    with tempfile.TemporaryDirectory(prefix=f"m256_fix{fix.id:02d}_") as tmp:
        d = Path(tmp)
        try:
            fix.builder(d)
        except SkipFixture as e:
            return ("skip", str(e))
        return ("digest", v1.fingerprint(d))


def parse_selection(args: argparse.Namespace) -> list[Fixture]:
    if args.fixture is not None:
        match = [f for f in FIXTURES if f.id == args.fixture]
        if not match:
            raise SystemExit(f"no fixture with id {args.fixture}")
        return match
    if args.range is not None:
        try:
            lo_str, hi_str = args.range.split("-", 1)
            lo, hi = int(lo_str), int(hi_str)
        except ValueError as e:
            raise SystemExit(f"--range must be in the form A-B (got {args.range!r})") from e
        if lo > hi:
            raise SystemExit(f"--range bounds reversed: {lo} > {hi}")
        return [f for f in FIXTURES if lo <= f.id <= hi]
    return list(FIXTURES)


def emit_generate_block(generated: list[dict]) -> str:
    payload = {
        "version": "matrix256v1",
        "fixture_doc": "CONFORMANCE_FIXTURES.md",
        "fixtures": generated,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="matrix256v1 Tier-1 synthetic-fixture conformance runner."
    )
    sel = ap.add_mutually_exclusive_group()
    sel.add_argument("--fixture", type=int, help="run only the fixture with this id")
    sel.add_argument(
        "--range", help="run fixtures in this inclusive id range (e.g. 1-10)"
    )
    ap.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES_JSON,
        help=f"path to conformance_fixtures.json (default: {DEFAULT_FIXTURES_JSON})",
    )
    ap.add_argument(
        "--generate",
        action="store_true",
        help="construct fixtures and emit a JSON block of computed digests instead of "
        "verifying against the spec repo",
    )
    args = ap.parse_args(argv)

    selected = parse_selection(args)

    expected: dict[int, str] | None = None
    if not args.generate:
        if not args.fixtures.exists():
            print(
                f"error: {args.fixtures} not found. Pass --fixtures PATH or clone "
                "the spec repo as a sibling at ../matrix256/.",
                file=sys.stderr,
            )
            return 2
        expected = load_expected(args.fixtures)

    fail = 0
    skip = 0
    passed = 0
    generated: list[dict] = []

    for fix in selected:
        status, value = run_one(fix)
        if status == "skip":
            skip += 1
            print(f"[ skip ] fixture {fix.id:02d} — {fix.name}: {value}")
            continue
        produced = value
        if args.generate:
            generated.append(
                {
                    "id": fix.id,
                    "name": fix.name,
                    "expected_digest": produced,
                    "platform_requirements": list(fix.requirements),
                }
            )
            print(f"[ gen  ] fixture {fix.id:02d} — {fix.name}: {produced}")
            continue
        assert expected is not None
        exp = expected.get(fix.id)
        if exp is None:
            fail += 1
            print(
                f"[ FAIL ] fixture {fix.id:02d} — {fix.name}: no expected digest in "
                f"{args.fixtures}"
            )
            continue
        if produced == exp:
            passed += 1
            print(f"[ pass ] fixture {fix.id:02d} — {fix.name}: {produced}")
        else:
            fail += 1
            print(f"[ FAIL ] fixture {fix.id:02d} — {fix.name}")
            print(f"         produced: {produced}")
            print(f"         expected: {exp}")

    if args.generate:
        print()
        print("--- conformance_fixtures.json (paste into the matrix256 spec repo) ---")
        print(emit_generate_block(generated))
        print(f"\nsummary: {len(generated)} generated, {skip} skipped")
        return 0

    total = passed + fail + skip
    print(f"\nsummary: {passed} pass, {fail} fail, {skip} skip ({total} total)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
