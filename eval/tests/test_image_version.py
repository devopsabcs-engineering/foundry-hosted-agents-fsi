"""Image publication identifies exact source without mutating protected main."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("image_version", ROOT / "scripts" / "bump_version.py")
version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(version)


@pytest.mark.parametrize("app", ["web-chat", "reviewer-app"])
def test_source_qualified_version_does_not_write_source(tmp_path, monkeypatch, capsys, app):
    path = tmp_path / "apps" / app / "VERSION"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"1.2.3\r\n")
    monkeypatch.setattr(version, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["bump_version.py", "--app", app, "--source-sha", "a" * 40])
    version.main()
    assert capsys.readouterr().out == "1.2.3-" + "a" * 40 + "\n"
    assert path.read_bytes() == b"1.2.3\r\n"


@pytest.mark.parametrize("sha", ["", "a" * 39, "A" * 40, "z" * 40, "main", "../main"])
def test_invalid_source_sha_is_rejected_without_mutation(tmp_path, monkeypatch, sha):
    path = tmp_path / "apps" / "web-chat" / "VERSION"
    path.parent.mkdir(parents=True)
    path.write_text("1.2.3\n", encoding="utf-8")
    monkeypatch.setattr(version, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["bump_version.py", "--app", "web-chat", "--source-sha", sha])
    with pytest.raises(SystemExit) as failure:
        version.main()
    assert failure.value.code == 2
    assert path.read_text(encoding="utf-8") == "1.2.3\n"


def test_existing_manual_patch_bump_is_preserved(tmp_path, monkeypatch, capsys):
    path = tmp_path / "apps" / "web-chat" / "VERSION"
    path.parent.mkdir(parents=True)
    path.write_text("1.2.3\n", encoding="utf-8")
    monkeypatch.setattr(version, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["bump_version.py", "--app", "web-chat"])
    version.main()
    assert capsys.readouterr().out == "1.2.4\n"
    assert path.read_text(encoding="utf-8") == "1.2.4\n"


@pytest.mark.parametrize("value", ["1.2", "1.2.3-extra", "1.2.3\nmalformed"])
def test_invalid_base_version_is_rejected(tmp_path, monkeypatch, value):
    path = tmp_path / "apps" / "web-chat" / "VERSION"
    path.parent.mkdir(parents=True)
    path.write_text(value, encoding="utf-8")
    monkeypatch.setattr(version, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["bump_version.py", "--app", "web-chat", "--source-sha", "a" * 40])
    with pytest.raises(SystemExit) as failure:
        version.main()
    assert failure.value.code == 2
    assert path.read_text(encoding="utf-8") == value


@pytest.mark.parametrize("app", ["web-chat", "reviewer-app"])
def test_release_job_has_no_repository_write_permission_or_source_push(app):
    workflow = (ROOT / ".github" / "workflows" / f"{app}-build.yml").read_text(encoding="utf-8")
    release = workflow.split("\n  release:\n", 1)[1]
    assert "contents: read" in release and "contents: write" not in release
    assert "persist-credentials: false" in release
    assert '--source-sha "$GITHUB_SHA"' in release
    assert "steps.image.outputs.version" in release
    assert f'--image "pilot/{app}:v${{VERSION}}"' in release
    assert "git push" not in release and "git commit" not in release and "git rebase" not in release
