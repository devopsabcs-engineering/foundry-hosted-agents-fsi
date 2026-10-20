---
layout: default
title: Architecture
description: Agent Foundry déployé, traitement déterministe, validation humaine et isolation des démonstrations natives.
---

[English](../architecture.md) | [Atelier](index.md) | [Preuves actuelles](showcase-evidence.md)

## État déployé

La démonstration conservée utilise le véritable hôte Responses de Foundry :
agent staging **v5**, production **v6**, source approuvée `01af1fb`,
[livraison 39424857559](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39424857559).
Le suffixe `-poc` du compte/projet désigne la production. Les deux chats, les
deux applications de révision et les quatre services MCP sont déployés.
Les arbres `src`, `apps` et `infra` correspondent au main fusionné `a4b6008`.
Ces versions constituent une observation datée, pas des paramètres de routage.
Les anciens avertissements « author-only » ne décrivent plus cet inventaire.
Toute nouvelle modification d'infrastructure reste soumise à approbation.

Les données, tarifs et résultats sont synthétiques. Aucune offre réelle,
livraison au client ou approbation automatique n'est représentée.

## Architecture applicative

<details>
<summary>Image rendue si le composant Mermaid est indisponible</summary>

![Architecture applicative](../assets/architecture/architecture-fr-1.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    FApplicant["Navigateur pilote authentifie Entra"]
    FEmployee["Navigateur employe authentifie Entra"]
    subgraph FApps["Container Apps par environnement"]
        FChat["Chat React et FastAPI"]
        FReview["Revision React et FastAPI"]
        FMCP["MCP demandes et regles - lecture seule"]
    end
    subgraph FFoundry["Projet Microsoft Foundry"]
        FEndpoint["Endpoint Responses natif"]
        FAgent["Agent LangGraph heberge"]
    end
    FStore[("Cosmos DB cas et audit")]
    FMonitor["Application Insights et Log Analytics"]
    FApplicant -->|"Jeton pilote"| FChat
    FEmployee -->|"Jeton employe"| FReview
    FChat -->|"Identite managee"| FEndpoint
    FEndpoint --> FAgent
    FAgent -->|"MCP HTTPS direct"| FMCP
    FAgent -->|"Creer et soumettre"| FStore
    FReview -->|"Decisions humaines"| FStore
    FAgent -->|"Etapes sans donnees sensibles"| FMonitor
```

| Couche | Technologie et contrat | Responsabilité |
| --- | --- | --- |
| Interface | React, MSAL | Expériences distinctes du demandeur et de l'employé |
| API web | FastAPI, PyJWT | Validation du tenant, de l'audience et des autorisations |
| Hôte | Adaptateur LangGraph `1.0.0b17`, Responses `2.0.0` | Readiness, conversion et flux final borné |
| Orchestration | LangGraph déterministe | Intake, recherche de références et composition |
| Outils | FastMCP, HTTP streamable | Lecture de fixtures et du règlement épinglé |
| Persistance hébergée | Cosmos DB | Base `quote-preparation`, conteneur `cases`, partition `/caseId` |
| Persistance locale | SQLite | Même contrat `CaseStore`, sans partage hébergé |
| Démonstrations natives | Azure AI Projects `2.6.0` | Mémoire, fichiers, skills et évaluations isolés |
| Télémétrie | OpenTelemetry, Azure Monitor | Pipeline SDK unique et étapes assainies |

Le chemin de préparation n'utilise ni Redis, ni file de messages, ni plateforme
de traces tierce, ni modèle de tarification génératif. Le modèle provisionné
`gpt-4o-mini` n'est pas invoqué par ce graphe.

## Composants et routage réel

<details>
<summary>Image rendue si le composant Mermaid est indisponible</summary>

![Relations des composants](../assets/architecture/architecture-fr-2.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart LR
    GMain["main.py hote Responses"] --> GBridge["response_bridge.py conversion"]
    GBridge --> GGraph["graph.py superviseur"]
    GGraph --> GTools["toolbox.py"]
    GTools --> GCalc["calculator.py pur"]
    GTools --> GStore["case_store.py contrat"]
    GTools -->|"Heberge"| GRemote["Sessions MCP HTTP directes"]
    GTools -->|"Depot local complet"| GLocal["Fonctions MCP en processus"]
    GReviewer["API employe"] -->|"Sans toolbox"| GStore
    GStore -->|"COSMOS_ENDPOINT"| GCosmos["Cosmos avec ETag"]
    GStore -->|"Local sans Cosmos"| GSQLite["SQLite"]
```

* [main.py](../../src/quote-preparation-agent/main.py) lance le CLI avec un cas
  ou l'hôte réel sur le port 8088 sans argument.
* [response_bridge.py](../../src/quote-preparation-agent/response_bridge.py)
  convertit l'entrée Responses en nouvel état et ne diffuse que le JSON final
  bilingue, jamais les états intermédiaires.
* [graph.py](../../src/quote-preparation-agent/graph.py) choisit des étapes fixes
  et des messages modèles, sans inférence.
* [toolbox.py](../../src/quote-preparation-agent/toolbox.py) expose les lectures,
  le calcul et la soumission de brouillons, pas les décisions humaines.
* [L'API employé](../../apps/reviewer-app/app.py) accède directement au magasin.

Malgré les connexions déclarées dans `azure.yaml`, l'agent appelle directement
`APPLICATION_MCP_URL` et `RULEBOOK_MCP_URL`, pas la passerelle toolbox Foundry.
Ces services publics en lecture seule ne contiennent que des données
synthétiques. Le graphe est compilé sans checkpointer : une conversation
Foundry ne crée pas de persistance conversationnelle LangGraph.

## Parcours déterministe et cas incomplet

<details>
<summary>Image rendue si le composant Mermaid est indisponible</summary>

![Parcours de la demande](../assets/architecture/architecture-fr-3.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    HInput["Reference du cas"] --> HSupervisor["Superviseur"]
    HSupervisor --> HIntake["quote.INTAKE"]
    HIntake --> HValid["Reference valide"]
    HValid -->|"Oui"| HLookup["quote.REFERENCE_LOOKUP"]
    HLookup --> HRead["Demande et reglement epingle"]
    HRead --> HCompose["quote.COMPOSITION"]
    HCompose --> HCalc["Calcul pur et statut"]
    HCalc --> HDraft["Brouillon puis soumission"]
    HDraft --> HMessage["Accuse EN et FR borne"]
    HValid -->|"Non - sans lecture"| HReject["Rejet borne sans brouillon"]
    HMessage --> HFinal["Sortie demandeur seulement"]
    HReject --> HFinal
```

Chaque étape revient au superviseur avant la suivante et `END`. Le calcul et
la persistance font partie de `COMPOSITION`, pas de nouveaux nœuds ou spans.
Il existe exactement trois étapes personnalisées. « Pas de MCP distant dans
COMPOSITION » ne signifie pas « aucun appel de calcul ou de magasin ».

La [fixture CASE-SYN-005](../../data/synthetic/fixtures/case-syn-005-missing-plan.json)
a `input.plan: null`. Le calcul retourne `INCOMPLETE`, `amountCents: null`
et `MISSING_PLAN`. Le magasin d'exécution peut néanmoins enregistrer
`PENDING_REVIEW` avec cet instantané incomplet. Statut de calcul et état du
workflow sont deux dimensions distinctes. Le demandeur ne voit ni montant,
ni règlement brut, ni audit employé. Les blocs pédagogiques `workflow` et
`nextCommand` de la fixture ne déclenchent aucune approbation réelle.

## Approbation humaine et concurrence

<details>
<summary>Image rendue si le composant Mermaid est indisponible</summary>

![États de validation humaine](../assets/architecture/architecture-fr-4.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart LR
    JAgent["Creation agent"] --> JDraft["DRAFT revision N"]
    JDraft -->|"Soumettre"| JPending["PENDING_REVIEW"]
    JPending -->|"Employe approuve"| JApproved["APPROVED"]
    JPending -->|"Employe refuse"| JRejected["REJECTED"]
    JApproved -->|"Apercu pedagogique audite"| JPreview["Toujours APPROVED"]
    JApproved -->|"Reviser"| JRevised["DRAFT revision N plus 1"]
    JRejected -->|"Reviser"| JRevised
    JPending -->|"Reviser"| JRevised
    JDraft -->|"Reviser"| JRevised
    JRevised -->|"Resoumettre"| JPending
```

L'API vérifie le rôle `Reviewer`, le scope délégué `Review.Access`, l'identité
Entra et la révision consultée. Le magasin interdit l'auto-approbation et les
transitions invalides. Cosmos utilise des écritures conditionnelles ETag.
L'audit ajouté au document est une convention applicative, pas une garantie
de stockage réglementaire immuable. Réviser invalide l'approbation précédente.
L'aperçu du magasin reste pédagogique et audité, sans livraison ; l'API web
employé n'expose pas de route de livraison/aperçu au demandeur.
La suppression de la file synthétique exige une confirmation explicite.

Le chat vérifie l'appartenance pilote avant l'appel serveur par identité
managée. Les accès protégés anonymes retournent 401. Un endpoint de santé
ne prouve ni l'autorisation ni la disponibilité de l'agent.

## Fonctions natives isolées

<details>
<summary>Image rendue si le composant Mermaid est indisponible</summary>

![Isolation des fonctions natives](../assets/architecture/architecture-fr-5.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    KOperator["CLI operateur staging"]
    KOperator --> KFiles["Fichiers et generation reussie"]
    KOperator --> KSkill["Skill versionne du projet"]
    KSkill --> KRuntime["Consommation Responses isolee"]
    KOperator --> KSearch["File Search natif - six fichiers"]
    KOperator --> KMemory["Memoire synthetique TTL 3600"]
    KModel["gpt-4o-mini existant"] --> KMemory
    KEmbedding["Embedding staging approuve"] --> KMemory
    KMemory --> KAlice["Namespace Alice"]
    KMemory --> KBob["Namespace Bob"]
    KOperator --> KInvoice["Document Intelligence facture"]
    KOperator -.->|"Optionnel non accepte"| KOptional["IQ et modeles CU"]
```

Le rappel, les contrôles croisés et le refus 403 de l'identité employé ont
été vérifiés. Les namespaces ne sont pas des ACL. L'extraction de profil et
de résumé est désactivée ; la mémoire procédurale est un défaut du service.
Aucune extraction ni liaison à l'agent métier n'est revendiquée.
Les entrées expirent après une heure :
[Lab 17](labs/lab-17-native-skills-memory.md) réensemence le magasin existant.
Le skill est écrit par ce projet, pas fourni comme skill Microsoft préinstallé.
File Search et la facture vérifiés ne prouvent pas les options IQ/CU.

## Traces et évaluation native

<details>
<summary>Image rendue si le composant Mermaid est indisponible</summary>

![Provenance des traces et évaluations](../assets/architecture/architecture-fr-6.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart LR
    LStages["Etapes du graphe"] --> LProvider["Pipeline SDK unique"]
    LProvider --> LInsights["Dependencies Application Insights"]
    LInsights --> LQuery["Requete Log Analytics"]
    LQuery --> LExport["Export de neuf spans autorises"]
    LExport --> LReplay["Rejeu synthetique et empreintes"]
    LReplay --> LEval["Evaluation native"]
    LBenchmark["Faits attendus EN et FR"] --> LCapture["Reponses actuelles"]
    LCapture --> LJudge["Trois criteres natifs"]
```

Les spans personnalisés omettent texte et montants ; les erreurs enregistrent
un statut assaini sans exception brute. Les racines de requête de plateforme
et les dépendances SDK peuvent porter des identifiants différents.
L'export exige une ingestion réelle et une provenance cas/règlement non ambiguë.
Il produit un rejeu synthétique, pas une reconstruction de requête privée.

Le benchmark demandeur actuel a réussi cinq cas par langue sur trois critères.
Les scores restent indicatifs, mais toute preuve absente, incomplète ou en
erreur bloque la promotion. Les anciens échecs juge 0/10 et contrôles RAG
restent visibles ; ce n'est pas une amélioration mesurée sur le même dataset.

## Livraison et publication documentaire

<details>
<summary>Image rendue si le composant Mermaid est indisponible</summary>

![Livraison et publication](../assets/architecture/architecture-fr-7.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    MPR["PR liee a une issue"] --> MChecks["Tests builds Bicep CodeQL"]
    MApproval["Approbation humaine de la source exacte"] --> MDispatch["Declenchement manuel"]
    MChecks --> MDispatch
    MDispatch --> MStaging["Deploiement staging"]
    MStaging --> MGate["Readiness Cosmos et evaluations"]
    MGate --> MProtected["Approbation production protegee"]
    MProtected --> MProd["Promotion production"]
    MChecks --> MMerge["Fusion des sources documentaires"]
    MMerge --> MMain["Validation main terminee et verifiee"]
    MMain --> MWiki["Wiki et liens reels conserves"]
    MMerge --> MPages["Atelier GitHub Pages"]
    MChat["Mise a jour chat approuvee separement"] --> MProd
```

La production réutilise les digests MCP/employé résolus en staging et
reconstruit l'agent depuis la source approuvée. Le chat est mis à jour
séparément. Un build frontend sur main ne redéploie pas les applications.
L'embedding mémoire est un ajout staging optionnel.

[Le générateur wiki](../../scripts/publish_showcase_wiki.py) publie les sources
maintenues après contrôle de provenance main. Les tendances viennent des
artefacts de tests ; Home conserve les derniers liens de déploiement réels.
Une publication documentaire ne nécessite aucun redéploiement Azure.

## Références

* [Manifeste](../../azure.yaml) et [infrastructure](../../infra/README.md)
* [Guide natif](native-showcase.md) et [preuves authentiques](showcase-evidence.md)
* [Opérations](../wiki/operations.md), [workflows](../wiki/workflows.md)
  et [interprétation des preuves](../wiki/release-evidence.md)
* [Documentation Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents)
