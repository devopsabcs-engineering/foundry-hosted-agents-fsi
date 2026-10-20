"""Offline contracts for the operator-only native SDK showcase."""

import importlib.util
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import zipfile
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import UUID, uuid4

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "native_foundry_showcase", ROOT / "scripts" / "native_foundry_showcase.py",
)
showcase = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(showcase)
ENDPOINT = "https://example.services.ai.azure.com/api/projects/synthetic"
NAME = "showcase-synthetic-demo"
OPERATION_ID = "b4efdfdd-1f2b-4774-9d4e-e75742319631"


def test_exact_historical_generation_source_remains_downloadable_after_corpus_version_change(monkeypatch):
    historical = b"SYNTHETIC TRAINING ONLY: exact reviewed historical source"
    monkeypatch.setattr(
        showcase, "LEGACY_GENERATION_REFERENCE_SHA256", showcase.hashlib.sha256(historical).hexdigest(),
    )
    client = Mock()
    client.files.content.return_value.content = historical
    assert showcase.file_content(client, "historical-file") == historical
    client.files.content.return_value.content = historical + b" unreviewed change"
    with pytest.raises(showcase.ShowcaseError):
        showcase.file_content(client, "historical-file")


class Model(dict):
    """Minimal model double; separate tests also assert installed SDK contracts."""

    def __getattr__(self, name):
        return self[name]

    def as_dict(self):
        return dict(self)


@pytest.fixture
def tmp_path():
    """Keep all scratch I/O inside this repository, never OS temporary folders."""
    directory = ROOT / ".local" / f"native-showcase-tests-{uuid4().hex}"
    directory.mkdir(parents=True)
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


@pytest.fixture
def models(monkeypatch):
    api = SimpleNamespace(**{
        name: Model for name in (
            "MemoryStoreDefaultDefinition", "MemoryStoreDefaultOptions",
            "SkillInlineContent", "ToolboxSkillReference", "DataGenerationJob",
            "DataGenerationJobInputs", "FileDataGenerationJobSource", "PromptDataGenerationJobSource",
            "SimpleQnADataGenerationJobOptions", "DataGenerationModelOptions",
            "DataGenerationJobOutputOptions",
        )
    })
    monkeypatch.setattr(showcase, "sdk_models", lambda: api)
    return api


@pytest.fixture
def project():
    api = Mock()
    api.beta.memory_stores.list.return_value = []
    api.beta.skills.list.return_value = []
    api.beta.datasets.list_generation_jobs.return_value = []
    api.beta.memory_stores.list_memories.return_value = []
    return api


def args(command, *arguments):
    return showcase.parser().parse_args(["--endpoint", ENDPOINT, command, *arguments])


def file_api():
    client = Mock()
    client.files.content.return_value.content = json.dumps(showcase.FIXTURE).encode()
    return client


def test_default_preflight_only_reads_native_beta_namespaces(project):
    parsed = showcase.parser().parse_args(["--endpoint", ENDPOINT])
    result = showcase.execute(project, None, parsed)
    assert result["mutated"] is False
    assert "NOT caller authorization" in result["warnings"][0]
    assert [call[0] for call in project.mock_calls] == [
        "beta.memory_stores.list", "beta.skills.list", "beta.datasets.list_generation_jobs",
    ]


@pytest.mark.parametrize("name", ["quote-tools", "production", "showcase-synthetic-../prod",
                                 "showcase-synthetic-ä", "showcase-synthetic-" + "x" * 80])
def test_reserved_or_invalid_names_rejected_before_network(name):
    with pytest.raises(SystemExit):
        args("memory-create", "--store", name, "--chat-model", "chat",
             "--embedding-model", "embedding", "--ttl-seconds", "3600")


@pytest.mark.parametrize("scope", ["user-123", "production", "alice", "../../bob"])
def test_arbitrary_scope_cannot_be_supplied(scope):
    with pytest.raises(SystemExit):
        args("memory-list", "--store", NAME, "--scope", scope)


@pytest.mark.parametrize("value", ["0", "-1", "inf", "nan", "3601"])
def test_timeouts_and_ttl_are_finite_and_bounded(value):
    with pytest.raises(SystemExit):
        showcase.parser().parse_args(["--endpoint", ENDPOINT, "--timeout", value])


