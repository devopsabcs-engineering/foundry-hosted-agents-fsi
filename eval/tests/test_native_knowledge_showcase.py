"""Offline native service contracts; no Azure credentials or live requests."""

import base64
import copy
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import native_knowledge_showcase as showcase  # noqa: E402

SEARCH = "https://additive-showcase.search.windows.net"
CU = "https://existing-foundry.cognitiveservices.azure.com"
RESOURCE = ("/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/test/"
            "providers/Microsoft.Search/searchServices/additive-showcase")
PRINCIPAL = "22222222-2222-2222-2222-222222222222"
OPERATION = CU + "/contentunderstanding/analyzerResults/job-123?api-version=2025-11-01"
PROJECT = "https://existing-foundry.services.ai.azure.com/api/projects/synthetic-project"


@pytest.fixture
def docs():
    return showcase.load_corpus()


def retrieval(doc, language="en"):
    return {
        "response": [{"content": [{"type": "text", "text": json.dumps([
            {"ref_id": "0", "title": doc["title"], "content": doc["content"]}])}]}],
        "activity": [{"id": 1, "type": "searchIndex",
                      "knowledgeSourceName": "fsi-showcase-source"}],
        "references": [{"id": "0", "type": "searchIndex", "docKey": doc["id"],
                        "activitySource": 1, "sourceData": doc}],
    }


@pytest.mark.parametrize("damage", [None, "changed-content", "changed-hash", "extra", "missing", "duplicate"])
def test_search_verifies_exact_reviewed_corpus_not_only_source_names(docs, damage):
    rows = copy.deepcopy(docs)
    if damage == "changed-content":
        rows[0]["content"] += " Changed outside review."
    elif damage == "changed-hash":
        rows[0]["sha256"] = "0" * 64
    elif damage == "extra":
        rows.append({**rows[0], "id": "UNREVIEWED"})
    elif damage == "missing":
        rows.pop()
    elif damage == "duplicate":
        rows[-1] = rows[0]
    rest = Mock()
    rest.call.return_value = ({"@odata.count": len(rows), "value": rows}, {})
    knowledge = showcase.Knowledge(rest, SEARCH)
    if damage:
        with pytest.raises(showcase.ShowcaseError, match="Search corpus"):
            knowledge.verify_corpus(docs)
    else:
        result = knowledge.verify_corpus(docs)
        assert result["verified_documents"] == 6
        assert result["source_sha256"] == {doc["id"]: doc["sha256"] for doc in docs}
    request = rest.call.call_args.args
    assert request[0] == "POST"
    assert "/docs/search?" in request[1]
    assert request[3]["top"] == 7


def extracted():
    return {"status": "Succeeded", "result": {
        "analyzerId": "prebuilt-invoice", "apiVersion": "2025-11-01",
        "contents": [{"markdown": "SYN-REPAIR-001", "fields": {
            "InvoiceId": {"type": "string", "valueString": "SYN-REPAIR-001",
                          "confidence": 0.95, "source": "D(1,1,1,2,1,2,2,1,2)",
                          "spans": [{"offset": 0, "length": 14}]}}}]}}


def test_corpus_is_complete_bilingual_synthetic_and_versioned(docs):
    assert len(docs) == 6
    assert {d["language"] for d in docs} == {"en", "fr"}
    assert all(d["version"] == ("2" if d["id"].startswith("FSI-PRIVACY-") else "1")
               and len(d["sha256"]) == 64 for d in docs)
    assert all(showcase.MARKER in d["content"] for d in docs)
    privacy = next(d for d in docs if d["id"] == "FSI-PRIVACY-EN")["content"]
    assert "memory" in privacy and "audit" in privacy and "license" in privacy
    assert "unsupported" in docs[0]["content"]


@pytest.fixture
def native_search(docs, tmp_path):
    client = Mock()
    store = SimpleNamespace(
        id="vs_native", name="showcase-synthetic-native-knowledge", status="completed",
        metadata={"synthetic": "true"}, file_counts=SimpleNamespace(completed=6),
        model_dump=lambda **kw: {"id": "vs_native", "name": "showcase-synthetic-native-knowledge"},
    )
    client.vector_stores.create.return_value = store
    client.vector_stores.retrieve.return_value = store
    client.vector_stores.files.list.return_value = [
        SimpleNamespace(id=f"assistant-{index}", status="completed", vector_store_id="vs_native")
        for index in range(6)
    ]
    client.files.create.side_effect = [
        SimpleNamespace(id=f"assistant-{index}") for index in range(6)
    ]
    batch = SimpleNamespace(
        id="batch-native", status="completed",
        file_counts=SimpleNamespace(completed=6, failed=0, cancelled=0, in_progress=0),
        model_dump=lambda **kw: {"id": "batch-native", "status": "completed"},
    )
    client.vector_stores.file_batches.create.return_value = batch
    search = showcase.NativeFileSearch(client, PROJECT)
    output = tmp_path / "native-store.json"
    return search, client, docs, output, batch


