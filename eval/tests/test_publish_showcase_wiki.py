"""Wiki rendering keeps bilingual navigation without bypassing provenance controls."""

import sys
import re
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import publish_showcase_wiki as wiki  # noqa: E402
from render_architecture_diagrams import diagram_blocks, digest  # noqa: E402


@pytest.mark.parametrize("source", wiki.PAGES)
def test_actual_docs_render_with_wiki_peer_and_absolute_repository_links(source):
    text = (wiki.ROOT / source).read_text(encoding="utf-8")
    result = wiki.render(source, text, "devopsabcs-engineering/foundry-hosted-agents-fsi")
    assert result.startswith("# ")
    assert "\nlayout: default" not in result
    if not source.endswith("sidebar.md"):
        assert "https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/blob/main/" in result
    links = [urlsplit(target) for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", result)]
    if not source.endswith(("sidebar.md", "langfuse-pilot-evidence.md")) and "/labs/" not in source:
        assert any(link.scheme == "https" and link.hostname == "learn.microsoft.com" for link in links)
    assert "](../" not in result and "](fr/" not in result


def test_publish_twice_is_idempotent_and_preserves_existing_wiki_home(tmp_path):
    section = "<!-- deployment-links:start -->\nDeployment links stay here.\n<!-- deployment-links:end -->"
    (tmp_path / "Home.md").write_text(f"# Obsolete home\n\n{section}\n", encoding="utf-8")
    (tmp_path / "Continuous-Test-Trends.md").write_text("generated trends", encoding="utf-8")
    argv = ["--wiki", str(tmp_path), "--repository", "owner/repo"]
    assert wiki.main(argv) == 0
    first = (tmp_path / "Home.md").read_text(encoding="utf-8")
    assert wiki.main(argv) == 0
    assert (tmp_path / "Home.md").read_text(encoding="utf-8") == first
    assert "Deployment links stay here." in first
    assert wiki.deployment_section(first) == section
    assert "Obsolete home" not in first
    assert (tmp_path / "Continuous-Test-Trends.md").read_text() == "generated trends"
    for page, _ in wiki.PAGES.values():
        assert (tmp_path / f"{page}.md").is_file()
    assert (tmp_path / "Native-Foundry-Showcase.md").is_file()
    assert (tmp_path / "Native-Foundry-Showcase-FR.md").is_file()
    assert (tmp_path / "Native-Foundry-Evidence.md").is_file()
    assert (tmp_path / "Native-Foundry-Evidence-FR.md").is_file()
    for name in wiki.SCREENSHOTS:
        expected = (wiki.ROOT / "docs" / "assets" / "evidence" / name).read_bytes()
        assert expected.startswith(b"\x89PNG\r\n\x1a\n")
        assert (tmp_path / "assets" / "evidence" / name).read_bytes() == expected
    for name in wiki.DIAGRAM_IMAGES:
        expected = (wiki.ROOT / "docs" / "assets" / "architecture" / name).read_bytes()
        assert expected.startswith(b"\x89PNG\r\n\x1a\n")
        assert (tmp_path / "assets" / "architecture" / name).read_bytes() == expected


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
        "revision-staging-completed-en.png",
        "revision-staging-completed-fr.png",
        "revision-production-completed-en.png",
        "revision-production-completed-fr.png",
        "foundry-production-agent-v7.png",
    ):
        assert f"](assets/evidence/{name})" in rendered
    peer = "Native-Foundry-Evidence-FR" if source == "docs/showcase-evidence.md" else "Native-Foundry-Evidence"
    assert f"]({peer})" in rendered


@pytest.mark.parametrize("suffix", ["", "-FR"])
def test_langfuse_gallery_publishes_all_six_images_without_changing_bytes(tmp_path, suffix):
    assert wiki.main(["--wiki", str(tmp_path), "--repository", "owner/repo"]) == 0
    evidence = (tmp_path / f"Langfuse-Pilot-Evidence{suffix}.md").read_text(encoding="utf-8")
    assert f"](Langfuse-and-Foundry{suffix})" in evidence
    guide = (tmp_path / f"Langfuse-and-Foundry{suffix}.md").read_text(encoding="utf-8")
    assert ("L'export de production reste" if suffix else "Production export remains disabled") in guide
    assert "AUTH_DISABLE_SIGNUP=true" in guide
    peer = "" if suffix else "-FR"
    assert f"](Langfuse-Pilot-Evidence{peer})" in evidence
    assert f"](Langfuse-and-Foundry{peer})" in guide
    expected_images = {
        "2026-10-27/sign-in-desktop.webp",
        "2026-10-27/sign-up-desktop.webp",
        "2026-10-27/sign-in-mobile.webp",
        "2026-10-28/project-desktop.webp",
        "2026-10-28/trace-desktop.webp",
        "2026-10-28/project-mobile.webp",
    }
    images = re.findall(r"!\[[^\]]*\]\(assets/langfuse-pilot/([^\s)]+)\)", evidence)
    assert len(images) == 6 and set(images) == expected_images
    for image in images:
        expected = (wiki.ROOT / "docs/assets/langfuse-pilot" / image).read_bytes()
        assert expected.startswith(b"RIFF") and expected[8:12] == b"WEBP"
        assert (tmp_path / "assets/langfuse-pilot" / image).read_bytes() == expected
    assert "blob/main/docs/assets/langfuse-pilot/2026-10-28/ingestion-evidence.json" in evidence
    assert ("SSH opérateur et tunnel restent bloqués" if suffix else "Operator SSH and tunnel access remain blocked") in evidence
    assert not (tmp_path / "assets/langfuse-pilot/2026-10-28/ingestion-evidence.json").exists()


