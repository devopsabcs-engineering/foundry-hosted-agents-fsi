"""Operator-only, synthetic native Foundry demonstrations; no deployment changes.

Requires azure-ai-projects==2.6.0 and Azure Identity. With no subcommand the
CLI performs read-only preflight. Mutations always require a named subcommand.
"""

import argparse
from datetime import timedelta
import hashlib
from io import BytesIO
import json
import math
import re
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from uuid import UUID
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = ROOT / "data" / "showcase" / "runtime-skill" / "SKILL.md"
PREFIX = "showcase-synthetic-"
SCOPES = {
    "fixture-alice": "showcase-synthetic-operator-alice-v1",
    "fixture-bob": "showcase-synthetic-operator-bob-v1",
}
MEMORIES = {
    "fixture-alice": "SYNTHETIC-ALICE-V1 prefers French workshop explanations.",
    "fixture-bob": "SYNTHETIC-BOB-V1 prefers English workshop explanations.",
}
FIXTURE = {
    "synthetic": True,
    "fixture_id": "foundry-native-showcase-v2",
    "reference": (
        "SYNTHETIC TRAINING ONLY. This educational workshop demonstrates a fictional "
        "Ontario auto-insurance quote-preparation workflow. It contains no real "
        "applicant, policy, price, insurer decision or personal information. "
        "The agent accepts a fabricated case reference such as CASE-SYN-001. "
        "Intake validates the reference before any read-only application or rulebook "
        "lookup. The application MCP returns synthetic application details. The "
        "rulebook MCP returns pinned educational rules under RULEBOOK-SYN-ON. "
        "The deterministic calculator is distinct from a language model. The agent "
        "prepares a draft and submits it as PENDING_REVIEW. Only an authorized "
        "employee may approve, reject or revise a draft. An applicant-facing "
        "message must never disclose an amount before employee approval. "
        "The same bounded response is available in English and French. "
        "An invalid reference produces a bounded rejection without tool access. "
        "Cosmos DB persists business approval state and audit records. Native "
        "Foundry memory stores preferences, not the authoritative approval record. "
        "Memory scopes partition records but do not authenticate or authorize users. "
        "Project RBAC and application authorization remain necessary. Runtime "
        "skills in this showcase are authored by the project, not prebuilt Microsoft "
        "skills. A registered skill is not proof that an agent consumed it. "
        "Native evaluation uses versioned built-in evaluators and retained run IDs. "
        "Relevant and irrelevant retrieval contexts are measured separately. "
        "No output from this workshop is binding, delivered as insurance, or "
        "authorized for model training. Generate questions and answers only about "
        "these fictional technical and governance facts."
    ),
    "records": [
        {"id": "SYNTHETIC-ALICE-V1", "language": "fr", "topic": "workshop"},
        {"id": "SYNTHETIC-BOB-V1", "language": "en", "topic": "workshop"},
    ],
}
SCOPE_WARNING = (
    "Scope keys are logical namespaces, NOT caller authorization. These keys bind "
    "only operator-configured synthetic fixture identities. Do not expose this CLI "
    "or scope selection to an end-user UI. Project RBAC remains required."
)
GENERATION_STATUSES = {"queued", "in_progress", "succeeded", "failed", "cancelled"}
LEGACY_GENERATION_REFERENCE_SHA256 = "129d4f7ed93e532ba3762057caaea0e0efa2d976a23e73a315f6cf46934033f0"
GENERATION_PROMPT = (
    "Generate standalone English and French technical question-answer pairs "
    "grounded only in the supplied synthetic reference. Cover architecture, "
    "intake, read-only MCP, calculator, employee approval, bilingual output, "
    "memory scope versus authorization, versioning, evaluation and tracing. "
    "Do not generate applicant profiles, prices or actual insurer policies."
)


class ShowcaseError(ValueError):
    """A failed safety check or an unsuccessful native operation."""


def validate_project_endpoint(value):
    endpoint = urlsplit(value)
    if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username
            or endpoint.password or endpoint.query or endpoint.fragment
            or not endpoint.hostname.endswith(".services.ai.azure.com")
            or endpoint.port not in (None, 443)
            or not re.fullmatch(r"/api/projects/[A-Za-z0-9_-]+", endpoint.path)):
        raise ShowcaseError("Use an explicit HTTPS Foundry /api/projects/<project> endpoint")
    return value