def test_native_file_search_indexes_exact_corpus_without_new_search_model_or_agent(native_search):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    assert evidence["state"] == "completed"
    assert evidence["hosted_agent_changed"] is False
    assert len(evidence["files"]) == 6
    assert json.loads(output.read_text()) == evidence
    client.vector_stores.create.assert_called_once_with(
        name="showcase-synthetic-native-knowledge",
        expires_after={"anchor": "last_active_at", "days": 7},
        metadata={"synthetic": "true", "purpose": "session2-native-first"},
    )
    assert client.files.create.call_count == 6
    assert all(call.kwargs["purpose"] == "assistants" for call in client.files.create.call_args_list)
    submitted = client.vector_stores.file_batches.create.call_args.kwargs
    assert set(submitted) == {"file_ids"}
    assert len(submitted["file_ids"]) == 6
    assert {item["language"] for item in evidence["files"]} == {"en", "fr"}
    client.vector_stores.files.update.assert_not_called()
    client.responses.create.assert_not_called()


def test_native_file_search_refuses_overwrite_before_creating_resources(native_search):
    search, client, docs, output, _ = native_search
    output.write_text("preserve")
    with pytest.raises(FileExistsError):
        search.create(docs, output)
    client.vector_stores.create.assert_not_called()
    assert output.read_text() == "preserve"


@pytest.mark.parametrize("failure", ["upload", "failed-index", "timeout"])
def test_native_file_search_retains_partial_resource_identity_and_fails_explicitly(
    native_search, monkeypatch, failure,
):
    search, client, docs, output, batch = native_search
    if failure == "upload":
        client.files.create.side_effect = RuntimeError("Explicit upload failure")
    elif failure == "failed-index":
        batch.file_counts.failed = 1
    else:
        batch.status = "in_progress"
        monkeypatch.setattr(showcase.time, "monotonic", iter([0, 121]).__next__)
    with pytest.raises((showcase.ShowcaseError, RuntimeError)):
        search.create(docs, output)
    partial = json.loads(output.read_text())
    assert partial["vector_store"]["id"] == "vs_native"
    assert partial["state"] == "creating"
    client.responses.create.assert_not_called()


def file_search_response(evidence, docs, language="en", scenario="approval"):
    document = next(doc for doc in docs if doc["id"] == f"FSI-REVIEW-{language.upper()}")
    record = next(record for record in evidence["files"] if record["id"] == document["id"])
    return {
        "id": "resp-grounded", "status": "completed", "output": [
            {"type": "file_search_call", "status": "completed", "results": [{
                "file_id": record["file_id"], "filename": document["id"] + ".txt",
                "vector_store_id": "vs_native", "text": document["content"],
            }]},
            {"type": "message", "content": [{
                "type": "output_text",
                "text": "OUT_OF_CORPUS" if scenario == "out-of-corpus" else document["id"] + ": employee review.",
                "annotations": [] if scenario == "out-of-corpus" else [
                    {"type": "file_citation", "file_id": record["file_id"]},
                ],
            }]},
        ],
    }


@pytest.mark.parametrize("language,scenario", [
    ("en", "approval"), ("fr", "approval"), ("en", "out-of-corpus"), ("fr", "out-of-corpus"),
])
def test_native_file_search_requires_real_tool_results_and_citations(native_search, language, scenario):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    native = file_search_response(evidence, docs, language, scenario)
    client.responses.create.return_value.model_dump.return_value = native
    result = search.query(evidence, docs, "existing-model", language, scenario)
    assert result["source_citations_verified"] is True
    assert result["response_id"] == "resp-grounded"
    call = client.responses.create.call_args.kwargs
    assert call["model"] == "existing-model"
    assert call["tools"][0]["type"] == "file_search"
    assert "filters" not in call["tools"][0]
    assert "postvalidated citation language" in result["language_control"]
    assert call["include"] == ["file_search_call.results"]
    assert call["input"] == showcase.FILE_SEARCH_QUESTIONS[scenario][language]


@pytest.mark.parametrize("failure", [
    "failed-response", "missing-tool", "failed-tool", "unknown-file", "wrong-store",
    "wrong-language", "invented-excerpt", "invented-citation", "no-citation", "amount",
])
def test_native_file_search_never_labels_ungrounded_or_failed_output_success(native_search, failure):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    native = file_search_response(evidence, docs)
    result = native["output"][0]["results"][0]
    content = native["output"][1]["content"][0]
    if failure == "failed-response":
        native["status"] = "failed"
    elif failure == "missing-tool":
        native["output"] = native["output"][1:]
    elif failure == "failed-tool":
        native["output"][0]["status"] = "in_progress"
    elif failure == "unknown-file":
        result["file_id"] = "assistant-unknown"
    elif failure == "wrong-store":
        result["vector_store_id"] = "vs_unrelated"
    elif failure == "wrong-language":
        native = file_search_response(evidence, docs, language="fr")
    elif failure == "invented-excerpt":
        result["text"] = "This synthetic-looking text was never in the reviewed corpus."
    elif failure == "invented-citation":
        content["annotations"][0]["file_id"] = "assistant-unretrieved"
    elif failure == "no-citation":
        content["annotations"] = []
    else:
        content["text"] += " 100 CAD"
    client.responses.create.return_value.model_dump.return_value = native
    with pytest.raises(showcase.ShowcaseError):
        search.query(evidence, docs, "existing-model", "en", "approval")


