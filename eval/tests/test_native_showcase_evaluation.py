"""Offline checks for actual native request shapes, measured controls, and safety gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_showcase_evaluation as showcase  # noqa: E402


@pytest.fixture
def native_clients(tmp_path):
    project, client = MagicMock(), MagicMock()
    evaluator = {
        "name": "builtin.retrieval", "version": "15", "evaluator_type": "builtin",
    }
    project.beta.evaluators.list_versions.return_value = [
        SimpleNamespace(version="15", as_dict=lambda: evaluator)
    ]
    client.evals.create.return_value = SimpleNamespace(id="eval-native")
    run = SimpleNamespace(
        id="evalrun-native", status="completed",
        model_dump=lambda **kwargs: {"id": "evalrun-native", "status": "completed"},
    )
    client.evals.runs.create.return_value = run
    items = [
        {
            "status": "completed",
            "datasource_item": {"item": {"variant": variant}},
            "results": [{"name": "retrieval", "score": score, "passed": score >= 3}],
        }
        for variant, score in [("relevant", 5), ("irrelevant", 1)]
    ]
    client.evals.runs.output_items.list.return_value = [
        SimpleNamespace(model_dump=lambda value=value, **kwargs: value) for value in items
    ]
    args = SimpleNamespace(
        evaluator_version="15", source_revision="a" * 40,
        deployment="judge-existing", output_dir=tmp_path, timeout=30,
    )
    return project, client, args


@pytest.mark.parametrize("nested", [True, False])
def test_retrieval_calls_actual_versioned_builtin_and_compares_controls(native_clients, nested):
    project, client, args = native_clients
    if not nested:
        items = client.evals.runs.output_items.list.return_value
        for item in items:
            value = item.model_dump()
            value["datasource_item"] = value["datasource_item"]["item"]
    result = showcase.retrieval_comparison(project, client, args)
    assert result["comparison"]["passed"]
    assert result["comparison"]["scores"] == {"relevant": 5, "irrelevant": 1}
    from azure.ai.projects.models import EvaluatorType

    project.beta.evaluators.list_versions.assert_called_once_with(
        "builtin.retrieval", type=EvaluatorType.BUILT_IN
    )
    criterion = client.evals.create.call_args.kwargs["testing_criteria"][0]
    assert criterion["evaluator_version"] == "15"
    assert criterion["data_mapping"] == {"query": "{{item.query}}", "context": "{{item.context}}"}
    submitted = client.evals.runs.create.call_args.kwargs["data_source"]["source"]["content"]
    assert {row["item"]["variant"] for row in submitted} == {"relevant", "irrelevant"}
    identity = json.loads((args.output_dir / "run-identity.json").read_text())
    assert identity["scenario"] == "synthetic-retrieval-controls-not-hosted-agent-regression"
    assert identity["source_revision"] == args.source_revision
    assert len(identity["dataset_sha256"]) == 64


@pytest.fixture
def grounding_clients(native_clients):
    project, client, args = native_clients
    args.evaluator_version = "18"
    args.grounding_evaluator = "groundedness"
    evaluator = {"name": "builtin.groundedness", "version": "18", "evaluator_type": "builtin"}
    project.beta.evaluators.list_versions.return_value = [
        SimpleNamespace(version="18", as_dict=lambda: evaluator),
    ]
    for variant in ["baseline", "candidate"]:
        answer = "Scopes authorize actions." if variant == "baseline" else "Scopes do not authorize access."
        native = {
            "id": f"resp-{variant}", "status": "completed", "model": "same-existing-model",
            "instructions": variant + " instructions", "output": [
                {"type": "file_search_call", "status": "completed",
                 "queries": [variant + " rewritten retrieval query"], "results": [{
                     "file_id": "assistant-synthetic", "filename": "FSI-PRIVACY-FR.txt",
                     "text": "SYNTHETIC TRAINING ONLY | FSI-PRIVACY-FR | version 2\n"
                             "Scopes do not authorize access.",
                 }]},
                {"type": "message", "content": [{
                    "type": "output_text", "text": answer,
                    "annotations": [{"type": "file_citation", "file_id": "assistant-synthetic"}],
                }]},
            ],
        }
        path = args.output_dir / f"{variant}.json"
        showcase.write_json(path, {
            "service": "Native Foundry File Search (not Foundry IQ)", "synthetic": True,
            "scenario": "privacy", "language": "fr", "response_id": native["id"],
            "answer": answer, "native_response": native,
        })
        setattr(args, variant + "_results", path)
    client.responses.input_items.list.return_value = [SimpleNamespace(model_dump=lambda **kw: {
        "role": "user", "content": [{"type": "input_text", "text": "Do scope keys authorize access?"}],
    })]
    client.evals.runs.output_items.list.return_value = [
        SimpleNamespace(model_dump=lambda variant=variant, score=score, **kw: {
            "status": "completed", "datasource_item": {"variant": variant},
            "results": [{"name": "groundedness", "score": score}],
        }) for variant, score in [("baseline", 1), ("candidate", 5)]
    ]
    return project, client, args


def test_grounding_comparison_uses_native_inputs_not_rewritten_retrieval_queries(grounding_clients):
    project, client, args = grounding_clients
    result = showcase.grounding_comparison(project, client, args)
    assert result["comparison"]["scores"] == {"baseline": 1, "candidate": 5}
    assert result["comparison"]["passed"]
    assert "not a hosted-agent" in result["comparison"]["scope"]
    criterion = client.evals.create.call_args.kwargs["testing_criteria"][0]
    assert criterion["evaluator_name"] == "builtin.groundedness"
    assert criterion["evaluator_version"] == "18"
    assert criterion["data_mapping"]["response"] == "{{item.response}}"
    submitted = client.evals.runs.create.call_args.kwargs["data_source"]["source"]["content"]
    assert len({row["item"]["query"] for row in submitted}) == 1
    assert len({row["item"]["retrieval_queries"] for row in submitted}) == 2
    assert all(len(row["item"]["native_input_sha256"]) == 64 for row in submitted)


def test_grounding_comparison_refuses_missing_native_inputs_before_evaluation(grounding_clients):
    project, client, args = grounding_clients
    client.responses.input_items.list.return_value = []
    with pytest.raises(ValueError, match="native user input"):
        showcase.grounding_comparison(project, client, args)
    client.evals.create.assert_not_called()


def test_grounding_comparison_rejects_different_actual_user_questions(grounding_clients):
    project, client, args = grounding_clients
    client.responses.input_items.list.side_effect = [
        [SimpleNamespace(model_dump=lambda text=text, **kw: {
            "role": "user", "content": [{"type": "input_text", "text": text}],
        })] for text in ["question one", "question two"]
    ]
    with pytest.raises(ValueError, match="same question"):
        showcase.grounding_comparison(project, client, args)
    client.evals.create.assert_not_called()


def test_grounding_comparison_does_not_claim_improvement_when_judge_disagrees(grounding_clients):
    project, client, args = grounding_clients
    client.evals.runs.output_items.list.return_value[0] = SimpleNamespace(model_dump=lambda **kw: {
        "status": "completed", "datasource_item": {"variant": "baseline"},
        "results": [{"name": "groundedness", "score": 4}],
    })
    with pytest.raises(RuntimeError, match="did not verify"):
        showcase.grounding_comparison(project, client, args)
    assert json.loads((args.output_dir / "comparison.json").read_text())["passed"] is False


def test_native_service_grounding_uses_binary_scores_and_no_model_initialization(grounding_clients):
    project, client, args = grounding_clients
    args.grounding_evaluator, args.evaluator_version, args.deployment = "groundedness_pro", "8", None
    evaluator = {"name": "builtin.groundedness_pro", "version": "8", "evaluator_type": "builtin"}
    project.beta.evaluators.list_versions.return_value = [
        SimpleNamespace(version="8", as_dict=lambda: evaluator),
    ]
    client.evals.runs.output_items.list.return_value = [
        SimpleNamespace(model_dump=lambda variant=variant, score=score, **kw: {
            "status": "completed", "datasource_item": {"variant": variant},
            "results": [{"name": "groundedness_pro", "score": score}],
        }) for variant, score in [("baseline", 0.0), ("candidate", 1.0)]
    ]
    result = showcase.grounding_comparison(project, client, args)
    assert result["comparison"]["scores"] == {"baseline": False, "candidate": True}
    assert result["comparison"]["passed"] is True
    assert result["judge_deployment"] is None
    criterion = client.evals.create.call_args.kwargs["testing_criteria"][0]
    assert criterion["initialization_parameters"] == {}
    assert criterion["evaluator_name"] == "builtin.groundedness_pro"


@pytest.mark.parametrize("score", [None, "1", 0.5, 5, float("nan")])
def test_native_binary_grounding_rejects_non_binary_results(score):
    with pytest.raises(RuntimeError, match="binary score"):
        showcase.control_scores([{
            "datasource_item": {"variant": "baseline"},
            "results": [{"name": "groundedness_pro", "score": score}],
        }], "groundedness_pro", {"baseline", "candidate"})


def test_retrieval_fails_when_judge_does_not_distinguish_controls(native_clients):
    project, client, args = native_clients
    client.evals.runs.output_items.list.return_value[1] = SimpleNamespace(
        model_dump=lambda **kwargs: {
            "status": "completed", "datasource_item": {"item": {"variant": "irrelevant"}},
            "results": [{"name": "retrieval", "score": 4}],
        }
    )
    with pytest.raises(RuntimeError, match="did not distinguish"):
        showcase.retrieval_comparison(project, client, args)
    assert not json.loads((args.output_dir / "comparison.json").read_text())["passed"]


@pytest.mark.parametrize("score", [None, True, 0, 6, float("nan"), "5"])
def test_retrieval_rejects_missing_or_invalid_scores(native_clients, score):
    project, client, args = native_clients
    client.evals.runs.output_items.list.return_value[0] = SimpleNamespace(
        model_dump=lambda **kwargs: {
            "status": "completed", "datasource_item": {"item": {"variant": "relevant"}},
            "results": [{"name": "retrieval", "score": score}],
        }
    )
    with pytest.raises(RuntimeError, match="valid 1-to-5"):
        showcase.retrieval_comparison(project, client, args)


def test_builtin_catalog_does_not_silently_use_custom_or_other_versions(native_clients):
    project, _, _ = native_clients
    with pytest.raises(ValueError, match="not available"):
        showcase.builtin(project, "builtin.retrieval", "999")
    project.beta.evaluators.list_versions.return_value[0].as_dict = lambda: {
        "evaluator_type": "custom"
    }
    with pytest.raises(ValueError, match="not a Microsoft built-in"):
        showcase.builtin(project, "builtin.retrieval", "15")


def test_run_timeout_cancels_instead_of_leaving_an_unbounded_job(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(showcase.time, "monotonic", iter([0, 31]).__next__)
    with pytest.raises(TimeoutError, match="cancellation requested"):
        showcase.wait_for_run(client, "eval-id", SimpleNamespace(id="run-id", status="running"), 30)
    client.evals.runs.cancel.assert_called_once_with(eval_id="eval-id", run_id="run-id")


def test_red_team_requires_exact_reviewed_taxonomy_before_any_run(native_clients):
    project, client, args = native_clients
    args.taxonomy = "synthetic-policy"
    args.approved_taxonomy_sha256 = "0" * 64
    project.beta.evaluation_taxonomies.get.return_value.as_dict.return_value = {
        "id": "taxonomy-1", "taxonomy_categories": [{"name": "premature-disclosure"}],
    }
    with pytest.raises(ValueError, match="not reviewed"):
        showcase.red_team(project, client, args)
    client.evals.create.assert_not_called()


def test_red_team_pins_target_and_bounded_native_generation(native_clients):
    project, client, args = native_clients
    args.agent, args.agent_version, args.taxonomy, args.turns = "synthetic-agent", "2", "policy", 1
    taxonomy = {
        "id": "taxonomy-1",
        "taxonomy_input": {
            "type": "agent", "target": {"type": "azure_ai_agent", "name": args.agent, "version": "2"},
            "risk_categories": ["ProhibitedActions"],
        },
        "taxonomy_categories": [{"name": "premature-disclosure"}],
    }
    project.beta.evaluation_taxonomies.get.return_value.as_dict.return_value = taxonomy
    args.approved_taxonomy_sha256 = showcase.taxonomy_digest(taxonomy)
    result = showcase.red_team(project, client, args)
    source = client.evals.runs.create.call_args.kwargs["data_source"]
    assert source["type"] == "azure_ai_red_team"
    assert source["target"] == taxonomy["taxonomy_input"]["target"]
    assert source["item_generation_params"]["num_turns"] == 1
    assert source["item_generation_params"]["attack_strategies"] == ["Base64"]
    assert result["reviewed_taxonomy_sha256"] == args.approved_taxonomy_sha256


@pytest.mark.parametrize("operation", ["anything", "'; delete", "a" * 31, "A" * 32])
def test_trace_query_rejects_non_trace_ids(operation):
    with pytest.raises(ValueError, match="actual 32-character"):
        showcase.trace_query(operation)


def test_trace_query_uses_native_tables_and_no_prompt_or_payload_columns():
    query = showcase.trace_query("a" * 32)
    assert "AppDependencies, AppRequests" in query
    assert "take 200" in query and "ago(24h)" in query
    assert "policy_sha256" in query
    assert "Messages" not in query and "gen_ai.input" not in query


def test_evidence_is_immutable(tmp_path):
    path = tmp_path / "identity.json"
    showcase.write_json(path, {"id": "native-run"})
    with pytest.raises(FileExistsError):
        showcase.write_json(path, {"id": "replacement"})


def test_taxonomy_review_hash_is_stable_but_sensitive_to_content():
    first, reordered = {"a": 1, "b": 2}, {"b": 2, "a": 1}
    assert showcase.taxonomy_digest(first) == showcase.taxonomy_digest(reordered)
    assert showcase.taxonomy_digest(first) != showcase.taxonomy_digest({"a": 2, "b": 2})


@pytest.mark.parametrize("case", ["CASE-SYN-001", "real-person@example.test"])
def test_trace_to_dataset_requires_recorded_synthetic_case_and_policy(tmp_path, case):
    operation = "a" * 32
    trace_file = tmp_path / "trace.json"
    trace_file.write_text(json.dumps({"tables": [{
        "columns": [{"name": name} for name in [
            "OperationId", "execution_kind", "case_id", "policy_sha256",
        ]],
        "rows": [[operation, "deterministic", case, "b" * 64]],
    }]}), encoding="utf-8")
    output = tmp_path / "dataset"
    output.mkdir()
    args = SimpleNamespace(
        trace_file=trace_file, operation_id=operation, source_revision="c" * 40, output_dir=output,
    )
    if case != "CASE-SYN-001":
        with pytest.raises(ValueError, match="exactly one synthetic case"):
            showcase.trace_dataset(args)
        assert not list(output.iterdir())
    else:
        result = showcase.trace_dataset(args)
        assert case in result["data"][0]["query"]
        lineage = result["data"][0]["lineage"]
        assert lineage["operation_id"] == operation
        assert lineage["policy_sha256"] == "b" * 64
        assert lineage["replay_kind"] == "synthetic-case-replay-not-original-user-prompt"


def test_cli_rejects_credential_exfiltration_endpoint_before_authentication(tmp_path):
    with pytest.raises(SystemExit, match="2"):
        showcase.main([
            "catalog", "--endpoint", "https://attacker.test/api/projects/p",
            "--output-dir", str(tmp_path / "out"),
        ])


@pytest.mark.parametrize("mismatch", [None, "dataset", "same-run", "failed-run", "runner-hash"])
def test_comparison_requires_two_completed_native_runs_and_matching_configuration(
    native_clients, tmp_path, mismatch,
):
    project, client, args = native_clients
    baseline = showcase.retrieval_comparison(project, client, args)
    candidate = json.loads(json.dumps(baseline))
    candidate["run_id"] = "evalrun-second"
    if mismatch == "dataset":
        candidate["dataset_sha256"] = "different"
    elif mismatch == "same-run":
        candidate["run_id"] = baseline["run_id"]
    elif mismatch == "failed-run":
        candidate["run"]["status"] = "failed"
    elif mismatch == "runner-hash":
        candidate.pop("runner_sha256")
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_text(json.dumps(baseline), encoding="utf-8")
    second.write_text(json.dumps(candidate), encoding="utf-8")
    output = tmp_path / "compare"
    output.mkdir()
    args = SimpleNamespace(baseline_results=first, candidate_results=second, output_dir=output)
    if mismatch:
        with pytest.raises(ValueError):
            showcase.compare_runs(args)
    else:
        result = showcase.compare_runs(args)
        assert result["score_delta"] == {"relevant": 0, "irrelevant": 0}
        assert result["scope"] == "controlled-evaluator-repeatability-not-hosted-agent-improvement"
