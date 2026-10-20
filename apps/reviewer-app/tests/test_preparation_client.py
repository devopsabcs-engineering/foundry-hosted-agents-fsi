import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preparation_client import PreparationClient, PreparationError, validate_agent_endpoint  # noqa: E402

ENDPOINT = "https://example.services.ai.azure.com/api/projects/demo/agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1"


def test_real_async_identity_client_starts_with_container_app_identity_environment(monkeypatch):
    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://127.0.0.1:42356/msi/token")
    monkeypatch.setenv("IDENTITY_HEADER", "synthetic-startup-test")

    async def run():
        client = PreparationClient(ENDPOINT, "11111111-1111-1111-1111-111111111111")
        await client.close()

    asyncio.run(run())


@pytest.mark.parametrize("endpoint", [
    ENDPOINT.replace("https:", "http:"), ENDPOINT.replace(".azure.com", ".azure.com.attacker.test"),
    ENDPOINT.replace("quote-preparation-agent", "other-agent"),
    ENDPOINT + "#fragment", ENDPOINT.replace("v1", "v2"),
    ENDPOINT.replace("example.", "user:password@example."),
])
def test_endpoint_rejects_untrusted_targets(endpoint):
    with pytest.raises(ValueError):
        validate_agent_endpoint(endpoint)


def test_native_invocation_uses_managed_identity_and_only_trusted_reference():
    observed = []

    async def run():
        class Credential:
            async def get_token(self, scope):
                assert scope == "https://ai.azure.com/.default"
                return SimpleNamespace(token="test-managed-identity")

        def handler(request):
            observed.append(json.loads(request.content))
            assert request.headers["Authorization"].startswith("Bearer ")
            return httpx.Response(200, json={"object": "response", "id": "resp-native"})

        client = PreparationClient.__new__(PreparationClient)
        client.endpoint, client.credential = ENDPOINT, Credential()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client.http:
            assert await client.prepare("CASE-SYN-005", 2, "private-capability") == "resp-native"

    asyncio.run(run())
    assert observed == [{"input": json.dumps({
        "caseId": "CASE-SYN-005", "revision": 2, "preparationId": "private-capability",
    }), "stream": False}]


@pytest.mark.parametrize("body", [
    {}, {"object": "response", "id": "resp", "status": "failed"},
    {"object": "response", "id": "resp", "error": {"code": "failure"}},
    {"object": "response", "id": ""},
])
def test_noncompletion_is_not_success(body):
    async def run():
        class Credential:
            async def get_token(self, scope):
                return SimpleNamespace(token="test")

        client = PreparationClient.__new__(PreparationClient)
        client.endpoint, client.credential = ENDPOINT, Credential()
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=body)
        )) as client.http:
            with pytest.raises(PreparationError):
                await client.prepare("CASE-SYN-005", 2, "private")
    asyncio.run(run())
