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


@pytest.mark.parametrize("repository", ["https://evil.test", "../repo", "owner/repo/other"])
def test_rejects_untrusted_repository_link_base(repository):
    with pytest.raises(ValueError, match="owner/name"):
        wiki.render("docs/native-showcase.md", "---\ntitle: Test\n---\n\nbody", repository)


def test_workflow_keeps_main_provenance_check_before_wiki_renderer():
    path = wiki.ROOT / ".github" / "workflows" / "publish-test-trends.yml"
    workflow = path.read_text(encoding="utf-8")
    assert workflow.index('.head_branch == "main"') < workflow.index("python scripts/publish_showcase_wiki.py")
    assert "branches: [main]" in workflow