def test_store_definition_uses_timedelta_and_explicit_models(project, models):
    parsed = args("memory-create", "--store", NAME, "--chat-model", "explicit-chat",
                  "--embedding-model", "explicit-embedding", "--ttl-seconds", "1800")
    showcase.execute(project, None, parsed)
    call = project.beta.memory_stores.create.call_args.kwargs
    assert call["name"] == NAME
    assert call["definition"]["chat_model"] == "explicit-chat"
    assert call["definition"]["embedding_model"] == "explicit-embedding"
    assert call["definition"]["options"]["default_ttl_seconds"].total_seconds() == 1800


def test_seed_is_sequentially_repeatable_and_only_uses_fixed_fixture(project):
    parsed = args("memory-seed", "--store", NAME, "--scope", "fixture-alice")
    memory = {"memory_id": "mem-real", "content": showcase.MEMORIES["fixture-alice"]}
    project.beta.memory_stores.create_memory.return_value = memory
    first = showcase.execute(project, None, parsed)
    project.beta.memory_stores.list_memories.return_value = [memory]
    second = showcase.execute(project, None, parsed)
    assert first["reused"] is False and second["reused"] is True
    project.beta.memory_stores.create_memory.assert_called_once_with(
        NAME, scope=showcase.SCOPES["fixture-alice"],
        content=showcase.MEMORIES["fixture-alice"], kind="user_profile",
    )


def test_memory_list_has_fixed_operator_scope(project):
    parsed = args("memory-list", "--store", NAME, "--scope", "fixture-bob")
    showcase.execute(project, None, parsed)
    project.beta.memory_stores.list_memories.assert_called_once_with(
        NAME, scope=showcase.SCOPES["fixture-bob"],
    )


@pytest.mark.parametrize("positive,negative,passes", [
    ({"memories": [{"content": showcase.MEMORIES["fixture-alice"]}]}, {"memories": []}, True),
    ({"memories": []}, {"memories": []}, False),
    ({"memories": [{"content": showcase.MEMORIES["fixture-alice"]}]},
     {"memories": [{"content": showcase.MEMORIES["fixture-alice"]}]}, False),
])
def test_scope_negative_requires_positive_retrieval_and_no_leak(project, positive, negative, passes):
    parsed = args("memory-search", "--store", NAME, "--scope", "fixture-alice")
    project.beta.memory_stores.search_memories.side_effect = [positive, negative]
    if passes:
        assert showcase.execute(project, None, parsed)["scope_negative_check"] == "passed"
    else:
        with pytest.raises(showcase.ShowcaseError):
            showcase.execute(project, None, parsed)
    calls = project.beta.memory_stores.search_memories.call_args_list
    assert calls[0].kwargs["scope"] == showcase.SCOPES["fixture-alice"]
    assert calls[1].kwargs["scope"] == showcase.SCOPES["fixture-bob"]
    assert calls[0].kwargs["items"] == calls[1].kwargs["items"]


def test_registration_is_project_authored_not_consumption(project, models):
    parsed = args("skill-register", "--name", NAME, "--file", str(showcase.SKILL_FILE))
    project.beta.skills.create.return_value = {"id": "skill-real", "version": "7"}
    result = showcase.execute(project, None, parsed)
    assert result["evidence_state"] == "registered" and result["consumed"] is False
    call = project.beta.skills.create.call_args
    assert call.args == (NAME,)
    assert call.kwargs["default"] is False
    content = call.kwargs["inline_content"]
    assert content["metadata"]["author"] == "project"
    assert "not a Microsoft built-in" in content["description"]
    assert "## Evidence boundaries" in content["instructions"]
    assert not content["instructions"].startswith("---")
    project.toolboxes.create_version.assert_not_called()


def test_registration_rejects_arbitrary_runtime_instructions(project, models):
    parsed = args("skill-register", "--name", NAME, "--file", str(ROOT / "README.md"))
    with pytest.raises(showcase.ShowcaseError, match="project-authored"):
        showcase.execute(project, None, parsed)
    project.beta.skills.create.assert_not_called()


def test_attachment_is_pinned_to_separate_toolbox_and_not_agent(project, models):
    parsed = args("skill-attach", "--name", NAME, "--version", "7",
                  "--toolbox", "showcase-synthetic-skills")
    result = showcase.execute(project, None, parsed)
    assert result["evidence_state"] == "attached" and result["consumed"] is False
    project.beta.skills.get_version.assert_called_once_with(NAME, "7")
    call = project.toolboxes.create_version.call_args
    assert call.args == ("showcase-synthetic-skills",)
    assert call.kwargs["tools"] == []
    assert call.kwargs["skills"] == [{"name": NAME, "version": "7"}]
    project.agents.assert_not_called()
    project.toolboxes.update.assert_not_called()