def plain(value):
    if hasattr(value, "as_dict"):
        return value.as_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def synthetic_name(value):
    if not value.startswith(PREFIX) or len(value) > 80:
        raise argparse.ArgumentTypeError(f"Use an isolated name starting with {PREFIX}")
    if not all(c.isascii() and (c.isalnum() or c == "-") for c in value):
        raise argparse.ArgumentTypeError("Names must contain ASCII letters, digits, or hyphens")
    return value


def positive(value):
    number = float(value)
    if not math.isfinite(number) or not 0 < number <= 3600:
        raise argparse.ArgumentTypeError("Value must be greater than zero and at most 3600")
    return number


def validate_fixture(data):
    try:
        decoded = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ShowcaseError("Input must be the exported synthetic JSON fixture") from exc
    if json.dumps(decoded, sort_keys=True) != json.dumps(FIXTURE, sort_keys=True):
        raise ShowcaseError("Only the exact exported synthetic fixture is accepted; no customer data")


def fixture_bytes(path):
    data = Path(path).read_bytes()
    if len(data) > 4096:
        raise ShowcaseError("Synthetic input exceeds the 4096-byte limit")
    validate_fixture(data)
    return data


def sdk_models():
    from azure.ai.projects import models

    return models


def file_content(openai, file_id):
    response = openai.files.content(file_id)
    data = response.content
    if len(data) > 32768:
        raise ShowcaseError("Source is not the bounded synthetic fixture")
    if (data != generation_reference_bytes()
            and hashlib.sha256(data).hexdigest() != LEGACY_GENERATION_REFERENCE_SHA256):
        validate_fixture(data)
    return data


def generation_reference_bytes():
    from native_knowledge_showcase import load_corpus

    documents = load_corpus()
    text = "\n\n".join([
        FIXTURE["reference"],
        (ROOT / "data" / "showcase" / "generation-reference.txt").read_text(encoding="utf-8"),
        *[f'{document["id"]}: {document["title"]}\n{document["content"]}'
          for document in documents],
    ]).encode("utf-8")
    if not 1024 <= len(text) <= 32768:
        raise ShowcaseError("Pinned generation reference must contain 1KB to 32KB of synthetic context")
    return text


def preflight(project):
    return {
        "memory_stores": [plain(x) for x in project.beta.memory_stores.list()],
        "skills": [plain(x) for x in project.beta.skills.list()],
        "generation_jobs": [plain(x) for x in project.beta.datasets.list_generation_jobs()],
        "prerequisites": [
            "Memory needs explicit chat and embedding deployment names with supported models.",
            "Generation needs an explicit service-supported base model name (not assumed deployment name).",
            "Skill registration is not runtime consumption; a compatible runtime must invoke it.",
            "Dataset upload additionally needs a project storage connection.",
        ],
        "warnings": [SCOPE_WARNING],
        "mutated": False,
    }


def create_memory_store(project, args):
    models = sdk_models()
    return plain(project.beta.memory_stores.create(
        name=args.store,
        definition=models.MemoryStoreDefaultDefinition(
            chat_model=args.chat_model,
            embedding_model=args.embedding_model,
            options=models.MemoryStoreDefaultOptions(
                default_ttl_seconds=timedelta(seconds=args.ttl_seconds),
            ),
        ),
        description="Isolated synthetic workshop memory; not an authorization boundary.",
    ))


