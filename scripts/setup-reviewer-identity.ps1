<#
.SYNOPSIS
    Creates or updates the Entra application registration for the reviewer app.

.DESCRIPTION
    Sibling of scripts/setup-web-chat-identity.ps1. Registers a distinct
    application that exposes the Review.Access delegated scope and the Reviewer
    app role, creates its service principal, and grants admin consent for the
    scope. Safe to re-run: the application is resolved by exact display name and
    patched when it already exists.

    Requires the Microsoft Graph Application.ReadWrite.All permission. Azure
    resource roles grant no Graph rights, so a CI OIDC identity may not have it.

.PARAMETER RedirectUri
    Additional redirect URI to register alongside the approved localhost origin.
    Must be HTTPS unless it is the approved localhost value.

.PARAMETER TenantId
    Tenant the signed-in account must already be targeting.

.PARAMETER ReviewerGroupId
    Optional security group granted the Reviewer app role.

.EXAMPLE
    ./scripts/setup-reviewer-identity.ps1 -TenantId <guid> -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$RedirectUri = 'http://localhost:8100',
    [Parameter(Mandatory = $true)]
    [string]$TenantId,
    [string]$ReviewerGroupId
)

$ErrorActionPreference = 'Stop'
$displayName = 'Foundry Quote Preparation Reviewer'
$scopeId = '9c1f7a34-58b2-4d06-8e73-1a4c0b9d5e27'
$roleId = '4f8b2e61-0d75-4a93-b6c8-7e35a1d29f04'
$scopeValue = 'Review.Access'
$roleValue = 'Reviewer'
$localRedirectUri = 'http://localhost:8100'
$protectedDisplayNames = @('Foundry Quote Preparation Web Chat')

$graphPermissionMessage = @'
Microsoft Graph refused the request because the signed-in identity lacks the
required permission.

Required: Microsoft Graph application permission "Application.ReadWrite.All"
with tenant administrator consent, granted to the identity running this script.
Granting the Reviewer app role to a group additionally needs
"AppRoleAssignment.ReadWrite.All", and admin-consenting the Review.Access scope
additionally needs "DelegatedPermissionGrant.ReadWrite.All".

Azure subscription roles such as Owner or Contributor grant zero Graph rights,
so a GitHub Actions OIDC identity will not have these unless they were consented
explicitly. An administrator can run this same script unchanged from their own
workstation after "az login --tenant <tenant>".
'@

function Test-GraphPermissionFailure([string]$Text) {
    if (-not $Text) { return $false }
    return ($Text -match 'Authorization_RequestDenied') -or
        ($Text -match 'Insufficient privileges') -or
        ($Text -match 'AADSTS65001') -or
        ($Text -match '\bForbidden\b') -or
        ($Text -match '\(403\)') -or
        ($Text -match 'status code 403')
}

function Invoke-Graph([string]$Method, [string]$Path, $Body) {
    $arguments = @('rest', '--method', $Method, '--url', "https://graph.microsoft.com/v1.0/$Path", '--output', 'json')
    $temporary = $null
    $errorFile = [System.IO.Path]::GetTempFileName()
    try {
        if ($null -ne $Body) {
            $temporary = [System.IO.Path]::GetTempFileName()
            [System.IO.File]::WriteAllText($temporary, ($Body | ConvertTo-Json -Depth 20))
            $arguments += @('--headers', 'Content-Type=application/json', '--body', "@$temporary")
        }
        $result = & az @arguments 2>$errorFile
        if ($LASTEXITCODE -ne 0) {
            $failure = Get-Content -LiteralPath $errorFile -Raw -ErrorAction SilentlyContinue
            if (Test-GraphPermissionFailure $failure) { throw $graphPermissionMessage }
            throw "Graph $Method $Path failed."
        }
        if ($result) { return ($result | ConvertFrom-Json) }
    }
    finally {
        if ($temporary) { Remove-Item $temporary -Force -ErrorAction SilentlyContinue }
        Remove-Item $errorFile -Force -ErrorAction SilentlyContinue
    }
}

function Get-ApplicationByExactName([string]$Name) {
    $filter = [uri]::EscapeDataString("displayName eq '$Name'")
    $response = Invoke-Graph GET "applications?`$filter=$filter" $null
    $exact = @($response.value | Where-Object { $_.displayName -ceq $Name })
    if ($exact.Count -gt 1) { throw "Cannot uniquely resolve the reviewer application '$Name'." }
    if ($exact.Count -eq 0) { return $null }
    return $exact[0]
}

if ($protectedDisplayNames -contains $displayName) {
    throw 'The reviewer display name collides with an existing application. Refusing to continue.'
}

$account = az account show -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $account.tenantId -ne $TenantId) { throw 'Sign in to the approved tenant first.' }

$uri = [uri]$RedirectUri
if ($uri.Scheme -ne 'https' -and $RedirectUri -ne $localRedirectUri) {
    throw "Only HTTPS or the approved localhost redirect ($localRedirectUri) is allowed."
}

if ($ReviewerGroupId) {
    $group = Invoke-Graph GET "groups/$ReviewerGroupId" $null
    if (-not $group.securityEnabled) { throw 'Reviewer group must be security enabled.' }
}

