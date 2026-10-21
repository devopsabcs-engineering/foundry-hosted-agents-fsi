"""Offline native IQ protocol, isolation and evidence contracts."""

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import native_foundry_iq as iq  # noqa: E402

PROJECT = "https://existing-foundry.services.ai.azure.com/api/projects/synthetic-project"
PROJECT_ID = (
    "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/test/providers/"
    "Microsoft.CognitiveServices/accounts/existing-foundry/projects/synthetic-project"
)
SEARCH = "https://additive-showcase.search.windows.net"
SEARCH_ID = (
    "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/test/providers/"
    "Microsoft.Search/searchServices/additive-showcase"
)


@pytest.fixture
def native(tmp_path, monkeypatch):
    rest, project, client = Mock(), Mock(), Mock()
    companion = iq.FoundryIQ(rest, project, client, PROJECT, PROJECT_ID, SEARCH, SEARCH_ID)
    monkeypatch.setattr(companion, "preflight", Mock(return_value={"verified": True}))
    monkeypatch.setattr(companion.knowledge, "verify_corpus",
                        Mock(return_value={"verified_documents": 6}))
    fields = [{"name": name} for name in ("id", "title", "content", "language", "version", "sha256")]
    monkeypatch.setattr(companion.knowledge, "status", Mock(return_value={
        "indexes": {"fields": fields},
        "knowledgebases": {"knowledgeSources": [{"name": "fsi-showcase-source"}],
                          "retrievalReasoningEffort": {"kind": "minimal"}, "outputMode": "extractiveData"},
        "knowledgesources": {"kind": "searchIndex", "searchIndexParameters": {
            "searchIndexName": "fsi-showcase-index", "sourceDataFields": fields,
        }},
    }))
    project.agents.create_version.return_value = SimpleNamespace(version="1")
    rest.call.return_value = ({"properties": companion.connection_properties()}, {})
    return companion, rest, project, client, tmp_path / "binding.json"


def binding(native):
    companion, _, project, _, output = native
    value = companion.create("existing-mini", "a" * 40, output)
    project.agents.get_version.return_value = SimpleNamespace(
        definition=companion.definition("existing-mini"),
    )
    return value


def response(language="en", scenario="approval"):
    source = f"FSI-REVIEW-{language.upper()}"
    return {
        "id": "resp-native", "status": "completed", "output": [
            {"type": "mcp_call", "id": "mcp-native", "status": "completed",
             "name": iq.TOOL, "server_label": iq.LABEL,
             "output": json.dumps({"retrieved_text": f"{source} | version 1\nEmployee review."})},
            {"type": "message", "content": [{"type": "output_text", "text": (
                "OUT_OF_CORPUS" if scenario == "out-of-corpus" else f"Employee review [{source}]"
            )}]},
        ],
    }


def test_create_uses_actual_managed_identity_mcp_contract_and_pinned_evidence(native):
    companion, rest, project, client, output = native
    value = binding(native)
    assert json.loads(output.read_text()) == value
    assert value["state"] == "registered-not-yet-query-verified"
    assert value["quote_agent_changed"] is False
    assert "2026-08-01-preview" in companion.mcp_endpoint
    assert "2025-10-01-preview" in companion.connection_url
    properties = companion.connection_properties()
    assert properties["authType"] == "ProjectManagedIdentity"
    assert properties["audience"] == "https://search.azure.com/"
    assert "credentials" not in properties
    definition = project.agents.create_version.call_args.kwargs["definition"].as_dict()
    assert definition["kind"] == "prompt"
    assert definition["tools"] == [{
        "type": "mcp", "server_label": iq.LABEL, "server_url": companion.mcp_endpoint,
        "allowed_tools": [iq.TOOL], "require_approval": "never",
        "project_connection_id": "fsi-showcase-iq",
    }]
    assert project.agents.create_version.call_args.kwargs["agent_name"] == "fsi-showcase-iq"
    assert all(call.args[0] == "GET" for call in rest.call.call_args_list)
    client.responses.create.assert_not_called()


def test_missing_connection_is_created_once_with_exact_auth_and_target(native):
    companion, rest, _, _, output = native
    cause = HTTPError(companion.connection_url, 404, "missing", None, None)
    error = iq.ShowcaseError("Expected missing connection")
    error.__cause__ = cause
    rest.call.side_effect = [error, ({"properties": companion.connection_properties()}, {})]
    companion.create("existing-mini", "a" * 40, output)
    put = rest.call.call_args_list[1]
    assert put.args == (
        "PUT", companion.connection_url, iq.ARM_SCOPE,
        {"properties": companion.connection_properties()}, (200, 201),
    )


@pytest.mark.parametrize("code", [401, 403, 429, 500])
def test_connection_errors_do_not_trigger_mutating_fallback(native, code):
    companion, rest, project, _, output = native
    error = iq.ShowcaseError("Explicit connection failure")
    error.__cause__ = HTTPError(companion.connection_url, code, "failed", None, None)
    rest.call.side_effect = error
    with pytest.raises(iq.ShowcaseError):
        companion.create("existing-mini", "a" * 40, output)
    assert rest.call.call_count == 1
    project.agents.create_version.assert_not_called()
    assert json.loads(output.read_text())["state"] == "connecting"