def memory_demo(project, args):
    api = project.beta.memory_stores
    scope = SCOPES[args.scope]
    if args.command == "memory-seed":
        existing = list(api.list_memories(args.store, scope=scope))
        matches = [x for x in existing if x["content"] == MEMORIES[args.scope]]
        memory = matches[0] if matches else api.create_memory(
            args.store, scope=scope, content=MEMORIES[args.scope], kind="user_profile",
        )
        return {
            "memory": plain(memory), "reused": bool(matches),
            "warnings": [SCOPE_WARNING, "Sequentially repeatable; concurrent seed calls are not atomic."],
        }
    if args.command == "memory-list":
        return {"memories": [plain(x) for x in api.list_memories(args.store, scope=scope)],
                "scope": scope, "warnings": [SCOPE_WARNING]}
    # A positive retrieval is required as well as absence in the other scope:
    # an empty store or an unavailable index cannot produce a false PASS.
    other = next(key for key in SCOPES if key != args.scope)
    positive_result = plain(api.search_memories(
        args.store, scope=scope, items=MEMORIES[args.scope],
    ))
    negative_result = plain(api.search_memories(
        args.store, scope=SCOPES[other], items=MEMORIES[args.scope],
    ))
    marker = MEMORIES[args.scope].split()[0]
    if marker not in json.dumps(positive_result):
        raise ShowcaseError("Positive memory retrieval missing; seed first or wait for indexing")
    if marker in json.dumps(negative_result):
        raise ShowcaseError("Synthetic scope-negative check FAILED: other scope returned the marker")
    return {
        "scope": scope, "negative_scope": SCOPES[other],
        "positive": positive_result, "negative": negative_result,
        "scope_negative_check": "passed", "warnings": [SCOPE_WARNING],
    }


def register_skill(project, args):
    path = Path(args.file).resolve()
    if path != SKILL_FILE.resolve():
        raise ShowcaseError("Register only the project-authored data/showcase/runtime-skill/SKILL.md")
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3 or not text.startswith("---\n"):
        raise ShowcaseError("Runtime skill needs YAML frontmatter and Markdown instructions")
    models = sdk_models()
    version = project.beta.skills.create(
        args.name,
        inline_content=models.SkillInlineContent(
            description="Project-authored synthetic bilingual workshop briefing; not a Microsoft built-in.",
            instructions=parts[2].strip(),
            metadata={"author": "project", "sha256": hashlib.sha256(text.encode()).hexdigest()},
        ),
        default=False,
    )
    return {"skill": plain(version), "evidence_state": "registered", "consumed": False,
            "note": "Each registration creates an immutable version; preserve its exact version."}


def attach_skill(project, args):
    models = sdk_models()
    skill = project.beta.skills.get_version(args.name, args.version)
    toolbox = project.toolboxes.create_version(
        args.toolbox, tools=[],
        skills=[models.ToolboxSkillReference(name=args.name, version=args.version)],
        description="Separate synthetic showcase toolbox; no production tools or agent updates.",
    )
    return {"skill": plain(skill), "toolbox": plain(toolbox),
            "evidence_state": "attached", "consumed": False,
            "note": "Attachment is to this isolated toolbox only, not to any running agent."}


