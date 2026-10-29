"""Session-2 bilingual navigation and native capability documentation stay paired."""

from pathlib import Path
import json
import re
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTATION = sorted({
    *ROOT.glob("*.md"),
    *(ROOT / "docs").rglob("*.md"),
    *(ROOT / "scripts").glob("*.md"),
    *(ROOT / "infra").rglob("README*.md"),
})
PAIRED_GUIDES = sorted(
    path for path in (ROOT / "docs").rglob("*.md")
    if path.relative_to(ROOT / "docs").parts[0] not in {"fr", "wiki"}
)
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


def heading_ids(text):
    """GitHub-style IDs for maintained headings, excluding fenced examples."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    anchors = set(re.findall(r'<a\s+(?:id|name)="([^"]+)"', text))
    counts = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", text, re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(slug + (f"-{count}" if count else ""))
    return anchors


@pytest.mark.parametrize("path", DOCUMENTATION, ids=lambda path: path.relative_to(ROOT).as_posix())
def test_repository_documentation_metadata_and_local_navigation(path):
    text = path.read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert frontmatter, f"{path} lacks frontmatter"
    for field in ("title", "description"):
        assert re.search(rf"^{field}:\s+\S", frontmatter[1], re.MULTILINE)
    if path.is_relative_to(ROOT / "docs/fr"):
        assert "lang: fr" in frontmatter[1]
    for target in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", text):
        link = urlsplit(target)
        if link.scheme or link.netloc:
            continue
        destination = path.parent / unquote(link.path) if link.path else path
        assert destination.exists(), f"{path.relative_to(ROOT)} links to missing {target}"
        if link.fragment and destination.is_file() and destination.suffix == ".md":
            assert unquote(link.fragment) in heading_ids(destination.read_text(encoding="utf-8")), (
                f"{path.relative_to(ROOT)} links to missing heading {target}"
            )


@pytest.mark.parametrize("english", PAIRED_GUIDES, ids=lambda path: path.relative_to(ROOT).as_posix())
def test_all_paired_guides_preserve_technical_commands_and_evidence(english):
    french = ROOT / "docs/fr" / english.relative_to(ROOT / "docs")
    assert french.is_file(), f"Missing translation: {french}"
    texts = [path.read_text(encoding="utf-8") for path in (english, french)]
    patterns = (
        r"evalrun_[a-f0-9]+|resp_[A-Za-z0-9]+|actions/runs/\d+|sha256:[a-f0-9]+",
        r"scripts[/\\][\w.-]+\.(?:py|ps1)",
    )
    for pattern in patterns:
        assert set(re.findall(pattern, texts[0])) == set(re.findall(pattern, texts[1])), (
            f"Technical provenance/command mismatch: {english.relative_to(ROOT)}"
        )


@pytest.mark.parametrize("source", [
    "docs/index.md", "docs/fr/index.md",
    "docs/architecture.md", "docs/fr/architecture.md",
    "docs/evaluation-guide.md", "docs/fr/evaluation-guide.md",
    "docs/native-showcase.md", "docs/fr/native-showcase.md",
    "docs/labs/index.md", "docs/fr/labs/index.md",
])
def test_langfuse_is_discoverable_from_both_language_paths_without_implying_remote_export(source):
    text = (ROOT / source).read_text(encoding="utf-8")
    prefix = "../" if "/labs/" in source else ""
    assert f"]({prefix}langfuse-integration.md)" in text
    assert re.search(rf"\]\({re.escape(prefix)}langfuse-pilot-evidence\.md(?:#[^)]+)?\)", text)
    assert re.search(
        r"(?:[Pp]roduction (?:Langfuse )?export(?: remains)?|"
        r"export (?:Langfuse )?de production(?: reste)?)\s+(?:disabled|désactivé)|"
        r"disabled by default|Désactivé par défaut",
        text,
    )


@pytest.mark.parametrize("source", [
    "README.md", "README.fr.md", "docs/index.md", "docs/fr/index.md",
    "docs/architecture.md", "docs/fr/architecture.md",
    "docs/native-showcase.md", "docs/fr/native-showcase.md",
    "docs/labs/index.md", "docs/fr/labs/index.md",
    "docs/showcase-evidence.md", "docs/fr/showcase-evidence.md",
    "docs/wiki/home.md", "docs/wiki/operations.md", "docs/wiki/release-evidence.md",
    "infra/README.md",
])
def test_release_summaries_reference_latest_approved_source_not_historical_screenshots(source):
    text = (ROOT / source).read_text(encoding="utf-8")
    assert "42c627c" in text
    assert "40567253202" in text or source in {"docs/index.md", "docs/fr/index.md"}


@pytest.mark.parametrize("source", ["docs/showcase-evidence.md", "docs/fr/showcase-evidence.md"])
def test_latest_release_evidence_does_not_relabel_earlier_revision_screenshots(source):
    text = (ROOT / source).read_text(encoding="utf-8")
    current, historical = text.split(
        "## Earlier approved revision-workflow release" if "/fr/" not in source
        else "## Livraison antérieure du parcours de révision", 1
    )
    for token in ("42c627cddba2cc14743f8120322634227d1f7366", "968", "50",
                  "evalrun_b78c38b8505a438a91bef59309b0d075",
                  "evalrun_8922edc672e24be6a5deb252399f1001", "LANGFUSE_*"):
        assert token in current
    assert "revision-production-completed-en.png" not in current
    assert "39527950931" in historical and "revision-production-completed-en.png" in historical


def test_root_readmes_have_reciprocal_languages_and_native_showcase_entry():
    for filename, peer, runbook in [
        ("README.md", "README.fr.md", "docs/native-showcase.md"),
        ("README.fr.md", "README.md", "docs/fr/native-showcase.md"),
    ]:
        content = (ROOT / filename).read_text(encoding="utf-8")
        assert f"]({peer})" in content
        assert f"]({runbook})" in content


@pytest.mark.parametrize("filename,folder,gallery", [
    ("README.md", "docs", "Langfuse-Pilot-Evidence#authenticated-project-and-trace-views"),
    ("README.fr.md", "docs/fr", "Langfuse-Pilot-Evidence-FR#projet-et-trace"),
])
def test_root_readmes_link_verified_langfuse_evidence_and_latest_release(filename, folder, gallery):
    text = (ROOT / filename).read_text(encoding="utf-8")
    for token in (
        f"]({folder}/langfuse-integration.md)", f"]({folder}/langfuse-pilot-evidence.md#",
        f"/wiki/{gallery}", "40567253202", "v8",
    ):
        assert token in text, f"{filename} omits {token}"
    assert "These authored\nfiles are not evidence" not in text


def test_top_level_workshop_guides_are_paired():
    english = {path.name for path in (ROOT / "docs").glob("*.md")}
    french = {path.name for path in (ROOT / "docs/fr").glob("*.md")}
    assert english == french


@pytest.mark.parametrize("filename", ["langfuse-integration.md", "langfuse-pilot-evidence.md"])
def test_langfuse_translations_share_commands_evidence_and_reciprocal_links(filename):
    english = (ROOT / "docs" / filename).read_text(encoding="utf-8")
    french = (ROOT / "docs/fr" / filename).read_text(encoding="utf-8")
    assert f"](fr/{filename})" in english
    assert f"](../{filename})" in french
    assert "lang: fr" in french.split("---", 2)[1]
    assert powershell_blocks(english) == powershell_blocks(french)
    assert len(re.findall(r"^#{2,3} ", english, re.MULTILINE)) == len(re.findall(r"^#{2,3} ", french, re.MULTILINE))
    for text, directory in [(english, "docs"), (french, "docs/fr")]:
        for token in ("AUTH_DISABLE_SIGNUP=true", "4.70.1", "127.0.0.1:3000", "0600"):
            assert token in text
        for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text):
            if not target.startswith(("https://", "http://", "#")):
                assert (ROOT / directory / target.split("#")[0]).exists(), (directory, target)
    assets = lambda text: set(re.findall(r"assets/langfuse-pilot/([^\s)]+)", text))
    assert assets(english) == assets(french)


def test_signup_hardening_evidence_preserves_single_membership_and_final_deallocation():
    assets = ROOT / "docs/assets/langfuse-pilot/2026-10-28"
    result = json.loads((assets / "signup-hardening-evidence.json").read_text(encoding="utf-8"))
    power = json.loads((assets / "signup-hardening-power-evidence.json").read_text(encoding="utf-8"))
    assert result["signupDisabledInWebAndWorker"] is True
    assert result["retainedAccountAndOwnerMembershipVerified"] is True
    assert set(result["counts"].values()) == {1}
    assert len(result["services"]) == 6
    assert sum(service["health"] == "healthy" for service in result["services"]) == 5
    assert result["credentialsDisclosed"] is False
    assert result["cleanupMarker"] == "TASK_OWNED_TEMPORARY_DIRECTORY_REMOVED"
    assert any(status["code"] == "PowerState/deallocated" for status in power["statuses"])
    for folder in ("docs", "docs/fr"):
        text = (ROOT / folder / "langfuse-pilot-evidence.md").read_text(encoding="utf-8")
        for token in ("2026-10-28T20:31:57.939369Z", power["observedAt"], "signup-hardening-evidence.json"):
            assert token in text


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
