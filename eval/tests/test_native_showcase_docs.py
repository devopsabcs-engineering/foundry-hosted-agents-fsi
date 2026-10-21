"""Session-2 bilingual navigation and native capability documentation stay paired."""

from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[2]
NATIVE_LABS = {
    "lab-15-native-files-generation.md": (
        "fixture-export", "file-upload", "generation-submit", "generation-status",
        "generation-download", "--operation-id", "--samples 15", "--download-file",
    ),
    "lab-16-native-search-invoice.md": (
        "validate-corpus", "file-search-create", "file-search-query", "file-search-index",
        "cu-preflight", "invoice-analyze", "--store-evidence", "--language",
    ),
    "lab-17-native-skills-memory.md": (
        "skill-register", "skill-attach", "skill-consume", "memory-create",
        "memory-seed", "memory-list", "memory-search",
    ),
    "lab-18-native-evaluation-traces.md": (
        "catalog", "retrieval-compare", "compare-runs", "grounding-compare",
        "--grounding-evaluator groundedness_pro", "trace-export", "trace-dataset",
        "--source-revision", "--operation-id", "run_judge_evaluation.py",
    ),
}


def powershell_blocks(text):
    return re.findall(r"```powershell\n(.*?)```", text, flags=re.DOTALL)


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


def test_iq_and_cu_extension_contracts_and_safety_boundaries_are_bilingual():
    for source in ["docs/native-showcase.md", "docs/fr/native-showcase.md"]:
        text = (ROOT / source).read_text(encoding="utf-8")
        for token in (
            "native_foundry_iq.py", "--binding", "--project-resource-id",
            "ProjectManagedIdentity", "queryPrincipalType=ServicePrincipal",
            "2025-10-01-preview", "2026-08-01-preview", "knowledge_base_retrieve",
            "fsi-showcase-cu-completion", "fsi-showcase-cu-embedding",
            "--model-deployments", "SYN-REPAIR-001", "OUT_OF_CORPUS",
            "content-understanding.bicep", "SQLite", "Cosmos",
            "prepare_redteam_shadow.py", "--allow-new-code-deployment",
            "--source-definition-sha256", "--source-content-sha256",
            "--source-deployment-provenance", "--staging-endpoint", "shadow-preflight",
            "CASE_STORE_DB_PATH=:memory:", "FOUNDRY_PROJECT_ENDPOINT",
            "scan_completed", "report_complete", "no_violations",
            "redteam_protocol_entrypoint.py", "redteam_protocol_package.py",
            "--protocol-revision", "--protocol-entrypoint-sha256", "--protocol-content-sha256",
            "fsi-showcase-redteam-protocol-quote-001", "immutable_artifact_equality",
            "bd25b1e5c627802521ff178fa5bfea20e42d3a3d1063b1fe9357ed48c76a83ee",
        ):
            assert token in text, f"{source} omits extension contract {token}"
        assert "```mermaid" in text
        assert "red-team --endpoint $endpoint --agent quote-preparation-agent" not in text


def test_all_lab_filenames_are_paired_and_both_indexes_link_twenty_labs():
    en = ROOT / "docs/labs"
    fr = ROOT / "docs/fr/labs"
    assert {path.name for path in en.glob("*.md")} == {
        path.name for path in fr.glob("*.md")
    }
    for folder in (en, fr):
        labs = {path.name for path in folder.glob("lab-*.md")}
        assert len(labs) == 20
        assert set(NATIVE_LABS) <= labs
        index = (folder / "index.md").read_text(encoding="utf-8")
        links = set(re.findall(r"\]\((lab-[^)]+\.md)\)", index))
        assert links == labs
    assert "twenty-lab" in (en / "index.md").read_text(encoding="utf-8")
    assert "vingt ateliers" in (fr / "index.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("filename,commands", NATIVE_LABS.items())
def test_native_labs_have_identical_executable_blocks_and_command_coverage(filename, commands):
    en = (ROOT / "docs/labs" / filename).read_text(encoding="utf-8")
    fr = (ROOT / "docs/fr/labs" / filename).read_text(encoding="utf-8")
    en_blocks = powershell_blocks(en)
    assert len(en_blocks) >= 3
    assert en_blocks == powershell_blocks(fr), f"Command drift in {filename}"
    script = "\n".join(en_blocks)
    for command in commands:
        assert command in script, f"{filename} omits executable command/flag {command}"
    assert "Join-Path '.local'" in script
    assert "$env:TEMP" not in script
    assert "& .venv\\Scripts\\python.exe" in script


@pytest.mark.parametrize("folder", ["docs/labs", "docs/fr/labs"])
@pytest.mark.parametrize("filename", NATIVE_LABS)
def test_native_labs_have_metadata_reciprocal_links_and_real_relative_targets(folder, filename):
    path = ROOT / folder / filename
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    metadata = text.split("---", 2)[1]
    assert "title:" in metadata
    assert "description:" in metadata
    assert "permalink:" in metadata
    if folder == "docs/fr/labs":
        assert "lang: fr" in metadata
        peer = f"../../labs/{filename}"
    else:
        peer = f"../fr/labs/{filename}"
    assert f"]({peer})" in text
    for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text):
        if target.startswith(("https://", "http://", "#")):
            continue
        assert (path.parent / target.split("#")[0]).is_file(), (
            f"Broken link in {folder}/{filename}: {target}"
        )


