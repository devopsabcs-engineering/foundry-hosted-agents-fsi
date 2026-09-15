---
permalink: /labs/lab-09-teardown
title: "Lab 09 - Teardown"
description: "Stop the local processes you started, clean up any on-disk state, and confirm the local labs provisioned nothing in Azure."
---

> 🇫🇷 **[Version française](../fr/labs/lab-09-teardown)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

Allow 10 minutes. Complete this lab even if an earlier lab's exercise did not fully pass.

## Learning Objectives

By the end of this lab, you will be able to:

* Stop any MCP server process you started in Labs 04 and 05
* Remove any on-disk state you created while experimenting with the approval repository
* Confirm Labs 00 through 08 provisioned no Azure resources, so there is no cloud teardown to run yet

## Exercises

### Exercise 9.1: Stop Any Running MCP Servers

If a terminal from Lab 04 or Lab 05 still has `python mcp/application-server/main.py` or `python mcp/rulebook-server/main.py` running, stop it.

```powershell
# In the terminal where the server is running
Ctrl+C
```

If you started a server in a background job instead, stop it explicitly:

```powershell
Get-Job | Where-Object { $_.Command -match 'application-server|rulebook-server' } | Stop-Job
```

### Exercise 9.2: Deactivate the Virtual Environment

```powershell
deactivate
```

### Exercise 9.3 (Hands-on): Remove Any On-Disk Approval Database

`ApprovalRepository` defaults to an in-memory SQLite database (`:memory:`), so nothing persists across a process restart unless you explicitly passed a file path in one of the earlier labs. If you did, remove that file now.

```powershell
if (Test-Path .\lab-approvals.db) { Remove-Item .\lab-approvals.db -Force }
```

Adjust the path if you used a different file name during Labs 03 or 07.

### Exercise 9.4: Confirm There Is No Cloud Teardown Yet

Labs 00 through 08 never provision Azure infrastructure. Every component runs locally: the calculator and approval repository are pure Python and SQLite, the MCP servers run as local processes, and the agent runs in-process with no hosted Foundry call. There is no resource group, subscription resource, or `azd` environment created by those labs to delete.

That changes from Lab 10 onward, where the pilot surfaces introduce an Azure foundation, an Entra app registration, and a dedicated teardown workflow. Each of those labs cleans up after itself.

## Validation Checklist

* [ ] Every MCP server process you started in Labs 04-05 has been stopped
* [ ] Your Python virtual environment is deactivated
* [ ] Any on-disk SQLite file you created for approval-repository experiments has been removed
* [ ] You confirmed the local labs created no Azure resources to delete

## Knowledge Check

* Why does `ApprovalRepository` default to `:memory:` rather than a file path?
* Lab 14 introduces a teardown workflow that refuses to delete its own resource group. What does that suggest about how the pilot's resources are grouped?

## Next Steps

You have completed the local half of the workshop. Continue to [Lab 10: Provision the Azure Foundation](lab-10-azure-foundation.md), which introduces the pilot surfaces and the infrastructure behind them.
