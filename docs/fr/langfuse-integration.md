---
layout: default
title: Langfuse et Foundry
description: Intégration OTLP facultative limitée aux métadonnées, pilote Azure synthétique sur une VM et comparaison avec l'observabilité native.
lang: fr
nav_order: 23
---

[English](../langfuse-integration.md) | [Accueil des ateliers](index.md) | [Guide des évaluations](evaluation-guide.md) | [README français](../../README.fr.md)

## Recommandation

Conservez Foundry, Application Insights, Azure Monitor et les contrôles
d'évaluation existants par défaut. Ajoutez Langfuse lorsqu'un besoin concret de
gestion des prompts, d'expérimentation multifournisseur ou d'annotation humaine
justifie un système supplémentaire. Langfuse les complète; il n'est pas nécessaire
pour obtenir des traces, jeux de données, juges, évaluations de production ou
contrôles de régression dans Azure.

Des capacités communes ne signifient pas des interfaces, sémantiques
d'évaluation, disponibilités ou responsabilités opérationnelles identiques.
Foundry prend aussi en charge les frameworks tiers via OpenTelemetry; le traçage
multifournisseur n'est pas exclusif à Langfuse. Vérifiez région, type d'agent,
version du SDK, autorisations, politique réseau, statut de préversion et édition
Langfuse avant d'adopter une fonctionnalité.

## Comparaison des capacités

| Besoin                      | Solution Foundry et Azure native                                            | Complément possible de Langfuse                                                        |
|-----------------------------|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| Traces et spans             | Traçage Foundry avec Application Insights et OpenTelemetry                  | Seconde vue orientée LLM, commune aux applications et fournisseurs                      |
| Ingestion OTEL              | Export Azure Monitor OpenTelemetry vers Application Insights                | OTLP/HTTP vers un backend exploité séparément, pas le même point d'ingestion             |
| Appels LLM, agents et outils | Instrumentation des frameworks et traces des agents Foundry                 | Conventions d'observation communes à un parc applicatif hétérogène                      |
| Latence et exceptions       | Requêtes, dépendances, exceptions Application Insights et traces Foundry     | Débogage orienté LLM avec prompts, scores et expériences                                |
| Exploration des traces      | Interface Traces Foundry, Application Insights et Log Analytics/KQL          | Espace d'ingénierie LLM associé aux annotations et expériences                           |
| Surveillance de production  | Alertes Azure Monitor et tableaux opérationnels et qualité Foundry           | Tendances des scores et processus qualité, sans remplacer la surveillance infrastructure |
| Jeux d'évaluation           | Jeux versionnés Foundry et fixtures JSONL synthétiques existantes            | Espace de jeux et expériences partagé par les équipes multifournisseurs                 |
| LLM comme juge              | Évaluateurs intégrés et personnalisés à base de prompts Foundry              | Autres définitions de juges, calibration et gestion des scores                          |
| Scores personnalisés        | Évaluateurs par code, prompt ou endpoint Foundry et tests du dépôt           | Annotations humaines, scores externes et contrôles personnalisés réunis                 |
| Évaluation hors ligne       | SDK/service d'évaluation Foundry et contrôles du dépôt                       | Comparaison d'expériences sur prompts, modèles et code                                  |
| Évaluation de production    | Évaluations Foundry continues et fondées sur les traces                      | Évaluations en ligne et annotations Langfuse configurées séparément                     |
| Tests de régression         | Jeux et évaluateurs versionnés intégrés à CI/CD                              | Expériences Langfuse en CI; seuils et gestion des échecs explicites dans les deux cas     |
| Traces vers jeux de données | Sélection de traces et génération de jeux natives Foundry                   | Curation dans un processus de jeux et expériences Langfuse déjà adopté                  |
| Cycle de vie des prompts    | Artefacts applicatifs et agents versionnés et livraisons gouvernées          | Registre avec versions, labels, cache et observations si l'application l'utilise         |

Azure natif suffit si l'équipe peut déboguer, évaluer, exploiter et décider des
livraisons avec les outils natifs et les contrôles CI existants. Choisissez
Langfuse pour une amélioration démontrée du travail, pas parce qu'Application
Insights ne pourrait pas collecter des traces LLM ou que Foundry manquerait
d'évaluations. Aucun des deux ne transforme un juge non calibré ou une moyenne
suffisante en approbation réglementaire. Les calculs déterministes et
l'approbation par un employé restent obligatoires.

