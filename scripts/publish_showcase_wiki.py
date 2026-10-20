"""Render the bilingual showcase docs into an already-cloned wiki; never push."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "docs/native-showcase.md": ("Native-Foundry-Showcase", "Native Foundry showcase"),
    "docs/fr/native-showcase.md": ("Native-Foundry-Showcase-FR", "Fonctions natives Foundry"),
}


def render(source: str, text: str, repository: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repository):
        raise ValueError("repository must have the GitHub owner/name format")
    if source not in PAGES:
        raise ValueError("Only the two pinned showcase source pages can be published")
    frontmatter = re.match(r"\A---\r?\n.*?\r?\n---\r?\n", text, re.DOTALL)
    if not frontmatter:
        raise ValueError("Showcase source is missing frontmatter")
    body = text[frontmatter.end():].lstrip()
    base = f"https://github.com/{repository}/blob/main/{source}"
    peer = "fr/native-showcase.md" if source == "docs/native-showcase.md" else "../native-showcase.md"
    peer_page = "Native-Foundry-Showcase-FR" if source == "docs/native-showcase.md" else "Native-Foundry-Showcase"

    def link(match):
        target = match.group(2)
        if target == peer:
            target = peer_page
        elif not target.startswith(("#", "https://", "http://", "mailto:")):
            target = urljoin(base, target)
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
    home = args.wiki / "Home.md"
    text = home.read_text(encoding="utf-8") if home.exists() else "# Home\n"
    marker = "<!-- native-showcase:start -->"
    end = "<!-- native-showcase:end -->"
    section = (
        f"{marker}\n## Native Foundry showcase / Fonctions natives\n\n"
        "[English](Native-Foundry-Showcase) | [Français](Native-Foundry-Showcase-FR)\n"
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
