"""Keep native Foundry extension authentication fresh after provisioning."""

import re
from pathlib import Path

import pytest


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "deploy-and-evaluate.yml"
)


@pytest.mark.parametrize(
    "step_name",
    ["Deploy candidate to staging", "Deploy evaluated source to production"],
)
def test_native_oidc_login_precedes_each_agent_deployment(step_name):
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(
        rf"^      - name: {re.escape(step_name)}\n(.*?)(?=^      - name:|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"Missing deployment step: {step_name}"
    step = match.group(1)
    run = step.split("        run: |\n", 1)[1]

    assert 'AZURE_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}' in step
    assert 'AZURE_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}' in step
    assert 'azd auth login --client-id "$AZURE_CLIENT_ID" --tenant-id "$AZURE_TENANT_ID"' in run
    assert "--federated-credential-provider github" in run
    assert run.index("set -euo pipefail") < run.index("azd auth login") < run.index("azd deploy")


@pytest.mark.parametrize(
    "step_name",
    [
        "Configure azd authentication",
        "Deploy candidate to staging",
        "Configure azd authentication and select production environment",
        "Deploy evaluated source to production",
    ],
)
def test_native_login_exits_delegated_auth_mode_before_authenticating(step_name):
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(
        rf"^      - name: {re.escape(step_name)}\n(.*?)(?=^      - name:|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"Missing authentication step: {step_name}"
    run = match.group(1).split("        run: |\n", 1)[1]
    login = run.index("azd auth login")
    switch = run.index("azd config set auth.useAzCliAuth false")
    assert switch < login
    assert "auth.useAzCliAuth true" not in run[switch:login]
    if "auth.useAzCliAuth true" in run:
        assert run.index("auth.useAzCliAuth true") > login