$application = Get-ApplicationByExactName $displayName
if (-not $application) {
    if (-not $PSCmdlet.ShouldProcess($displayName, 'Create application registration')) {
        Write-Verbose "Would create '$displayName', its service principal, the $scopeValue scope, and the $roleValue app role."
        return
    }
    $application = Invoke-Graph POST 'applications' @{
        displayName    = $displayName
        signInAudience = 'AzureADMyOrg'
    }
}

$redirects = @($application.spa.redirectUris) + @($localRedirectUri, $RedirectUri)
$redirects = @($redirects | Where-Object { $_ } | Sort-Object -Unique)
if ($PSCmdlet.ShouldProcess($displayName, 'Update application configuration')) {
    Invoke-Graph PATCH "applications/$($application.id)" @{
        signInAudience        = 'AzureADMyOrg'
        identifierUris        = @("api://$($application.appId)")
        groupMembershipClaims = 'SecurityGroup'
        spa                   = @{ redirectUris = $redirects }
        api                   = @{
            requestedAccessTokenVersion = 2
            oauth2PermissionScopes      = @(@{
                    id                      = $scopeId
                    value                   = $scopeValue
                    type                    = 'Admin'
                    isEnabled               = $true
                    adminConsentDisplayName = 'Review submitted quote cases'
                    adminConsentDescription = 'Read the review queue and record approval decisions as the signed-in reviewer.'
                })
        }
        requiredResourceAccess = @(@{
                resourceAppId  = $application.appId
                resourceAccess = @(@{ id = $scopeId; type = 'Scope' })
            })
        appRoles              = @(@{
                id                 = $roleId
                value              = $roleValue
                displayName        = 'Reviewer'
                description        = 'Authorized to approve, reject, or request revision on submitted cases.'
                allowedMemberTypes = @('User')
                isEnabled          = $true
            })
    } | Out-Null
}

$principal = $null
$principalFilter = [uri]::EscapeDataString("appId eq '$($application.appId)'")
$principalResponse = Invoke-Graph GET "servicePrincipals?`$filter=$principalFilter" $null
$principals = @($principalResponse.value)
if ($principals.Count -gt 1) { throw 'Cannot uniquely resolve the service principal.' }
if ($principals.Count -eq 1) { $principal = $principals[0] }
if (-not $principal) {
    if ($PSCmdlet.ShouldProcess($displayName, 'Create service principal')) {
        $principal = Invoke-Graph POST 'servicePrincipals' @{ appId = $application.appId; appRoleAssignmentRequired = $true }
    }
}

if ($principal) {
    if ($PSCmdlet.ShouldProcess($displayName, 'Require app role assignment')) {
        Invoke-Graph PATCH "servicePrincipals/$($principal.id)" @{ appRoleAssignmentRequired = $true } | Out-Null
    }

    if ($ReviewerGroupId) {
        $assignments = Invoke-Graph GET "servicePrincipals/$($principal.id)/appRoleAssignedTo" $null
        if (-not ($assignments.value | Where-Object { $_.principalId -eq $ReviewerGroupId -and $_.appRoleId -eq $roleId })) {
            if ($PSCmdlet.ShouldProcess($ReviewerGroupId, "Assign the $roleValue app role")) {
                Invoke-Graph POST "servicePrincipals/$($principal.id)/appRoleAssignedTo" @{
                    principalId = $ReviewerGroupId; resourceId = $principal.id; appRoleId = $roleId
                } | Out-Null
            }
        }
    }

    $grants = Invoke-Graph GET "servicePrincipals/$($principal.id)/oauth2PermissionGrants" $null
    if (-not ($grants.value | Where-Object { $_.resourceId -eq $principal.id -and $_.scope -eq $scopeValue -and $_.consentType -eq 'AllPrincipals' })) {
        if ($PSCmdlet.ShouldProcess($scopeValue, 'Grant tenant-wide admin consent')) {
            Invoke-Graph POST 'oauth2PermissionGrants' @{
                clientId = $principal.id; resourceId = $principal.id; consentType = 'AllPrincipals'; scope = $scopeValue
            } | Out-Null
        }
    }
}

if (-not $WhatIfPreference) {
    $verified = Invoke-Graph GET "applications/$($application.id)" $null
    if ($verified.api.requestedAccessTokenVersion -ne 2 -or $verified.groupMembershipClaims -ne 'SecurityGroup') {
        throw 'Application configuration verification failed.'
    }
    if (-not ($verified.appRoles | Where-Object { $_.value -eq $roleValue -and $_.id -eq $roleId })) {
        throw "The $roleValue app role is missing after configuration."
    }
    if (-not ($verified.api.oauth2PermissionScopes | Where-Object { $_.value -eq $scopeValue -and $_.id -eq $scopeId })) {
        throw "The $scopeValue scope is missing after configuration."
    }
}

$principalId = ''
if ($principal) { $principalId = $principal.id }

$outputs = [ordered]@{
    reviewer_tenant_id             = $TenantId
    reviewer_client_id             = $application.appId
    reviewer_application_object_id = $application.id
    reviewer_service_principal_id  = $principalId
    reviewer_scope_uri             = "api://$($application.appId)/$scopeValue"
    reviewer_role_value            = $roleValue
}

if ($env:GITHUB_OUTPUT) {
    foreach ($key in $outputs.Keys) {
        Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "$key=$($outputs[$key])"
    }
}

$outputs | ConvertTo-Json -Depth 5
