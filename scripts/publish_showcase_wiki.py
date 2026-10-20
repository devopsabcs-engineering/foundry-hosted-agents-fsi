"""Render the bilingual showcase docs into an already-cloned wiki; never push."""

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
}
SCREENSHOTS = (
    "staging-chat-en.png",
    "staging-chat-fr.png",
    "production-reviewer-en.png",
    "release-39356610865.png",
    "foundry-staging-agent-v3.png",
)


def render(source: str, text: str, repository: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository):
        raise ValueError("repository must have the GitHub owner/name format")
    if source not in PAGES:
        raise ValueError("Only pinned showcase source pages can be published")
    frontmatter = re.match(r"\A---\r?\n.*?\r?\n---\r?\n", text, re.DOTALL)
    if not frontmatter:
        raise ValueError("Showcase source is missing frontmatter")
    body = text[frontmatter.end():].lstrip()
    base = f"https://github.com/{repository}/blob/main/{source}"
    page_links = {
        f"https://github.com/{repository}/blob/main/{path}": page
        for path, (page, _) in PAGES.items()
    }

    def link(match):
        target = match.group(2)
        if not target.startswith(("#", "https://", "http://", "mailto:")):
            target = urljoin(base, target)
            target = page_links.get(target, target)
            for filename in SCREENSHOTS:
                if target == f"https://github.com/{repository}/blob/main/docs/assets/evidence/{filename}":
                    target = f"assets/evidence/{filename}"
        return f"[{match.group(1)}]({target})"

    body = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, body)
    return f"# {PAGES[source][1]}\n\n{body.rstrip()}\n"


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
    for path, content in rendered.items():
        path.write_text(content, encoding="utf-8")
    assets = args.wiki / "assets" / "evidence"
    assets.mkdir(parents=True, exist_ok=True)
    for filename in SCREENSHOTS:
        shutil.copyfile(ROOT / "docs" / "assets" / "evidence" / filename, assets / filename)
    home = args.wiki / "Home.md"
    text = home.read_text(encoding="utf-8") if home.exists() else "# Home\n"
    marker = "<!-- native-showcase:start -->"
    end = "<!-- native-showcase:end -->"
    section = (
        f"{marker}\n## Native Foundry showcase / Fonctions natives\n\n"
        "[English](Native-Foundry-Showcase) | [Français](Native-Foundry-Showcase-FR)\n"
        "\n[Evidence and screenshots](Native-Foundry-Evidence) | "
        "[Preuves et captures](Native-Foundry-Evidence-FR)\n"
        f"{end}"
    )
    if marker in text:
        if end not in text:
            raise ValueError("Wiki Home has an incomplete native showcase section")
        text = re.sub(re.escape(marker) + ".*?" + re.escape(end), section, text, flags=re.DOTALL)
    else:
        text = text.rstrip() + "\n\n" + section + "\n"
    home.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