def consume_skill(project, openai, args):
    discovered = [plain(skill) for skill in project.beta.skills.list()]
    if not any(skill.get("name") == args.name for skill in discovered):
        raise ShowcaseError("Requested skill was not discovered in the native project catalog")
    skill = plain(project.beta.skills.get_version(args.name, args.version))
    if skill.get("name") != args.name or skill.get("version") != args.version or not skill.get("id"):
        raise ShowcaseError("Native catalog did not resolve the exact pinned skill version")
    archive = bytearray()
    for chunk in project.beta.skills.download_version(args.name, args.version):
        archive.extend(chunk)
        if len(archive) > 65536:
            raise ShowcaseError("Native skill archive exceeds the synthetic showcase limit")
    with zipfile.ZipFile(BytesIO(archive)) as bundle:
        entries = bundle.infolist()
        if len(entries) != 1 or entries[0].filename != "SKILL.md" or entries[0].file_size > 16384:
            raise ShowcaseError("Native skill must contain only a bounded SKILL.md, never executable files")
        downloaded = bundle.read(entries[0]).decode("utf-8")
    parts = downloaded.split("---", 2)
    if not downloaded.startswith("---\n") or len(parts) != 3:
        raise ShowcaseError("Downloaded native skill has no valid Markdown body")
    instructions = parts[2].strip()
    expected = SKILL_FILE.read_text(encoding="utf-8").split("---", 2)[2].strip()
    if instructions != expected:
        raise ShowcaseError("Native skill content differs from the reviewed synthetic project skill")
    identity = args.scope
    preference = "French" if identity == "fixture-alice" else "English"
    languages = ["Francais", "English"] if preference == "French" else ["English", "Francais"]
    output_schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            **{language: {"type": "string"} for language in languages},
            "synthetic": {"type": "boolean", "enum": [True]},
            "approved": {"type": "boolean", "enum": [False]},
        },
        "required": ["English", "Francais", "synthetic", "approved"],
    }
    metadata = {"showcase_skill_id": skill["id"], "showcase_skill_version": args.version}
    response = openai.responses.create(
        model=args.model,
        instructions=(
            instructions + "\nReturn the bilingual explanation in the structured English/Francais "
            "fields. Mark synthetic=true and approved=false. Do not include any monetary amount."
        ),
        input=(
            f"For {'SYNTHETIC-ALICE-V1' if identity == 'fixture-alice' else 'SYNTHETIC-BOB-V1'}, "
            f"explain why an employee must approve a synthetic draft before preview. "
            f"The configured preference is {preference}."
        ),
        tools=[],
        text={"format": {
            "type": "json_schema", "name": "synthetic_bilingual_skill_brief",
            "schema": output_schema, "strict": True,
        }},
        max_output_tokens=700,
        metadata=metadata,
    )
    native_response = plain(response)
    if (
        response.status != "completed" or not response.id or not response.output_text
        or native_response.get("metadata") != metadata
    ):
        raise ShowcaseError("Native skill consumer returned no completed response with pinned skill lineage")
    result = json.loads(response.output_text)
    if (
        not isinstance(result, dict)
        or set(result) != {"English", "Francais", "synthetic", "approved"}
        or next(iter(result)) != languages[0]
        or result["synthetic"] is not True or result["approved"] is not False
        or any(not isinstance(result[key], str) or not result[key].strip()
               for key in ["English", "Francais"])
        or re.search(r"[$\u20ac\u00a3]|\b\d[\d.,]*\s*(?:CAD|USD|dollars?|euros?)\b",
                     result["English"] + result["Francais"], re.IGNORECASE)
    ):
        raise ShowcaseError("Native skill consumer violated the bounded synthetic bilingual contract")
    return {
        "skill": skill, "evidence_state": "consumed", "consumed": True,
        "runtime": "isolated operator Responses consumer, not the hosted quote agent",
        "discovered": True, "downloaded_instructions_sha256": hashlib.sha256(
            instructions.encode("utf-8")
        ).hexdigest(),
        "response_id": response.id, "model_deployment": args.model,
        "result": result, "native_response": native_response,
    }


def upload(project, openai, args):
    data = fixture_bytes(args.file)
    if args.command == "file-upload":
        return {"file": plain(openai.files.create(
            file=(Path(args.file).with_suffix(".txt").name, generation_reference_bytes(), "text/plain"),
            purpose="user_data",
        )), "synthetic_fixture": FIXTURE["fixture_id"]}
    return {"dataset": plain(project.datasets.upload_file(
        name=args.name, version=args.version, file_path=str(Path(args.file).resolve()),
        connection_name=args.connection,
    )), "synthetic_fixture": FIXTURE["fixture_id"]}


def submit_generation(project, openai, args):
    file_content(openai, args.file_id)
    models = sdk_models()
    job = models.DataGenerationJob(inputs=models.DataGenerationJobInputs(
        name=args.name,
        sources=[
            models.FileDataGenerationJobSource(
                id=args.file_id,
                description="Self-contained fictional workshop architecture and governance reference.",
            ),
            models.PromptDataGenerationJobSource(
                prompt=GENERATION_PROMPT,
            ),
        ],
        options=models.SimpleQnADataGenerationJobOptions(
            max_samples=args.samples,
            model_options=models.DataGenerationModelOptions(model=args.model),
        ),
        # Fine-tuning scenario yields native Azure OpenAI file outputs, which can
        # be downloaded without inventing an evaluation-dataset storage URL.
        scenario="supervised_finetuning",
        output_options=models.DataGenerationJobOutputOptions(name=args.name),
    ))
    poller = project.beta.datasets.begin_create_generation_job(
        job, operation_id=str(UUID(str(args.operation_id))), polling=False,
    )
    job_id = poller.details["job_id"]
    if not job_id:
        raise ShowcaseError("Native service returned no job ID; do not retry with a new operation ID")
    submitted = plain(project.beta.datasets.get_generation_job(job_id))
    check_job(submitted, job_id)
    return {"job_id": job_id, "operation_id": str(args.operation_id),
            "job": submitted,
            "source_file_id": args.file_id, "local_generation_fallback": False}