@pytest.mark.parametrize("key,value", [
    ("target", "https://wrong.search.windows.net"), ("authType", "None"),
    ("audience", "https://management.azure.com/"), ("category", "AzureOpenAI"),
])
def test_existing_connection_mismatch_never_overwrites_or_creates_agent(native, key, value):
    companion, rest, project, _, output = native
    properties = companion.connection_properties()
    properties[key] = value
    rest.call.return_value = ({"properties": properties}, {})
    with pytest.raises(iq.ShowcaseError, match="refusing overwrite"):
        companion.create("existing-mini", "a" * 40, output)
    project.agents.create_version.assert_not_called()
    assert rest.call.call_count == 1


def test_fresh_output_and_revision_checked_before_remote_effects(native):
    companion, rest, project, _, output = native
    with pytest.raises(iq.ShowcaseError, match="revision"):
        companion.create("existing-mini", "main", output)
    output.write_text("preserve")
    with pytest.raises(FileExistsError):
        companion.create("existing-mini", "a" * 40, output)
    rest.call.assert_not_called()
    project.agents.create_version.assert_not_called()
    assert output.read_text() == "preserve"


@pytest.mark.parametrize("language,scenario", [
    ("en", "approval"), ("fr", "approval"),
    ("en", "out-of-corpus"), ("fr", "out-of-corpus"),
])
def test_query_pins_agent_version_and_retains_actual_mcp_source_markers(native, language, scenario):
    companion, _, _, client, output = native
    value = binding(native)
    raw = response(language, scenario)
    client.responses.create.return_value.model_dump.return_value = raw
    evidence_path = output.with_name("query.json")
    result = companion.query(value, language, scenario, evidence_path)
    args = client.responses.create.call_args.kwargs
    assert "agent" not in args["extra_body"]
    assert args["extra_body"]["agent_reference"] == {
        "type": "agent_reference", "name": "fsi-showcase-iq", "version": "1",
    }
    assert args["max_tool_calls"] == 1
    assert args["max_output_tokens"] == 1000
    assert result["native_tool_call_id"] == "mcp-native"
    assert result["native_response"] == raw
    assert result["state"] == "query-verified"
    assert json.loads(evidence_path.read_text()) == result
    assert bool(result["source_id_citations"]) == (scenario != "out-of-corpus")
    if scenario != "out-of-corpus":
        assert "not a semantic judge" in result["citation_validation"]


@pytest.mark.parametrize("damage", [
    "no-call", "failed-call", "wrong-tool", "wrong-server", "no-tool-id",
    "empty-output", "no-answer", "wrong-language", "unknown-source",
    "not-retrieved", "wrong-topic", "failed-response", "incomplete-response",
])
def test_iq_never_accepts_model_only_or_unattributed_answers(damage):
    raw = response()
    tool, message = raw["output"]
    if damage == "no-call":
        raw["output"] = [message]
    elif damage == "failed-call":
        tool["error"] = {"message": "retrieval failed"}
    elif damage == "wrong-tool":
        tool["name"] = "write_case"
    elif damage == "wrong-server":
        tool["server_label"] = "other"
    elif damage == "no-tool-id":
        tool.pop("id")
    elif damage == "empty-output":
        tool["output"] = ""
    elif damage == "no-answer":
        message["content"] = []
    elif damage == "wrong-language":
        message["content"][0]["text"] = "FSI-REVIEW-FR"
    elif damage == "unknown-source":
        message["content"][0]["text"] = "No supporting source"
    elif damage == "not-retrieved":
        tool["output"] = "Unrelated retrieved text"
    elif damage == "wrong-topic":
        message["content"][0]["text"] = "FSI-PRIVACY-EN"
    elif damage == "failed-response":
        raw["status"] = "failed"
    else:
        raw["incomplete_details"] = {"reason": "max_output_tokens"}
    with pytest.raises(iq.ShowcaseError):
        iq.validate_iq_response(raw, iq.load_corpus(), "en", "approval")


def test_failed_query_retains_native_response_for_inspection(native):
    companion, _, _, client, output = native
    value = binding(native)
    raw = response()
    raw["output"][0]["error"] = "explicit service failure"
    client.responses.create.return_value.model_dump.return_value = raw
    evidence_path = output.with_name("failed-query.json")
    with pytest.raises(iq.ShowcaseError):
        companion.query(value, "en", "approval", evidence_path)
    result = json.loads(evidence_path.read_text())
    assert result["native_response"] == raw
    assert result["state"] == "response-received-not-yet-validated"