@pytest.mark.parametrize("payload", [
    {"synthetic": True, "customer": "real customer"},
    {"synthetic": True, "fixture_id": "foundry-native-showcase-v1", "records": []},
    {**showcase.FIXTURE, "synthetic": 1},
    {**showcase.FIXTURE, "extra": "private information"},
])
def test_synthetic_label_alone_does_not_allow_arbitrary_data(payload):
    with pytest.raises(showcase.ShowcaseError):
        showcase.validate_fixture(json.dumps(payload).encode())


def test_file_upload_uses_project_openai_file_api(project, tmp_path):
    source = tmp_path / "synthetic.json"
    source.write_text(json.dumps(showcase.FIXTURE), encoding="utf-8")
    client = file_api()
    client.files.create.return_value = {"id": "file-real", "purpose": "user_data"}
    result = showcase.execute(project, client, args("file-upload", "--file", str(source)))
    assert result["file"]["id"] == "file-real"
    call = client.files.create.call_args.kwargs
    assert call["purpose"] == "user_data"
    assert call["file"] == ("synthetic.txt", showcase.generation_reference_bytes(), "text/plain")
    assert 1024 <= len(call["file"][1]) <= 32768
    assert 1024 <= len(source.read_bytes()) <= 4096


@pytest.fixture
def skill_consumer(project):
    name, version = "showcase-synthetic-bilingual-brief", "1"
    project.beta.skills.list.return_value = [{"name": name}]
    project.beta.skills.get_version.return_value = {
        "name": name, "version": version, "id": "skill-native:1",
    }
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("SKILL.md", showcase.SKILL_FILE.read_text(encoding="utf-8"))
    project.beta.skills.download_version.return_value = [archive.getvalue()]
    payload = {
        "Francais": "Exemple synthetique. Un employe revise le brouillon.",
        "English": "Synthetic workshop example. An employee reviews the draft.",
        "synthetic": True, "approved": False,
    }
    response = SimpleNamespace(
        id="resp-native", status="completed", output_text=json.dumps(payload),
        model_dump=lambda **kw: {
            "id": "resp-native", "status": "completed", "output_text": json.dumps(payload),
            "metadata": {"showcase_skill_id": "skill-native:1", "showcase_skill_version": "1"},
        },
    )
    client = Mock()
    client.responses.create.return_value = response
    parsed = args(
        "skill-consume", "--name", name, "--version", version,
        "--model", "existing-model", "--scope", "fixture-alice",
    )
    return project, client, parsed, payload, response


@pytest.mark.parametrize("scope,first_language", [
    ("fixture-alice", "Francais"), ("fixture-bob", "English"),
])
def test_native_skill_is_discovered_downloaded_and_consumed_without_agent_mutation(
    skill_consumer, scope, first_language,
):
    project, client, parsed, payload, response = skill_consumer
    parsed.scope = scope
    payload = {first_language: payload[first_language], **payload}
    response.output_text = json.dumps(payload)
    result = showcase.execute(project, client, parsed)
    assert result["consumed"] is True and result["discovered"] is True
    assert result["response_id"] == "resp-native"
    assert "not the hosted quote agent" in result["runtime"]
    call = client.responses.create.call_args.kwargs
    assert call["model"] == "existing-model"
    assert call["tools"] == []
    assert call["metadata"]["showcase_skill_id"] == "skill-native:1"
    assert next(iter(call["text"]["format"]["schema"]["properties"])) == first_language
    assert "Synthetic bilingual workshop brief" in call["instructions"]
    project.agents.create_version.assert_not_called()
    project.toolboxes.create_version.assert_not_called()


