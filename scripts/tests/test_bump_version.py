"""Tests for scripts/bump_version.py.

Covers the pure `bump()` function directly: default-shaped patch/minor/major
increments and malformed-version error handling. No filesystem VERSION files
are touched by these tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import bump_version  # noqa: E402


def test_bump_patch_default():
    assert bump_version.bump("1.0.0", "patch") == "1.0.1"


def test_bump_minor_resets_patch():
    assert bump_version.bump("1.2.3", "minor") == "1.3.0"


def test_bump_major_resets_minor_and_patch():
    assert bump_version.bump("1.2.3", "major") == "2.0.0"


@pytest.mark.parametrize("malformed", ["1.0", "v1.0.0", "abc", "1.0.0.0", ""])
def test_bump_rejects_malformed_version(malformed):
    with pytest.raises(ValueError):
        bump_version.bump(malformed, "patch")


def test_bump_rejects_invalid_part():
    with pytest.raises(ValueError):
        bump_version.bump("1.0.0", "bogus")
