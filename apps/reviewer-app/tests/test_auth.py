"""Claim-level tests for the reviewer auth module.

`ReviewerAuth.verify` does two separable things: it decodes and signature-checks
a token, then it applies the tenant, audience, scope, role, and `oid` rules that
decide whether that token belongs to a reviewer. Only the second half is this
application's own logic, so the decode seam is replaced with a duck-typed
stand-in and every case is expressed as a claim dictionary. Minting real RS256
tokens would exercise PyJWT rather than these rules.

`monkeypatch` is pytest's own fixture and is used only to swap the module-level
`jwt` reference and restore it afterwards. The stand-in it installs is duck
typed, matching how `test_app.py` substitutes collaborators.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import jwt as real_jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import auth as auth_module  # noqa: E402
from auth import ReviewerAuth  # noqa: E402
from messages import message  # noqa: E402

TENANT = "11111111-1111-4111-8111-111111111111"
CLIENT = "22222222-2222-4222-8222-222222222222"
OBJECT_ID = "33333333-3333-4333-8333-333333333333"
TOKEN = "header.payload.signature"


def valid_claims() -> dict:
    return {
        "iss": f"https://login.microsoftonline.com/{TENANT}/v2.0",
        "aud": CLIENT,
        "tid": TENANT,
        "azp": CLIENT,
        "oid": OBJECT_ID,
        "scp": "Review.Access",
        "roles": ["Reviewer"],
    }


class StubJwt:
    """Duck-types the slice of the `jwt` module that `verify` touches.

    The two exception attributes must be the real classes because `verify`
    names them in `except` clauses.
    """

    PyJWTError = real_jwt.PyJWTError
    PyJWKClientConnectionError = real_jwt.PyJWKClientConnectionError

    def __init__(self, claims=None, raises=None):
        self._claims = claims
        self._raises = raises
        self.decode_calls = 0

    def decode(self, token, key, **options):
        self.decode_calls += 1
        if self._raises is not None:
            raise self._raises
        return dict(self._claims)


@pytest.fixture
def build_verifier(monkeypatch):
    """Return a factory yielding a `ReviewerAuth` over fixed decode output."""

    def build(claims=None, raises=None) -> ReviewerAuth:
        verifier = ReviewerAuth(TENANT, CLIENT)
        verifier.keys = SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key="public-key")
        )
        monkeypatch.setattr(auth_module, "jwt", StubJwt(claims, raises))
        return verifier

    return build


def test_a_reviewer_token_is_accepted(build_verifier):
    identity = build_verifier(valid_claims()).verify(TOKEN)

    assert identity.tenant_id == TENANT
    assert identity.object_id == OBJECT_ID
    assert identity.role == "Reviewer"


def test_authorize_accepts_a_bearer_token(build_verifier):
    identity = asyncio.run(build_verifier(valid_claims()).authorize(f"Bearer {TOKEN}"))

    assert identity.object_id == OBJECT_ID


@pytest.mark.parametrize(
    "header",
    [None, "", "   ", TOKEN, "Token abc.def.ghi", "bearer abc.def.ghi", "BearerX abc", "Bearer"],
    ids=[
        "missing",
        "empty",
        "whitespace",
        "no-prefix",
        "wrong-scheme",
        "lower-case-scheme",
        "prefix-without-space",
        "scheme-only",
    ],
)
def test_a_malformed_authorization_header_is_rejected(build_verifier, header):
    verifier = build_verifier(valid_claims())

    with pytest.raises(HTTPException) as failure:
        asyncio.run(verifier.authorize(header))

    assert failure.value.status_code == 401
    assert auth_module.jwt.decode_calls == 0


def test_an_oversized_token_is_rejected_without_decoding(build_verifier):
    """The bound is checked before the token reaches PyJWT, so a huge header
    cannot be turned into parsing work."""
    verifier = build_verifier(valid_claims())

    with pytest.raises(HTTPException) as failure:
        asyncio.run(verifier.authorize("Bearer " + "a" * 40000))

    assert failure.value.status_code == 401
    assert auth_module.jwt.decode_calls == 0


def test_a_token_from_another_tenant_is_rejected(build_verifier):
    claims = valid_claims()
    claims["tid"] = "99999999-9999-4999-8999-999999999999"

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 403


def test_a_missing_tenant_claim_is_rejected(build_verifier):
    claims = valid_claims()
    del claims["tid"]

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 403


@pytest.mark.parametrize("azp", ["other-client", "", None], ids=["other", "empty", "null"])
def test_a_token_issued_to_another_application_is_rejected(build_verifier, azp):
    """`azp` names the client that obtained the token. Without this check a
    token minted for any other application in the tenant would be accepted."""
    claims = valid_claims()
    claims["azp"] = azp

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 403


@pytest.mark.parametrize(
    "scp",
    ["", "User.Read", "Review.AccessAll", "XReview.Access", "review.access"],
    ids=["empty", "other-scope", "suffix", "prefix", "wrong-case"],
)
def test_a_token_without_the_review_scope_is_rejected(build_verifier, scp):
    claims = valid_claims()
    claims["scp"] = scp

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 403
    assert "Review permission" in failure.value.detail["detail"]
    assert failure.value.detail["code"] == "SCOPE_REQUIRED"


def test_a_missing_scope_claim_is_rejected(build_verifier):
    claims = valid_claims()
    del claims["scp"]

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 403


def test_the_review_scope_is_accepted_among_several(build_verifier):
    claims = valid_claims()
    claims["scp"] = "User.Read Review.Access offline_access"

    assert build_verifier(claims).verify(TOKEN).object_id == OBJECT_ID


@pytest.mark.parametrize(
    "roles",
    [[], ["Preparer"], ["reviewer"], "Reviewer", "ReviewerAdmin", None],
    ids=["empty", "other-role", "wrong-case", "bare-string", "substring", "null"],
)
def test_a_token_without_the_reviewer_role_is_rejected(build_verifier, roles):
    """A bare string would make the `in` test a substring match, so `roles`
    must be a list before the role name is looked for in it."""
    claims = valid_claims()
    claims["roles"] = roles

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 403
    assert "Reviewer role" in failure.value.detail["detail"]
    assert failure.value.detail["code"] == "ROLE_REQUIRED"


def test_a_missing_roles_claim_is_rejected(build_verifier):
    """`roles` is never truncated the way `groups` can be, so an absent claim
    means the role was not assigned rather than that it overflowed."""
    claims = valid_claims()
    del claims["roles"]

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 403


def test_the_reviewer_role_is_accepted_among_several(build_verifier):
    claims = valid_claims()
    claims["roles"] = ["Preparer", "Reviewer"]

    assert build_verifier(claims).verify(TOKEN).role == "Reviewer"


@pytest.mark.parametrize("oid", ["", None, 12345], ids=["empty", "null", "not-a-string"])
def test_a_token_without_a_user_identity_is_rejected(build_verifier, oid):
    claims = valid_claims()
    claims["oid"] = oid

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN)

    assert failure.value.status_code == 401


def test_a_rejected_token_surfaces_as_401(build_verifier):
    verifier = build_verifier(raises=real_jwt.InvalidSignatureError("bad signature"))

    with pytest.raises(HTTPException) as failure:
        verifier.verify(TOKEN)

    assert failure.value.status_code == 401
    assert "bad signature" not in failure.value.detail["detail"]
    assert failure.value.detail["code"] == "INVALID_TOKEN"


def test_an_expired_token_surfaces_as_401(build_verifier):
    verifier = build_verifier(raises=real_jwt.ExpiredSignatureError("expired"))

    with pytest.raises(HTTPException) as failure:
        verifier.verify(TOKEN)

    assert failure.value.status_code == 401


def test_an_unreachable_jwks_endpoint_surfaces_as_503(build_verifier):
    """A signing-key outage is not the caller's fault, so it must not be
    reported as an authentication failure that prompts a pointless re-sign-in."""
    verifier = build_verifier(raises=real_jwt.PyJWKClientConnectionError("jwks down"))

    with pytest.raises(HTTPException) as failure:
        verifier.verify(TOKEN)

    assert failure.value.status_code == 503


def test_the_configured_role_is_not_normalised_as_a_guid():
    """`roles` carries appRole *value* strings. Passing the configured role
    through `uuid.UUID()` the way the web-chat group id is would fail at
    startup, so the constructor must keep it verbatim."""
    verifier = ReviewerAuth(TENANT, CLIENT, "Reviewer", "Review.Access")

    assert verifier.required_role == "Reviewer"
    assert verifier.required_scope == "Review.Access"
    assert verifier.issuer == f"https://login.microsoftonline.com/{TENANT}/v2.0"


def test_verify_returns_french_text_and_code_when_requested(build_verifier):
    claims = valid_claims()
    claims["scp"] = ""

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN, language="fr-CA")

    assert failure.value.status_code == 403
    assert failure.value.detail == {
        "detail": message("SCOPE_REQUIRED", "fr-CA"),
        "code": "SCOPE_REQUIRED",
    }


def test_an_unrecognized_language_falls_back_to_english(build_verifier):
    claims = valid_claims()
    claims["scp"] = ""

    with pytest.raises(HTTPException) as failure:
        build_verifier(claims).verify(TOKEN, language="de-DE")

    assert failure.value.detail == {
        "detail": message("SCOPE_REQUIRED", "en-CA"),
        "code": "SCOPE_REQUIRED",
    }


def test_authorize_localizes_the_missing_bearer_token_error(build_verifier):
    verifier = build_verifier(valid_claims())

    with pytest.raises(HTTPException) as failure:
        asyncio.run(verifier.authorize(None, language="fr-CA"))

    assert failure.value.status_code == 401
    assert failure.value.detail == {
        "detail": message("SIGNIN_REQUIRED", "fr-CA"),
        "code": "SIGNIN_REQUIRED",
    }
