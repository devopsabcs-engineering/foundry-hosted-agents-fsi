import asyncio
from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from messages import DEFAULT_LANGUAGE, message


@dataclass(frozen=True)
class Identity:
    tenant_id: str
    object_id: str


class PilotAuth:
    def __init__(self, tenant_id: str, client_id: str, group_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.group_id = group_id
        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        self.keys = PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            timeout=10,
        )

    def verify(self, token: str, language: str = DEFAULT_LANGUAGE) -> Identity:
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
            raise HTTPException(503, {"detail": message("SIGNIN_UNAVAILABLE", language),
                                       "code": "SIGNIN_UNAVAILABLE"}) from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(401, {"detail": message("INVALID_TOKEN", language),
                                       "code": "INVALID_TOKEN"}) from exc
        if claims.get("tid") != self.tenant_id or claims.get("azp") != self.client_id:
            raise HTTPException(403, {"detail": message("APP_NOT_AUTHORIZED", language),
                                       "code": "APP_NOT_AUTHORIZED"})
        if "Chat.Access" not in claims.get("scp", "").split():
            raise HTTPException(403, {"detail": message("SCOPE_REQUIRED", language),
                                       "code": "SCOPE_REQUIRED"})
        if self.group_id not in claims.get("groups", []):
            raise HTTPException(403, {"detail": message("MEMBERSHIP_REQUIRED", language),
                                       "code": "MEMBERSHIP_REQUIRED"})
        if not isinstance(claims["oid"], str) or not claims["oid"]:
            raise HTTPException(401, {"detail": message("IDENTITY_REQUIRED", language),
                                       "code": "IDENTITY_REQUIRED"})
        return Identity(claims["tid"], claims["oid"])

    async def authorize(self, authorization: str | None, language: str = DEFAULT_LANGUAGE) -> Identity:
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 32768:
            raise HTTPException(401, {"detail": message("SIGNIN_REQUIRED", language),
                                       "code": "SIGNIN_REQUIRED"})
        return await asyncio.to_thread(self.verify, authorization[7:], language)