def test_native_file_search_rejects_modified_or_other_project_store_before_inference(native_search):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    evidence["files"][0]["sha256"] = "f" * 64
    client.vector_stores.retrieve.reset_mock()
    with pytest.raises(showcase.ShowcaseError):
        search.query(evidence, docs, "existing-model", "en", "approval")
    client.vector_stores.retrieve.assert_not_called()
    client.responses.create.assert_not_called()


def test_native_file_search_accepts_an_explicit_out_of_corpus_decline_with_zero_hits(native_search):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    native = file_search_response(evidence, docs, scenario="out-of-corpus")
    native["output"][0]["results"] = []
    client.responses.create.return_value.model_dump.return_value = native
    result = search.query(evidence, docs, "existing-model", "en", "out-of-corpus")
    assert result["answer"] == "OUT_OF_CORPUS"
    assert result["retrieved_sources"] == result["cited_sources"] == []


def test_native_indexing_resumes_completed_batch_without_reupload_or_duplicate_batch(native_search):
    search, client, docs, output, batch = native_search
    evidence = search.create(docs, output)
    evidence["state"] = "creating"
    client.files.create.reset_mock()
    client.vector_stores.file_batches.create.reset_mock()
    client.vector_stores.file_batches.retrieve.return_value = batch
    resumed = search.index(evidence, docs, output.parent / "resumed.json")
    assert resumed["state"] == "completed"
    client.files.create.assert_not_called()
    client.vector_stores.file_batches.create.assert_not_called()
    client.vector_stores.file_batches.retrieve.assert_called_once_with(
        "batch-native", vector_store_id="vs_native",
    )


def test_native_query_preserves_failed_response_evidence_without_success_flags(native_search):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    native = file_search_response(evidence, docs)
    native["output"][1]["content"][0]["annotations"] = []
    client.responses.create.return_value.model_dump.return_value = native
    failure = output.parent / "failed-response.json"
    with pytest.raises(showcase.ShowcaseError, match="resp-grounded failed validation"):
        search.query(evidence, docs, "existing-model", "en", "approval", failure)
    saved = json.loads(failure.read_text())
    assert saved["validation_state"] == "pending"
    assert saved["native_response"]["id"] == "resp-grounded"
    assert "grounding_verified" not in saved
    client.responses.create.reset_mock()
    with pytest.raises(FileExistsError):
        search.query(evidence, docs, "existing-model", "en", "approval", failure)
    client.responses.create.assert_not_called()


@pytest.mark.parametrize("result_store", [None, ""])
def test_native_file_search_checks_membership_when_optional_result_store_is_absent(
    native_search, result_store,
):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    native = file_search_response(evidence, docs)
    native["output"][0]["results"][0]["vector_store_id"] = result_store
    client.responses.create.return_value.model_dump.return_value = native
    result = search.query(evidence, docs, "existing-model", "en", "approval")
    assert result["source_citations_verified"] is True
    assert result["store_membership_verified"] is True
    client.vector_stores.files.list.assert_called_once_with("vs_native", limit=7)


def test_native_file_search_refuses_unknown_store_membership_before_model_call(native_search):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    client.vector_stores.files.list.return_value[0].id = "assistant-unreviewed"
    with pytest.raises(showcase.ShowcaseError, match="membership"):
        search.query(evidence, docs, "existing-model", "en", "approval")
    client.responses.create.assert_not_called()


def test_native_file_citation_identifies_source_without_requiring_duplicated_prose_ids(native_search):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    native = file_search_response(evidence, docs)
    native["output"][1]["content"][0]["text"] = "Only an authorized employee may approve the preparation."
    client.responses.create.return_value.model_dump.return_value = native
    result = search.query(evidence, docs, "existing-model", "en", "approval")
    assert result["cited_sources"] == ["FSI-REVIEW-EN"]
    assert result["source_citations_verified"] is True


def test_native_citation_validation_does_not_claim_semantic_entailment(native_search):
    search, client, docs, output, _ = native_search
    evidence = search.create(docs, output)
    client.responses.create.return_value.model_dump.return_value = file_search_response(evidence, docs)
    result = search.query(evidence, docs, "existing-model", "en", "approval")
    assert result["validation_state"] == "source-verified"
    assert "grounding_verified" not in result
    assert "separate native evaluator" in result["answer_grounding"]
    with pytest.raises(showcase.ShowcaseError, match="covering the requested topic"):
        search.query(evidence, docs, "existing-model", "en", "privacy")


def test_privacy_version_two_explicitly_denies_authentication_and_authorization(docs):
    en = next(doc for doc in docs if doc["id"] == "FSI-PRIVACY-EN")
    fr = next(doc for doc in docs if doc["id"] == "FSI-PRIVACY-FR")
    assert en["version"] == fr["version"] == "2"
    assert "do not authenticate" in en["content"] and "do not authorize" in en["content"]
    assert "n'authentifient" in fr["content"] and "n'autorisent aucun" in fr["content"]


