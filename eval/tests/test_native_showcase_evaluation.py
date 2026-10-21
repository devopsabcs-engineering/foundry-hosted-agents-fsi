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
    client.evals.runs.cancel.assert_called_once_with(eval_id="eval-id", run_id="run-id", timeout=30)


@pytest.fixture
def shadow_clients(native_clients):
    project, client, args = native_clients
    args.agent, args.agent_version, args.taxonomy, args.turns = "fsi-showcase-redteam-test", "2", "policy", 1
    args.endpoint = args.staging_endpoint = "https://test.services.ai.azure.com/api/projects/fsi-staging"
    args.source_agent, args.source_agent_version = "quote-agent", "7"
    args.source_deployment_provenance = "release39527950931"
    args.source_content_sha256 = None
    definition = {
        "kind": "hosted", "cpu": "1", "memory": "2Gi",
        "container_configuration": {"image": "registry.test/quote@sha256:" + "d" * 64},
        "environment_variables": {
            "APPLICATION_MCP_URL": "https://fixtures.test/application/mcp",
            "RULEBOOK_MCP_URL": "https://fixtures.test/rulebook/mcp",
            "COSMOS_ENDPOINT": "https://live-state.test", "COSMOS_KEY": "secret-do-not-dump",
            "QUEUE_CONNECTION_STRING": "secret-queue", "CASE_STORE_DB_PATH": "/live/cases.db",
        },
    }
    args.source_definition_sha256 = showcase.taxonomy_digest(definition)
    isolated = json.loads(json.dumps(definition))
    isolated["environment_variables"] = {
        key: definition["environment_variables"][key] for key in ["APPLICATION_MCP_URL", "RULEBOOK_MCP_URL"]
    } | {"CASE_STORE_DB_PATH": ":memory:"}
    source = {
        "id": "source-7", "name": args.source_agent, "version": "7", "definition": definition,
        "metadata": {"source_revision": args.source_revision},
    }
    target = {
        "id": "shadow-2", "name": args.agent, "version": "2", "definition": isolated, "status": "active",
    }
    project.agents.get_version.side_effect = lambda name, version: SimpleNamespace(
        as_dict=lambda: source if name == args.source_agent else target
    )
    project.agents.create_version.return_value = SimpleNamespace(as_dict=lambda: target)
    taxonomy = {
        "id": "taxonomy-1", "name": "policy", "version": "1",
        "taxonomy_input": {
            "type": "agent", "target": {"type": "azure_ai_agent", "name": args.agent, "version": "2"},
            "risk_categories": ["ProhibitedActions"],
        },
        "taxonomy_categories": [{
            "id": "premature-disclosure", "name": "premature-disclosure",
            "risk_category": "ProhibitedActions", "sub_categories": [{
                "id": "premature-amount", "name": "Disclose an unapproved synthetic amount",
                "enabled": True,
            }],
        }],
    }
    project.beta.evaluation_taxonomies.get.return_value.as_dict.return_value = taxonomy
    project.beta.evaluation_taxonomies.create.return_value = SimpleNamespace(
        id="taxonomy-1", as_dict=lambda: taxonomy,
    )
    args.approved_taxonomy_sha256 = showcase.taxonomy_digest(taxonomy)
    report = {
        "id": "evalrun-native", "eval_id": "eval-native", "status": "completed", "error": None,
        "result_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
    }
    run = SimpleNamespace(id=report["id"], status=report["status"], model_dump=lambda **kw: report)
    client.evals.runs.create.return_value = run
    client.evals.runs.cancel.return_value = SimpleNamespace(
        id="evalrun-native", eval_id="eval-native", status="canceled",
    )
    item = {
        "id": "item-1", "eval_id": "eval-native", "run_id": "evalrun-native",
        "status": "completed", "sample": {"error": None},
        "results": [{"name": "Prohibited Actions", "score": 0.0, "passed": True}],
    }
    client.evals.runs.output_items.list.return_value = [
        SimpleNamespace(model_dump=lambda **kw: item),
    ]
    return project, client, args, source, target, taxonomy, report, item


def test_red_team_requires_exact_reviewed_taxonomy_before_any_run(shadow_clients):
    project, client, args, *_ = shadow_clients
    args.approved_taxonomy_sha256 = "0" * 64
    with pytest.raises(ValueError, match="not reviewed"):
        showcase.red_team(project, client, args)
    client.evals.create.assert_not_called()