@pytest.mark.parametrize("failure", ["missing", "wrong-version", "changed-content", "executable"])
def test_native_skill_refuses_unreviewed_or_undiscovered_content_before_model_call(
    skill_consumer, failure,
):
    project, client, parsed, _, _ = skill_consumer
    if failure == "missing":
        project.beta.skills.list.return_value = []
    elif failure == "wrong-version":
        project.beta.skills.get_version.return_value["version"] = "2"
    else:
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr(
                "SKILL.md",
                "---\nname: unexpected\n---\nUnreviewed instructions"
                if failure == "changed-content"
                else showcase.SKILL_FILE.read_text(encoding="utf-8"),
            )
            if failure == "executable":
                bundle.writestr("script.py", "raise RuntimeError('never run')")
        project.beta.skills.download_version.return_value = [archive.getvalue()]
    with pytest.raises(showcase.ShowcaseError):
        showcase.execute(project, client, parsed)
    client.responses.create.assert_not_called()


@pytest.mark.parametrize("failure", [
    "amount", "empty-language", "approval", "failed-response", "missing-lineage", "language-order",
])
def test_native_skill_rejects_unbounded_or_failed_output(skill_consumer, failure):
    project, client, parsed, payload, response = skill_consumer
    if failure == "amount":
        payload["English"] = "The total is 100 CAD."
    elif failure == "empty-language":
        payload["Francais"] = ""
    elif failure == "approval":
        payload["approved"] = True
    elif failure == "missing-lineage":
        response.model_dump = lambda **kw: {}
    elif failure == "language-order":
        payload = {"English": payload["English"], "Francais": payload["Francais"],
                   "synthetic": True, "approved": False}
    else:
        response.status = "failed"
    response.output_text = json.dumps(payload)
    with pytest.raises(showcase.ShowcaseError):
        showcase.execute(project, client, parsed)


def test_dataset_upload_uses_nonbeta_dataset_version_api(project, tmp_path):
    source = tmp_path / "synthetic.json"
    source.write_text(json.dumps(showcase.FIXTURE), encoding="utf-8")
    parsed = args("dataset-upload", "--file", str(source), "--name", NAME,
                  "--version", "1", "--connection", "storage-explicit")
    showcase.execute(project, None, parsed)
    project.datasets.upload_file.assert_called_once_with(
        name=NAME, version="1", file_path=str(source.resolve()), connection_name="storage-explicit",
    )
    project.beta.datasets.upload_file.assert_not_called()


def test_bad_local_upload_is_rejected_before_mutation(project, tmp_path):
    source = tmp_path / "customer.json"
    source.write_text('{"synthetic":true,"customer":"private"}', encoding="utf-8")
    client = file_api()
    with pytest.raises(showcase.ShowcaseError):
        showcase.execute(project, client, args("file-upload", "--file", str(source)))
    client.files.create.assert_not_called()


def test_oversized_or_invalid_json_fixture_rejected(tmp_path):
    source = tmp_path / "oversize.json"
    source.write_bytes(b"x" * 4097)
    with pytest.raises(showcase.ShowcaseError, match="4096"):
        showcase.fixture_bytes(source)
    with pytest.raises(showcase.ShowcaseError, match="synthetic JSON"):
        showcase.validate_fixture(b"invalid")


def generation_args():
    return args("generation-submit", "--name", NAME, "--file-id", "file-input",
                "--model", "explicit-model", "--samples", "15", "--operation-id", OPERATION_ID)


@pytest.mark.parametrize("samples", ["0", "4", "14", "101"])
def test_generation_rejects_outside_native_minimum_and_workshop_cap(samples):
    with pytest.raises(SystemExit):
        args("generation-submit", "--name", NAME, "--file-id", "file-input",
             "--model", "explicit-model", "--samples", samples, "--operation-id", OPERATION_ID)


def test_actual_flattened_generation_result_can_download_only_its_grounded_output(project, tmp_path):
    project.beta.datasets.get_generation_job.return_value = {
        "id": "job-native", "status": "succeeded", "name": NAME,
        "sources": [
            {"type": "file", "id": "file-input"},
            {"type": "prompt", "prompt": showcase.GENERATION_PROMPT},
        ],
        "result": {"outputs": [{"type": "file", "id": "file-output"}]},
    }
    client = Mock()
    client.files.content.side_effect = [
        SimpleNamespace(content=showcase.generation_reference_bytes()),
        SimpleNamespace(content=b'{"messages":[]}\n'),
    ]
    output = tmp_path / "native.jsonl"
    result = showcase.execute(project, client, args(
        "generation-download", "--job-id", "job-native", "--file-id", "file-output",
        "--download-file", str(output),
    ))
    assert output.read_bytes() == b'{"messages":[]}\n'
    assert result["job_id"] == "job-native"
    assert len(result["sha256"]) == 64


