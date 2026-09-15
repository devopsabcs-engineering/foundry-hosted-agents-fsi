<#
.SYNOPSIS
    Deletes the Entra objects created by scripts/setup-reviewer-identity.ps1.

.DESCRIPTION
    Removes the reviewer service principal and application registration,
    resolved by exact, case-sensitive display name. The web-chat application is
    explicitly protected: a prefix or case-insensitive match can never select it.

    Safe to re-run. Objects that are already absent are reported and skipped, so
    a rerun after a partial failure exits zero. When -PurgeDeletedItems is set,
    a rerun also sweeps the Entra recycle bin, so a run whose delete succeeded
    but whose purge failed can be completed rather than leaving the display name
    reserved for 30 days.

    Requires the Microsoft Graph Application.ReadWrite.All permission.

.PARAMETER TenantId
    Tenant the signed-in account must already be targeting.

.PARAMETER PurgeDeletedItems
    Also hard-delete the application from the Entra recycle bin so the display
    name and identifier URI can be reused immediately instead of after 30 days.

.EXAMPLE
    ./scripts/remove-reviewer-identity.ps1 -TenantId <guid> -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [string]$TenantId,
    [switch]$PurgeDeletedItems
)

$ErrorActionPreference = 'Stop'
$displayName = 'Foundry Quote Preparation Reviewer'
$protectedDisplayNames = @('Foundry Quote Preparation Web Chat')

$graphPermissionMessage = @'
Microsoft Graph refused the request because the signed-in identity lacks the
required permission.

Required: Microsoft Graph application permission "Application.ReadWrite.All"
with tenant administrator consent, granted to the identity running this script.

Azure subscription roles such as Owner or Contributor grant zero Graph rights,
so a GitHub Actions OIDC identity will not have this unless it was consented
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

function Get-DeletedApplicationsByExactName([string]$Name) {
    # Soft-deleted applications live outside /applications for 30 days and keep
    # the display name reserved, so the same exact-match filter is applied here.
    $filter = [uri]::EscapeDataString("displayName eq '$Name'")
    $response = Invoke-Graph GET "directory/deletedItems/microsoft.graph.application?`$filter=$filter" $null
    return @($response.value | Where-Object { $_.displayName -ceq $Name })
}

function Assert-NotProtected($Application) {
    if ($Application.displayName -cne $displayName) {
        throw "Refusing to delete '$($Application.displayName)': it is not an exact match for '$displayName'."
    }
    if ($protectedDisplayNames -contains $Application.displayName) {
        throw "Refusing to delete the protected application '$($Application.displayName)'."
    }
}

$account = az account show -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $account.tenantId -ne $TenantId) { throw 'Sign in to the approved tenant first.' }

$removed = [ordered]@{
    tenantId             = $TenantId
    displayName          = $displayName
    servicePrincipal     = 'absent'
    application          = 'absent'
    deletedItemPurged    = 'skipped'
}

$application = Get-ApplicationByExactName $displayName
if (-not $application) {
    # No live application, but an earlier run may have deleted it and then failed
    # before purging. Finish that job rather than reporting success and leaving
    # the display name reserved for the rest of the 30-day retention window.
    if ($PurgeDeletedItems) {
        foreach ($item in (Get-DeletedApplicationsByExactName $displayName)) {
            Assert-NotProtected $item
            if ($PSCmdlet.ShouldProcess("directory/deletedItems/$($item.id)", 'Purge from the recycle bin')) {
                Invoke-Graph DELETE "directory/deletedItems/$($item.id)" $null | Out-Null
                $removed.deletedItemPurged = 'purged'
            }
            else { $removed.deletedItemPurged = 'would purge' }
        }
    }
    $removed | ConvertTo-Json -Depth 5
    return
}
Assert-NotProtected $application

$principalFilter = [uri]::EscapeDataString("appId eq '$($application.appId)'")
$principalResponse = Invoke-Graph GET "servicePrincipals?`$filter=$principalFilter" $null
$principals = @($principalResponse.value)
if ($principals.Count -gt 1) { throw 'Cannot uniquely resolve the service principal.' }
if ($principals.Count -eq 1) {
    $principal = $principals[0]
    if ($PSCmdlet.ShouldProcess("servicePrincipals/$($principal.id)", 'Delete service principal')) {
        Invoke-Graph DELETE "servicePrincipals/$($principal.id)" $null | Out-Null
        $removed.servicePrincipal = 'deleted'
    }
    else { $removed.servicePrincipal = 'would delete' }
}

if ($PSCmdlet.ShouldProcess("applications/$($application.id)", 'Delete application registration')) {
    Invoke-Graph DELETE "applications/$($application.id)" $null | Out-Null
    $removed.application = 'deleted'

    if ($PurgeDeletedItems) {
        if ($PSCmdlet.ShouldProcess("directory/deletedItems/$($application.id)", 'Purge from the recycle bin')) {
            Invoke-Graph DELETE "directory/deletedItems/$($application.id)" $null | Out-Null
            $removed.deletedItemPurged = 'purged'
        }
    }
}
else {
    $removed.application = 'would delete'
    if ($PurgeDeletedItems) { $removed.deletedItemPurged = 'would purge' }
}

$removed | ConvertTo-Json -Depth 5
