"""Validate the bilingual teaching package offline, without model calls."""

import ast
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
import run_judge_evaluation as runner  # noqa: E402

LABS = [
    ROOT / "docs" / language / "labs" / "lab-19-evaluation-engineering.md"
    for language in ("", "fr")
]
GUIDES = [ROOT / "docs" / language / "evaluation-guide.md" for language in ("", "fr")]
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def python_examples(path):
    text = path.read_text(encoding="utf-8")
    return re.findall(r"^@'\n(.*?)^'@ \| & \$python", text, re.MULTILINE | re.DOTALL)


def anchors(text):
    result = set(re.findall(r'<a id="([^"]+)"', text))
    for heading in re.findall(r"^#{1,6} (.+)$", text, re.MULTILINE):
        clean = "".join(
            char for char in heading.lower()
            if char in " _-" or unicodedata.category(char)[0] in "LMN"
        )
        result.add(clean.replace(" ", "-"))
        result.add(re.sub(r" +", "-", clean))
    return result


@pytest.mark.parametrize("path", LABS + GUIDES)
def test_teaching_pages_have_metadata_and_resolving_links(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert re.search(r"^title: .+", text, re.MULTILINE)
    assert re.search(r"^description: .+", text, re.MULTILINE)
    assert not re.search(r"^# ", text, re.MULTILINE)
    for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text):
        if re.match(r"(?:https?://|mailto:)", target):
            continue
        filename, _, fragment = unquote(target).partition("#")
        destination = path.parent / filename if filename else path
        assert destination.exists(), (path, target)
        if fragment and destination.suffix == ".md":
            assert fragment in anchors(destination.read_text(encoding="utf-8")), (path, target)


def test_translations_share_all_ten_exercises_and_executable_python():
    for path in LABS:
        text = path.read_text(encoding="utf-8")
        assert re.findall(r"^## (?:Exercise|Exercice) 19\.(\d+):", text, re.MULTILINE) == [
            str(number) for number in range(1, 11)
        ]
        assert len(python_examples(path)) == 3
        for index, source in enumerate(python_examples(path)):
            ast.parse(source, filename=f"{path.name}:example{index}")
    assert python_examples(LABS[0]) == python_examples(LABS[1])


def test_judge_only_recipe_reuses_captures_and_fails_on_existing_output(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    root = tmp_path / "experiment"
    root.mkdir()
    (root / "experiment.json").write_text(json.dumps({
        "endpoint": "https://example.test",
        "observedAgentVersion": "6",
        "judgeDeployment": "test-judge",
    }), encoding="utf-8-sig")
    captured = [{"id": "example", "response": "Submitted for review."}]
    for locale in ("en-CA", "fr-CA"):
        folder = root / f"{locale}-trial1"
        folder.mkdir()
        (folder / "captured.json").write_text(json.dumps(captured), encoding="utf-8")
    calls = []

    def evaluate(records, args):
        assert records == captured
        assert args.output_dir.is_dir()
        assert args.minimum_pass_rate == 1.0
        assert args.version == "6" and args.deployment == "test-judge"
        reuse = json.loads((args.output_dir / "capture-reuse.json").read_text())
        assert reuse["fresh_agent_inference"] is False
        assert Path(reuse["source"]).name == "captured.json"
        calls.append(args)

    def forbidden_capture(*args, **kwargs):
        pytest.fail("Judge-only recipe must not recapture an agent")

    monkeypatch.setattr(runner, "evaluate", evaluate)
    monkeypatch.setattr(runner, "capture", forbidden_capture)
    monkeypatch.setattr(sys, "argv", ["-", str(root)])
    source = python_examples(LABS[0])[0]
    exec(compile(source, "judge-only-example", "exec"), {})
    assert len(calls) == 2
    with pytest.raises(FileExistsError):
        exec(compile(source, "judge-only-example", "exec"), {})
    assert len(calls) == 2


def test_trial_inspector_rejects_missing_results_instead_of_averaging(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    root = tmp_path / "experiment"
    root.mkdir()
    monkeypatch.setattr(sys, "argv", ["-", str(root)])
    source = python_examples(LABS[0])[1]
    with pytest.raises(ValueError, match="No trial evidence"):
        exec(compile(source, "trial-inspection-example", "exec"), {})
    folder = root / "en-CA-trial1"
    folder.mkdir()
    (folder / "run-identity.json").write_text('{"run_id": "evalrun_test"}')
    result = {
        "run": {"id": "evalrun_test", "status": "completed",
                "result_counts": {"total": 5, "errored": 0, "skipped": 0}},
        "items": [{
            "id": f"item{index}",
            "status": "completed",
            "results": [{"name": metric, "score": 5, "passed": True}
                        for metric in ("coherence", "groundedness", "task_adherence")],
        } for index in range(5)],
    }
    (folder / "results.json").write_text(json.dumps(result))
    exec(compile(source, "trial-inspection-example", "exec"), {})
    assert "evalrun_test" in capsys.readouterr().out
    result["items"].pop()
    (folder / "results.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="Missing or duplicate"):
        exec(compile(source, "trial-inspection-example", "exec"), {})


def test_wilson_example_matches_stated_interval(capsys):
    exec(compile(python_examples(LABS[0])[2], "wilson-example", "exec"), {})
    assert capsys.readouterr().out.strip() == "5/5: [0.566, 1.000]"


@pytest.mark.parametrize("language", ["en", "fr"])
def test_powerpoint_contains_readable_bounded_slides_and_instructor_notes(language):
    deck = ROOT / "docs" / "assets" / "decks" / f"foundry-evaluation-engineering-{language}.pptx"
    with ZipFile(deck) as archive:
        assert archive.testzip() is None
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        size = presentation.find("p:sldSz", NS)
        width, height = int(size.attrib["cx"]), int(size.attrib["cy"])
        slide_names = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
        assert len(slide_names) == 34
        for number in range(1, 35):
            slide = ET.fromstring(archive.read(f"ppt/slides/slide{number}.xml"))
            texts = [text.text or "" for text in slide.findall(".//a:t", NS)]
            assert any(f"{number} / 34" in text for text in texts)
            for transform in slide.findall(".//a:xfrm", NS):
                offset = transform.find("a:off", NS)
                extent = transform.find("a:ext", NS)
                if offset is not None and extent is not None:
                    x, y = int(offset.attrib["x"]), int(offset.attrib["y"])
                    w, h = int(extent.attrib["cx"]), int(extent.attrib["cy"])
                    assert min(x, y, w, h) >= 0
                    assert x + w <= width + 9144 and y + h <= height + 9144
            assert all(int(run.attrib["sz"]) >= 1000 for run in slide.findall(".//a:rPr[@sz]", NS))
            notes = ET.fromstring(archive.read(f"ppt/notesSlides/notesSlide{number}.xml"))
            note_text = " ".join(node.text or "" for node in notes.findall(".//a:t", NS))
            assert len(note_text) > 200
            assert "learn.microsoft.com" in note_text and "evaluation-guide.html" in note_text
        all_text = " ".join(archive.read(name).decode() for name in slide_names)
        for token in ("Wilson", "COMPOSITION", "groundedness", "SystemError", "39527950931"):
            assert token in all_text