### Conditions du parcours natif traces vers jeux de données

Le [parcours natif Foundry](https://learn.microsoft.com/azure/foundry/observability/how-to/traces-to-dataset)
permet la sélection manuelle de traces et la génération de jeux versionnés.
Le parcours SDK documenté exige `azure-ai-projects>=2.8.0`; ce dépôt fixe
actuellement `2.6.0`. La disponibilité de la plateforme ne prouve pas que le SDK
figé ou la configuration du projet l'implémente. Étudiez la mise à niveau
séparément, sans modifier implicitement le contrat d'évaluation.

Ce parcours exige des régions compatibles, l'accès au projet et les droits de
son identité sur la ressource Application Insights connectée. Le guide actuel
exige aussi l'accès public aux requêtes Application Insights et, pour un stockage
fourni par le client, un accès public au stockage. N'assouplissez pas les
contrôles réseau privés du dépôt sans approbation plateforme/sécurité. Utilisez
les fixtures synthétiques sélectionnées si ces exigences sont incompatibles avec
vos limites. Échantillonnage et suppression de contenu privé sont distincts.

## Ce que cette intégration implémente

L'adaptateur hébergé initialise d'abord le fournisseur existant appartenant au
SDK. L'[exporteur facultatif](../../src/quote-preparation-agent/langfuse_telemetry.py)
ajoute ensuite un seul processeur asynchrone borné par fournisseur :

```text
Agent hébergé / LangGraph / workflow déterministe
                    |
         Fournisseur OTel existant
              /             \
     Exporteur Azure     Scopes retenus, copies nettoyées
        existant                    |
           |                  OTLP/HTTP + clés de projet
  Application Insights              |
    / traces Foundry             Langfuse
```

* L'export est désactivé sauf si `LANGFUSE_TRACING_ENABLED=true`.
* `LANGFUSE_HOST` est une origine HTTPS sans chemin, requête ni identifiants. HTTP n'est permis que pour les tunnels `localhost`, `127.0.0.1` ou `::1`.
* Les clés du projet passent par `LANGFUSE_PUBLIC_KEY` et `LANGFUSE_SECRET_KEY`. Les en-têtes dédiés ne remplacent ni l'authentification Azure ni les paramètres génériques `OTEL_EXPORTER_OTLP_*`.
* L'exporteur cible `/api/public/otel/v1/traces`, utilise l'authentification Basic par clés de projet et l'en-tête d'ingestion v4, pas OTLP/gRPC.
* Seuls les scopes du workflow, du serveur SDK et du callback LangGraph configuré sont transmis. Les scopes HTTP/base de données inconnus sont exclus.
* Les identifiants de trace/span/parent, horodatages, type et code de statut sont conservés. Les noms sont normalisés; les attributs sont limités et leur format vérifié.
* Seuls les étapes approuvées, hachages de politique, références synthétiques de dossier, révisions bornées et références de préparation déjà hachées peuvent être inclus. Événements, liens, descriptions d'exception, attributs arbitraires, trace state et métadonnées originales de ressource sont supprimés de la copie Langfuse.
* Azure reçoit les spans originaux. Une configuration facultative absente/invalide désactive Langfuse avec un avertissement générique. Les erreurs d'export ne font pas échouer l'agent.
* La file est limitée à 512 spans, les lots à 64 et le délai HTTP à cinq secondes. L'hôte/fournisseur vide la file à l'arrêt; aucun envoi réseau forcé par requête. Une panne peut perdre la télémétrie facultative; la livraison n'est pas garantie.

Le processus émet les vraies étapes déterministes `INTAKE`, `REFERENCE_LOOKUP`
et `COMPOSITION`, pas de fausses générations LLM ou mesures de tokens/coûts.
Des ancêtres inconnus ou distants peuvent manquer dans Langfuse. Les identifiants
communs permettent la corrélation sans copier les traces serveur Foundry dans
ce processus. Revérifiez scopes et parents si l'instrumentation change.

Aucun prompt, réponse, argument d'outil, identité client ou contenu arbitraire
n'est volontairement transmis. Cette minimisation n'est pas une certification
de conformité. Des observations limitées aux métadonnées ne permettent pas un
jugement sémantique du contenu, le rejeu de prompts ou des jeux complets de
requêtes/réponses.

OTLP ne synchronise ni versions de prompts, jeux, annotations humaines,
résultats d'évaluation ni scores. Cette modification n'installe pas un second
callback LangGraph, ne récupère pas de prompts Langfuse, ne modifie pas les
contrôles de livraison et n'active pas de juges en ligne. Ces intégrations exigent
des décisions explicites de schéma, responsabilité, confidentialité et coût.
Utilisez des données d'évaluation synthétiques approuvées pour toute expérience.

## Pilote Azure sur une VM

> [!WARNING]
> Le pilote synthétique approuvé séparément dispose de preuves de santé locale
> à la VM, pages de connexion/inscription, appartenance et connexion humaines,
> vues authentifiées du projet/de la trace et ingestion OTLP synthétique réelle
> locale à la VM. Il est volontairement désalloué entre les démonstrations
> approuvées. Les [preuves et limites d'accès](langfuse-pilot-evidence.md)
> distinguent ces contrôles de SSH opérateur, de l'export depuis Foundry distant
> et de la réception correspondante dans Azure. L'export de production reste
> désactivé. Ne modifiez pas les ressources staging/production conservées et ne
> contournez pas les contrôles de déploiement.

Le [modèle Bicep autonome](../../infra/langfuse-pilot.bicep) crée VM, réseau,
NSG, NIC et IPv4 publique statique dans un groupe distinct. Il n'est inclus ni
dans l'infrastructure principale ni dans le manifeste de l'agent. Le défaut est
`Standard_D4s_v5` (4 vCPU, 16 Gio), disque OS Premium de 128 Gio, accès SSH par
clé, Trusted Launch et correctifs plateforme. L'image Ubuntu provient de
`latest` au déploiement; les images de conteneur, pas l'OS, sont figées par digest.

[Cloud-init](../../infra/langfuse-pilot/cloud-init.yaml) installe Docker/Compose
et crée les secrets aléatoires localement dans `/opt/langfuse-pilot/.env`, mode
`0600`. Aucun mot de passe ni clé de projet dans les paramètres Bicep, sorties
de déploiement ou données personnalisées VM. Les administrateurs root/Docker
peuvent toujours lire configuration et secrets; ce n'est pas un coffre de production.

La [pile Compose](../../infra/langfuse-pilot/docker-compose.yml) exécute Langfuse
web/worker 4.70.1, PostgreSQL, Redis, ClickHouse et MinIO sur cette VM. Elle suit
la sélection de services amont 4.70.1 : digests immuables, aucun mot de passe
d'exemple, contrôles de santé, journaux bornés et volumes nommés persistants.
Seul le web publie un port, lié à `127.0.0.1:3000`. Bases et stockage objet ne
sont pas publiés. Téléversements multimodaux, exports par lots, fonctions IA
intégrées et télémétrie fournisseur ne sont pas configurés/activés pour ce pilote.

### Approbation et déploiement

1. Approuvez groupe isolé, abonnement/région Azure, propriétaire, expiration,
   budget, IPv4 publique opérateur et clé publique SSH. Ne transmettez jamais
   de clé privée SSH ni secret de projet dans le chat.
2. Chiffrez les heures VM, disque Premium 128 Gio, IPv4 statique, trafic sortant
   et sauvegardes éventuelles dans le
   [calculateur Azure](https://azure.microsoft.com/pricing/calculator/).
   Aucune estimation régionale n'est approuvée ici. La désallocation arrête le
   calcul, pas les frais de disque/IP allouée; l'arrêt de l'OS ne suffit pas.
3. Utilisez votre workflow Bicep approuvé ou **Deploy Bicep File** dans VS Code
   sur le seul groupe isolé. Fournissez `operatorIpv4Address` sans `/32`,
   `sshPublicKey` et les substitutions approuvées. Examinez ARM what-if avant
   d'approuver. Aucun Foundry, Cosmos, application conservée, rôle ou peering requis.
4. Après le déploiement approuvé séparément, connectez-vous par SSH et lancez
   `sudo cloud-init status --wait`, puis
   `sudo docker compose --project-directory /opt/langfuse-pilot ps`.
   Un succès ARM ne prouve pas le succès de cloud-init ou des migrations.
5. Dans un autre terminal, utilisez la sortie `sshTunnelCommand` ou :

   ```powershell
   ssh -N -o ExitOnForwardFailure=yes -L 3000:127.0.0.1:3000 pilotadmin@<pilot-public-ip>
   ```

6. Sur une nouvelle instance, ouvrez <http://localhost:3000>, créez le premier
   utilisateur, l'organisation, le projet synthétique et ses clés API. Le pilote
   déployé possède déjà une organisation, un projet et des clés root-only issus
   de l'initialisation approuvée sans interface. L'intégration humaine approuvée
   séparément a vérifié le rôle propriétaire, la connexion et les vues projet/trace.
   Le mot de passe reste dans `.synthetic-user.env`, lisible uniquement par root;
   récupérez-le par un accès opérateur approuvé, jamais dans le chat ou les preuves.
   Ne recréez ni compte ni projet et ne supposez pas que d'autres utilisateurs
   héritent de cette appartenance. Aucun administrateur par défaut n'existe.
   La maintenance approuvée du 2026-10-28 a fixé `AUTH_DISABLE_SIGNUP=true` dans
   l'environnement protégé et vérifié la valeur dans les deux conteneurs, en
   conservant compte, appartenance propriétaire, projet et clés. Le modèle du
   dépôt exige toujours ce durcissement explicite après l'intégration sur une
   nouvelle instance. Consultez les [preuves de désactivation](langfuse-pilot-evidence.md#inscriptions).

Utilisez le tunnel sur un poste de confiance. Toute personne accédant au port
local redirigé peut atteindre la connexion/API Langfuse. La règle SSH prévue par
le modèle limite l'accès à l'IPv4 `/32` fournie; la gouvernance déléguée l'a
supprimée sur le pilote et SSH reste bloqué. Respectez les
[conditions de démarrage et d'accès](langfuse-pilot-evidence.md#fonctionnement-sur-demande)
sans désactiver la gouvernance ni restaurer répétitivement sa règle supprimée.
Aucun accès web/OTLP public. Les paquets Ubuntu, registres d'images et toute
connexion ultérieure explicitement configurée à un juge/modèle exigent une sortie réseau.

### Activation et test synthétique

Utilisez un terminal local dédié à l'agent et l'environnement virtuel de
l'atelier. Retirez les paramètres Cosmos/MCP hérités s'ils dirigent le test vers
les environnements conservés. Installez les dépendances actualisées de l'agent
et configurez l'exporteur facultatif avant de démarrer l'hôte :

```powershell
python -m pip install -r src/quote-preparation-agent/requirements.txt
$env:LANGFUSE_HOST = 'http://localhost:3000'
$env:LANGFUSE_PUBLIC_KEY = Read-Host 'Synthetic Langfuse project public key'
$env:LANGFUSE_SECRET_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Synthetic Langfuse project secret key' -AsSecureString)).Password
$env:LANGFUSE_TRACING_ENABLED = 'true'
python src/quote-preparation-agent/main.py
```

Gardez le tunnel SSH ouvert. Dans un autre terminal, vérifiez le serveur
Responses local et soumettez uniquement un dossier synthétique connu :

```powershell
Invoke-RestMethod http://localhost:8088/readiness
Invoke-RestMethod -Method Post -Uri http://localhost:8088/responses -ContentType application/json -Body '{"input":"CASE-SYN-001","stream":false}'
```

Utilisez le mode serveur/hébergé **sans** argument de dossier. Le parcours CLI
`main.py CASE-SYN-001` n'initialise volontairement pas le traçage hébergé. Pour
deux destinations, conservez la configuration Application Insights approuvée et
ses identifiants Entra/RBAC requis. Ne les remplacez pas par Langfuse. Une
observation Langfuse locale ne prouve pas l'ingestion Azure.

Vérifiez les trois étapes d'une requête dans Langfuse, l'absence de contenu et
de mesures inventées de tokens/coûts, et le même identifiant de trace de 32
caractères hexadécimaux dans Application Insights. Pour une ressource liée à un
workspace, interrogez son espace Log Analytics :

```kusto
union AppRequests, AppDependencies, AppTraces
| where OperationId == '<trace-id-from-langfuse>'
| project TimeGenerated, Name, OperationId, ParentId
| order by TimeGenerated asc
```

Tenez compte du délai d'ingestion. Provoquez une panne contrôlée de l'exporteur
et confirmez que l'agent répond et qu'Azure reçoit encore ses spans. Pour revenir
en arrière, redémarrez l'hôte avec `LANGFUSE_TRACING_ENABLED=false`; modifier une
variable ne retire pas un processeur déjà attaché au fournisseur actif. Retirez
ensuite les variables de clés du terminal. Ne les affichez pas, ne les écrivez
pas en clair dans l'historique et ne les versionnez pas dans un fichier d'environnement.

Un agent Foundry distant **ne peut pas atteindre le tunnel localhost de votre
poste**. Le pilote montre le même adaptateur hébergé en exécution locale. Un
export depuis Foundry exige endpoint TLS accessible approuvé séparément,
DNS/routage/sortie, connectivité privée ou ingress contrôlé et injection de
secrets à l'exécution. Le manifeste reste volontairement inchangé; le pilote
n'est pas un raccourci vers un endpoint de télémétrie public ou de production.

### Responsabilité et nettoyage

Cette pile sur une VM n'offre ni HA, sauvegarde automatique, SSO, reprise validée
après sinistre ni politique gérée de conservation. Les volumes survivent au
remplacement des conteneurs et aux arrêts/démarrages VM, pas à la suppression
du disque. Supprimer seulement la VM détache le disque OS : données et frais
peuvent persister. Supprimer le groupe isolé détruit pilote et données. Ne
supprimez pas les groupes conservés de l'atelier.

Fixez une courte durée de conservation/nettoyage approuvée. La rotation des
journaux ne limite pas les tables ClickHouse, événements bruts ni bases.
Surveillez le disque et retirez ce pilote jetable à l'échéance. Une sauvegarde
doit inclure bases, objets et secrets de chiffrement/authentification protégés;
un volume nommé n'est pas une sauvegarde. Réexaminez les digests pour les mises
à jour de sécurité.

Pour la production, évaluez le
[module Terraform Azure officiel](https://github.com/langfuse/langfuse-terraform-azure)
ou une architecture supportée revue indépendamment. Le parcours officiel utilise
AKS, PostgreSQL/Redis gérés et ClickHouse avec état; son coût n'est pas celui de
cette VM. Langfuse prend Azure Blob Storage en charge nativement, mais
l'intégration documentée emploie une clé de compte statique, pas une identité
managée supposée. Révisez rotation, réseau, conservation, restauration,
Entra/SSO, édition/licence et astreinte avant approbation de production.

## Vérification

Lancez les tests ciblés sans identifiants Azure ou Langfuse :

```powershell
python -m pytest src/quote-preparation-agent/tests/test_case_telemetry.py src/quote-preparation-agent/tests/test_hosted_telemetry.py src/quote-preparation-agent/tests/test_langfuse_telemetry.py -q
```

Ils couvrent réutilisation du fournisseur SDK, activation/désactivation,
identifiants identiques, idempotence, projection privée, configuration invalide,
échecs d'export et récepteur HTTP/protobuf local réel. Ils ne prouvent ni
acceptation par un serveur Langfuse actif, ingestion Azure, démarrage VM ou
exécution de juges/jeux. Continuous Validation vérifie aussi l'interpolation
Compose avec de faux identifiants et compile le Bicep autonome sans déploiement.

## Références

* [Observabilité Microsoft Foundry](https://learn.microsoft.com/azure/foundry/concepts/observability)
* [Évaluations cloud Foundry](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation)
* [Évaluations de jeux Foundry](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-datasets)
* [Évaluateurs personnalisés Foundry](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/custom-evaluators)
* [Ingestion OTEL Langfuse](https://langfuse.com/integrations/native/opentelemetry)
* [Langfuse avec un fournisseur OTEL existant](https://langfuse.com/faq/all/existing-otel-setup)
* [Évaluations Langfuse](https://langfuse.com/docs/evaluation/overview)
* [Gestion des prompts Langfuse](https://langfuse.com/docs/prompt-management/overview)
* [Source Compose amont 4.70.1](https://github.com/langfuse/langfuse/blob/v4.70.1/docker-compose.yml)
* [Guide Docker Compose Langfuse](https://langfuse.com/self-hosting/deployment/docker-compose)
* [Configuration Azure Blob Storage Langfuse](https://langfuse.com/self-hosting/infrastructure/blobstorage#azure-blob-storage)