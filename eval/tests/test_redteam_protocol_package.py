"""Offline fidelity and failure guards for a separately pinned protocol package."""

import hashlib
import io
import json
import stat
import sys
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import redteam_protocol_package as package  # noqa: E402


def sha(content):
    return hashlib.sha256(content).hexdigest()


def native_zip(extra=(), *, graph=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("main.py", b"original main\r\n")
        archive.writestr("response_bridge.py", b"original converter\r\n")
        archive.writestr(
            "graph.py",
            graph if graph is not None else (ROOT / "src" / "quote-preparation-agent" / "graph.py").read_bytes(),
        )
        for name, content in extra:
            info = zipfile.ZipInfo(name)
            info.filename = name
            archive.writestr(info, content)
    return buffer.getvalue()


@pytest.fixture
def reviewed(monkeypatch):
    entrypoint = (ROOT / "scripts" / package.ENTRYPOINT).read_bytes()
    monkeypatch.setattr(package, "reviewed_entrypoint", lambda revision, digest: entrypoint)
    return {"protocol_revision": "a" * 40, "entrypoint_sha256": sha(entrypoint)}


def test_derived_zip_preserves_every_original_file_and_has_a_distinct_reproducible_pin(reviewed):
    original = native_zip([("requirements.txt", b"original dependencies\r\n")])
    derived, proof = package.build_package(original, source_sha256=sha(original), **reviewed)
    repeated, repeated_proof = package.build_package(original, source_sha256=sha(original), **reviewed)
    assert derived == repeated and proof == repeated_proof
    assert derived != original
    assert proof["source_content_sha256"] == sha(original)
    assert proof["target_content_sha256"] == sha(derived)
    assert proof["immutable_artifact_equality"] is False
    assert proof["cloud_operations_performed"] is False
    assert proof["baseline_modified"] is False
    with zipfile.ZipFile(io.BytesIO(original)) as before, zipfile.ZipFile(io.BytesIO(derived)) as after:
        assert set(after.namelist()) == set(before.namelist()) | {package.ENTRYPOINT}
        for member in before.infolist():
            assert after.read(member.filename) == before.read(member.filename)
            assert after.getinfo(member.filename).CRC == member.CRC
        assert sha(after.read(package.ENTRYPOINT)) == reviewed["entrypoint_sha256"]
        assert after.getinfo(package.ENTRYPOINT).date_time == (1980, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("member", [
    "../escape.py", "/absolute.py", "C:/absolute.py", "C:drive.py", r"folder\escape.py",
    "folder/../../escape.py", "main.py", "redteam_protocol_entrypoint.py",
])
def test_unsafe_duplicate_or_preexisting_overlay_entries_are_rejected(reviewed, member):
    with pytest.warns(UserWarning) if member == "main.py" else nullcontext():
        original = native_zip([(member, b"unreviewed")])
    with pytest.raises(ValueError, match="unsafe|duplicate|unmodified original"):
        package.build_package(original, source_sha256=sha(original), **reviewed)


def test_symlink_is_rejected(reviewed):
    original = native_zip()
    buffer = io.BytesIO(original)
    with zipfile.ZipFile(buffer, "a") as archive:
        info = zipfile.ZipInfo("link.py")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "graph.py")
    content = buffer.getvalue()
    with pytest.raises(ValueError, match="unsafe"):
        package.build_package(content, source_sha256=sha(content), **reviewed)


@pytest.mark.parametrize("damage", ["wrong-pin", "invalid-zip", "changed-graph", "expanded-size", "file-count"])
def test_damaged_source_is_never_packaged_as_a_protocol_correction(reviewed, damage):
    original = native_zip()
    expected = sha(original)
    if damage == "wrong-pin":
        expected = "0" * 64
    elif damage == "invalid-zip":
        original = b"not a native ZIP"
    elif damage == "changed-graph":
        original = native_zip(graph=b"def default_model(prompt): return remote_llm(prompt)\n")
    elif damage == "expanded-size":
        original = native_zip([("oversized.txt", b"x" * (package.MAX_PACKAGE_BYTES + 1))])
    elif damage == "file-count":
        original = native_zip([(f"extra-{i}.py", b"") for i in range(1000)])
    if damage != "wrong-pin":
        expected = sha(original)
    with pytest.raises(ValueError):
        package.build_package(original, source_sha256=expected, **reviewed)


def test_crlf_only_graph_materialization_is_supported(reviewed):
    graph = (ROOT / "src" / "quote-preparation-agent" / "graph.py").read_bytes().replace(b"\r\n", b"\n")
    original = native_zip(graph=graph.replace(b"\n", b"\r\n"))
    _, proof = package.build_package(original, source_sha256=sha(original), **reviewed)
    assert proof["supported_graph_sha256"] == sha(graph)


@pytest.mark.parametrize("source", [
    b"", b"SUPPORTED_GRAPH_SHA256 = 'wrong'\n",
    b"SUPPORTED_GRAPH_SHA256 = 'a' * 64\n",
    b"SUPPORTED_GRAPH_SHA256 = '" + b"a" * 64 + b"'\nSUPPORTED_GRAPH_SHA256 = '" + b"b" * 64 + b"'\n",
])
def test_entrypoint_must_have_one_literal_supported_graph_hash(source):
    with pytest.raises(ValueError, match="pin one"):
        package.supported_graph_hash(source)


def test_reviewed_entrypoint_requires_exact_git_revision_and_file_hash(monkeypatch):
    content = b"reviewed entrypoint\n"
    calls = []

    def git(arguments, **kwargs):
        calls.append(arguments)
        return SimpleNamespace(stdout="a" * 40 + "\n" if len(calls) == 1 else content)

    monkeypatch.setattr(package.subprocess, "run", git)
    assert package.reviewed_entrypoint("a" * 40, sha(content)) == content
    assert calls[-1] == ["git", "show", "a" * 40 + ":" + package.ENTRYPOINT_PATH]
    calls.clear()
    with pytest.raises(ValueError, match="exact reviewed Git revision"):
        package.reviewed_entrypoint("b" * 40, sha(content))
    calls.clear()
    with pytest.raises(ValueError, match="entrypoint differs"):
        package.reviewed_entrypoint("a" * 40, "0" * 64)


def test_preparation_cli_is_local_only_fresh_and_never_overwrites_source(tmp_path, monkeypatch, reviewed):
    original = native_zip()
    source = tmp_path / "original.zip"
    source.write_bytes(original)
    monkeypatch.setattr(package, "REPO_ROOT", tmp_path)
    output = tmp_path / ".local" / "protocol"
    argv = [
        "--source-zip", str(source), "--source-content-sha256", sha(original),
        "--protocol-revision", reviewed["protocol_revision"],
        "--protocol-entrypoint-sha256", reviewed["entrypoint_sha256"],
        "--output-dir", str(output),
    ]
    assert package.main(argv) == 0
    proof = json.loads((output / "protocol-preparation.json").read_text())
    assert sha((output / "protocol-native-code.zip").read_bytes()) == proof["target_content_sha256"]
    assert source.read_bytes() == original
    with pytest.raises(SystemExit):
        package.main(argv)
    with pytest.raises(SystemExit):
        package.main(argv[:-1] + [str(tmp_path / "outside-local")])
