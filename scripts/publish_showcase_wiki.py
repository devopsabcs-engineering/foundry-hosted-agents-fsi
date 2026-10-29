"""Render maintained documentation into an already-cloned wiki; never push."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "docs/native-showcase.md": ("Native-Foundry-Showcase", "Native Foundry showcase"),
    "docs/fr/native-showcase.md": ("Native-Foundry-Showcase-FR", "Fonctions natives Foundry"),
    "docs/showcase-evidence.md": ("Native-Foundry-Evidence", "Native Foundry evidence"),
    "docs/fr/showcase-evidence.md": ("Native-Foundry-Evidence-FR", "Preuves natives Foundry"),
    "docs/architecture.md": ("Architecture", "Architecture"),
    "docs/fr/architecture.md": ("Architecture-FR", "Architecture"),
    "docs/wiki/home.md": ("Home", "Foundry hosted agents FSI"),
    "docs/wiki/sidebar.md": ("_Sidebar", "Navigation"),
    "docs/wiki/operations.md": ("Operations", "Operations"),
    "docs/wiki/workflows.md": ("Workflows", "Workflows"),
    "docs/wiki/release-evidence.md": ("Release-Evidence", "Release evidence"),
    "docs/langfuse-integration.md": ("Langfuse-and-Foundry", "Langfuse and Foundry"),
    "docs/fr/langfuse-integration.md": ("Langfuse-and-Foundry-FR", "Langfuse et Foundry"),
    "docs/langfuse-pilot-evidence.md": ("Langfuse-Pilot-Evidence", "Langfuse pilot runtime evidence"),
    "docs/fr/langfuse-pilot-evidence.md": ("Langfuse-Pilot-Evidence-FR", "Preuves d'exécution du pilote Langfuse"),
    "docs/evaluation-guide.md": ("Evaluation-Engineering", "Evaluation engineering"),
    "docs/fr/evaluation-guide.md": ("Evaluation-Engineering-FR", "Ingénierie des évaluations"),
    "docs/labs/lab-19-evaluation-engineering.md": ("Lab-19-Evaluation-Engineering", "Lab 19 - Evaluation engineering"),
    "docs/fr/labs/lab-19-evaluation-engineering.md": ("Lab-19-Evaluation-Engineering-FR", "Atelier 19 - Ingénierie des évaluations"),
}
DIAGRAMS = {
    "docs/architecture.md": ("architecture-en", 7),
    "docs/fr/architecture.md": ("architecture-fr", 7),
    "docs/wiki/workflows.md": ("workflows", 1),
}
DIAGRAM_IMAGES = tuple(
    f"{prefix}-{index}.png"
    for prefix, count in DIAGRAMS.values()
    for index in range(1, count + 1)
)
SCREENSHOTS = (
    "staging-chat-en.png",
    "staging-chat-fr.png",
    "production-reviewer-en.png",
    "release-39356610865.png",
    "foundry-staging-agent-v3.png",
    "production-reviewer-persistence-en.png",
    "production-reviewer-persistence-fr.png",
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
    "lab19-project-evaluations-2026-10-23.png",
    "lab19-v6-evaluation-overview-2026-10-23.png",
    "lab19-v6-run-results-2026-10-23.png",
    "lab19-dataset-target-2026-10-23.png",
    "lab19-practice-upload-2026-10-23.png",
    "lab19-practice-preview-2026-10-23.png",
    "lab19-groundedness-mapping-2026-10-23.png",
    "lab19-practice-review-2026-10-23.png",
    "foundry-evaluator-coherence-v13-2026-10-23.png",
    "foundry-evaluator-groundedness-v18-2026-10-23.png",
    "foundry-evaluator-task-adherence-v17-2026-10-23.png",
)
LANGFUSE_SCREENSHOTS = (
    "2026-10-27/sign-in-desktop.webp",
    "2026-10-27/sign-up-desktop.webp",
    "2026-10-27/sign-in-mobile.webp",
    "2026-10-28/project-desktop.webp",
    "2026-10-28/trace-desktop.webp",
    "2026-10-28/project-mobile.webp",
)
ASSET_GROUPS = {
    "evidence": SCREENSHOTS,
    "architecture": DIAGRAM_IMAGES,
    "langfuse-pilot": LANGFUSE_SCREENSHOTS,
}


def render(source: str, text: str, repository: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository):
        raise ValueError("repository must have the GitHub owner/name format")
    if source not in PAGES:
        raise ValueError("Only pinned documentation source pages can be published")
    frontmatter = re.match(r"\A---\r?\n.*?\r?\n---\r?\n", text, re.DOTALL)
    if not frontmatter:
        raise ValueError("Showcase source is missing frontmatter")
    body = text[frontmatter.end():].lstrip()
    base = f"https://github.com/{repository}/blob/main/{source}"
    page_links = {
        f"https://github.com/{repository}/blob/main/{path}": page
        for path, (page, _) in PAGES.items()
    }
    asset_base = f"https://github.com/{repository}/blob/main/docs/assets/"

    def link(match):
        target = match.group(1)
        if not target.startswith(("#", "https://", "http://", "mailto:")):
            target = urljoin(base, target)
            path, separator, fragment = target.partition("#")
            target = page_links.get(path, path) + separator + fragment
            if path.startswith(asset_base) and path.endswith((".pptx", ".jsonl")):
                target = path.replace("/blob/main/", "/raw/refs/heads/main/", 1) + separator + fragment
            for directory, filenames in ASSET_GROUPS.items():
                for filename in filenames:
                    if target == f"{asset_base}{directory}/{filename}":
                        target = f"assets/{directory}/{filename}"
        return f"({target})"

    body = re.sub(r"(?<=\])\(([^)\s]+)\)", link, body)
    return f"# {PAGES[source][1]}\n\n{body.rstrip()}\n"


def deployment_section(text: str) -> str:
    start = "<!-- deployment-links:start -->"
    end = "<!-- deployment-links:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Wiki Home must contain exactly one complete deployment-links section")
    first, last = text.index(start), text.index(end)
    if last < first:
        raise ValueError("Wiki Home deployment-links markers are out of order")
    return text[first:last + len(end)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args(argv)
    if not args.wiki.is_dir():
        parser.error("--wiki must be an existing cloned wiki directory")
    rendered = {
        args.wiki / f"{page}.md": render(source, (ROOT / source).read_text(encoding="utf-8"), args.repository)
        for source, (page, _) in PAGES.items()
    }
    home = args.wiki / "Home.md"
    if home.exists():
        existing = deployment_section(home.read_text(encoding="utf-8"))
        rendered[home] = rendered[home].replace(deployment_section(rendered[home]), existing, 1)
    for path, content in rendered.items():
        path.write_text(content, encoding="utf-8")
    for directory, filenames in ASSET_GROUPS.items():
        assets = args.wiki / "assets" / directory
        for filename in filenames:
            target = assets / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "docs" / "assets" / directory / filename, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