def test_native_generation_shape_idempotency_and_no_polling_thread(project, models):
    parsed = generation_args()
    client = file_api()
    project.beta.datasets.begin_create_generation_job.return_value.details = {"job_id": "job-real"}
    project.beta.datasets.get_generation_job.return_value = {"id": "job-real", "status": "queued"}
    for _ in range(2):
        result = showcase.execute(project, client, parsed)
        assert result["job_id"] == "job-real"
        assert result["local_generation_fallback"] is False
    calls = project.beta.datasets.begin_create_generation_job.call_args_list
    assert len(calls) == 2 and calls[0] == calls[1]
    assert calls[0].kwargs == {"operation_id": OPERATION_ID, "polling": False}
    inputs = calls[0].args[0]["inputs"]
    assert inputs["sources"][0]["id"] == "file-input"
    assert inputs["options"]["max_samples"] == 15
    assert inputs["options"]["model_options"]["model"] == "explicit-model"
    assert inputs["scenario"] == "supervised_finetuning"
    assert inputs["output_options"]["name"] == NAME
    assert isinstance(parsed.operation_id, UUID)


def test_untrusted_remote_source_is_rejected_before_job_submission(project, models):
    client = file_api()
    client.files.content.return_value.content = b'{"synthetic":true}'
    with pytest.raises(showcase.ShowcaseError):
        showcase.execute(project, client, generation_args())
    project.beta.datasets.begin_create_generation_job.assert_not_called()


def test_missing_native_job_id_never_fabricates_success(project, models):
    project.beta.datasets.begin_create_generation_job.return_value.details = {"job_id": None}
    with pytest.raises(showcase.ShowcaseError, match="no job ID"):
        showcase.execute(project, file_api(), generation_args())
    project.beta.datasets.get_generation_job.assert_not_called()


def test_immediately_failed_submission_returns_real_job_failure(project, models):
    project.beta.datasets.begin_create_generation_job.return_value.details = {"job_id": "job-real"}
    project.beta.datasets.get_generation_job.return_value = {
        "id": "job-real", "status": "failed", "error": {"code": "model_unavailable"},
    }
    with pytest.raises(showcase.ShowcaseError, match="model_unavailable"):
        showcase.execute(project, file_api(), generation_args())


def test_service_error_propagates_without_local_generation_fallback(project, models):
    project.beta.datasets.begin_create_generation_job.side_effect = RuntimeError("native rejected")
    with pytest.raises(RuntimeError, match="native rejected"):
        showcase.execute(project, file_api(), generation_args())
    project.beta.datasets.begin_create_generation_job.assert_called_once()


@pytest.mark.parametrize("status", ["failed", "cancelled", "made-up"])
def test_unsuccessful_or_unknown_jobs_fail_loudly(project, status):
    project.beta.datasets.get_generation_job.return_value = {
        "id": "job-real", "status": status, "error": {"code": "unsupported_model"},
    }
    with pytest.raises(showcase.ShowcaseError, match=status):
        showcase.execute(project, None, args("generation-status", "--job-id", "job-real"))


def test_polling_is_bounded_and_resumable(project):
    parsed = args("generation-status", "--job-id", "job-real",
                  "--wait-seconds", "3", "--poll-seconds", "2")
    project.beta.datasets.get_generation_job.return_value = {"id": "job-real", "status": "queued"}
    clock = Mock(side_effect=[0, 0, 2, 3])
    sleep = Mock()
    with pytest.raises(TimeoutError, match="resume with generation-status"):
        showcase.get_job(project, parsed, clock=clock, sleep=sleep)
    assert [x.args[0] for x in sleep.call_args_list] == [2, 1]
    assert project.beta.datasets.get_generation_job.call_count == 3


def test_status_is_single_read_by_default(project):
    project.beta.datasets.get_generation_job.return_value = {"id": "job-real", "status": "queued"}
    result = showcase.execute(project, None, args("generation-status", "--job-id", "job-real"))
    assert result["job"]["status"] == "queued"
    project.beta.datasets.get_generation_job.assert_called_once_with("job-real")