@pytest.mark.parametrize("source", ["docs/wiki/home.md", "docs/wiki/sidebar.md"])
def test_langfuse_wiki_navigation_opens_authenticated_gallery(source):
    rendered = wiki.render(source, (wiki.ROOT / source).read_text(encoding="utf-8"), "owner/repo")
    assert "](Langfuse-and-Foundry)" in rendered
    assert "](Langfuse-Pilot-Evidence#authenticated-project-and-trace-views)" in rendered
    assert "](Langfuse-and-Foundry-FR)" in rendered
    assert "](Langfuse-Pilot-Evidence-FR#projet-et-trace)" in rendered


def test_generated_wiki_internal_links_fragments_and_copied_assets_resolve(tmp_path):
    """Validate the rendered graph, not only individual source substitutions."""
    assert wiki.main(["--wiki", str(tmp_path), "--repository", "owner/repo"]) == 0
    for path in tmp_path.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", text):
            link = urlsplit(target)
            if link.scheme or link.netloc:
                continue
            destination = tmp_path / link.path if link.path else path
            if link.path and not link.path.startswith("assets/"):
                destination = destination.with_suffix(".md")
            assert destination.is_file(), (path.name, target)
            if link.fragment:
                body = re.sub(r"```.*?```", "", destination.read_text(encoding="utf-8"), flags=re.DOTALL)
                headings = {
                    re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*$", body, re.MULTILINE)
                }
                assert link.fragment in headings, (path.name, target)


@pytest.mark.parametrize("suffix", ["", "-FR"])
def test_langfuse_hardening_evidence_and_links_survive_wiki_rendering(tmp_path, suffix):
    assert wiki.main(["--wiki", str(tmp_path), "--repository", "owner/repo"]) == 0
    text = (tmp_path / f"Langfuse-Pilot-Evidence{suffix}.md").read_text(encoding="utf-8")
    for name in ("signup-hardening-evidence.json", "signup-hardening-power-evidence.json"):
        target = f"https://github.com/owner/repo/blob/main/docs/assets/langfuse-pilot/2026-10-28/{name}"
        assert f"]({target})" in text
    assert "2026-10-28T20:34:18.3798186Z" in text
    assert "AUTH_DISABLE_SIGNUP=true" in text


@pytest.mark.parametrize("source", [
    "docs/evaluation-guide.md", "docs/fr/evaluation-guide.md",
    "docs/labs/lab-19-evaluation-engineering.md", "docs/fr/labs/lab-19-evaluation-engineering.md",
])
def test_evaluation_guide_images_stay_local_to_wiki(source):
    text = (wiki.ROOT / source).read_text(encoding="utf-8")
    rendered = wiki.render(source, text, "owner/repo")
    images = re.findall(r"!\[[^\]]*\]\((?:\.\./)*assets/evidence/([^\s)]+)\)", text)
    assert images
    for name in images:
        assert name in wiki.SCREENSHOTS
        assert rendered.count(f"](assets/evidence/{name})") == text.count(f"evidence/{name})")


@pytest.mark.parametrize("source", wiki.PAGES)
def test_dataset_and_deck_links_download_repository_assets(source):
    text = (wiki.ROOT / source).read_text(encoding="utf-8")
    rendered = wiki.render(source, text, "owner/repo")
    base = f"https://github.com/owner/repo/blob/main/{source}"
    for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text):
        absolute = urljoin(base, target)
        if "/docs/assets/" in absolute and absolute.endswith((".pptx", ".jsonl")):
            expected = absolute.replace("/blob/main/", "/raw/refs/heads/main/", 1)
            assert f"]({expected})" in rendered


@pytest.mark.parametrize("repository", ["https://evil.test", "../repo", "owner/repo/other"])
def test_rejects_untrusted_repository_link_base(repository):
    with pytest.raises(ValueError, match="owner/name"):
        wiki.render("docs/native-showcase.md", "---\ntitle: Test\n---\n\nbody", repository)