def check_job(job, job_id):
    status = job["status"]
    if status not in GENERATION_STATUSES:
        raise ShowcaseError(f"Unknown native job status: {status}")
    if status in {"failed", "cancelled"}:
        raise ShowcaseError(json.dumps({"job_id": job_id, "status": status,
                                        "error": job.get("error")}))


def get_job(project, args, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + args.wait_seconds
    while True:
        job = plain(project.beta.datasets.get_generation_job(args.job_id))
        check_job(job, args.job_id)
        status = job["status"]
        if status == "succeeded" or not args.wait_seconds:
            return job
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError(f"Native job {args.job_id} still {status}; resume with generation-status")
        sleep(min(args.poll_seconds, remaining))


def download_generation(project, openai, args):
    job = get_job(project, args)
    if job["status"] != "succeeded":
        raise ShowcaseError("Download requires a succeeded native job")
    inputs = job.get("inputs", job)
    if not inputs.get("name", "").startswith(PREFIX):
        raise ShowcaseError("Job does not identify an isolated synthetic showcase")
    sources = inputs.get("sources", [])
    files = [source for source in sources if source.get("type") == "file"]
    prompts = [source for source in sources if source.get("type") == "prompt"]
    if (
        len(files) != 1 or len(prompts) > 1 or len(sources) != len(files) + len(prompts)
        or any(source.get("prompt") != GENERATION_PROMPT for source in prompts)
    ):
        raise ShowcaseError("Job must reference one verified synthetic file and only the pinned prompt")
    file_content(openai, files[0]["id"])
    outputs = job.get("result", {}).get("outputs", [])
    if not any(x.get("type") == "file" and x.get("id") == args.file_id for x in outputs):
        raise ShowcaseError("Requested file is not a native output of this successful job")
    response = openai.files.content(args.file_id)
    # Exclusive creation prevents overwriting prior evidence or unrelated files.
    with Path(args.download_file).open("xb") as stream:
        stream.write(response.content)
    return {"job_id": args.job_id, "file_id": args.file_id,
            "download_file": str(Path(args.download_file).resolve()),
            "sha256": hashlib.sha256(response.content).hexdigest(),
            "review_required": "Generated synthetic output still requires human review; not training approval."}


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--endpoint", required=True)
    cli.add_argument("--output", help="JSON evidence path; stdout if omitted; refuses overwrite")
    cli.add_argument("--timeout", type=positive, default=30, help="Per-request timeout in seconds")
    commands = cli.add_subparsers(dest="command")
    commands.add_parser("preflight")
    fixture = commands.add_parser("fixture-export", help="Write only the fixed synthetic input locally")
    fixture.add_argument("--file", required=True)
    create = commands.add_parser("memory-create")
    create.add_argument("--store", type=synthetic_name, required=True)
    create.add_argument("--chat-model", required=True)
    create.add_argument("--embedding-model", required=True)
    create.add_argument("--ttl-seconds", type=positive, required=True)
    for command in ("memory-seed", "memory-list", "memory-search"):
        sub = commands.add_parser(command)
        sub.add_argument("--store", type=synthetic_name, required=True)
        sub.add_argument("--scope", choices=SCOPES, required=True)
    register = commands.add_parser("skill-register")
    register.add_argument("--name", type=synthetic_name, required=True)
    register.add_argument("--file", required=True)
    consume = commands.add_parser("skill-consume")
    consume.add_argument("--name", type=synthetic_name, required=True)
    consume.add_argument("--version", required=True)
    consume.add_argument("--model", required=True)
    consume.add_argument("--scope", choices=SCOPES, required=True)
    attach = commands.add_parser("skill-attach")
    attach.add_argument("--name", type=synthetic_name, required=True)
    attach.add_argument("--version", required=True)
    attach.add_argument("--toolbox", type=synthetic_name, required=True)
    for command in ("file-upload", "dataset-upload"):
        sub = commands.add_parser(command)
        sub.add_argument("--file", required=True)
        if command == "dataset-upload":
            sub.add_argument("--name", type=synthetic_name, required=True)
            sub.add_argument("--version", required=True)
            sub.add_argument("--connection", required=True)
    submit = commands.add_parser("generation-submit")
    submit.add_argument("--name", type=synthetic_name, required=True)
    submit.add_argument("--file-id", required=True)
    submit.add_argument("--model", required=True, help="Service-supported base model name")
    submit.add_argument("--samples", type=int, choices=range(15, 101), required=True)
    submit.add_argument("--operation-id", type=UUID, required=True, help="Reuse UUID for idempotent retry")
    for command in ("generation-status", "generation-download"):
        sub = commands.add_parser(command)
        sub.add_argument("--job-id", required=True)
        sub.add_argument("--wait-seconds", type=positive, default=0)
        sub.add_argument("--poll-seconds", type=positive, default=5)
        if command == "generation-download":
            sub.add_argument("--file-id", required=True)
            sub.add_argument("--download-file", required=True)
    return cli


def execute(project, openai, args):
    if args.command in (None, "preflight"):
        return preflight(project)
    if args.command == "memory-create":
        return create_memory_store(project, args)
    if args.command.startswith("memory-"):
        return memory_demo(project, args)
    if args.command == "skill-register":
        return register_skill(project, args)
    if args.command == "skill-consume":
        return consume_skill(project, openai, args)
    if args.command == "skill-attach":
        return attach_skill(project, args)
    if args.command in ("file-upload", "dataset-upload"):
        return upload(project, openai, args)
    if args.command == "generation-submit":
        return submit_generation(project, openai, args)
    if args.command == "generation-status":
        return {"job": get_job(project, args)}
    if args.command == "generation-download":
        return download_generation(project, openai, args)
    raise ShowcaseError(f"Unsupported command: {args.command}")


def main(argv=None):
    args = parser().parse_args(argv)
    validate_project_endpoint(args.endpoint)
    if args.output and Path(args.output).exists():
        raise FileExistsError(args.output)
    if args.output and not Path(args.output).parent.is_dir():
        raise FileNotFoundError(f"Evidence directory must already exist: {Path(args.output).parent}")
    if args.command == "fixture-export":
        with Path(args.file).open("x", encoding="utf-8") as stream:
            json.dump(FIXTURE, stream, ensure_ascii=False, indent=2)
        result = {"file": str(Path(args.file).resolve()), "synthetic": True}
    else:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        with DefaultAzureCredential() as credential, AIProjectClient(
            endpoint=args.endpoint, credential=credential,
            connection_timeout=args.timeout, read_timeout=args.timeout, retry_total=0,
        ) as project:
            needs_files = args.command in {
                "file-upload", "generation-submit", "generation-download", "skill-consume",
            }
            if needs_files:
                with project.get_openai_client() as client:
                    result = execute(project, client.with_options(
                        timeout=args.timeout, max_retries=0,
                    ), args)
            else:
                result = execute(project, None, args)
    evidence = {"schema_version": 1, "command": args.command or "preflight",
                "endpoint": args.endpoint, "result": result}
    encoded = json.dumps(evidence, ensure_ascii=False, indent=2, default=str)
    if args.output:
        with Path(args.output).open("x", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
    print(encoded)
    return 0


if __name__ == "__main__":
    from azure.core.exceptions import AzureError
    from openai import OpenAIError

    try:
        sys.exit(main())
    except (AzureError, OpenAIError, ValueError, OSError, TimeoutError) as exc:
        print(json.dumps({"schema_version": 1, "error": type(exc).__name__,
                          "message": str(exc)}), file=sys.stderr)
        sys.exit(1)