def test_succeeded_poll_returns_native_result(project):
    project.beta.datasets.get_generation_job.side_effect = [
        {"id": "job-real", "status": "in_progress"},
        {"id": "job-real", "status": "succeeded", "result": {"generated_samples": 4}},
    ]
    parsed = args("generation-status", "--job-id", "job-real", "--wait-seconds", "3")
    result = showcase.get_job(project, parsed, clock=Mock(side_effect=[0, 0]), sleep=Mock())
    assert result["result"]["generated_samples"] == 4


def completed_job():
    return {
        "id": "job-real", "status": "succeeded",
        "inputs": {"name": NAME, "sources": [{"type": "file", "id": "file-input"}]},
        "result": {"outputs": [{"type": "file", "id": "file-output"}], "generated_samples": 4},
    }


def test_download_verifies_native_job_source_and_output_ids(project, tmp_path):
    target = tmp_path / "generated.jsonl"
    project.beta.datasets.get_generation_job.return_value = completed_job()
    client = file_api()
    client.files.content.side_effect = [
        SimpleNamespace(content=json.dumps(showcase.FIXTURE).encode()),
        SimpleNamespace(content=b'{"synthetic_generated":true}\n'),
    ]
    parsed = args("generation-download", "--job-id", "job-real", "--file-id", "file-output",
                  "--download-file", str(target))
    result = showcase.execute(project, client, parsed)
    assert target.read_bytes() == b'{"synthetic_generated":true}\n'
    assert result["file_id"] == "file-output" and len(result["sha256"]) == 64
    assert [x.args for x in client.files.content.call_args_list] == [
        ("file-input",), ("file-output",),
    ]


@pytest.mark.parametrize("change", ["output", "source", "name", "pending"])
def test_download_cannot_fetch_unrelated_files(project, tmp_path, change):
    job = completed_job()
    if change == "output":
        job["result"]["outputs"] = [{"type": "file", "id": "unrelated"}]
    elif change == "source":
        job["inputs"]["sources"] = [{"type": "prompt", "prompt": "unverified"}]
    elif change == "name":
        job["inputs"]["name"] = "production-data"
    else:
        job["status"] = "queued"
    project.beta.datasets.get_generation_job.return_value = job
    target = tmp_path / "must-not-exist.jsonl"
    with pytest.raises(showcase.ShowcaseError):
        showcase.execute(project, file_api(), args(
            "generation-download", "--job-id", "job-real", "--file-id", "file-output",
            "--download-file", str(target),
        ))
    assert not target.exists()


def test_local_fixture_export_no_sdk_or_cloud_needed(tmp_path, capsys):
    target = tmp_path / "synthetic.json"
    assert showcase.main(["--endpoint", ENDPOINT, "fixture-export", "--file", str(target)]) == 0
    showcase.fixture_bytes(target)
    assert json.loads(capsys.readouterr().out)["result"]["synthetic"] is True
    with pytest.raises(FileExistsError):
        showcase.main(["--endpoint", ENDPOINT, "fixture-export", "--file", str(target)])


