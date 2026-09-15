"""Entra token verification for the reviewer surface.

Structurally this is `apps/web-chat/auth.py` with the pilot *group* check
replaced by an app *role* check. The difference matters in two places:

* The `roles` claim carries `appRole.value` strings, not object GUIDs, so the
  configured role is a plain string and must not be normalised through
  `uuid.UUID()` the way `PILOT_GROUP_ID` is. Doing so would fail at startup.
* `roles` is never subject to the overage truncation that affects `groups`, so
  there is no `_claim_names` fallback to fail closed on here. An absent or
  empty `roles` claim simply yields 403.

Tenant, audience, scope, and non-empty `oid` validation are unchanged.
"""

import asyncio
from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient


@dataclass(frozen=True)
class Identity:
    tenant_id: str
    object_id: str
    role: str


class ReviewerAuth:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        required_role: str = "Reviewer",
        required_scope: str = "Review.Access",
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.required_role = required_role
        self.required_scope = required_scope
        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        self.keys = PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            timeout=10,
        )

    def verify(self, token: str) -> Identity:
        try:
            key = self.keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid"]},
                leeway=30,
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise HTTPException(503, "Sign-in verification is temporarily unavailable.") from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(401, "A valid access token is required.") from exc
        if claims.get("tid") != self.tenant_id or claims.get("azp") != self.client_id:
            raise HTTPException(403, "This application is not authorized.")
        if self.required_scope not in claims.get("scp", "").split():
            raise HTTPException(403, "Review permission is required.")
        roles = claims.get("roles")
        # A bare string would make `in` a substring match, so require a list.
        if not isinstance(roles, list) or self.required_role not in roles:
            raise HTTPException(403, "Reviewer role is required. Contact the pilot administrator.")
        if not isinstance(claims["oid"], str) or not claims["oid"]:
            raise HTTPException(401, "A user identity is required.")
        return Identity(claims["tid"], claims["oid"], self.required_role)

    async def authorize(self, authorization: str | None) -> Identity:
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 32768:
            raise HTTPException(401, "Sign in to continue.")
        return await asyncio.to_thread(self.verify, authorization[7:])
