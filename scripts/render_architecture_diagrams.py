"""Refresh checked-in PNG fallbacks from Mermaid using the existing mmdc CLI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from publish_showcase_wiki import DIAGRAMS, ROOT


def diagram_blocks(text: str) -> list[str]:
    return [block.strip() + "\n" for block in re.findall(r"```mermaid\n(.*?)```", text, re.DOTALL)]


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> int:
    executable = shutil.which("mmdc")
    if not executable:
        raise RuntimeError("mmdc is required; use the existing Mermaid CLI to refresh diagram fallbacks")
    version = subprocess.run([executable, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    output = ROOT / "docs" / "assets" / "architecture"
    records = []
    with tempfile.TemporaryDirectory(prefix="foundry-diagrams-") as temporary:
        staged = Path(temporary)
        for source, (prefix, count) in DIAGRAMS.items():
            blocks = diagram_blocks((ROOT / source).read_text(encoding="utf-8"))
            if len(blocks) != count:
                raise ValueError(f"{source} has {len(blocks)} diagrams; expected {count}")
            for index, block in enumerate(blocks, 1):
                name = f"{prefix}-{index}.png"
                input_path = staged / "diagram.mmd"
                input_path.write_text(block, encoding="utf-8")
                subprocess.run(
                    [executable, "-i", str(input_path), "-o", str(staged / name), "-w", "1600", "-s", "2"],
                    check=True,
                )
                records.append({
                    "source": source,
                    "index": index,
                    "asset": name,
                    "diagram_sha256": digest(block.encode("utf-8")),
                    "image_sha256": digest((staged / name).read_bytes()),
                })
        output.mkdir(parents=True, exist_ok=True)
        for record in records:
            shutil.copyfile(staged / record["asset"], output / record["asset"])
    (output / "manifest.json").write_text(
        json.dumps({"renderer": f"mmdc {version}", "diagrams": records}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
