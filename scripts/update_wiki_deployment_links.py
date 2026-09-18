"""Refresh the "Deployment Links" section of a wiki page in place.

Invoked by `publish-test-trends.yml` after cloning this repository's wiki,
alongside the `scripts/ci_results.py --wiki` call that regenerates
`Continuous-Test-Trends.md`. Replaces the text between the
`<!-- deployment-links:start -->` / `<!-- deployment-links:end -->` markers
in the given file with the current output of
`scripts.deployment_summary.render()`, leaving the rest of the page
untouched. Fails loudly (non-zero exit) if the markers are not both
present, rather than silently appending or skipping.

The wiki-publish job has no `azd`/Azure login context of its own, so
`render()` there would only ever show the unconditional "Repository" row.
Pass `--from-file <path>` one or more times (each pointing at a
`deployment_summary.py --environment <env> --out ...` fragment produced by a
job that DID have real deployment context, e.g. `deploy-staging`/
`promote-production`) to republish those real, environment-labeled links
instead of re-deriving (and losing) them here. When more than one
`--from-file` is given, every fragment is concatenated under a single
"## Deployment Links" heading so staging and production links are both
visible at once, each under its own "### <Environment>" subheading.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deployment_summary import render  # noqa: E402

START = "<!-- deployment-links:start -->"
END = "<!-- deployment-links:end -->"


def update(text: str, content: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"Could not find {START} ... {END} markers to update")
    replacement = f"{START}\n{content.rstrip()}\n{END}"
    return pattern.sub(replacement, text, count=1)


def seed(text: str, content: str) -> str:
    """Append a marked Deployment Links section to a page that has none.

    Used with --create-missing so a wiki that has never been published to does
    not hard-fail the publish job on its first run.
    """
    body = text.rstrip()
    section = f"{START}\n{content.rstrip()}\n{END}"
    return (f"{body}\n\n{section}\n" if body else f"{section}\n")


def main() -> None:
    args = sys.argv[1:]
    create_missing = "--create-missing" in args
    if create_missing:
        args.remove("--create-missing")
    from_files: list[str] = []
    while "--from-file" in args:
        index = args.index("--from-file")
        from_files.append(args[index + 1])
        del args[index:index + 2]
    if len(args) != 1:
        print(
            "usage: update_wiki_deployment_links.py <path-to-wiki-page> "
            "[--from-file <path>]... [--create-missing]",
            file=sys.stderr,
        )
        raise SystemExit(2)
    path = Path(args[0])
    if from_files:
        fragments = [Path(from_file).read_text(encoding="utf-8").rstrip() for from_file in from_files]
        intro = (
            "## Deployment Links\n\n"
            "Values reflect the current `azd`/environment configuration for each "
            "listed environment at run time, not proof that this run deployed or "
            "validated them. Rows for destinations that are not currently "
            "configured are omitted rather than invented."
        )
        content = "\n\n".join([intro, *fragments])
    else:
        content = render()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if create_missing and START not in existing:
        path.write_text(seed(existing, content), encoding="utf-8")
        return
    path.write_text(update(existing, content), encoding="utf-8")


if __name__ == "__main__":
    main()
