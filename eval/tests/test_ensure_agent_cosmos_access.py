"""Post-deploy RBAC uses the live runtime principal, never a stale project identity."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ensure_agent_cosmos_access as access  # noqa: E402

PRINCIPAL = "11111111-2222-3333-4444-555555555555"
ACCOUNT = "cosmos-test"
MISSING_GRANT = RuntimeError(
    f"Request blocked by Auth {ACCOUNT} : principal [{PRINCIPAL}] "
    "does not have required RBAC permissions"
)


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    details = tmp_path / "agent.json"
    details.write_text(json.dumps({
        "name": "quote-preparation-agent",
        "status": "active",
        "instance_identity": {"principal_id": PRINCIPAL},
        "definition": {"environment_variables": {
            "COSMOS_ENDPOINT": f"https://{ACCOUNT}.documents.azure.com:443/",
        }},
    }), encoding="utf-8")
    invoke = Mock(return_value=[{"response": "Submitted for employee review."}])
    grant = Mock()
    sleep = Mock()
    monkeypatch.setattr(access, "capture", invoke)
    monkeypatch.setattr(access.subprocess, "run", grant)
    monkeypatch.setattr(access.time, "sleep", sleep)
    args = SimpleNamespace(
        endpoint="https://example.test", agent="quote-preparation-agent",
        agent_details=details, resource_group="rg-test", cosmos_account=ACCOUNT,
    )
    return args, invoke, grant, sleep


def test_working_runtime_needs_no_grant(deployment):
    args, invoke, grant, sleep = deployment
    access.ensure_access(args)
    invoke.assert_called_once()
    grant.assert_not_called()
    sleep.assert_not_called()


def test_restores_only_verified_runtime_principal_with_existing_bicep(deployment):
    args, invoke, grant, sleep = deployment
    invoke.side_effect = [MISSING_GRANT, MISSING_GRANT, [{"response": "Ready"}]]
    access.ensure_access(args)
    command = grant.call_args.args[0]
    assert f"principalIds={json.dumps([PRINCIPAL])}" in command
    assert f"accountName={ACCOUNT}" in command
    assert any(value.endswith("cosmos-rbac.bicep") for value in command)
    assert grant.call_args.kwargs == {"check": True}
    assert invoke.call_count == 3
    sleep.assert_called_once_with(20)


@pytest.mark.parametrize("error", [
    RuntimeError("ManagedIdentityCredential invalid_scope"),
    RuntimeError("No assistant response text"),
    RuntimeError(str(MISSING_GRANT).replace(PRINCIPAL, "another-principal")),
    RuntimeError(str(MISSING_GRANT).replace(ACCOUNT, "another-account")),
])
def test_unexpected_errors_do_not_trigger_a_grant(deployment, error):
    args, invoke, grant, sleep = deployment
    invoke.side_effect = error
    with pytest.raises(RuntimeError):
        access.ensure_access(args)
    grant.assert_not_called()
    sleep.assert_not_called()


def test_persistent_rbac_failure_blocks_readiness(deployment):
    args, invoke, grant, sleep = deployment
    invoke.side_effect = MISSING_GRANT
    with pytest.raises(RuntimeError):
        access.ensure_access(args)
    assert invoke.call_count == 7
    assert sleep.call_count == 5


@pytest.mark.parametrize(("key", "value"), [
    ("name", "another-agent"),
    ("status", "creating"),
    ("definition", {"environment_variables": {"COSMOS_ENDPOINT": "https://another.documents.azure.com"}}),
    ("instance_identity", {"principal_id": "not-a-guid"}),
])
def test_invalid_deployment_details_fail_before_invocation(deployment, key, value):
    args, invoke, grant, sleep = deployment
    details = json.loads(args.agent_details.read_text(encoding="utf-8"))
    details[key] = value
    args.agent_details.write_text(json.dumps(details), encoding="utf-8")
    with pytest.raises(ValueError):
        access.ensure_access(args)
    invoke.assert_not_called()
    grant.assert_not_called()