def invoice_result():
    return {"status": "succeeded", "analyzeResult": {
        "modelId": "prebuilt-invoice", "apiVersion": showcase.DI_API,
        "content": "SYN-REPAIR-001",
        "documents": [{"fields": {"InvoiceId": {
            "content": "SYN-REPAIR-001", "confidence": 0.95,
            "spans": [{"offset": 0, "length": 14}],
            "boundingRegions": [{"pageNumber": 1, "polygon": [0, 0, 1, 0, 1, 1, 0, 1]}],
        }}}],
    }}


def test_native_pretrained_invoice_service_requires_no_new_llm_defaults():
    rest = Mock()
    operation = CU + (
        "/documentintelligence/documentModels/prebuilt-invoice/analyzeResults/invoice-1"
        "?api-version=2024-11-30"
    )
    rest.call.side_effect = [({}, {"Operation-Location": operation}), (invoice_result(), {})]
    result = showcase.DocumentIntelligence(rest, CU).analyze()
    assert result["native_result"]["status"] == "succeeded"
    assert result["service"] == "Azure AI Document Intelligence"
    submitted = rest.call.call_args_list[0]
    assert submitted.args[1].endswith("prebuilt-invoice:analyze?api-version=2024-11-30")
    assert base64.b64decode(submitted.args[3]["base64Source"]).startswith(b"%PDF-1.4")
    assert len(rest.call.call_args_list) == 2
    assert all("/defaults" not in call.args[1] for call in rest.call.call_args_list)


@pytest.mark.parametrize("invalid", ["span", "confidence", "model", "fields", "source"])
def test_native_invoice_rejects_uninspectable_extraction(invalid):
    result = invoice_result()
    field = result["analyzeResult"]["documents"][0]["fields"]["InvoiceId"]
    if invalid == "span":
        field["spans"][0]["length"] = 99999
    elif invalid == "confidence":
        field["confidence"] = float("nan")
    elif invalid == "model":
        result["analyzeResult"]["modelId"] = "unknown"
    elif invalid == "source":
        field["boundingRegions"] = []
    else:
        result["analyzeResult"]["documents"] = []
    with pytest.raises(showcase.ShowcaseError):
        showcase.validate_invoice(result)


def test_native_invoice_never_follows_cross_origin_operation():
    rest = Mock()
    rest.call.return_value = ({}, {"Operation-Location": "https://attacker.test/results/1"})
    with pytest.raises(showcase.ShowcaseError, match="unsafe Document Intelligence"):
        showcase.DocumentIntelligence(rest, CU).analyze()
    assert rest.call.call_count == 1


def corpus_folder(monkeypatch):
    """Mock file reads in memory rather than create a temporary data directory."""
    originals = {
        p.name: p.read_text(encoding="utf-8") for p in showcase.CORPUS.iterdir() if p.is_file()
    }
    read = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda self, **kw: (
        originals[self.name] if self.parent == showcase.CORPUS else read(self, **kw)))
    return originals


@pytest.mark.parametrize("change", ["hash", "authority", "duplicate", "missing", "traversal", "real-data"])
def test_rejects_invalid_provenance_and_changed_corpus(monkeypatch, change):
    files = corpus_folder(monkeypatch)
    manifest = json.loads(files["provenance.json"])
    if change == "hash":
        files["scope-en.txt"] += "changed"
    elif change == "authority":
        manifest["authority"] = "insurer"
    elif change == "duplicate":
        manifest["sources"].append(manifest["sources"][0])
    elif change == "missing":
        manifest["sources"].pop()
    elif change == "traversal":
        manifest["sources"][0]["file"] = "../scope-en.txt"
    else:
        manifest["contains_real_personal_data"] = True
    files["provenance.json"] = json.dumps(manifest)
    with pytest.raises(showcase.ShowcaseError):
        showcase.load_corpus()


def test_hashes_allow_checkout_line_endings(monkeypatch, docs):
    # Path.read_text normalizes platform newline sequences before the pinned hash.
    assert all("\r" not in d["content"] for d in docs)


def test_upsert_creates_native_index_source_and_base_without_model():
    rest = Mock()
    rest.call.return_value = ({}, {})
    knowledge = showcase.Knowledge(rest, SEARCH)
    knowledge.upsert()
    calls = rest.call.call_args_list
    assert [c.args[0] for c in calls] == ["PUT", "PUT", "PUT", "GET", "GET", "GET"]
    assert calls[0].args[1] == SEARCH + "/indexes/fsi-showcase-index?api-version=2026-04-01"
    assert calls[1].args[3]["kind"] == "searchIndex"
    assert calls[1].args[3]["searchIndexParameters"]["semanticConfigurationName"] == "showcase-semantic"
    assert calls[2].args[3]["knowledgeSources"] == [{"name": "fsi-showcase-source"}]
    assert calls[2].args[1].endswith("?api-version=2026-08-01-preview")
    assert calls[2].args[3]["retrievalReasoningEffort"] == {"kind": "minimal"}
    assert calls[2].args[3]["outputMode"] == "extractiveData"
    assert "models" not in calls[2].args[3]
    assert "vectorSearch" not in calls[0].args[3]
    assert all(c.args[4] == (200, 201, 204) for c in calls[:3])
    assert all(c.args[4] == (200,) for c in calls[3:])


