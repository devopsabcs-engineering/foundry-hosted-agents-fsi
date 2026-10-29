---
layout: default
title: Foundry hosted agents FSI
description: Customer demo navigation, retained deployment baseline and verified live links.
---

## Customer demo / Démonstration client

The synthetic quote-preparation demo is deployed and retained in staging and
production. Start with the [current evidence](../showcase-evidence.md), not
historical author-only descriptions.

* [Architecture](../architecture.md) | [Architecture française](../fr/architecture.md)
* [English workshop](../index.md) | [Atelier français](../fr/index.md)
* [Native Foundry showcase](../native-showcase.md) | [Fonctions natives](../fr/native-showcase.md)
* [Authentic screenshots and evidence](../showcase-evidence.md) | [Preuves et captures](../fr/showcase-evidence.md)
* [Operations](operations.md) | [Workflow inventory](workflows.md)
* [Release evidence](release-evidence.md) | [Continuous test trends](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Continuous-Test-Trends)
* [Evaluation engineering guide](../evaluation-guide.md) | [Guide des évaluations](../fr/evaluation-guide.md)
* [Deep Lab 19](../labs/lab-19-evaluation-engineering.md) | [Atelier 19](../fr/labs/lab-19-evaluation-engineering.md)
* [English evaluation PowerPoint](../assets/decks/foundry-evaluation-engineering-en.pptx) | [PowerPoint français](../assets/decks/foundry-evaluation-engineering-fr.pptx)
* [English practice JSONL](../assets/datasets/portal-practice-en-CA.jsonl) | [JSONL de pratique français](../assets/datasets/portal-practice-fr-CA.jsonl)

Lab 19 and the 37-slide evaluation decks share the retained-run overview,
detailed-results and evaluator-catalog walkthrough. Practice datasets are authored
synthetic controls, not captured agent responses. Read-only inspection needs no
new evaluation; uploads and paid submissions require separate approval.

L'Atelier 19 et les présentations d'évaluation de 37 diapositives partagent les
captures conservées et le catalogue des évaluateurs. Les jeux de pratique sont
des contrôles synthétiques rédigés, pas des réponses agent capturées. Aucun nouvel
essai pour la lecture seule; téléversement et soumission payante à autoriser.

## Langfuse synthetic pilot

Open the [authenticated screenshot gallery](../langfuse-pilot-evidence.md#authenticated-project-and-trace-views)
for the desktop project, persisted synthetic trace, and mobile project captured
on `2026-10-28`. The [full pilot evidence](../langfuse-pilot-evidence.md) also
includes the earlier sign-in/sign-up views, capture manifests, ingestion records,
and cleanup/deallocation evidence. The [integration guide](../langfuse-integration.md)
compares Langfuse with Foundry, Application Insights, and Azure Monitor.

These are retained guest-local screenshots, not a live workstation connection.
The pilot is deallocated between approved demonstration windows; operator SSH,
secure password retrieval, and remote backend correlation remain outstanding.
Approved maintenance verified `AUTH_DISABLE_SIGNUP=true` in both Langfuse
containers and retained the existing user, owner membership, project, and keys.
The VM was confirmed deallocated at `2026-10-28T20:34:18Z`.
Production Langfuse export remains disabled.

La [galerie authentifiée en français](../fr/langfuse-pilot-evidence.md#projet-et-trace)
présente le projet sur ordinateur/mobile et la trace synthétique persistée.
Les [preuves complètes](../fr/langfuse-pilot-evidence.md) et le
[guide Langfuse et Foundry](../fr/langfuse-integration.md) décrivent ingestion,
compte, nettoyage et limites. La maintenance approuvée a vérifié
`AUTH_DISABLE_SIGNUP=true` dans les deux conteneurs en conservant utilisateur,
rôle propriétaire, projet et clés. VM désallouée à `2026-10-28T20:34:18Z`;
SSH opérateur, récupération sécurisée du mot de passe et corrélation Azure restent
à résoudre. Ces captures locales conservées ne prouvent pas un accès interactif
depuis le poste. L'export Langfuse de production reste désactivé.

## Deployed baseline

Release [40567253202](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/40567253202)
deployed approved runtime source `42c627c`: staging agent v7 and production v8.
Both environments include chat, employee review, two read-only MCP endpoints,
Cosmos persistence and native telemetry. The project suffix `-poc` means
production. The retained revision-2 correction/audit, self-approval denial and
reviewer invocation200/memory403 screenshots belong to the earlier v6/v7
release, not a new v7/v8 application capture. Chat rollout remains separate.
Production Langfuse export remains disabled. Documentation-only changes do not
dispatch a release; release evidence is not a fresh availability check.

La [livraison consignée](../fr/showcase-evidence.md#livraison-approuvée-actuelle)
`40567253202` sur `42c627c` correspond à staging v7/production v8. Les captures
de correction et contrôles reviewer conservés restent associés à la livraison
antérieure v6/v7. L'export Langfuse de production reste désactivé; une
publication documentaire ne déploie pas l'agent et ne vérifie pas sa santé actuelle.

The graph uses deterministic stages and calculator logic, not a generative
pricing model. Employee approval remains separate. Native skills, File Search,
memory and trace replay are isolated operator demonstrations, not implicit
dependencies of the quote agent. All inputs and outputs are synthetic.

## Live deployment links

<!-- deployment-links:start -->
Deployment links are populated from verified release artifacts. If no new
artifact is available, publication preserves the last verified section.
<!-- deployment-links:end -->

## Publication ownership

This page and all maintained wiki guides are rendered from
[repository documentation](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/tree/main/docs).
Continuous-Test-Trends and its history are generated from actual validation
artifacts. Dynamic deployment links come only from release artifacts.
See [Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents)
for the platform contract.
