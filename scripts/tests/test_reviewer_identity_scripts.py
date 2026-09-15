"""Tests for the reviewer Entra identity scripts.

These scripts talk to Microsoft Graph and cannot be exercised against a live
tenant from CI, so the assertions here are static: they parse both scripts with
the PowerShell parser to prove zero syntax errors, they exercise the Graph
permission detector against representative `az rest` failure payloads, and they
assert the correctness properties a live run cannot be relied on to catch ---
stable hard-coded GUIDs that never collide with the web-chat application, an
exact and case-sensitive display-name match before any delete,
`SupportsShouldProcess` on both scripts, the GitHub Actions output contract, and
the absence of a `Microsoft.Graph` module dependency.

Tests that shell out skip when `pwsh` is unavailable; the textual assertions
always run.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = SCRIPTS_DIR / "setup-reviewer-identity.ps1"
REMOVE_SCRIPT = SCRIPTS_DIR / "remove-reviewer-identity.ps1"
WEB_CHAT_SCRIPT = SCRIPTS_DIR / "setup-web-chat-identity.ps1"

SETUP_TEXT = SETUP_SCRIPT.read_text(encoding="utf-8")
REMOVE_TEXT = REMOVE_SCRIPT.read_text(encoding="utf-8")
WEB_CHAT_TEXT = WEB_CHAT_SCRIPT.read_text(encoding="utf-8")

REVIEWER_DISPLAY_NAME = "Foundry Quote Preparation Reviewer"
WEB_CHAT_DISPLAY_NAME = "Foundry Quote Preparation Web Chat"
GUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

EXPECTED_OUTPUT_KEYS = [
    "reviewer_tenant_id",
    "reviewer_client_id",
    "reviewer_application_object_id",
    "reviewer_service_principal_id",
    "reviewer_scope_uri",
    "reviewer_role_value",
]

pwsh = shutil.which("pwsh")
requires_pwsh = pytest.mark.skipif(pwsh is None, reason="pwsh is not installed")

BOTH_SCRIPTS = pytest.mark.parametrize(
    "text",
    [SETUP_TEXT, REMOVE_TEXT],
    ids=["setup-reviewer-identity", "remove-reviewer-identity"],
)


def _run_pwsh(command: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [str(pwsh), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )


def _assignment(text: str, name: str) -> str:
    """Return the single-quoted literal assigned to `$name` at script scope."""
    match = re.search(rf"^\${name} = '([^']*)'", text, re.MULTILINE)
    assert match is not None, f"${name} is not assigned a literal string"
    return match.group(1)


def _block(text: str, header: str) -> str:
    """Return the brace-matched block that `header` opens.

    Slicing a fixed number of characters after a header breaks the moment the
    block grows, so the whole construct is matched instead.
    """
    start = text.index(header)
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unbalanced block for {header!r}")


ABSENT_BRANCH = _block(REMOVE_TEXT, "if (-not $application) {")


@pytest.mark.parametrize("script", [SETUP_SCRIPT, REMOVE_SCRIPT], ids=lambda p: p.name)
def test_script_exists(script: Path):
    assert script.is_file()


@requires_pwsh
@pytest.mark.parametrize("script", [SETUP_SCRIPT, REMOVE_SCRIPT], ids=lambda p: p.name)
def test_script_parses_without_errors(script: Path):
    completed = _run_pwsh(
        "$errors = $null; "
        "[void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{script.as_posix()}', [ref]$null, [ref]$errors); "
        "if ($errors) { $errors | ForEach-Object { $_.ToString() }; exit 1 }"
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@BOTH_SCRIPTS
def test_supports_should_process(text: str):
    assert "[CmdletBinding(SupportsShouldProcess)]" in text
    assert "$PSCmdlet.ShouldProcess(" in text


@BOTH_SCRIPTS
def test_error_action_preference_matches_sibling(text: str):
    assert "$ErrorActionPreference = 'Stop'" in text


@BOTH_SCRIPTS
def test_uses_az_rest_against_graph_v1(text: str):
    assert "https://graph.microsoft.com/v1.0/" in text
    assert "graph.microsoft.com/beta" not in text
    assert "@('rest', '--method', $Method, '--url'" in text


@BOTH_SCRIPTS
def test_does_not_depend_on_the_graph_powershell_module(text: str):
    assert "Microsoft.Graph" not in text
    assert "Connect-MgGraph" not in text
    assert "Install-Module" not in text


@BOTH_SCRIPTS
def test_names_the_required_graph_permission(text: str):
    assert "Application.ReadWrite.All" in text
    assert "Authorization_RequestDenied" in text
    assert "Test-GraphPermissionFailure" in text


@BOTH_SCRIPTS
def test_asserts_the_tenant_before_any_write(text: str):
    assert "Sign in to the approved tenant first." in text
    assert text.index("Sign in to the approved tenant first.") < text.index("$PSCmdlet.ShouldProcess(")


def test_display_name_is_distinct_from_web_chat():
    reviewer_name = _assignment(SETUP_TEXT, "displayName")
    web_chat_name = _assignment(WEB_CHAT_TEXT, "displayName")

    assert reviewer_name == REVIEWER_DISPLAY_NAME
    assert web_chat_name == WEB_CHAT_DISPLAY_NAME
    assert reviewer_name != web_chat_name
    assert not reviewer_name.startswith(web_chat_name)
    assert not web_chat_name.startswith(reviewer_name)


def test_remove_targets_the_same_display_name_as_setup():
    assert _assignment(REMOVE_TEXT, "displayName") == _assignment(SETUP_TEXT, "displayName")


def test_identifiers_are_stable_hard_coded_guids():
    scope_id = _assignment(SETUP_TEXT, "scopeId")
    role_id = _assignment(SETUP_TEXT, "roleId")

    assert GUID_PATTERN.match(scope_id), scope_id
    assert GUID_PATTERN.match(role_id), role_id
    assert scope_id != role_id
    assert "New-Guid" not in SETUP_TEXT
    assert "[guid]::NewGuid" not in SETUP_TEXT


def test_identifiers_do_not_collide_with_web_chat():
    reviewer = {_assignment(SETUP_TEXT, "scopeId"), _assignment(SETUP_TEXT, "roleId")}
    web_chat = {_assignment(WEB_CHAT_TEXT, "scopeId"), _assignment(WEB_CHAT_TEXT, "roleId")}

    assert reviewer.isdisjoint(web_chat)


def test_exposes_the_review_scope_and_reviewer_role():
    assert _assignment(SETUP_TEXT, "scopeValue") == "Review.Access"
    assert _assignment(SETUP_TEXT, "roleValue") == "Reviewer"
    assert "allowedMemberTypes = @('User')" in SETUP_TEXT


def test_registers_a_redirect_uri():
    assert "redirectUris = $redirects" in SETUP_TEXT
    assert "Sort-Object -Unique" in SETUP_TEXT, "redirect URIs must be merged and deduped to stay idempotent"


def test_setup_is_idempotent_by_lookup_before_create():
    assert SETUP_TEXT.index("Get-ApplicationByExactName $displayName") < SETUP_TEXT.index(
        "Invoke-Graph POST 'applications'"
    )
    assert "if (-not $application) {" in SETUP_TEXT


def test_setup_emits_the_github_actions_output_contract():
    assert "$env:GITHUB_OUTPUT" in SETUP_TEXT
    for key in EXPECTED_OUTPUT_KEYS:
        assert key in SETUP_TEXT, f"missing output key {key}"
    assert "ConvertTo-Json" in SETUP_TEXT, "the same values must always reach stdout"


def test_remove_requires_an_exact_case_sensitive_match():
    assert "-ceq $Name" in REMOVE_TEXT
    assert "Assert-NotProtected" in REMOVE_TEXT
    assert "$Application.displayName -cne $displayName" in REMOVE_TEXT


def test_remove_protects_the_web_chat_application():
    assert f"$protectedDisplayNames = @('{WEB_CHAT_DISPLAY_NAME}')" in REMOVE_TEXT
    assert "Refusing to delete the protected application" in REMOVE_TEXT


def test_remove_is_idempotent_when_the_application_is_absent():
    assert "return" in ABSENT_BRANCH
    assert "throw" not in ABSENT_BRANCH


def test_remove_sweeps_the_recycle_bin_before_reporting_absent():
    """If the delete succeeded and the purge did not, a rerun finds no live
    application. Without this sweep it reports `absent` and exits zero, and the
    soft-deleted object keeps the display name reserved for 30 days."""
    assert "directory/deletedItems/microsoft.graph.application?" in REMOVE_TEXT
    assert "Get-DeletedApplicationsByExactName" in ABSENT_BRANCH
    assert "Invoke-Graph DELETE" in ABSENT_BRANCH


def test_the_recycle_bin_sweep_only_runs_when_purging_was_requested():
    guarded = _block(ABSENT_BRANCH, "if ($PurgeDeletedItems) {")

    assert "Get-DeletedApplicationsByExactName" in guarded
    assert "Invoke-Graph DELETE" in guarded


def test_the_recycle_bin_sweep_matches_exactly_and_case_sensitively():
    lookup = _block(REMOVE_TEXT, "function Get-DeletedApplicationsByExactName")

    assert "-ceq $Name" in lookup
    assert "$filter=" in lookup, "the sweep must filter server-side by display name"


def test_the_recycle_bin_sweep_cannot_purge_the_web_chat_application():
    guarded = _block(ABSENT_BRANCH, "if ($PurgeDeletedItems) {")

    assert guarded.index("Assert-NotProtected") < guarded.index("Invoke-Graph DELETE")


def test_the_recycle_bin_sweep_honours_what_if():
    guarded = _block(ABSENT_BRANCH, "if ($PurgeDeletedItems) {")

    assert guarded.index("$PSCmdlet.ShouldProcess(") < guarded.index("Invoke-Graph DELETE")
    assert "'would purge'" in guarded


def test_the_recycle_bin_sweep_reuses_the_graph_permission_handling():
    """Going through Invoke-Graph is what turns a missing
    Application.ReadWrite.All into the actionable message rather than a raw
    `az rest` failure."""
    lookup = _block(REMOVE_TEXT, "function Get-DeletedApplicationsByExactName")

    assert "Invoke-Graph GET" in lookup
    assert "az rest" not in lookup
    assert "az rest" not in ABSENT_BRANCH


def test_reporting_absent_still_records_the_purge_outcome():
    assert "deletedItemPurged    = 'skipped'" in REMOVE_TEXT
    assert "$removed.deletedItemPurged = 'purged'" in ABSENT_BRANCH


def test_remove_deletes_the_service_principal_before_the_application():
    assert REMOVE_TEXT.index("'Delete service principal'") < REMOVE_TEXT.index(
        "'Delete application registration'"
    )


@BOTH_SCRIPTS
def test_no_secret_material_is_written(text: str):
    for forbidden in ("passwordCredential", "addPassword", "clientSecret", "get-access-token"):
        assert forbidden not in text, f"{forbidden} would risk printing a credential"


# Representative `az rest` stderr payloads. The denial samples are the shapes
# Microsoft Graph actually returns when the caller lacks Application.ReadWrite.All.
GRAPH_DENIALS = [
    'Bad Request({"error":{"code":"Authorization_RequestDenied","message":"Insufficient privileges to complete the operation."}})',
    "Forbidden({'error': {'code': 'Authorization_RequestDenied'}})",
    "ERROR: Request failed with status code 403",
]
GRAPH_NON_DENIALS = [
    'Bad Request({"error":{"code":"Request_BadRequest","message":"Invalid value specified."}})',
    "ERROR: Request failed with status code 404",
    "",
]


@requires_pwsh
@pytest.mark.parametrize("script", [SETUP_SCRIPT, REMOVE_SCRIPT], ids=lambda p: p.name)
def test_graph_permission_detector_classifies_real_payloads(script: Path):
    """Extract `Test-GraphPermissionFailure` from the script and exercise it."""
    text = script.read_text(encoding="utf-8")
    definition = text[text.index("function Test-GraphPermissionFailure") : text.index("function Invoke-Graph")]

    denials = ";".join(f"Test-GraphPermissionFailure @'\n{s}\n'@" for s in GRAPH_DENIALS)
    allowed = ";".join(f"Test-GraphPermissionFailure @'\n{s}\n'@" for s in GRAPH_NON_DENIALS)
    completed = _run_pwsh(
        f"{definition}\n$denied = @({denials})\n$other = @({allowed})\n"
        "($denied -join ',') + '|' + ($other -join ',')"
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    denied_results, other_results = completed.stdout.strip().split("|")
    assert denied_results.split(",") == ["True"] * len(GRAPH_DENIALS)
    assert other_results.split(",") == ["False"] * len(GRAPH_NON_DENIALS)
