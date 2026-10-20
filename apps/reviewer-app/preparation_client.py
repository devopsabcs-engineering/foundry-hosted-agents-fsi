"""Managed-identity invocation of the native quote-preparation Responses endpoint."""

import json
import re
from urllib.parse import urlsplit

import httpx
from azure.identity.aio import DefaultAzureCredential


class PreparationError(Exception):
    pass


def validate_agent_endpoint(endpoint: str) -> str:
    url = urlsplit(endpoint)
    if (
        url.scheme != "https" or not url.hostname
        or not url.hostname.endswith(".services.ai.azure.com")
        or url.username or url.password or url.port not in (None, 443) or url.fragment
        or not re.fullmatch(
            r"/api/projects/[A-Za-z0-9._-]+/agents/quote-preparation-agent/endpoint/protocols/openai/responses",
            url.path,
        )
        or url.query != "api-version=v1"
    ):
        raise ValueError("AGENT_ENDPOINT must be the native quote-preparation Foundry Responses endpoint")
    return endpoint


class PreparationClient:
    def __init__(self, endpoint: str, managed_identity_client_id: str | None = None):
        self.endpoint = validate_agent_endpoint(endpoint)
        self.credential = DefaultAzureCredential(managed_identity_client_id=managed_identity_client_id)
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15))

    async def close(self):
        await self.http.aclose()
        await self.credential.close()

    async def prepare(self, case_id: str, revision: int, request_id: str) -> str:
        token = await self.credential.get_token("https://ai.azure.com/.default")
        response = await self.http.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {token.token}"},
            json={"input": json.dumps({
                "caseId": case_id, "revision": revision, "preparationId": request_id,
            }), "stream": False},
        )
        response.raise_for_status()
        try:
            body = response.json()
        except ValueError as exc:
            raise PreparationError("Invalid native Responses response") from exc
        if (
            not isinstance(body, dict) or body.get("object") != "response"
            or body.get("status") not in (None, "completed") or body.get("error")
            or not isinstance(body.get("id"), str) or not body["id"].strip()
            or len(body["id"]) > 256
        ):
            raise PreparationError("Native Responses invocation did not complete")
        return body["id"]