@pytest.mark.parametrize("folder", ["docs/labs", "docs/fr/labs"])
def test_native_labs_preserve_failed_controls_and_prerequisite_boundaries(folder):
    texts = {
        filename: (ROOT / folder / filename).read_text(encoding="utf-8")
        for filename in NATIVE_LABS
    }
    generation, search, memory, evaluation = texts.values()
    for token in (
        "user_data", "supervised_finetuning", "$failureExit", "historical-failure.stderr.txt",
        "datagen-a866fd3be0104ae4b6ec4808b76cbec2", "datagen-afe38ec64fb744a09e845119139e4064",
        "datagen-4e74a27bd5f24a87a08ea35ad788c8cb", "datagen-af8399a33bd7477b8279591b5a408c7a",
        "26", "generation-reference.txt", "showcase-evidence.md",
    ):
        assert token in generation
    for token in (
        "source_citations_verified", "store_membership_verified", "OUT_OF_CORPUS",
        "DefaultsNotSet", "prebuilt-invoice", "2024-11-30", "Foundry IQ",
    ):
        assert token in search
    for token in (
        "consumed: false", "consumed: true", "approved: false", "positive",
        "negative", "scope_negative_check", "Cosmos DB", "embedding",
    ):
        assert token in memory
    for token in (
        "builtin.groundedness", "builtin.groundedness_pro", "5/5", "`true`",
        "$groundingExit", "$groundingProExit", "$selfExit",
        "HTTP 403", "trace_verified: false", "force_flush()", "traceparent",
        "AGENT_TASK_INSTRUCTIONS", "trace-file", "source-revision",
    ):
        assert token in evaluation
    assert evaluation.index("trace-export --workspace-id") < evaluation.index(
        "trace-dataset --trace-file"
    ) < evaluation.index("run_judge_evaluation.py --endpoint")


@pytest.mark.parametrize("folder", ["docs/labs", "docs/fr/labs"])
def test_memory_lab_reuses_existing_store_and_checks_both_scopes(folder):
    text = (ROOT / folder / "lab-17-native-skills-memory.md").read_text(encoding="utf-8")
    script = "\n".join(powershell_blocks(text))
    assert "memory-create --help" in script
    assert "memory-create --store" not in script
    assert "--ttl-seconds 3600" in text
    for scope in ("fixture-alice", "fixture-bob"):
        assert f"memory-search --store $store --scope {scope}" in script
    for token in ("HTTP 409", "HTTP 403", "3600", "showcase-memory-embedding"):
        assert token in text


@pytest.mark.parametrize("source", ["docs/showcase-evidence.md", "docs/fr/showcase-evidence.md"])
def test_current_evidence_keeps_approved_runtime_and_native_run_provenance(source):
    text = (ROOT / source).read_text(encoding="utf-8")
    for token in (
        "39424857559", "01af1fbdb3c43e91510d0f902e0716a4c70f7789",
        "quote-preparation-agent:5", "version `6`", "476", "36", "13/13",
        "evalrun_80031091728f4b5f9ce459f0df23902d",
        "evalrun_b34fdb38ba084a928e230b6898b28637",
        "evalrun_7fe89f5118b54b6d8bb68ae619479875",
        "f63bbcfefd1b3b252a4c343bdc99fd2b", "quote.COMPOSITION",
        "3600", "HTTP 403", "0/10", "DNS",
    ):
        assert token in text, f"{source} omits {token}"
