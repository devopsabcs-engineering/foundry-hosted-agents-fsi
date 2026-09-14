"""AUTHOR-ONLY -- this evaluation harness cannot run yet.

Gated behind G2 (platform/security), G3 (reproducible compatibility), and
G6 (regulatory/privacy) sign-off, and behind the more basic prerequisite
that no hosted quote-preparation-agent endpoint exists yet: this
repository has no `scripts/invoke-agent.sh` equivalent, no
Responses-protocol smoke-test harness, and
`src/quote-preparation-agent/main.py` is documented as a local-only entry
point (see `azure.yaml`'s own top-of-file gating banner). Do not remove
`main()`'s guard or wire `capture()` into a real hosted invocation until a
real hosted endpoint exists and all three gates are explicitly cleared by
their owners.

Adapted from the sibling `foundry-hosted-agents` repository's
`eval/run_hosted_evaluation.py`. `criteria()`, `collect_output_items()`,
and `evaluate()`'s Azure AI Evaluation SDK usage (`AIProjectClient`,
`client.evals.create`, `client.evals.runs.create`, and its completion
polling loop) are ported near-verbatim -- that logic only inspects the
Azure AI Evaluation SDK's payload shape and is domain-agnostic; it needs a
real hosted endpoint to run, not a rewrite. `agent_instructions()` is
adapted to AST-extract this repository's `AGENT_TASK_INSTRUCTIONS`
constant from `src/quote-preparation-agent/graph.py` instead of the
sibling's `REPORT_COMPOSER_PROMPT`. `capture()` is replaced entirely: the
sibling shells out to `scripts/invoke-agent.sh` to obtain live hosted
responses, and this repository has no equivalent, so `capture()` instead
raises immediately with a clear, explicit error rather than a silent
no-op or an invented invocation mechanism.

Usage (once activated -- do not run before then):
    python eval/run_judge_evaluation.py \\
        --endpoint <project endpoint> --agent quote-preparation-agent \\
        --version <agent version> --deployment <judge deployment> \\
        --dataset <converted judge dataset, see eval/convert_judge_dataset.py> \\
        --output-dir <dir>
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from judge_gate import METRICS, validate_results  # noqa: E402

AUTHOR_ONLY_MESSAGE = (
    "eval/run_judge_evaluation.py is AUTHOR-ONLY and not yet runnable: this "
    "repository has no hosted-agent invocation harness (no "
    "scripts/invoke-agent.sh equivalent, no Responses-protocol endpoint) "
    "and no hosted quote-preparation-agent deployment exists yet. This "
    "step cannot run until the agent is hosted and Gates G2/G3/G6 clear. "
    "See azure.yaml."
)


def agent_instructions() -> str:
    source = Path(__file__).parents[1] / "src" / "quote-preparation-agent" / "graph.py"
    names = {"AGENT_TASK_INSTRUCTIONS"}
    prompts = {}
    for statement in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    prompts[target.id] = ast.literal_eval(statement.value)
    if prompts.keys() != names or any(not isinstance(value, str) or not value for value in prompts.values()):
        raise ValueError("Cannot resolve agent instructions for task-adherence evaluation")
    return "\n\n".join(prompts.values())


def criteria(deployment: str) -> list[dict]:
    return [
        {
            "type": "azure_ai_evaluator",
            "name": metric,
            "evaluator_name": f"builtin.{metric}",
            "initialization_parameters": {"deployment_name": deployment},
            "data_mapping": {
                "query": "{{item.task_query}}" if metric == "task_adherence" else "{{item.query}}",
                "context": "{{item.context}}",
                "response": "{{item.output_items}}" if metric == "task_adherence" else "{{item.response}}",
            },
        }
        for metric in METRICS
    ]


def collect_output_items(client, eval_id: str, run_id: str, expected_count: int) -> list[dict]:
    for attempt in range(7):
        items = [
            item.model_dump(mode="json")
            for item in client.evals.runs.output_items.list(eval_id=eval_id, run_id=run_id)
        ]
        if len(items) >= expected_count or attempt == 6:
            return items
        print(f"Evaluation outputs available: {len(items)}/{expected_count}; retrying retrieval", flush=True)
        time.sleep(10)


def capture(records: list[dict], args) -> list[dict]:
    """Raise immediately: no hosted-agent invocation harness exists yet.

    Unlike the sibling's `capture()`, which shells out to
    `scripts/invoke-agent.sh` per dataset record, this repository has no
    such script and no hosted endpoint. Raising here (rather than a
    silent no-op) makes any accidental call fail loudly and explains
    exactly what is missing and what must happen before this can run.
    """
    raise RuntimeError(AUTHOR_ONLY_MESSAGE)


def evaluate(captured: list[dict], args) -> None:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    instructions = agent_instructions()
    evaluation_records = [
        {**record, "task_query": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": record["query"]},
        ]}
        for record in captured
    ]
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=args.endpoint, credential=credential) as project,
        project.get_openai_client() as client,
    ):
        evaluation = client.evals.create(
            name=f"Hosted CI {args.agent}:{args.version}",
            data_source_config={
                "type": "custom",
                "include_sample_schema": False,
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "task_query": {"type": "array"},
                        "context": {"type": "string"},
                        "response": {"type": "string"},
                        "output_items": {"type": "array"},
                    },
                    "required": ["query", "task_query", "context", "response", "output_items"],
                },
            },
            testing_criteria=criteria(args.deployment),
        )
        run = client.evals.runs.create(
            eval_id=evaluation.id,
            name=f"{args.agent}:{args.version}",
            data_source={
                "type": "jsonl",
                "source": {
                    "type": "file_content",
                    "content": [{"item": record} for record in evaluation_records],
                },
            },
        )
        identity = {
            "eval_id": evaluation.id,
            "run_id": run.id,
            "endpoint": args.endpoint,
            "agent": args.agent,
            "version": args.version,
        }
        (args.output_dir / "run-identity.json").write_text(json.dumps(identity, indent=2), encoding="utf-8")
        print(f"Evaluation {evaluation.id}, run {run.id}", flush=True)
        deadline = time.monotonic() + 1200
        while run.status not in ("completed", "failed", "canceled", "cancelled"):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Evaluation exceeded 20 minutes: {run.id}")
            time.sleep(10)
            run = client.evals.runs.retrieve(eval_id=evaluation.id, run_id=run.id)
        items = collect_output_items(client, evaluation.id, run.id, len(captured))
        result = {"run": run.model_dump(mode="json"), "items": items}
        (args.output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        summary = [
            f"## Hosted Evaluation: {args.agent}:{args.version}",
            f"Run: {run.id}",
            "",
            "| Metric | Passed | Errored | Failed |",
            "| --- | --- | --- | --- |",
        ]
        for metric in result["run"].get("per_testing_criteria_results", []):
            summary.append(
                f"| {metric['testing_criteria']} | {metric['passed']} | "
                f"{metric.get('errored', 'unknown')} | {metric['failed']} |"
            )
        try:
            validate_results(result["run"], items, len(captured), args.minimum_pass_rate)
        except ValueError as error:
            summary.extend(["", f"**FAIL:** {error}"])
            raise
        else:
            summary.extend(["", "**PASS:** model-judged responses satisfy quality policy; "
                            "the release also requires capture and deterministic policy checks."])
        finally:
            text = "\n".join(summary) + "\n"
            (args.output_dir / "summary.md").write_text(text, encoding="utf-8")
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
                    handle.write(text)
            print(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--minimum-pass-rate", type=float, default=1.0)
    args = parser.parse_args(argv)
    if not 0 < args.minimum_pass_rate <= 1:
        parser.error("minimum-pass-rate must be in (0, 1]")

    # Guard: this repository has no hosted-agent invocation harness or
    # hosted endpoint yet. Exit here -- before any Azure SDK import, any
    # filesystem/subprocess side effect, and any call to capture()/
    # evaluate() -- so an accidental invocation fails fast and clearly
    # instead of raising a raw traceback deep inside capture().
    print(AUTHOR_ONLY_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