@pytest.mark.parametrize("status", [200, 201, 204, 202, 400, 403, 500])
def test_upsert_accepts_only_successful_resource_put_statuses(status):
    rest = showcase.Rest(Mock())
    rest.credential.get_token.return_value.token = "synthetic"

    def reply(request, **kwargs):
        result = Mock()
        result.status = status if request.method == "PUT" else 200
        result.read.return_value = b""
        result.headers = {}
        result.__enter__ = Mock(return_value=result)
        result.__exit__ = Mock(return_value=False)
        return result

    rest.opener.open = Mock(side_effect=reply)
    knowledge = showcase.Knowledge(rest, SEARCH)
    if status in (200, 201, 204):
        assert knowledge.upsert() == {
            "indexes": {}, "knowledgesources": {}, "knowledgebases": {},
        }
        assert rest.opener.open.call_count == 6
    else:
        with pytest.raises(showcase.ShowcaseError, match=f"Unexpected HTTP {status}"):
            knowledge.upsert()
        assert rest.opener.open.call_count == 1


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_upsert_no_content_support_does_not_relax_other_methods(method):
    rest = showcase.Rest(Mock())
    rest.credential.get_token.return_value.token = "synthetic"
    reply = Mock()
    reply.status = 204
    reply.__enter__ = Mock(return_value=reply)
    reply.__exit__ = Mock(return_value=False)
    rest.opener.open = Mock(return_value=reply)
    with pytest.raises(showcase.ShowcaseError, match="Unexpected HTTP 204"):
        showcase.Knowledge(rest, SEARCH).call(method, "synthetic")


def test_cli_prints_native_unicode_on_legacy_windows_stdout(monkeypatch):
    result = {"answer": "Préparation synthétique \u30101:0\u2020source\u3011"}
    knowledge = Mock()
    knowledge.query.return_value = result
    monkeypatch.setattr(showcase, "Rest", Mock())
    monkeypatch.setattr(showcase, "Knowledge", Mock(return_value=knowledge))
    buffer = io.BytesIO()
    stdout = io.TextIOWrapper(buffer, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stdout)
    assert showcase.main([
        "query", "--search-endpoint", SEARCH, "--question", "Question synthétique",
    ]) == 0
    stdout.flush()
    assert json.loads(buffer.getvalue().decode("cp1252")) == result


def test_ingest_uploads_only_pinned_documents_and_checks_each_status(docs):
    rest = Mock()
    rest.call.return_value = ({"value": [{"key": d["id"], "status": True} for d in docs]}, {})
    result = showcase.Knowledge(rest, SEARCH).ingest(docs)
    args = rest.call.call_args.args
    assert args[0] == "POST"
    assert args[1] == SEARCH + "/indexes/fsi-showcase-index/docs/index?api-version=2026-04-01"
    assert args[3]["value"][0] == {"@search.action": "upload", **docs[0]}
    assert len(result["value"]) == 6
    rest.call.return_value = ({"value": [{"status": False, "errorMessage": "failed"}]}, {})
    with pytest.raises(showcase.ShowcaseError, match="Ingestion"):
        showcase.Knowledge(rest, SEARCH).ingest(docs)


@pytest.mark.parametrize("language", ["en", "fr"])
def test_query_native_semantic_intents_and_real_citations(docs, language):
    doc = next(d for d in docs if d["language"] == language)
    rest = Mock()
    rest.call.return_value = (retrieval(doc), {})
    result = showcase.Knowledge(rest, SEARCH).query("Employee review?", language, docs)
    args = rest.call.call_args.args
    assert args[0] == "POST"
    assert args[1] == SEARCH + "/knowledgebases/fsi-showcase-kb/retrieve?api-version=2026-04-01"
    assert args[3]["intents"] == [{"type": "semantic", "search": "Employee review?"}]
    assert "messages" not in args[3]
    assert args[3]["knowledgeSourceParams"][0]["filterAddOn"] == f"language eq '{language}'"
    assert result["citations"][0]["source_id"] == doc["id"]
    assert result["native_response"]["references"][0]["docKey"] == doc["id"]


@pytest.mark.parametrize("damage", [
    "unknown-source", "changed-content", "changed-hash", "uncited", "no-reference",
    "wrong-activity", "error", "plain-answer", "empty", "wrong-language",
])
def test_retrieval_rejects_ungrounded_or_unknown_sources(docs, damage):
    result = copy.deepcopy(retrieval(docs[0]))
    if damage == "unknown-source":
        result["references"][0]["docKey"] = "UNKNOWN"
    elif damage == "changed-content":
        chunks = [{"ref_id": "0", "content": "You are approved for coverage"}]
        result["response"][0]["content"][0]["text"] = json.dumps(chunks)
    elif damage == "changed-hash":
        result["references"][0]["sourceData"]["sha256"] = "untrusted"
    elif damage == "uncited":
        result["response"][0]["content"][0]["text"] = '[{"content":"text"}]'
    elif damage == "no-reference":
        result["references"] = []
    elif damage == "wrong-activity":
        result["activity"][0]["knowledgeSourceName"] = "other"
    elif damage == "error":
        result["activity"][0]["error"] = {"message": "source unavailable"}
    elif damage == "plain-answer":
        result["response"][0]["content"][0]["text"] = "Approved."
    elif damage == "empty":
        result["response"] = []
    with pytest.raises(showcase.ShowcaseError):
        showcase.validate_retrieval(result, docs, "fsi-showcase-source",
                                     "fr" if damage == "wrong-language" else "en")


