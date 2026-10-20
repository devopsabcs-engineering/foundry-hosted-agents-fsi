"""Wiki rendering keeps bilingual navigation without bypassing provenance controls."""

import sys
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import publish_showcase_wiki as wiki  # noqa: E402


@pytest.mark.parametrize("source", wiki.PAGES)
def test_actual_docs_render_with_wiki_peer_and_absolute_repository_links(source):
    text = (wiki.ROOT / source).read_text(encoding="utf-8")
    result = wiki.render(source, text, "devopsabcs-engineering/foundry-hosted-agents-fsi")
    assert result.startswith("# ")
    assert "\nlayout: default" not in result
    assert "https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/blob/main/" in result
    assert "](Native-Foundry-Showcase" in result
    links = [urlsplit(target) for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", result)]
    assert any(link.scheme == "https" and link.hostname == "learn.microsoft.com" for link in links)
    assert "](../" not in result and "](fr/" not in result


def test_publish_twice_is_idempotent_and_preserves_existing_wiki_home(tmp_path):
    (tmp_path / "Home.md").write_text("# Existing home\n\nDeployment links stay here.\n", encoding="utf-8")
    argv = ["--wiki", str(tmp_path), "--repository", "owner/repo"]
    assert wiki.main(argv) == 0
    first = (tmp_path / "Home.md").read_text(encoding="utf-8")
    assert wiki.main(argv) == 0
    assert (tmp_path / "Home.md").read_text(encoding="utf-8") == first
    assert "Deployment links stay here." in first
    assert first.count("<!-- native-showcase:start -->") == 1
    assert (tmp_path / "Native-Foundry-Showcase.md").is_file()
    assert (tmp_path / "Native-Foundry-Showcase-FR.md").is_file()
    assert (tmp_path / "Native-Foundry-Evidence.md").is_file()
    assert (tmp_path / "Native-Foundry-Evidence-FR.md").is_file()
    for name in wiki.SCREENSHOTS:
        expected = (wiki.ROOT / "docs" / "assets" / "evidence" / name).read_bytes()
        assert expected.startswith(b"\x89PNG\r\n\x1a\n")
        assert (tmp_path / "assets" / "evidence" / name).read_bytes() == expected


@pytest.mark.parametrize("source", ["docs/showcase-evidence.md", "docs/fr/showcase-evidence.md"])
def test_evidence_images_and_peer_pages_stay_local_to_wiki(source):
    rendered = wiki.render(source, (wiki.ROOT / source).read_text(encoding="utf-8"), "owner/repo")
    language = "en" if source == "docs/showcase-evidence.md" else "fr"
    assert f"](assets/evidence/staging-chat-{language}.png)" in rendered
    assert "](assets/evidence/production-reviewer-en.png)" in rendered
    assert "](assets/evidence/release-39356610865.png)" in rendered
    assert "](assets/evidence/foundry-staging-agent-v3.png)" in rendered
    assert f"](assets/evidence/production-reviewer-persistence-{language}.png)" in rendered
    for name in (
        "foundry-generation-portal.png",
        "foundry-index-portal.png",
        "foundry-skill-portal.png",
        "foundry-evaluation-portal.png",
        "foundry-traces-portal.png",
        "foundry-staging-playground-v4.png",
        "foundry-production-playground-v5.png",
        "release-39424857559.png",
        "foundry-memory-portal.png",
        "foundry-staging-playground-v5.png",
        "foundry-production-playground-v6.png",
    ):
        assert f"](assets/evidence/{name})" in rendered
    peer = "Native-Foundry-Evidence-FR" if source == "docs/showcase-evidence.md" else "Native-Foundry-Evidence"
    assert f"]({peer})" in rendered


@pytest.mark.parametrize("repository", ["https://evil.test", "../repo", "owner/repo/other"])
def test_rejects_untrusted_repository_link_base(repository):
    with pytest.raises(ValueError, match="owner/name"):
        wiki.render("docs/native-showcase.md", "---\ntitle: Test\n---\n\nbody", repository)


def test_workflow_keeps_main_provenance_check_before_wiki_renderer():
    path = wiki.ROOT / ".github" / "workflows" / "publish-test-trends.yml"
    workflow = path.read_text(encoding="utf-8")
    assert workflow.index('.head_branch == "main"') < workflow.index("python scripts/publish_showcase_wiki.py")
    assert "branches: [main]" in workflow
