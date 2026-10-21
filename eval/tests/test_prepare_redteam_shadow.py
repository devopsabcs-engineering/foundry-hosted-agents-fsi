"""Offline preparation must never execute azd or alter the approved quote source."""

import importlib.util
import io
import json
import zipfile
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prepare_redteam_shadow.py"
spec = importlib.util.spec_from_file_location("prepare_redteam_shadow", SCRIPT)
shadow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shadow)


@pytest.fixture
def preparation(tmp_path, monkeypatch):
    source = tmp_path / "src" / "quote-preparation-agent"
    source.mkdir(parents=True)
    (source / "main.py").write_text("print('unchanged')\n")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "ignored.pyc").write_bytes(b"cache")
    git = Mock(side_effect=["a" * 40, "", "src/quote-preparation-agent/main.py", "c" * 40])
    monkeypatch.setattr(shadow, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(shadow, "git", git)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("src/quote-preparation-agent/main.py", "print('unchanged')\n")
    monkeypatch.setattr(shadow, "git_archive", Mock(return_value=archive.getvalue()))
    args = SimpleNamespace(
        allow_new_code_deployment=True, source_revision="a" * 40, source_content_sha256="b" * 64,
        source_definition_sha256="d" * 64, source_deployment_provenance="release39527950931",
        source_agent="quote-preparation-agent", source_agent_version="7",
        staging_endpoint="https://test.services.ai.azure.com/api/projects/fsi-staging",
        agent="fsi-showcase-redteam-test", timeout=600, output_dir=tmp_path / ".local" / "shadow",
        runtime_setting=[
            "APPLICATION_MCP_URL=https://fixtures.test/application/mcp",
            "RULEBOOK_MCP_URL=https://fixtures.test/rulebook/mcp",
            "AZURE_AI_PROJECT_ENDPOINT=https://test.services.ai.azure.com/api/projects/fsi-staging",
            "FOUNDRY_TOOLBOX_VERSION=1", "AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini",
            "AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com/",
        ],
    )
    return args, source, git


def test_prepares_only_named_agent_with_same_source_and_private_store(preparation):
    args, source, git = preparation
    original = (source / "main.py").read_bytes()
    result = shadow.prepare(args)
    manifest = json.loads((args.output_dir / "azure.yaml").read_text())
    service = manifest["services"][args.agent]
    assert service["name"] == args.agent and service["project"] == "source"
    assert not Path(service["project"]).is_absolute()
    assert (args.output_dir / service["project"] / "main.py").is_file()
    assert (args.output_dir / "source" / "main.py").read_bytes() == b"print('unchanged')\n"
    assert not (args.output_dir / "source" / "__pycache__").exists()
    assert service["codeConfiguration"] == {
        "dependencyResolution": "remote_build", "entryPoint": "main.py", "runtime": "python_3_13",
    }
    assert "content_hash" not in json.dumps(manifest) and "contentHash" not in json.dumps(manifest)
    assert manifest["services"]["ai-project"] == {
        "host": "azure.ai.project", "endpoint": args.staging_endpoint,
    }
    assert not {"infra", "hooks"}.intersection(manifest)
    assert "toolboxes" not in service
    settings = {item["name"]: item["value"] for item in service["environmentVariables"]}
    assert settings["CASE_STORE_DB_PATH"] == ":memory:"
    assert settings["FOUNDRY_TOOLBOX_VERSION"] == "${SHADOW_FOUNDRY_TOOLBOX_VERSION}"
    assert "COSMOS_ENDPOINT" not in settings
    text = (args.output_dir / "preparation.json").read_text()
    assert "fixtures.test" not in text and "gpt-4o-mini" not in text
    assert not result["ready_for_native_scan"] and not result["running"]
    assert not result["cloud_operations_performed"]
    assert (source / "main.py").read_bytes() == original
    assert git.call_count == 4


def test_manifest_pins_validated_staging_endpoint_despite_ambient_production(preparation, monkeypatch):
    args, _, _ = preparation
    production = "https://production.services.ai.azure.com/api/projects/fsi-production"
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", production)
    shadow.prepare(args)
    manifest = json.loads((args.output_dir / "azure.yaml").read_text())
    project = manifest["services"]["ai-project"]
    assert project["endpoint"] == args.staging_endpoint
    assert project["endpoint"] != production
    assert "${" not in project["endpoint"]
    assert production not in json.dumps(manifest)


@pytest.mark.parametrize(("field", "value"), [
    ("allow_new_code_deployment", False), ("timeout", 0), ("timeout", 1201),
    ("staging_endpoint", "https://test.services.ai.azure.com/api/projects/fsi-production"),
    ("agent", "quote-preparation-agent"), ("source_agent_version", "latest"),
    ("source_revision", "main"), ("source_definition_sha256", "unknown"),
    ("source_content_sha256", "unknown"), ("source_deployment_provenance", ""),
    ("runtime_setting", ["COSMOS_ENDPOINT=https://live.test"]),
    ("runtime_setting", ["AZURE_OPENAI_API_KEY=secret"]),
])
def test_invalid_preparation_has_no_remote_or_local_effects(preparation, field, value):
    args, _, git = preparation
    setattr(args, field, value)
    with pytest.raises(ValueError):
        shadow.prepare(args)
    git.assert_not_called()
    assert not args.output_dir.exists()


@pytest.mark.parametrize("unsafe", ["source", "root", "occupied", "dirty", "untracked", "ignored-secret"])
def test_preparation_rejects_mutation_reuse_and_unreviewed_packaging(preparation, unsafe):
    args, source, git = preparation
    if unsafe == "source":
        args.output_dir = source / "new"
    elif unsafe == "root":
        args.output_dir = source.parents[1]
    elif unsafe == "occupied":
        args.output_dir.mkdir(parents=True)
        (args.output_dir / "existing").write_text("preserve")
    elif unsafe == "dirty":
        git.side_effect = ["a" * 40, "src/quote-preparation-agent/main.py"]
    elif unsafe in {"untracked", "ignored-secret"}:
        (source / (".env" if unsafe == "ignored-secret" else "extra.py")).write_text("not approved")
    with pytest.raises(ValueError):
        shadow.prepare(args)
    assert not (args.output_dir / "azure.yaml").exists()


@pytest.mark.parametrize("member", [
    "src/quote-preparation-agent/../escape.py", "other/escape.py",
    "src/quote-preparation-agent/C:escape.py",
    "src/quote-preparation-agent/C:/escape.py",
    r"src/quote-preparation-agent/C:\escape.py",
    "src/quote-preparation-agent///server/share/escape.py",
    r"src/quote-preparation-agent/\\server\share\escape.py",
    r"src/quote-preparation-agent/\escape.py",
    "src/quote-preparation-agent//escape.py",
    r"src/quote-preparation-agent/subdir\..\escape.py",
])
@pytest.mark.parametrize("path_semantics", ["native", "posix"])
def test_approved_archive_still_cannot_escape_local_snapshot(
    preparation, monkeypatch, member, path_semantics,
):
    args, _, _ = preparation
    if path_semantics == "posix":
        monkeypatch.setattr(shadow, "Path", PurePosixPath)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(member, "not a quote source path")
    monkeypatch.setattr(shadow, "git_archive", Mock(return_value=archive.getvalue()))
    with pytest.raises(ValueError, match="unreviewed paths"):
        shadow.prepare(args)
    assert not args.output_dir.exists()
