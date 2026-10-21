from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_reviewer_invocation_role_excludes_memory_and_management_permissions():
    text = (ROOT / "infra" / "modules" / "foundry-invoke-rbac.bicep").read_text(encoding="utf-8")
    assert "'eed3b665-ab3a-47b6-8f48-c9382fb1dad6'" in text
    assert "roleDefinitionId: consumerRoleId" in text
    assert "scope: project" in text
    assert "principalType: 'ServicePrincipal'" in text
    assert "resource invoker" not in text
    assert "dataActions:" not in text
    assert "agents/write" not in text
    assert "Microsoft.CognitiveServices/*" not in text
    assert "UserIdentityImpersonation" not in text


def test_reviewer_native_endpoint_and_client_are_declaratively_packaged():
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    module = (ROOT / "infra" / "modules" / "reviewer-app.bicep").read_text(encoding="utf-8")
    docker = (ROOT / "apps" / "reviewer-app" / "Dockerfile").read_text(encoding="utf-8")
    assert "projectEndpoint}/agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1" in main
    assert "module reviewerFoundryRbac" in main
    assert "name: 'AGENT_ENDPOINT'" in module
    assert "value: agentEndpoint" in module
    assert "apps/reviewer-app/preparation_client.py" in docker
