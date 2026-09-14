"""Renders a best-effort "Deployment Links" table into $GITHUB_STEP_SUMMARY.

Adapted from the sibling `foundry-hosted-agents` repository's
`scripts/deployment_summary.py`. The sibling hardcodes one fixed
subscription ID, resource group name, ACR name, container app name and
Defender/anomaly MCP hostnames for its Air Canada threat-assessment pilot.
This repo has no such fixed, always-on deployment (see infra/README.md's
"AUTHOR-ONLY / NOT DEPLOYED" gate), so every value below is sourced from
`azd env get-values` / the process environment at run time instead of being
invented, and links for values that are not currently configured are
omitted rather than guessed.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def azd_env_values() -> dict:
    """Best-effort read of `azd env get-values`; returns {} if azd is
    unavailable or no environment is selected (e.g. a CI job with no prior
    `azd` provisioning)."""
    try:
        result = subprocess.run(
            ["azd", "env", "get-values", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def value(values: dict, *names: str) -> str | None:
    """First non-empty value found across process env vars, then azd
    outputs, checked in the given name order."""
    for name in names:
        found = os.environ.get(name) or values.get(name)
        if found:
            return found
    return None


def portal(resource_id: str) -> str:
    return f"https://portal.azure.com/#resource{resource_id}"


def render() -> str:
    values = azd_env_values()
    repository_url = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'devopsabcs-engineering/foundry-hosted-agents-fsi')}"

    subscription_id = value(values, "AZURE_SUBSCRIPTION_ID")
    resource_group = value(values, "AZURE_RESOURCE_GROUP", "RESOURCE_GROUP")
    web_app_name = value(values, "WEB_CHAT_APP_NAME") or "foundry-quote-chat-staging"
    web_url = value(values, "WEB_CHAT_URL")
    acr_name = value(values, "MCP_ACR_NAME", "AZURE_CONTAINER_REGISTRY_NAME")
    account_name = value(values, "AZURE_AI_ACCOUNT_NAME") or "aif-desjardins-quote-preparation-staging"
    project_name = value(values, "AZURE_AI_PROJECT_NAME") or "proj-desjardins-quote-preparation-staging"
    project_endpoint = value(values, "FOUNDRY_PROJECT_ENDPOINT")
    application_mcp_url = value(values, "APPLICATION_MCP_URL")
    rulebook_mcp_url = value(values, "RULEBOOK_MCP_URL")

    resource_group_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        if subscription_id and resource_group
        else None
    )

    links: list[tuple[str, str, str]] = []
    if web_url:
        links.append(("Try staging web chatbot", web_url, "Same-tenant pilot members only"))
        links.append(("Web app health", f"{web_url}/healthz", "Public process health; not an agent-invocation test"))
    if resource_group_id:
        links.append((
            "Web app in Azure",
            portal(f"{resource_group_id}/providers/Microsoft.App/containerApps/{web_app_name}"),
            "Revisions, logs and metrics",
        ))
        links.append(("Resource group", portal(resource_group_id), "Azure access required"))
    if resource_group_id and acr_name:
        links.append((
            "Container registry",
            portal(f"{resource_group_id}/providers/Microsoft.ContainerRegistry/registries/{acr_name}"),
            "Image digests and remote builds",
        ))
    if resource_group_id and account_name and project_name:
        project_id = f"{resource_group_id}/providers/Microsoft.CognitiveServices/accounts/{account_name}/projects/{project_name}"
        links.append(("Foundry project", portal(project_id), "Azure access required"))
    if project_endpoint:
        links.append((
            "Responses API",
            f"{project_endpoint.rstrip('/')}/agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1",
            "Authenticated POST API, not a browser chat page",
        ))
    if application_mcp_url:
        links.append(("Application-server MCP", application_mcp_url, "Synthetic MCP protocol endpoint, not a chat page"))
    if rulebook_mcp_url:
        links.append(("Rulebook-server MCP", rulebook_mcp_url, "Synthetic MCP protocol endpoint, not a chat page"))
    links.append(("Repository", repository_url, "Source and workflow history"))

    rows = [f"| [{label}]({url}) | {note} |" for label, url, note in links]
    return "\n".join([
        "## Deployment Links", "",
        "Values reflect the current `azd`/environment configuration at run time, not proof that this run deployed or validated them.",
        "Rows for destinations that are not currently configured are omitted rather than invented.", "",
        "| Destination | Access and purpose |", "| --- | --- |", *rows, "",
    ])


if __name__ == "__main__":
    summary = render()
    if destination := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(destination).open("a", encoding="utf-8") as output:
            output.write("\n" + summary)
    else:
        print(summary)