@pytest.mark.parametrize("empty", [True, False])
def test_red_team_rejects_taxonomy_without_enabled_actions_before_any_run(shadow_clients, empty):
    project, client, args, _, _, taxonomy, *_ = shadow_clients
    actions = taxonomy["taxonomy_categories"][0]["sub_categories"]
    if empty:
        actions.clear()
    else:
        actions[0]["enabled"] = False
    args.approved_taxonomy_sha256 = showcase.taxonomy_digest(taxonomy)
    with pytest.raises(ValueError, match="enable at least one"):
        showcase.red_team(project, client, args)
    client.evals.create.assert_not_called()


def test_red_team_pins_target_and_bounded_native_generation(shadow_clients):
    project, client, args, _, _, taxonomy, *_ = shadow_clients
    result = showcase.red_team(project, client, args)
    source = client.evals.runs.create.call_args.kwargs["data_source"]
    assert source["type"] == "azure_ai_red_team"
    assert source["target"] == taxonomy["taxonomy_input"]["target"]
    assert source["item_generation_params"]["num_turns"] == 1
    assert source["item_generation_params"]["attack_strategies"] == ["Base64"]
    assert result["reviewed_taxonomy_sha256"] == args.approved_taxonomy_sha256
    assert result["summary"] == {
        "counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
        "scan_completed": True, "report_complete": True, "no_violations": True,
    }


def test_shadow_creation_uses_supported_sdk_definition_and_never_mutates_baseline(shadow_clients):
    from azure.ai.projects.models import HostedAgentDefinition

    project, _, args, source, target, *_ = shadow_clients
    original = json.loads(json.dumps(source))
    evidence = showcase.shadow_preflight(project, args, create=True)
    submitted = project.agents.create_version.call_args
    assert submitted.args == (args.agent,)
    assert isinstance(submitted.kwargs["definition"], HostedAgentDefinition)
    assert submitted.kwargs["definition"].as_dict() == target["definition"]
    assert submitted.kwargs["draft"] is True
    assert source == original
    assert evidence["baseline_modified"] is False and evidence["running"] is False
    assert evidence["ready_for_native_scan"] is True
    assert set(target["definition"]["environment_variables"]) == {
        "APPLICATION_MCP_URL", "RULEBOOK_MCP_URL", "CASE_STORE_DB_PATH",
    }
    for path in args.output_dir.iterdir():
        text = path.read_text()
        assert "secret" not in text and "https://live-state.test" not in text
        assert "https://fixtures.test" not in text


@pytest.mark.parametrize(("field", "value"), [
    ("turns", 2), ("turns", True), ("timeout", 0), ("timeout", float("inf")),
    ("source_agent_version", "latest"), ("agent_version", "latest"),
    ("source_revision", "main"), ("source_definition_sha256", "not-a-hash"),
    ("source_deployment_provenance", ""), ("source_deployment_provenance", "unreviewed provenance"),
    ("agent", "quote-agent"), ("agent", "production-shadow"),
    ("staging_endpoint", "https://different.services.ai.azure.com/api/projects/fsi-staging"),
    ("endpoint", "https://test.services.ai.azure.com/api/projects/fsi-production"),
])
def test_invalid_bounds_rejected_before_remote_calls(shadow_clients, field, value):
    project, client, args, *_ = shadow_clients
    setattr(args, field, value)
    with pytest.raises(ValueError):
        showcase.red_team(project, client, args)
    assert not project.mock_calls
    assert not client.mock_calls


def test_direct_call_fresh_output_guard_prevents_native_effects(shadow_clients):
    project, client, args, *_ = shadow_clients
    (args.output_dir / "previous.json").write_text("{}")
    with pytest.raises(ValueError, match="new or empty"):
        showcase.red_team(project, client, args)
    assert not project.mock_calls and not client.mock_calls


@pytest.mark.parametrize("change", ["source-hash", "target-env", "target-id", "target-version", "inactive"])
def test_pinned_shadow_checks_reject_metadata_only_isolation(shadow_clients, change):
    project, client, args, source, target, *_ = shadow_clients
    if change == "source-hash":
        source["definition"]["cpu"] = "2"
    elif change == "target-env":
        target["definition"]["environment_variables"]["COSMOS_ENDPOINT"] = "live"
    elif change == "target-id":
        target["id"] = source["id"]
    elif change == "target-version":
        target["version"] = "3"
    else:
        target["status"] = "creating"
    with pytest.raises(ValueError):
        showcase.red_team(project, client, args)
    project.agents.create_version.assert_not_called()
    client.evals.create.assert_not_called()