def test_binding_tampering_and_live_definition_changes_block_request(native):
    companion, _, project, client, _ = native
    value = binding(native)
    changed = copy.deepcopy(value)
    changed["agent"] = "quote-preparation-agent"
    with pytest.raises(iq.ShowcaseError, match="binding"):
        companion.check_binding(changed)
    project.agents.get_version.return_value.definition = companion.definition("different-model")
    with pytest.raises(iq.ShowcaseError, match="definition"):
        companion.check_binding(value)
    client.responses.create.assert_not_called()


def test_canonical_native_tool_filter_preserves_original_binding_digest(native):
    companion, _, project, client, _ = native
    value = binding(native)
    current = companion.definition("existing-mini").as_dict()
    current["tools"][0]["allowed_tools"] = {"tool_names": [iq.TOOL]}
    project.agents.get_version.return_value = SimpleNamespace(
        definition=SimpleNamespace(as_dict=lambda: current),
    )
    companion.check_binding(value)
    assert current["tools"][0]["allowed_tools"] == {"tool_names": [iq.TOOL]}
    client.responses.create.assert_not_called()


@pytest.mark.parametrize("allowed", [
    {"tool_names": [iq.TOOL, "write_case"]},
    {"tool_names": []},
    {"tool_names": [iq.TOOL], "read_only": True},
    {"tool_names": [iq.TOOL], "unexpected": "unreviewed"},
    {"tool_names": None},
])
def test_canonical_native_filter_drift_still_blocks_before_model_request(native, allowed):
    companion, _, project, client, _ = native
    value = binding(native)
    current = companion.definition("existing-mini").as_dict()
    current["tools"][0]["allowed_tools"] = allowed
    project.agents.get_version.return_value = SimpleNamespace(
        definition=SimpleNamespace(as_dict=lambda: current),
    )
    with pytest.raises(iq.ShowcaseError, match="definition"):
        companion.check_binding(value)
    client.responses.create.assert_not_called()


def test_optional_knowledge_reference_properties_do_not_change_its_pinned_source(native):
    companion, _, _, _, _ = native
    companion.knowledge.status.return_value["knowledgebases"]["knowledgeSources"][0][
        "alwaysQuerySource"
    ] = True
    assert companion.verify_knowledge()["verified_documents"] == 6


def test_preflight_verifies_actual_project_identity_and_isolated_source(native, monkeypatch):
    companion, rest, _, _, _ = native
    monkeypatch.delattr(companion, "preflight")
    expected_objects = companion.knowledge.status()
    monkeypatch.delattr(companion.knowledge, "status")
    verify = Mock(return_value={"verified_role": "reader"})
    monkeypatch.setattr(iq, "preflight_search", verify)
    rest.call.side_effect = [
        ({"identity": {"principalId": "actual-project-mi"}}, {}),
        (expected_objects["indexes"], {}),
        (expected_objects["knowledgesources"], {}),
        (expected_objects["knowledgebases"], {}),
    ]
    result = companion.preflight()
    assert result["project_managed_identity"] == "actual-project-mi"
    assert verify.call_args.args[-2:] == ("actual-project-mi", "query")


@pytest.mark.parametrize("damage", [
    "base", "index", "kind", "index-fields", "source-fields",
    "reasoning", "retrieval-model", "synthesis", "extra-instructions",
])
def test_query_rechecks_mutable_knowledge_links_and_schema_before_model_request(native, damage):
    companion, _, _, client, output = native
    value = binding(native)
    objects = companion.knowledge.status.return_value
    if damage == "reasoning":
        objects["knowledgebases"]["retrievalReasoningEffort"] = {"kind": "low"}
    elif damage == "retrieval-model":
        objects["knowledgebases"]["models"] = [{"kind": "azureOpenAI"}]
    elif damage == "synthesis":
        objects["knowledgebases"]["outputMode"] = "answerSynthesis"
    elif damage == "extra-instructions":
        objects["knowledgebases"]["retrievalInstructions"] = "Use another source"
    if damage == "base":
        objects["knowledgebases"]["knowledgeSources"] = [{"name": "unreviewed-source"}]
    elif damage == "index":
        objects["knowledgesources"]["searchIndexParameters"]["searchIndexName"] = "other-index"
    elif damage == "kind":
        objects["knowledgesources"]["kind"] = "web"
    elif damage == "index-fields":
        objects["indexes"]["fields"] = objects["indexes"]["fields"] + [{"name": "unreviewed"}]
    elif damage == "source-fields":
        objects["knowledgesources"]["searchIndexParameters"]["sourceDataFields"] = [{"name": "unreviewed"}]
    with pytest.raises(iq.ShowcaseError):
        companion.query(value, "en", "approval", output.with_name("changed-knowledge.json"))
    client.responses.create.assert_not_called()


def test_wrong_project_or_nonisolated_namespace_is_rejected_before_io():
    with pytest.raises(iq.ShowcaseError, match="must match"):
        iq.FoundryIQ(Mock(), Mock(), Mock(), PROJECT,
                    PROJECT_ID.replace("/projects/synthetic-project", "/projects/other-project"),
                    SEARCH, SEARCH_ID, prefix="fsi-showcase")