def test_existing_evidence_file_prevents_mutation(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text("retain me", encoding="utf-8")
    with pytest.raises(FileExistsError):
        showcase.main(["--endpoint", ENDPOINT, "--output", str(evidence),
                       "fixture-export", "--file", str(tmp_path / "must-not-exist.json")])
    assert evidence.read_text(encoding="utf-8") == "retain me"
    assert not (tmp_path / "must-not-exist.json").exists()


def test_missing_evidence_directory_rejected_before_mutation(tmp_path):
    with pytest.raises(FileNotFoundError, match="Evidence directory"):
        showcase.main(["--endpoint", ENDPOINT,
                       "--output", str(tmp_path / "missing" / "evidence.json"),
                       "fixture-export", "--file", str(tmp_path / "must-not-exist.json")])
    assert not (tmp_path / "must-not-exist.json").exists()


@pytest.mark.parametrize("endpoint", [
    "http://example/api/projects/x", "https://example/agents",
    "https://example/api/projects/",
    "https://user:secret@example/api/projects/x",
    "https://example/api/projects/x?token=not-allowed",
])
def test_invalid_endpoint_rejected_before_cloud_or_local_write(endpoint, tmp_path):
    target = tmp_path / "must-not-exist.json"
    with pytest.raises(showcase.ShowcaseError, match="HTTPS Foundry"):
        showcase.main(["--endpoint", endpoint, "fixture-export", "--file", str(target)])
    assert not target.exists()


@pytest.mark.parametrize("command", ["preflight", "file-upload"])
def test_cli_has_explicit_transport_timeouts_and_no_automatic_retries(
    project, monkeypatch, tmp_path, command, capsys,
):
    projects_module = pytest.importorskip("azure.ai.projects")
    identity_module = pytest.importorskip("azure.identity")
    credential = MagicMock()
    project_context = MagicMock()
    project_context.__enter__.return_value = project
    factory = Mock(return_value=project_context)
    monkeypatch.setattr(projects_module, "AIProjectClient", factory)
    monkeypatch.setattr(identity_module, "DefaultAzureCredential", Mock(return_value=credential))
    source = tmp_path / "synthetic.json"
    source.write_text(json.dumps(showcase.FIXTURE), encoding="utf-8")
    extra = ["--file", str(source)] if command == "file-upload" else []
    client = MagicMock()
    project.get_openai_client.return_value = client
    client.__enter__.return_value.with_options.return_value.files.create.return_value = {"id": "file-real"}
    assert showcase.main(["--endpoint", ENDPOINT, "--timeout", "7", command, *extra]) == 0
    factory.assert_called_once_with(
        endpoint=ENDPOINT, credential=credential.__enter__.return_value,
        connection_timeout=7, read_timeout=7, retry_total=0,
    )
    if command == "file-upload":
        client.__enter__.return_value.with_options.assert_called_once_with(timeout=7, max_retries=0)
    else:
        project.get_openai_client.assert_not_called()
    assert json.loads(capsys.readouterr().out)["schema_version"] == 1
    project_context.__exit__.assert_called_once()
    credential.__exit__.assert_called_once()


def test_installed_sdk_230_contracts_and_wire_serialization():
    azure_models = pytest.importorskip("azure.ai.projects.models")
    from azure.ai.projects import AIProjectClient
    from azure.core.credentials import AzureKeyCredential

    project = AIProjectClient(ENDPOINT, AzureKeyCredential("offline-no-request"))
    assert callable(project.beta.datasets.begin_create_generation_job)
    assert not hasattr(project.beta.datasets, "create_generation_job")
    assert callable(project.datasets.upload_file)
    inputs = azure_models.DataGenerationJobInputs(
        name=NAME, sources=[azure_models.FileDataGenerationJobSource(id="file-input")],
        options=azure_models.SimpleQnADataGenerationJobOptions(
            max_samples=4, model_options=azure_models.DataGenerationModelOptions(model="explicit-model"),
        ), scenario="supervised_finetuning",
    )
    wire = azure_models.DataGenerationJob(inputs=inputs).as_dict()
    assert wire["inputs"]["sources"] == [{"type": "file", "id": "file-input"}]
    assert wire["inputs"]["options"]["type"] == "simple_qna"
    assert azure_models.ToolboxSkillReference(name=NAME, version="7").as_dict() == {
        "type": "skill_reference", "name": NAME, "version": "7",
    }
    project.close()


def test_implementation_uses_real_sdk_models_not_just_test_doubles(project, monkeypatch):
    azure_models = pytest.importorskip("azure.ai.projects.models")
    monkeypatch.setattr(showcase, "sdk_models", lambda: azure_models)
    showcase.execute(project, None, args(
        "memory-create", "--store", NAME, "--chat-model", "chat",
        "--embedding-model", "embed", "--ttl-seconds", "600",
    ))
    definition = project.beta.memory_stores.create.call_args.kwargs["definition"].as_dict()
    assert definition == {
        "kind": "default", "chat_model": "chat", "embedding_model": "embed",
        "options": {"default_ttl_seconds": 600},
    }
    showcase.execute(project, None, args(
        "skill-register", "--name", NAME, "--file", str(showcase.SKILL_FILE),
    ))
    inline = project.beta.skills.create.call_args.kwargs["inline_content"].as_dict()
    assert inline["metadata"]["author"] == "project"
    project.beta.datasets.begin_create_generation_job.return_value.details = {"job_id": "job-real"}
    project.beta.datasets.get_generation_job.return_value = {"id": "job-real", "status": "queued"}
    showcase.execute(project, file_api(), generation_args())
    wire = project.beta.datasets.begin_create_generation_job.call_args.args[0].as_dict()
    assert wire["inputs"]["sources"][0]["type"] == "file"
    assert wire["inputs"]["options"]["type"] == "simple_qna"
    assert wire["inputs"]["options"]["model_options"] == {"model": "explicit-model"}