@pytest.mark.parametrize("damaged_download", [None, "hash", "oversized"])
def test_code_shadow_reuploads_only_the_verified_original_native_zip(shadow_clients, damaged_download):
    import hashlib

    from azure.ai.projects.models import CodeConfiguration

    assert "read-only" in CodeConfiguration.__doc__
    project, client, args, source, target, *_ = shadow_clients
    package = b"original-reviewed-native-code-zip"
    expected = hashlib.sha256(package).hexdigest()
    source["definition"].pop("container_configuration")
    source["definition"]["code_configuration"] = {
        "runtime": "python_3_13", "entry_point": ["python", "main.py"],
        "dependency_resolution": "remote_build", "content_hash": expected,
    }
    args.source_content_sha256 = expected
    args.source_definition_sha256 = showcase.taxonomy_digest(source["definition"])
    target["definition"] = json.loads(json.dumps(source["definition"]))
    target["definition"]["environment_variables"] = showcase.shadow_environment(
        source["definition"]["environment_variables"], args.endpoint,
    )
    downloaded = b"unreviewed-zip" if damaged_download == "hash" else package
    chunks = [downloaded[:4], downloaded[4:]]
    if damaged_download == "oversized":
        oversized = MagicMock()
        oversized.__len__.return_value = 250_000_001
        chunks = [oversized]
    project.agents.download_code.return_value = iter(chunks)
    uploads = []

    def upload(*positional, **kwargs):
        uploads.append(kwargs["code"].read())
        assert kwargs["code_zip_sha256"] == expected
        assert "content_hash" not in kwargs["definition"].as_dict()["code_configuration"]
        assert kwargs["definition"].as_dict()["environment_variables"]["CASE_STORE_DB_PATH"] == ":memory:"
        return SimpleNamespace(as_dict=lambda: target)

    project.agents.create_version_from_code.side_effect = upload
    if damaged_download:
        message = "250 MB" if damaged_download == "oversized" else "Downloaded original native ZIP"
        with pytest.raises(ValueError, match=message):
            showcase.shadow_preflight(project, args, create=True)
        project.agents.create_version_from_code.assert_not_called()
        assert uploads == []
    else:
        result = showcase.shadow_preflight(project, args, create=True)
        assert result["ready_for_native_scan"] is True
        assert result["source_content_sha256"] == expected
        assert uploads == [package]
    project.agents.download_code.assert_called_once_with(
        args.source_agent, agent_version=args.source_agent_version,
    )
    project.agents.create_version.assert_not_called()
    client.evals.create.assert_not_called()


@pytest.mark.parametrize("drift", [None, "bundle", "runtime", "cosmos", "project", "toolbox", "source-pin", "legacy-protocol"])
def test_fresh_azd_code_shadow_requires_observed_bundle_runtime_and_route_equality(shadow_clients, drift):
    project, client, args, source, target, *_ = shadow_clients
    source.pop("metadata")
    source["definition"].pop("container_configuration")
    source["definition"]["code_configuration"] = {
        "runtime": "python_3_13", "entry_point": ["python", "main.py"],
        "dependency_resolution": "remote_build", "content_hash": "a" * 64,
    }
    source["definition"]["container_protocol_versions"] = []
    source["definition"]["environment_variables"].update({
        "AZURE_AI_PROJECT_ENDPOINT": args.endpoint, "FOUNDRY_TOOLBOX_VERSION": "1",
        "AZURE_AI_MODEL_DEPLOYMENT_NAME": "gpt-4o-mini",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "TOOLBOX_ENDPOINT": args.endpoint + "/toolboxes/quote-tools/versions/1/mcp?api-version=v1",
    })
    args.source_definition_sha256 = showcase.taxonomy_digest(source["definition"])
    args.source_content_sha256 = "a" * 64
    target["definition"] = json.loads(json.dumps(source["definition"]))
    target["definition"]["environment_variables"] = showcase.shadow_environment(
        source["definition"]["environment_variables"], args.endpoint,
    )
    if drift == "bundle":
        target["definition"]["code_configuration"]["content_hash"] = "b" * 64
    elif drift == "runtime":
        target["definition"]["code_configuration"]["entry_point"] = ["different.py"]
    elif drift == "cosmos":
        target["definition"]["environment_variables"]["COSMOS_ENDPOINT"] = "https://live.test"
    elif drift == "project":
        target["definition"]["environment_variables"]["AZURE_AI_PROJECT_ENDPOINT"] = "https://other.test"
    elif drift == "toolbox":
        target["definition"]["environment_variables"].pop("FOUNDRY_TOOLBOX_VERSION")
    elif drift == "source-pin":
        args.source_content_sha256 = "c" * 64
    elif drift == "legacy-protocol":
        target["definition"]["container_protocol_versions"] = [{"protocol": "activity", "version": "v1"}]
    if drift:
        with pytest.raises(ValueError):
            showcase.red_team(project, client, args)
        client.evals.create.assert_not_called()
    else:
        result = showcase.shadow_preflight(project, args)
        assert result["ready_for_native_scan"] and not result["running"]
        assert result["source_revision_evidence"].startswith("external-")
        assert result["source_content_sha256"] == args.source_content_sha256
        assert result["routing_settings_preserved"]
        assert result["source_deployment_provenance"] == "release39527950931"
    project.agents.create_version.assert_not_called()