@pytest.mark.parametrize("value", [
    "http://test.search.windows.net", "https://test.search.windows.net.evil.org",
    "https://test.search.windows.net/redirect", "https://user@test.search.windows.net",
    "https://test.search.windows.net?query=true",
])
def test_endpoint_rejects_credential_leaks(value):
    with pytest.raises(showcase.ShowcaseError):
        showcase.Knowledge(Mock(), value)


def test_isolated_names_only():
    with pytest.raises(showcase.ShowcaseError):
        showcase.Knowledge(Mock(), SEARCH, "production")


def test_rest_uses_bearer_explicit_method_and_json():
    credential = Mock()
    credential.get_token.return_value.token = "not-a-real-token"
    rest = showcase.Rest(credential)
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock()
    response.__exit__.return_value = False
    response.status = 200
    response.headers = {}
    response.read.return_value = b'{"value":[]}'
    rest.opener.open = Mock(return_value=response)
    assert rest.call("POST", SEARCH, "scope", {"test": "value"})[0] == {"value": []}
    request = rest.opener.open.call_args.args[0]
    assert request.get_method() == "POST"
    assert json.loads(request.data) == {"test": "value"}
    assert request.get_header("Authorization") == "Bearer not-a-real-token"
    credential.get_token.assert_called_once_with("scope")


@pytest.mark.parametrize("error", [
    HTTPError(SEARCH, 403, "Forbidden", {}, io.BytesIO(b"PRIVATE RESPONSE")),
    URLError("offline"), TimeoutError(),
])
def test_rest_auth_and_transport_errors_are_not_success(error):
    rest = showcase.Rest(Mock())
    rest.opener.open = Mock(side_effect=error)
    with pytest.raises(showcase.ShowcaseError) as caught:
        rest.call("GET", SEARCH, "scope")
    assert "PRIVATE RESPONSE" not in str(caught.value)


def test_rest_rejects_partial_success():
    rest = showcase.Rest(Mock())
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock()
    response.__exit__.return_value = False
    response.status = 206
    rest.opener.open = Mock(return_value=response)
    with pytest.raises(showcase.ShowcaseError, match="206"):
        rest.call("POST", SEARCH, "scope")


def test_redirects_never_forward_tokens():
    with pytest.raises(showcase.ShowcaseError, match="redirect"):
        showcase.NoRedirect().redirect_request(None, None, 302, None, None, "https://evil.org")


def cu_rest(states):
    rest = Mock()
    rest.call.side_effect = [
        ({"analyzerId": "prebuilt-invoice",
          "models": {"completion": "prebuilt-analyzer-completion"},
          "supportedModels": {"completion": ["gpt-4.1"]}}, {}),
        ({"modelDeployments": {"prebuilt-analyzer-completion": "existing-deployment"}}, {}),
        ({"status": "NotStarted"}, {"Operation-Location": OPERATION}),
        *((state, {}) for state in states),
    ]
    return rest


def test_pdf_is_deterministic_and_has_correct_xref():
    pdf = showcase.synthetic_pdf()
    assert pdf == showcase.synthetic_pdf()
    assert pdf.startswith(b"%PDF-1.4")
    xref = int(pdf.split(b"startxref\n")[1].splitlines()[0])
    assert pdf[xref:xref + 4] == b"xref"
    assert b"SYN-REPAIR-001" in pdf
    offsets = pdf[xref:].splitlines()[3:8]
    for i, line in enumerate(offsets, 1):
        offset = int(line[:10])
        assert pdf[offset:].startswith(f"{i} 0 obj".encode())


def test_cu_extracts_fields_grounding_and_polls(monkeypatch):
    monkeypatch.setattr(showcase.time, "sleep", Mock())
    rest = cu_rest([{"status": "Running"}, extracted()])
    result = showcase.ContentUnderstanding(rest, CU).analyze()
    calls = rest.call.call_args_list
    assert [c.args[0] for c in calls] == ["GET", "GET", "POST", "GET", "GET"]
    assert calls[2].args[1] == CU + "/contentunderstanding/analyzers/prebuilt-invoice:analyze?api-version=2025-11-01"
    item = calls[2].args[3]["inputs"][0]
    assert item["mimeType"] == "application/pdf"
    assert base64.b64decode(item["data"]) == showcase.synthetic_pdf()
    assert calls[3].args[1] == OPERATION
    assert result["native_result"]["result"]["contents"][0]["fields"]["InvoiceId"]["spans"]
    assert "pricing" in result["warning"]


@pytest.mark.parametrize("status", ["Failed", "Canceled", "Unknown", None])
def test_cu_terminal_failures_do_not_fallback(status):
    rest = cu_rest([{"status": status, "error": {"code": "InvalidContent"}}])
    with pytest.raises(showcase.ShowcaseError, match="failed"):
        showcase.ContentUnderstanding(rest, CU).analyze()


