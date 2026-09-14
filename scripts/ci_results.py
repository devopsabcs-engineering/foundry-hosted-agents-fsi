"""Collect CI measurements and render durable, run-linked GitHub wiki trends.

Adapted from the sibling `foundry-hosted-agents` repository's
`scripts/ci_results.py`. That script's `evaluation_totals()`/`load_totals()`
read artifacts this repository's pipelines do not produce (`captured.json`,
`candidate-policy.json`, `run-identity.json`, `concurrent-sessions.json` --
there is no hosted-agent capture pipeline or load-test harness here; see
`eval/run_judge_evaluation.py`'s own AUTHOR-ONLY banner). This port drops
those two functions and the "load" dimension entirely, and adds two
repository-specific replacements: `deterministic_gate_totals()` (reads this
repository's real `eval/evaluation_gate.py` output) and `judge_totals()`
(reads LLM-judge evidence once `eval/run_judge_evaluation.py` is activated;
returns `None` gracefully today, matching every real run so far -- no
fabricated data). `junit_totals()`, `collect()`, `publish_history()`,
`chart()`, and `run_label()` are ported verbatim except where noted inline.
`web-chat-build.yml` invokes only this script's `--junit` mode (`junit_totals`
alone), so its by_type labels ("Web chat backend"/"Web chat frontend") are
preserved for compatibility.
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# This repository's LLM-judge counterpart to the sibling's
# eval/evaluation_gate.py is eval/judge_gate.py (see that module's own
# docstring): eval/evaluation_gate.py is the deterministic gate and has no
# METRICS/validate_results shape by design. judge_totals() below imports
# from judge_gate so a real judge_rates breakdown can be computed once
# eval/run_judge_evaluation.py actually runs against a hosted endpoint;
# until then judge_totals() returns None for every run.
from eval.judge_gate import METRICS, validate_results


def read_json(path):
    if not path.exists():
        return None
    if path.stat().st_size > 20_000_000:
        raise ValueError(f"Oversized evidence: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def junit_totals(directory):
    files = sorted(directory.glob("*.xml"))
    if not files:
        return None
    totals = dict(tests=0, failed=0, skipped=0, seconds=0.0)
    by_type = {}
    for path in files:
        root = ET.parse(path).getroot()
        label = {
            "agent": "Agent graph",
            "deterministic": "Deterministic evaluation",
            "reporting": "Reporting and contract tests",
            "backend": "Web chat backend",
            "frontend": "Web chat frontend",
        }.get(path.stem, "Other JUnit")
        by_type.setdefault(label, 0)
        for case in root.iter("testcase"):
            by_type[label] += 1
            totals["tests"] += 1
            totals["failed"] += int(case.find("failure") is not None or case.find("error") is not None)
            totals["skipped"] += int(case.find("skipped") is not None)
            duration = float(case.get("time", "0"))
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("Invalid JUnit duration")
            totals["seconds"] += duration
    totals["passed"] = totals["tests"] - totals["failed"] - totals["skipped"]
    totals["seconds"] = round(totals["seconds"], 3)
    totals["by_type"] = by_type
    return totals


def deterministic_gate_totals(path: Path = Path("eval/results.json")):
    """Read this repository's real `eval/evaluation_gate.py` output.

    Unlike the sibling's `evaluation_totals()` (which reads a live-hosted
    capture/policy pipeline this repository does not have), this reads the
    machine-readable report `eval/evaluation_gate.py` already writes today:
    `{"dataset_size": int, "records": [{"passed": bool, ...}], "bilingual_parity":
    {"passed": bool, ...}, "passed": bool}`. Returns `None` if the file is
    missing or malformed -- never raises -- so a run without this evidence
    yet does not break trend rendering.
    """
    try:
        report = read_json(path)
        if report is None:
            return None
        records = report["records"]
        passed_records = sum(1 for record in records if record["passed"])
        return {
            "dataset_size": report["dataset_size"],
            "passed_records": passed_records,
            "failed_records": len(records) - passed_records,
            "bilingual_parity": report["bilingual_parity"]["passed"],
            "gate_passed": report["passed"],
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def judge_totals(directory):
    """Read LLM-judge evaluation evidence, if any.

    This repository has no capture/policy-check pipeline distinct from the
    evaluation run itself (`eval/run_judge_evaluation.py`'s `capture()` is
    AUTHOR-ONLY and raises rather than producing a `captured.json`). Once a
    real hosted endpoint exists and this step actually runs, the judge
    harness's run/items payload is expected at `directory/judge-results.json`;
    until then this returns `None` for every run today, matching the
    repository's no-fabrication convention -- never raises for a missing file.
    """
    results = read_json(directory / "judge-results.json")
    if results is None:
        return None
    items = results.get("items", [])
    totals = {"captured": len(items), "judged": len(items), "judge_rates": None}
    try:
        totals["judge_rates"] = validate_results(results.get("run", {}), items, len(items), 0.000001)
    except ValueError:
        complete = True
        rates = {}
        for metric in METRICS:
            judged = [
                result
                for item in items
                for result in item.get("results", [])
                if result.get("name") == metric
            ]
            if (
                not judged
                or len(judged) != len(items)
                or any(
                    type(result.get("passed")) is not bool
                    or result.get("error")
                    or result.get("status") == "error"
                    for result in judged
                )
            ):
                complete = False
            else:
                rates[metric] = sum(result["passed"] for result in judged) / len(judged)
        if complete:
            try:
                validation_copy = json.loads(json.dumps(results))
                for item in validation_copy["items"]:
                    for result in item["results"]:
                        result["passed"] = True
                validate_results(validation_copy["run"], validation_copy["items"], len(items))
                totals["judge_rates"] = rates
            except ValueError:
                pass
    return totals


def collect(evidence, run, jobs):
    repository = run["repository"]["full_name"]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Invalid repository")
    run_id = int(run["id"])
    attempt = int(run.get("run_attempt", 1))
    record: dict[str, Any] = {
        "schema": 1,
        "repository": repository,
        "run_id": run_id,
        "attempt": attempt,
        "run_number": run.get("run_number"),
        "workflow": run["name"],
        "sha": run["head_sha"],
        "url": f"https://github.com/{repository}/actions/runs/{run_id}/attempts/{attempt}",
        "date": run["created_at"],
        "conclusion": run.get("conclusion") or "in_progress",
        "jobs": [
            {
                "name": job["name"],
                "conclusion": job.get("conclusion") or job.get("status"),
                "steps": [
                    {"name": step["name"], "conclusion": step.get("conclusion") or step.get("status")}
                    for step in job.get("steps", [])
                ],
            }
            for job in jobs["jobs"]
        ],
        "tests": None,
        "evaluation": None,
        "deterministic_gate": None,
        "context": {},
        "data_issues": [],
    }
    for key, loader, folder in [
        ("tests", junit_totals, "offline-test-evidence"),
        ("evaluation", judge_totals, "evaluation-evidence"),
    ]:
        try:
            record[key] = loader(evidence / folder)
        except (ValueError, KeyError, TypeError, AttributeError, ET.ParseError):
            record["data_issues"].append(f"Invalid {key} evidence; measurement withheld")
    # The deterministic gate's real eval/results.json is bundled as a flat
    # `results.json` alongside the JUnit XMLs in continuous-validation.yml's
    # "offline-test-evidence" artifact ("Stage deterministic gate result
    # alongside JUnit evidence" step), but in deploy-and-evaluate.yml's
    # separate `evaluate` job it is instead the sole contents of the
    # "evaluation-evidence" artifact. Try both locations, first match wins.
    # deterministic_gate_totals() itself never raises on a missing/malformed
    # file, so no outer try/except or data_issues entry is needed here.
    record["deterministic_gate"] = deterministic_gate_totals(
        evidence / "offline-test-evidence" / "results.json"
    ) or deterministic_gate_totals(evidence / "evaluation-evidence" / "results.json")
    try:
        context = read_json(evidence / "evaluation-evidence" / "context.json") or {}
        if not isinstance(context, dict):
            raise ValueError("Invalid context")
    except ValueError:
        context = {}
        record["data_issues"].append("Invalid deployment context; lineage unavailable")
    record["context"] = {
        key: context.get(key)
        for key in [
            "environment",
            "agent_version",
            "agent_content_hash",
            "dataset_sha256",
            "evaluator_sha256",
            "judge_deployment",
            "version_after",
        ]
    }
    return record


def cell(value):
    if value is None:
        return "N/A"
    return (
        str(value)
        .replace("|", "&#124;")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("<", "&lt;")
        .replace("`", "'")
    )


def summary(record):
    lines = [
        "## Continuous Test Results",
        "",
        f"[Source run {record['run_id']} / attempt {record['attempt']}]({record['url']})",
        "",
        f"Workflow outcome: **{cell(record['conclusion'])}**. Test-code SHA: `{cell(record['sha'])}`.",
        "",
        "| Job | Outcome |",
        "| --- | --- |",
    ]
    lines += [f"| {cell(job['name'])} | {cell(job['conclusion'])} |" for job in record["jobs"]]
    lines += [
        "",
        "<details><summary>Individual check outcomes</summary>",
        "",
        "| Job / check | Outcome |",
        "| --- | --- |",
    ]
    lines += [
        f"| {cell(job['name'])} / {cell(step['name'])} | {cell(step['conclusion'])} |"
        for job in record["jobs"]
        for step in job.get("steps", [])
    ]
    lines += ["", "</details>"]
    lines += ["", "| Measurement | Value |", "| --- | --- |"]
    tests, evaluation, gate = (
        record.get("tests") or {},
        record.get("evaluation") or {},
        record.get("deterministic_gate") or {},
    )
    values = {
        "Tests: passed / failed / skipped": " / ".join(
            cell(tests.get(key)) for key in ("passed", "failed", "skipped")
        ),
        "Deterministic gate: dataset size": gate.get("dataset_size"),
        "Deterministic gate: passed / failed records": " / ".join(
            cell(gate.get(key)) for key in ("passed_records", "failed_records")
        ),
        "Deterministic gate: bilingual parity": gate.get("bilingual_parity"),
        "Judge cases judged": evaluation.get("judged"),
        "Staging agent version": record["context"].get("agent_version") or evaluation.get("agent_version"),
    }
    for name, value in values.items():
        lines.append(f"| {name} | {cell(value)} |")
    for metric, rate in (evaluation.get("judge_rates") or {}).items():
        lines.append(f"| {metric} pass rate | {rate:.0%} |")
    lines += ["", "### Test Counts by Type", "", "| Type | Count |", "| --- | --- |"]
    lines += [f"| {name} | {cell(value)} |" for name, value in test_counts(record).items()]
    lines += [
        "",
        "N/A means not measured or unavailable, not zero. "
        "This repository has no hosted-agent capture pipeline; LLM-judge evaluation "
        "is author-only and inert until a real endpoint exists (see eval/run_judge_evaluation.py).",
    ]
    lines += [f"- {cell(issue)}" for issue in record["data_issues"]]
    return "\n".join(lines) + "\n"


def run_label(record):
    prefix = "R" if record["workflow"].startswith("Deploy") or record["workflow"] == "Hosted Agent CI/CD" else "V"
    return f"{prefix}{record.get('run_number') or record['run_id']}.{record['attempt']}"


def test_counts(record):
    tests = record.get("tests") or {}
    by_type = tests.get("by_type") or {}
    evaluation = record.get("evaluation") or {}
    return {
        "Total offline tests": tests.get("tests"),
        "Agent graph": by_type.get("Agent graph"),
        "Deterministic evaluation": by_type.get("Deterministic evaluation"),
        "Reporting and contract tests": by_type.get("Reporting and contract tests"),
        "Other JUnit": by_type.get("Other JUnit"),
        "Judge cases judged": evaluation.get("judged"),
        "Judge checks": evaluation["judged"] * len(METRICS)
        if evaluation.get("judge_rates") is not None and evaluation.get("judged") is not None else None,
    }


def chart(title, samples, axis):
    if not samples:
        return f"No valid measurements yet for {title}.\n"
    samples = samples[-12:]
    labels = ", ".join(f'"{run_label(record)}"' for record, _ in samples)
    values = ", ".join(str(round(value, 3)) for _, value in samples)
    maximum = 100 if axis == "pass percent" else max(1, math.ceil(max(value for _, value in samples)))
    return (
        f'```mermaid\nxychart-beta\n  title "{title}"\n  x-axis [{labels}]\n'
        f'  y-axis "{axis}" 0 --> {maximum}\n  bar [{values}]\n```\n'
    )


def render_trends(records):
    recent = sorted(records, key=lambda record: (record["date"], record["run_id"], record["attempt"]))[-50:]
    lines = [
        "---",
        "title: Continuous Test Trends",
        "description: CI test and evaluation measurements with immutable source-run links.",
        "---",
        "",
        "## Scope",
        "",
        "Updated automatically from completed trusted main-branch CI runs. "
        "Raw per-run aggregates are retained in `trend-history/`.",
        "Tables show the latest 50 attempts; each chart shows up to 12 available measurements. "
        "Missing data is never plotted as zero.",
        "Chart labels use V (validation) or R (release), workflow run number, and attempt. "
        "The table links each label to the full run ID.",
        "Failed and cancelled runs stay visible. Charts show measurements, not workflow status.",
        "This repository has no hosted-agent capture pipeline; LLM-judge evaluation is "
        "author-only and inert until a real endpoint exists and Gates G2/G3/G6 clear "
        "(see eval/run_judge_evaluation.py).",
        "",
        "## Recent Runs",
        "",
        "| Run / attempt | UTC | Workflow outcome | Test SHA | Agent version | "
        "Tests pass / fail / skip | Judge cases judged |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in reversed(recent):
        tests, evaluation = (
            record.get("tests") or {},
            record.get("evaluation") or {},
        )
        values = [
            f"[{run_label(record)} / {record['run_id']}]({record['url']})",
            cell(record["date"]),
            f"{cell(record['workflow'])}: {cell(record['conclusion'])}",
            cell(record["sha"][:7]),
            cell(record["context"].get("agent_version") or evaluation.get("agent_version")),
            " / ".join(cell(tests.get(key)) for key in ("passed", "failed", "skipped")),
            cell(evaluation.get("judged")),
        ]
        lines.append("| " + " | ".join(values) + " |")
    counts = [(record, test_counts(record)) for record in recent]
    count_types = list(test_counts({}))
    if not any(values["Other JUnit"] is not None for _, values in counts):
        count_types.remove("Other JUnit")
    lines += [
        "",
        "## Test Suite Growth",
        "",
        "Counts per run, not cumulative executions. Offline inventory includes skipped tests. "
        "Adding tests increases inventory; rerunning the same suite does not. Decreases remain visible.",
        "Total offline tests is the sum of the JUnit types, not an additional test type. "
        "Judge cases and judge checks are measured separately: these overlap or repeat scenarios "
        "and must not be added to the offline inventory. They reflect available results, "
        "not undiscovered or unexecuted cases.",
        "Historical records without a type breakdown show N/A until their retained artifacts are replayed.",
        "",
        "| Run / attempt | " + " | ".join(count_types) + " |",
        "| --- | " + " | ".join("---" for _ in count_types) + " |",
    ]
    for record, values in reversed(counts):
        lines.append(
            f"| [{run_label(record)} / {record['run_id']}]({record['url']}) | "
            + " | ".join(cell(values[name]) for name in count_types) + " |"
        )
    for name in count_types:
        lines += [
            "",
            chart(
                name,
                [(record, values[name]) for record, values in counts if values[name] is not None],
                "count",
            ),
        ]
    lines += [
        "",
        "## Test Failures",
        "",
        chart(
            "JUnit failures",
            [(record, record["tests"]["failed"]) for record in recent if record.get("tests") is not None],
            "failed tests",
        ),
    ]
    lines += [
        "",
        "## Deterministic Gate",
        "",
        "Real `eval/evaluation_gate.py` output for each run: dataset size, passed/failed record "
        "counts, and the bilingual-parity check. N/A means the deterministic-gate evidence was "
        "missing or malformed for that run, not zero passing records.",
        "",
        "| Run / attempt | Dataset size | Passed records | Failed records | Bilingual parity |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in reversed(recent):
        gate = record.get("deterministic_gate") or {}
        values = [
            f"[{run_label(record)} / {record['run_id']}]({record['url']})",
            cell(gate.get("dataset_size")),
            cell(gate.get("passed_records")),
            cell(gate.get("failed_records")),
            cell(gate.get("bilingual_parity")),
        ]
        lines.append("| " + " | ".join(values) + " |")
    groups = {}
    for record in recent:
        context = record["context"]
        dataset = context.get("dataset_sha256")
        if dataset and re.fullmatch(r"[a-f0-9]{64}", dataset):
            key = (
                dataset, context.get("evaluator_sha256"),
                context.get("judge_deployment"), context.get("environment")
            )
            groups.setdefault(key, []).append(record)
    lines += [
        "",
        "## Evaluation Trends",
        "",
        "Judge rates are grouped by dataset and evaluator code hashes, judge deployment and environment. "
        "Refusals are deterministic, not judge passes.",
    ]
    if not groups:
        lines += ["", "No comparable evaluation lineage has been collected yet."]
    for (dataset, evaluator, judge, environment), group in groups.items():
        lines += [
            "",
            f"### Dataset {dataset[:12]} / evaluator {cell(evaluator)[:12]}",
            "",
            f"Full dataset SHA-256: `{dataset}`.",
            f"Evaluator SHA-256: `{cell(evaluator)}`. "
            f"Judge: {cell(judge)}. Environment: {cell(environment)}.",
        ]
        for metric in METRICS:
            samples = [
                (record, record["evaluation"]["judge_rates"][metric] * 100)
                for record in group
                if (record.get("evaluation") or {}).get("judge_rates") is not None
            ]
            lines += ["", chart(metric, samples, "pass percent")]
    lines += ["", "## Reporting Gaps", ""]
    gaps = [
        f"- [{record['run_id']}.{record['attempt']}]({record['url']}): {cell(issue)}"
        for record in recent
        for issue in record["data_issues"]
    ]
    lines += gaps or [
        "No malformed-evidence or route-verification gaps detected. "
        "N/A cells can still indicate skipped tests or missing artifacts."
    ]
    return "\n".join(lines) + "\n"


def publish_history(record, wiki):
    directory = wiki / "trend-history"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{record['run_id']}-{record['attempt']}.json"
    previous = read_json(target)
    if previous:
        record = dict(record)
        for key in ("tests", "evaluation", "deterministic_gate"):
            if record.get(key) is None:
                record[key] = previous.get(key)
        record["context"] = {
            key: record["context"].get(key) or value for key, value in previous["context"].items()
        } | {key: value for key, value in record["context"].items() if value is not None}
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    records = [read_json(path) for path in sorted(directory.glob("*.json"))]
    (wiki / "Continuous-Test-Trends.md").write_text(render_trends(records), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ci-report"))
    parser.add_argument("--wiki", type=Path)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--agent-state", type=Path)
    parser.add_argument("--agent-version")
    parser.add_argument("--version-after")
    args = parser.parse_args()
    if args.context:
        if args.version_after:
            data = read_json(args.context)
            data["version_after"] = args.version_after
        else:
            state = read_json(args.agent_state) if args.agent_state else {"version": args.agent_version}
            if not state.get("version"):
                parser.error("A deployed agent version is required for context")
            data = {
                "environment": "staging",
                "agent_version": state["version"],
                "agent_content_hash": state.get("content_hash"),
                "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                "evaluator_sha256": hashlib.sha256(
                    (Path(__file__).parents[1] / "eval/run_judge_evaluation.py").read_bytes()
                    + (Path(__file__).parents[1] / "eval/judge_gate.py").read_bytes()
                ).hexdigest(),
                "judge_deployment": os.environ.get("JUDGE_DEPLOYMENT"),
            }
        args.context.parent.mkdir(parents=True, exist_ok=True)
        args.context.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return
    elif args.junit:
        totals = junit_totals(args.junit)
        text = (
            "## Offline Test Results\n\n"
            + (
                "\n".join(f"- {key}: {value}" for key, value in totals.items() if key != "by_type")
                + "\n\n| Test type | Count |\n| --- | --- |\n"
                + "\n".join(f"| {name} | {count} |" for name, count in totals["by_type"].items())
                if totals
                else "No JUnit results available; inspect failed setup/test steps."
            )
            + "\n"
        )
    else:
        if not all((args.evidence, args.run, args.jobs)):
            parser.error("--evidence, --run and --jobs are required")
        record = collect(args.evidence, read_json(args.run), read_json(args.jobs))
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        text = summary(record)
        (args.output / "summary.md").write_text(text, encoding="utf-8")
        if args.wiki:
            publish_history(record, args.wiki)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(text)


if __name__ == "__main__":
    main()