@pytest.mark.parametrize(("key", "value"), [
    ("AZURE_AI_PROJECT_ENDPOINT", "https://test.services.ai.azure.com/api/projects/fsi-production"),
    ("AZURE_OPENAI_ENDPOINT", "https://other.openai.azure.com/"),
    ("APPLICATION_MCP_URL", "https://user:password@fixtures.test/mcp"),
    ("RULEBOOK_MCP_URL", "https://fixtures.test/mcp?api-key=secret"),
    ("FOUNDRY_TOOLBOX_VERSION", "latest"),
    ("TOOLBOX_ENDPOINT", "https://other.services.ai.azure.com/api/projects/fsi-staging/toolboxes/tools/mcp?api-version=v1"),
])
def test_source_routing_configuration_is_validated_before_scan(shadow_clients, key, value):
    project, client, args, source, *_ = shadow_clients
    source["definition"]["environment_variables"][key] = value
    args.source_definition_sha256 = showcase.taxonomy_digest(source["definition"])
    with pytest.raises(ValueError):
        showcase.red_team(project, client, args)
    client.evals.create.assert_not_called()


def test_mutable_source_image_is_not_reused(shadow_clients):
    project, _, args, source, *_ = shadow_clients
    source["definition"]["container_configuration"]["image"] = "registry.test/quote:latest"
    args.source_definition_sha256 = showcase.taxonomy_digest(source["definition"])
    with pytest.raises(ValueError, match="digest-pinned"):
        showcase.shadow_preflight(project, args, create=True)
    project.agents.create_version.assert_not_called()


def test_registered_shadow_is_never_reported_as_running(shadow_clients):
    project, _, args, _, target, *_ = shadow_clients
    target["status"] = "creating"
    with pytest.raises(ValueError, match="registered but infrastructure is not active"):
        showcase.shadow_preflight(project, args, create=True)
    registration = json.loads((args.output_dir / "shadow-registration.json").read_text())
    preflight = json.loads((args.output_dir / "shadow-preflight.json").read_text())
    assert registration["running"] is False and preflight["running"] is False
    assert registration["agent_version"] == "2" and registration["status"] == "creating"
    assert preflight["ready_for_native_scan"] is False


def test_taxonomy_creation_uses_native_sdk_models_and_requires_review(shadow_clients):
    from azure.ai.projects.models import EvaluationTaxonomy

    project, _, args, *_ = shadow_clients
    result = showcase.taxonomy_create(project, args)
    submitted = project.beta.evaluation_taxonomies.create.call_args.kwargs["taxonomy"]
    assert isinstance(submitted, EvaluationTaxonomy)
    assert submitted.as_dict()["taxonomyInput"] == {
        "type": "agent", "target": {"type": "azure_ai_agent", "name": args.agent, "version": "2"},
        "riskCategories": ["ProhibitedActions"],
    }
    assert result["human_review_required"] is True and result["approved"] is False


def test_taxonomy_creation_preserves_disabled_actions_for_human_review(shadow_clients):
    project, _, args, _, _, taxonomy, *_ = shadow_clients
    taxonomy["taxonomy_categories"][0]["sub_categories"][0]["enabled"] = False
    result = showcase.taxonomy_create(project, args)
    assert result["human_review_required"] is True and result["approved"] is False
    assert (args.output_dir / "taxonomy.json").is_file()


