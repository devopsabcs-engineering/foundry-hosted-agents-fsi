from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def test_reviewer_invocation_role_excludes_memory_and_management_permissions():
    text = (ROOT / "infra" / "modules" / "foundry-invoke-rbac.bicep").read_text(encoding="utf-8")
    permission_block = re.search(r"\bdataActions:\s*\[([^]]+)]", text).group(1)
    actions = re.findall(r"'(Microsoft\.CognitiveServices/[^']+)'", permission_block)
    assert set(actions) == {
        "Microsoft.CognitiveServices/accounts/AIServices/endpoints/invoke/action",
        "Microsoft.CognitiveServices/accounts/AIServices/applications/invoke/action",
        "Microsoft.CognitiveServices/accounts/AIServices/responses/write",
    }
    assert "scope: project" in text
    assert "principalType: 'ServicePrincipal'" in text
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