def test_workflow_keeps_main_provenance_check_before_wiki_renderer():
    path = wiki.ROOT / ".github" / "workflows" / "publish-test-trends.yml"
    workflow = path.read_text(encoding="utf-8")
    assert workflow.index('.head_branch == "main"') < workflow.index("python scripts/publish_showcase_wiki.py")
    assert "branches: [main]" in workflow


def test_all_maintained_wiki_pages_are_source_backed():
    assert {page for page, _ in wiki.PAGES.values()} == {
        "Home", "_Sidebar", "Architecture", "Architecture-FR", "Operations",
        "Workflows", "Release-Evidence", "Native-Foundry-Showcase",
        "Native-Foundry-Showcase-FR", "Native-Foundry-Evidence",
        "Native-Foundry-Evidence-FR", "Evaluation-Engineering", "Evaluation-Engineering-FR",
        "Lab-19-Evaluation-Engineering", "Lab-19-Evaluation-Engineering-FR",
        "Langfuse-and-Foundry", "Langfuse-Pilot-Evidence",
        "Langfuse-and-Foundry-FR", "Langfuse-Pilot-Evidence-FR",
    }


@pytest.mark.parametrize("text", [
    "# Home\n",
    "<!-- deployment-links:start -->",
    "<!-- deployment-links:end -->\n<!-- deployment-links:start -->",
    "<!-- deployment-links:start --><!-- deployment-links:start --><!-- deployment-links:end -->",
])
def test_malformed_home_fails_before_any_page_is_overwritten(tmp_path, text):
    (tmp_path / "Home.md").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="deployment-links"):
        wiki.main(["--wiki", str(tmp_path), "--repository", "owner/repo"])
    assert (tmp_path / "Home.md").read_text(encoding="utf-8") == text
    assert not (tmp_path / "Architecture.md").exists()


def test_first_publication_and_fragment_peer_links(tmp_path):
    assert wiki.main(["--wiki", str(tmp_path), "--repository", "owner/repo"]) == 0
    assert "verified release artifacts" in (tmp_path / "Home.md").read_text()
    rendered = wiki.render(
        "docs/wiki/home.md",
        "---\ntitle: Test\n---\n[Architecture](../architecture.md#application-architecture)",
        "owner/repo",
    )
    assert "](Architecture#application-architecture)" in rendered


@pytest.mark.parametrize("source", wiki.PAGES)
def test_maintained_sources_resolve_local_links(source):
    text = (wiki.ROOT / source).read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text):
        if target.startswith(("#", "https://", "http://", "mailto:")):
            continue
        assert (wiki.ROOT / source).parent.joinpath(target.split("#")[0]).exists(), (source, target)


@pytest.mark.parametrize("source", ["docs/architecture.md", "docs/fr/architecture.md", "docs/wiki/workflows.md"])
def test_diagram_structure_and_architecture_coverage(source):
    text = (wiki.ROOT / source).read_text(encoding="utf-8")
    diagrams = re.findall(r"```mermaid\n(.*?)```", text, re.DOTALL)
    assert len(diagrams) >= (7 if "architecture" in source else 1)
    assert text.count("<!-- mermaid-checked:") == len(diagrams)
    identifiers = []
    for diagram in diagrams:
        assert diagram.startswith(("flowchart TD\n", "flowchart LR\n"))
        assert "\\n" not in diagram
        assert not any(character in diagram for character in ("—", "–", "{", "}"))
        assert diagram.count("subgraph ") == len(re.findall(r"^\s*end$", diagram, re.MULTILINE))
        nodes = re.findall(r'^\s*(\w+)\[', diagram, re.MULTILINE)
        assert len(nodes) < 40
        identifiers.extend(nodes)
    assert len(identifiers) == len(set(identifiers))


def test_rendered_fallbacks_match_all_mermaid_sources_and_image_hashes():
    directory = wiki.ROOT / "docs" / "assets" / "architecture"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["diagrams"]
    assert {record["asset"] for record in records} == set(wiki.DIAGRAM_IMAGES)
    assert len(records) == len(wiki.DIAGRAM_IMAGES)
    for source, (prefix, count) in wiki.DIAGRAMS.items():
        text = (wiki.ROOT / source).read_text(encoding="utf-8")
        blocks = diagram_blocks(text)
        assert len(blocks) == count
        assert text.count('<details markdown="1">') == count
        rendered = wiki.render(source, text, "owner/repo")
        for index, block in enumerate(blocks, 1):
            name = f"{prefix}-{index}.png"
            record = next(record for record in records if record["asset"] == name)
            assert record["source"] == source and record["index"] == index
            assert record["diagram_sha256"] == digest(block.encode("utf-8"))
            assert record["image_sha256"] == digest((directory / name).read_bytes())
            assert f"](assets/architecture/{name})" in rendered