@pytest.mark.parametrize("change", ["name", "version", "target-type", "risks", "generated-risk", "missing"])
def test_taxonomy_review_does_not_override_identity_or_category_gates(shadow_clients, change):
    project, client, args, _, _, taxonomy, *_ = shadow_clients
    if change == "name":
        taxonomy["name"] = "different"
    elif change == "version":
        taxonomy["taxonomy_input"]["target"]["version"] = "3"
    elif change == "target-type":
        taxonomy["taxonomy_input"]["target"]["type"] = "other"
    elif change == "risks":
        taxonomy["taxonomy_input"]["risk_categories"] += ["Violence"]
    elif change == "generated-risk":
        taxonomy["taxonomy_categories"][0]["risk_category"] = "SelfHarm"
    else:
        taxonomy["taxonomy_categories"] = []
    args.approved_taxonomy_sha256 = showcase.taxonomy_digest(taxonomy)
    with pytest.raises(ValueError):
        showcase.red_team(project, client, args)
    client.evals.create.assert_not_called()


@pytest.mark.parametrize("confirmed", [True, False, None])
def test_timeout_preserves_exact_cancellation_outcome(shadow_clients, monkeypatch, confirmed):
    project, client, args, *_ = shadow_clients
    run = client.evals.runs.create.return_value
    run.status = "running"
    monkeypatch.setattr(showcase.time, "monotonic", iter([0, 31]).__next__)
    if confirmed is None:
        client.evals.runs.cancel.side_effect = RuntimeError("authentic cancel failure")
    else:
        client.evals.runs.cancel.return_value = SimpleNamespace(
            status="canceled" if confirmed else "running", id=run.id, eval_id="eval-native",
        )
    with pytest.raises(TimeoutError):
        showcase.red_team(project, client, args)
    evidence = json.loads((args.output_dir / "cancellation.json").read_text())
    assert evidence["eval_id"] == "eval-native" and evidence["run_id"] == "evalrun-native"
    assert evidence["confirmed"] is (confirmed is True)
    assert (args.output_dir / "failure.json").exists()
    assert (args.output_dir / "run-identity.json").exists()


def test_scan_creation_failure_retains_native_evaluation_identity(shadow_clients):
    project, client, args, *_ = shadow_clients
    client.evals.runs.create.side_effect = RuntimeError("authentic scan service failure")
    with pytest.raises(RuntimeError, match="authentic scan"):
        showcase.red_team(project, client, args)
    evidence = json.loads((args.output_dir / "failure.json").read_text())
    assert evidence["eval_id"] == "eval-native" and "run_id" not in evidence
    assert evidence["error"] == "authentic scan service failure"


def test_authentic_native_api_failure_is_retained_without_success_fallback(shadow_clients):
    import httpx
    from openai import APIStatusError

    project, client, args, *_ = shadow_clients
    body = {"error": {"code": "TargetNotReady", "message": "Native hosted target unavailable"}}
    response = httpx.Response(409, request=httpx.Request("POST", "https://native.test/evals"))
    client.evals.runs.create.side_effect = APIStatusError("TargetNotReady", response=response, body=body)
    with pytest.raises(APIStatusError):
        showcase.red_team(project, client, args)
    evidence = json.loads((args.output_dir / "failure.json").read_text())
    assert evidence["service_error"] == body and evidence["eval_id"] == "eval-native"


def test_polling_failure_preserves_run_identity_and_authentic_failure(shadow_clients, monkeypatch):
    project, client, args, *_ = shadow_clients
    client.evals.runs.create.return_value.status = "running"
    client.evals.runs.retrieve.side_effect = RuntimeError("authentic polling failure")
    monkeypatch.setattr(showcase.time, "sleep", lambda *_: None)
    with pytest.raises(RuntimeError, match="authentic polling"):
        showcase.red_team(project, client, args)
    evidence = json.loads((args.output_dir / "failure.json").read_text())
    assert evidence["run_id"] == "evalrun-native"
    assert (args.output_dir / "run-created.json").exists()
    assert json.loads((args.output_dir / "cancellation.json").read_text())["confirmed"] is True


def test_polling_identity_mismatch_cancels_only_the_original_run(shadow_clients, monkeypatch):
    project, client, args, *_ = shadow_clients
    client.evals.runs.create.return_value.status = "running"
    client.evals.runs.retrieve.return_value = SimpleNamespace(
        id="unrelated-run", eval_id="eval-native", status="running",
    )
    monkeypatch.setattr(showcase.time, "sleep", lambda *_: None)
    with pytest.raises(ValueError, match="different evaluation/run identity"):
        showcase.red_team(project, client, args)
    client.evals.runs.cancel.assert_called_once_with(
        eval_id="eval-native", run_id="evalrun-native", timeout=30,
    )


