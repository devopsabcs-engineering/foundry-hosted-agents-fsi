"""Session-2 bilingual navigation and native capability documentation stay paired."""

from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_root_readmes_have_reciprocal_languages_and_native_showcase_entry():
    for filename, peer, runbook in [
        ("README.md", "README.fr.md", "docs/native-showcase.md"),
        ("README.fr.md", "README.md", "docs/fr/native-showcase.md"),
    ]:
        content = (ROOT / filename).read_text(encoding="utf-8")
        assert f"]({peer})" in content
        assert f"]({runbook})" in content


@pytest.mark.parametrize("source", ["docs/native-showcase.md", "docs/fr/native-showcase.md"])
def test_showcase_relative_links_resolve_to_real_repository_files(source):
    path = ROOT / source
    content = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", content):
        if target.startswith(("http://", "https://", "#")):
            continue
        assert (path.parent / target.split("#")[0]).exists(), f"Broken link in {source}: {target}"


def test_both_languages_cover_all_shipped_demo_commands_and_live_boundaries():
    for source in ["docs/native-showcase.md", "docs/fr/native-showcase.md"]:
        text = (ROOT / source).read_text(encoding="utf-8")
        for command in [
            "generation-submit", "generation-status", "generation-download", "memory-create",
            "memory-list", "memory-search", "skill-register", "skill-attach", "skill-consume", "invoice-analyze",
            "cu-preflight", "retrieval-compare", "taxonomy-create", "red-team", "trace-export",
            "trace-dataset", "compare-runs", "--source-revision", "consumed: false", "DefaultsNotSet",
            "file-search-create", "file-search-index", "file-search-query", "grounding-compare",
            "--grounding-evaluator groundedness_pro", "source_citations_verified",
            "trace_verified: false", "HTTP 403", "OUT_OF_CORPUS",
        ]:
            assert command in text, f"{source} omits {command}"
        assert "datagen-6424fd4d37904cebac2a1bbe9459df86" in text
        assert "dc10f004c929303f1485b33eaf97e83688fc59d47f9d3ca047fe1f4bbe204e48" in text
        assert "resp_0fe8c263eaea766a006ad690cce8a08190ba6eb665618a7d3e" in text
        assert "65c5c61f21d1c75f5f82a15b280392d8d20e69cdf57bbac679fec2c2106073df" in text
        assert "vs_035lJB6UtY795UZ6oOXOuDi9" in text
        assert "evalrun_90768c55e09946809a97eac233d7c4bb" in text
        assert "evalrun_8683ff9a323a40de87cbeed5d752def2" in text
