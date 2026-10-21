import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_reviewer_foundry_access as probe


def passing_result():
    return {
        "invocationHttpStatus": 200, "responseId": "resp-native",
        "memoryHttpStatus": 403, "attempts": 2,
        "tokenLogged": False, "memoryModified": False,
    }


def test_workload_probe_result_requires_both_positive_and_negative_controls():
    result = passing_result()
    assert probe.validate_result("cli log\n" + probe.MARKER + json.dumps(result)) == result


@pytest.mark.parametrize("change", [
    {"invocationHttpStatus": 403}, {"memoryHttpStatus": 200},
    {"memoryHttpStatus": 404}, {"responseId": ""}, {"responseId": None},
    {"tokenLogged": True}, {"memoryModified": True},
])
def test_incomplete_or_unsafe_control_fails(change):
    with pytest.raises(RuntimeError):
        probe.validate_result(probe.MARKER + json.dumps(passing_result() | change))


@pytest.mark.parametrize("stdout", ["", "success", probe.MARKER + "{}\n" + probe.MARKER + "{}"])
def test_missing_or_duplicate_probe_result_fails(stdout):
    with pytest.raises(RuntimeError):
        probe.validate_result(stdout)


def test_probe_runs_inside_actual_reviewer_and_persists_safe_evidence(monkeypatch, tmp_path):
    observed = []
    monkeypatch.setattr(probe.shutil, "which", lambda _: "/usr/bin/az")

    def run(command, **kwargs):
        observed.append(command)
        assert kwargs["check"] and kwargs["timeout"] == 1200
        return SimpleNamespace(stdout=probe.MARKER + json.dumps(passing_result()))

    monkeypatch.setattr(probe.subprocess, "run", run)
    output = tmp_path / "reviewer-access.json"
    args = SimpleNamespace(app="reviewer-staging", resource_group="rg-demo",
                           subscription="subscription-id", output=output)
    assert probe.verify_access(args) == passing_result()
    assert observed[0][:4] == ["/usr/bin/az", "containerapp", "exec", "--name"]
    assert "reviewer-staging" in observed[0]
    assert json.loads(output.read_text()) == passing_result()


def test_both_release_environments_gate_on_actual_reviewer_identity():
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github" / "workflows" / "deploy-and-evaluate.yml").read_text()
    assert workflow.count("python eval/verify_reviewer_foundry_access.py") == 2
    assert 'reviewer-access-staging.json' in workflow
    assert 'reviewer-access-production.json' in workflow