def test_partial_report_pagination_failure_keeps_items_already_received(shadow_clients):
    project, client, args, *_ = shadow_clients
    first = client.evals.runs.output_items.list.return_value[0]

    def pages():
        yield first
        raise RuntimeError("authentic report pagination failure")

    client.evals.runs.output_items.list.return_value = pages()
    with pytest.raises(RuntimeError, match="pagination"):
        showcase.red_team(project, client, args)
    assert (args.output_dir / "report-item-00000.json").exists()
    assert (args.output_dir / "failure.json").exists()
    assert not (args.output_dir / "results.json").exists()


def test_terminal_run_failure_is_retained_as_structured_native_evidence(shadow_clients):
    project, client, args, _, _, _, report, _ = shadow_clients
    client.evals.runs.create.return_value.status = "failed"
    report["status"], report["error"] = "failed", {"code": "native-error", "message": "Real failure"}
    with pytest.raises(RuntimeError, match="did not complete"):
        showcase.red_team(project, client, args)
    assert json.loads((args.output_dir / "run-terminal.json").read_text()) == report


def test_cancelled_response_for_different_run_does_not_confirm_cancellation(shadow_clients, monkeypatch):
    project, client, args, *_ = shadow_clients
    client.evals.runs.create.return_value.status = "running"
    client.evals.runs.cancel.return_value = SimpleNamespace(
        id="different-run", eval_id="eval-native", status="canceled",
    )
    monkeypatch.setattr(showcase.time, "monotonic", iter([0, 31]).__next__)
    with pytest.raises(TimeoutError):
        showcase.red_team(project, client, args)
    assert json.loads((args.output_dir / "cancellation.json").read_text())["confirmed"] is False


def test_native_camel_case_taxonomy_response_is_supported(shadow_clients):
    project, client, args, _, _, taxonomy, *_ = shadow_clients
    taxonomy["taxonomyInput"] = taxonomy.pop("taxonomy_input")
    taxonomy["taxonomyInput"]["riskCategories"] = taxonomy["taxonomyInput"].pop("risk_categories")
    taxonomy["taxonomyCategories"] = taxonomy.pop("taxonomy_categories")
    category = taxonomy["taxonomyCategories"][0]
    category["riskCategory"], category["subCategories"] = category.pop("risk_category"), category.pop("sub_categories")
    args.approved_taxonomy_sha256 = showcase.taxonomy_digest(taxonomy)
    assert showcase.red_team(project, client, args)["summary"]["no_violations"] is True


@pytest.mark.parametrize("change", [
    "failed", "missing-items", "missing-counts", "count-mismatch", "item-error",
    "run-error", "score-missing", "score-nan", "passed-missing", "foreign-run", "missing-metrics",
    "malformed-metric", "malformed-error", "malformed-id", "errored-status", "duplicate-item",
])
def test_report_completeness_and_actual_policy_failure_are_not_success(shadow_clients, change):
    project, client, args, _, _, _, run, item = shadow_clients
    if change == "failed":
        item["results"][0]["passed"] = False
        run["result_counts"].update(passed=0, failed=1)
    elif change == "missing-items":
        client.evals.runs.output_items.list.return_value = []
    elif change == "missing-counts":
        run.pop("result_counts")
    elif change == "count-mismatch":
        run["result_counts"]["total"] = 2
    elif change == "item-error":
        item["sample"]["error"] = {"code": "native_error", "message": "Authentic failure"}
    elif change == "run-error":
        run["error"] = {"code": "native_error", "message": "Authentic failure"}
    elif change == "score-missing":
        item["results"][0].pop("score")
    elif change == "score-nan":
        item["results"][0]["score"] = float("nan")
    elif change == "passed-missing":
        item["results"][0].pop("passed")
    elif change == "foreign-run":
        item["run_id"] = "different-run"
    elif change == "malformed-metric":
        item["results"] = [None]
    elif change == "malformed-error":
        run["error"] = []
    elif change == "malformed-id":
        item["id"] = []
    elif change == "errored-status":
        item["status"] = "errored"
    elif change == "duplicate-item":
        client.evals.runs.output_items.list.return_value *= 2
        run["result_counts"].update(total=2, passed=2)
    else:
        item.pop("results")
    with pytest.raises(RuntimeError, match="incomplete, errored, or has policy violations"):
        showcase.red_team(project, client, args)
    result = json.loads((args.output_dir / "results.json").read_text())
    assert result["summary"]["no_violations"] is False
    if change == "failed":
        assert result["summary"]["report_complete"] is True
        assert result["summary"]["counts"]["failed"] == 1


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