def test_cu_timeout_is_explicit_and_retains_operation(monkeypatch):
    rest = cu_rest([{"status": "Running"}])
    monkeypatch.setattr(showcase.time, "monotonic", Mock(side_effect=[0, 0, 2, 2]))
    monkeypatch.setattr(showcase.time, "sleep", Mock())
    with pytest.raises(showcase.ShowcaseError, match="polling timeout") as error:
        showcase.ContentUnderstanding(rest, CU).analyze(timeout=1)
    assert OPERATION in str(error.value)


@pytest.mark.parametrize("operation", [
    "", "https://evil.org/job", CU + "/different?api-version=2025-11-01",
    OPERATION.replace("2025-11-01", "2026-06-01-preview"),
])
def test_cu_unsafe_operation_url_rejected(operation):
    rest = cu_rest([])
    rest.call.side_effect = list(rest.call.side_effect)[:2] + [
        ({}, {"Operation-Location": operation})]
    with pytest.raises(showcase.ShowcaseError, match="Operation-Location"):
        showcase.ContentUnderstanding(rest, CU).analyze()
    assert rest.call.call_count == 3


def test_cu_corrupt_document_rejected_before_any_request(monkeypatch):
    rest = Mock()
    read = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda self, **kw:
                        "CORRUPT" if self == showcase.DOCUMENT else read(self, **kw))
    with pytest.raises(showcase.ShowcaseError, match="unmodified"):
        showcase.ContentUnderstanding(rest, CU).analyze()
    rest.call.assert_not_called()


def test_cu_unavailable_analyzer_never_starts_job():
    rest = Mock()
    rest.call.side_effect = showcase.ShowcaseError("HTTP 404 analyzer unavailable")
    with pytest.raises(showcase.ShowcaseError, match="404"):
        showcase.ContentUnderstanding(rest, CU).analyze()
    assert rest.call.call_count == 1


def test_cu_missing_model_alias_fails_preflight_without_changes():
    rest = Mock()
    rest.call.side_effect = [
        ({"models": {"completion": "prebuilt-analyzer-completion"}}, {}),
        ({"modelDeployments": {}}, {}),
    ]
    with pytest.raises(showcase.ShowcaseError, match="model aliases"):
        showcase.ContentUnderstanding(rest, CU).preflight()
    assert all(c.args[0] == "GET" for c in rest.call.call_args_list)


def test_cu_explicit_request_mapping_never_changes_defaults():
    rest = cu_rest([extracted()])
    responses = list(rest.call.side_effect)
    rest.call.side_effect = responses[:1] + responses[2:]
    mapping = {"prebuilt-analyzer-completion": "explicit-existing-deployment"}
    showcase.ContentUnderstanding(rest, CU, mapping).analyze()
    assert rest.call.call_args_list[1].args[3]["modelDeployments"] == mapping
    assert not any("/defaults?" in call.args[1] for call in rest.call.call_args_list)
    assert all(c.args[0] != "PATCH" for c in rest.call.call_args_list)


def test_cu_complete_two_model_override_does_not_require_account_defaults():
    rest = Mock()
    rest.call.return_value = ({
        "models": {"completion": "prebuilt-analyzer-completion",
                   "embedding": "prebuilt-analyzer-embedding"},
        "supportedModels": {"completion": ["gpt-4.1"], "embedding": ["text-embedding-3-large"]},
    }, {})
    mapping = {"prebuilt-analyzer-completion": "fsi-showcase-cu-completion",
               "prebuilt-analyzer-embedding": "fsi-showcase-cu-embedding"}
    result = showcase.ContentUnderstanding(rest, CU, mapping).preflight()
    assert result["defaults_read"] is False
    assert result["defaults"] is None
    assert result["request_model_deployments"] == mapping
    assert rest.call.call_count == 1


@pytest.mark.parametrize("mapping", [[], "", {"": "model"}, {"alias": ""}, {"alias": "../model"}])
def test_cu_rejects_malformed_override_before_remote_effects(mapping):
    rest = Mock()
    with pytest.raises(showcase.ShowcaseError):
        showcase.ContentUnderstanding(rest, CU, mapping)
    rest.call.assert_not_called()


def test_cu_unknown_alias_does_not_fall_back_to_shared_defaults():
    rest = Mock()
    rest.call.return_value = ({"models": {"completion": "expected-alias"}}, {})
    with pytest.raises(showcase.ShowcaseError, match="alias not used"):
        showcase.ContentUnderstanding(rest, CU, {"typo-alias": "existing"}).preflight()
    assert rest.call.call_count == 1


def test_cu_journals_actual_result_and_refuses_existing_evidence(tmp_path):
    output = tmp_path / "cu.json"
    rest = cu_rest([extracted()])
    result = showcase.ContentUnderstanding(rest, CU).analyze(evidence_path=output)
    assert json.loads(output.read_text()) == result
    assert result["service"] == "Azure AI Content Understanding"
    assert result["state"] == "Succeeded"
    assert result["operation_location"] == OPERATION
    assert len(result["document_sha256"]) == 64
    rest.call.reset_mock()
    with pytest.raises(FileExistsError):
        showcase.ContentUnderstanding(rest, CU).analyze(evidence_path=output)
    rest.call.assert_not_called()


def test_cu_timeout_retains_resumable_operation_without_claiming_cancellation(tmp_path, monkeypatch):
    output = tmp_path / "timeout.json"
    rest = cu_rest([{"status": "Running"}])
    monkeypatch.setattr(showcase.time, "monotonic", Mock(side_effect=[0, 0, 2, 2]))
    monkeypatch.setattr(showcase.time, "sleep", Mock())
    with pytest.raises(showcase.ShowcaseError, match="polling timeout"):
        showcase.ContentUnderstanding(rest, CU).analyze(timeout=1, evidence_path=output)
    result = json.loads(output.read_text())
    assert result["operation_location"] == OPERATION
    assert result["state"] == "timed-out-operation-may-still-run"


@pytest.mark.parametrize("confidence", [None, True, -0.1, 1.1, float("nan"), float("inf"), "0.95"])
def test_cu_grounding_requires_valid_native_confidence(confidence):
    result = extracted()
    result["result"]["contents"][0]["fields"]["InvoiceId"]["confidence"] = confidence
    with pytest.raises(showcase.ShowcaseError, match="confidence"):
        showcase.validate_extraction(result)


def test_cu_rejects_wrong_invoice_identity_even_when_grounded():
    result = extracted()
    result["result"]["contents"][0]["fields"]["InvoiceId"]["valueString"] = "OTHER-INVOICE"
    with pytest.raises(showcase.ShowcaseError, match="expected grounded synthetic invoice"):
        showcase.validate_extraction(result)


def test_cu_invoice_identity_must_occur_in_its_actual_text_span():
    result = extracted()
    result["result"]["contents"][0]["markdown"] = "UNRELATED-TEXT"
    with pytest.raises(showcase.ShowcaseError, match="expected grounded synthetic invoice"):
        showcase.validate_extraction(result)


def test_cu_containers_need_no_invented_confidence_when_scalar_fields_are_grounded():
    result = extracted()
    fields = result["result"]["contents"][0]["fields"]
    fields["Group"] = {
        "type": "object", "valueObject": {"Nested": copy.deepcopy(fields["InvoiceId"])},
        "spans": [{"offset": 0, "length": 14}],
    }
    showcase.validate_extraction(result)


@pytest.mark.parametrize("damage", ["no-fields", "no-spans", "bad-span", "wrong-analyzer", "no-source"])
def test_cu_success_without_valid_grounding_is_failure(damage):
    result = extracted()
    field = result["result"]["contents"][0]["fields"]["InvoiceId"]
    if damage == "no-fields":
        result["result"]["contents"][0]["fields"] = {}
    elif damage == "no-spans":
        field["spans"] = []
    elif damage == "bad-span":
        field["spans"][0]["length"] = 9999
    elif damage == "wrong-analyzer":
        result["result"]["analyzerId"] = "other"
    else:
        field.pop("source")
    with pytest.raises(showcase.ShowcaseError):
        showcase.validate_extraction(result)


def preflight_rest(operation="upsert"):
    rest = Mock()
    rest.call.side_effect = [
        ({"name": "additive-showcase", "location": "eastus", "sku": {"name": "basic"},
          "identity": {"principalId": PRINCIPAL}, "properties": {
              "semanticSearch": "free", "disableLocalAuth": True,
              "provisioningState": "succeeded"}}, {}),
        ({"value": [{"properties": {"roleDefinitionId": "/roles/" + showcase.ROLES[operation]}}]}, {}),
        ({"value": []}, {}), ({"value": []}, {}),
    ]
    return rest


def test_preflight_only_reads_explicit_additive_resource():
    rest = preflight_rest()
    result = showcase.preflight_search(rest, showcase.Knowledge(rest, SEARCH),
                                       RESOURCE, PRINCIPAL, "upsert")
    assert result["verified_role"] == showcase.ROLES["upsert"]
    assert all(c.args[0] == "GET" for c in rest.call.call_args_list)
    assert RESOURCE in rest.call.call_args_list[0].args[1]
    assert rest.call.call_args_list[-1].args[1].endswith("/knowledgebases?api-version=2026-04-01")


def test_preflight_missing_role_stops_before_any_mutation():
    rest = preflight_rest("query")
    with pytest.raises(showcase.ShowcaseError, match="grant"):
        showcase.preflight_search(rest, showcase.Knowledge(rest, SEARCH),
                                  RESOURCE, PRINCIPAL, "upsert")
    assert rest.call.call_count == 2
    assert all(c.args[0] == "GET" for c in rest.call.call_args_list)


def test_cli_local_validation_needs_no_credentials(monkeypatch, capsys):
    monkeypatch.setattr(showcase, "Rest", Mock(side_effect=AssertionError("No Azure allowed")))
    assert showcase.main(["validate-corpus"]) == 0
    assert len(json.loads(capsys.readouterr().out)["validated_sources"]) == 6
