---
title: Atelier Foundry Hosted Agents - Services financiers (FSI)
description: Atelier pratique bilingue adaptant les agents hébergés Microsoft Foundry à un scénario synthétique de préparation de soumissions d'assurance auto en Ontario, avec un calculateur déterministe et une approbation obligatoire par un employé.
---

[English](README.md) | [Français](README.fr.md)

## Présentation

Ce dépôt propose un atelier pratique bilingue (anglais/français) adapté
du dépôt voisin
[`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents).
Il remplace le scénario d'évaluation des menaces aériennes par un scénario
de services financiers : un agent synthétique de préparation de
soumissions d'assurance auto en Ontario, appuyé par un calculateur
déterministe et une étape d'approbation obligatoire par un employé,
persistée séparément, avant tout aperçu destiné au demandeur.

> [!IMPORTANT]
> Chaque donnée d'exemple, référentiel de règles et résultat de calcul de
> ce dépôt est synthétique et non contraignant. Rien ici ne représente un
> produit, un tarif ou une police Desjardins réel, et aucun organisme de
> réglementation ni assureur n'a révisé ou approuvé cet atelier.

## Parcours de l'apprenant

Le parcours par défaut de ces ateliers ne nécessite pas GitHub Copilot ni
aucun autre assistant de programmation par IA. Lorsque les auteurs de
l'atelier ont utilisé un outil assisté par IA pour rédiger ou réviser un
contenu, cette assistance est indiquée dans l'atelier ou le fichier
concerné plutôt que présentée comme faisant partie du parcours de
l'apprenant.

## Structure du dépôt

* [docs/](docs/) contient le site de l'atelier en anglais (Jekyll, thème
  Just the Docs). Commencez par [docs/index.md](docs/index.md).
* [docs/fr/](docs/fr/) contient le site de l'atelier en français, dont la
  structure correspond à celle du site anglais. Commencez par
  [docs/fr/index.md](docs/fr/index.md).
* [src/quote-preparation-agent/](src/quote-preparation-agent/) contient
  l'agent LangGraph hébergé de préparation de soumissions.
* [mcp/application-server/](mcp/application-server/) contient un service
  MCP en lecture seule exposant les données synthétiques des demandes.
* [mcp/rulebook-server/](mcp/rulebook-server/) contient un service MCP en
  lecture seule exposant les données synthétiques du référentiel de règles.
* [apps/workshop/](apps/workshop/) contient le calculateur déterministe,
  le dépôt des approbations et les vues du demandeur et du réviseur.
* [apps/web-chat/](apps/web-chat/) contient une interface de clavardage
  pilote interne pour l'agent hébergé, reprise du dépôt voisin. Elle est
  déployée séparément ([infra/web-chat.bicep](infra/web-chat.bicep)), aux
  côtés de [apps/reviewer-app/](apps/reviewer-app/). Consultez les
  [liens de déploiement](#liens-de-déploiement) pour les URL actuelles
  des deux interfaces.
* [data/synthetic/](data/synthetic/) contient les données d'exemple
  synthétiques et le schéma JSON du contrat de préparation de soumissions.
* [eval/](eval/) contient le banc d'évaluation des calculs, des
  approbations, des injections et de la parité bilingue.
* [infra/](infra/) contient les modules d'infrastructure Bicep, réservés
  aux auteurs jusqu'à la validation des exigences de plateforme et de
  réglementation.
* [scripts/](scripts/) contient les utilitaires partagés, dont le
  générateur de présentations bilingues pour l'atelier.

## Pour commencer

Commencez par la page d'accueil de l'atelier :
[docs/fr/index.md](docs/fr/index.md) en français ou
[docs/index.md](docs/index.md) en anglais. Le même contenu est publié
sous forme de site navigable à l'adresse
<https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/fr/>
(une connexion à GitHub est requise tant que ce dépôt est privé).

## Essayer l'interface de clavardage

L'interface dans [apps/web-chat/](apps/web-chat/) est déployée séparément en
production (consultez les [liens de déploiement](#liens-de-déploiement)
pour l'URL actuelle). Pour l'exécuter localement en utilisant l'agent
réellement déployé :

```powershell
cd apps/web-chat/frontend
npm install
npm run build
cd ..
$env:AGENT_ENDPOINT = "$env:FOUNDRY_PROJECT_ENDPOINT/agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1"
$env:ENTRA_TENANT_ID = (az account show --query tenantId -o tsv)
$env:ENTRA_CLIENT_ID = "<ID d'inscription d'application fourni par scripts/setup-web-chat-identity.ps1>"
$env:PILOT_GROUP_ID = "<ID d'objet du groupe de sécurité pilote>"
python -m uvicorn app:create_app --factory --host 127.0.0.1 --port 8000
```

Ouvrez ensuite <http://127.0.0.1:8000/>. L'écran d'accueil s'affiche sans
configuration Entra. Le bouton **Sign in with Microsoft** et la zone de
saisie des messages deviennent utilisables uniquement lorsque
`ENTRA_CLIENT_ID` et `PILOT_GROUP_ID` correspondent à une inscription
d'application et à un groupe pilote réels.

![Interface de clavardage pour la préparation de soumissions](assets/web-chat-ui.png)

Si `npm install` échoue avec `EALLOWREMOTE`, la valeur par défaut
`allow-remote = "none"` de npm 12 refuse les URL absolues des archives
tarball du proxy de flux d'entreprise. Relancez la commande avec
`npm install --allow-remote=all`.

## Essayer l'application de révision

[apps/reviewer-app/](apps/reviewer-app/) fournit la file de dossiers
destinée aux réviseurs : chaque dossier que l'agent soumet pour révision
y apparaît. L'accès est contrôlé par un rôle d'application Entra plutôt
que par l'appartenance au groupe de sécurité du clavardage. Consultez les
[liens de déploiement](#liens-de-déploiement) pour l'URL actuelle, ou
[l'atelier 13](docs/fr/labs/lab-13-reviewer-ui.md) pour exécuter
l'application localement avec une inscription Entra réelle.

![Interface de révision des soumissions](assets/reviewer-app-ui.png)

## Liens de déploiement

> [!NOTE]
> Les noms des ressources Azure et de l'environnement `azd` de production
> portent un suffixe historique `-poc` (par exemple
> `cosmos-desjardins-quote-preparation-poc` et
> `aif-desjardins-quote-preparation-poc`). Malgré ce suffixe, ces ressources
> sont celles de production, et non un déploiement de validation de concept
> distinct. Le tableau Deployment Links du wiki indique explicitement
> `(production)` ou `(staging)` pour chaque ligne. Fiez-vous à cette
> indication plutôt qu'au texte `-poc` dans un nom ou une URL.

Aucune URL de démonstration active n'est inscrite en dur ici, car les noms
d'hôtes Container Apps et le nom du projet Foundry dépendent de
l'environnement et peuvent changer lors d'un reprovisionnement.
La [page d'accueil du wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Home)
contient plutôt un tableau Deployment Links, actualisé automatiquement
après chaque exécution en préproduction ou en production du flux
[`Deploy and Evaluate (Staging -> Production)`](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/workflows/deploy-and-evaluate.yml).
Il fournit les liens vers les ressources déployées, dont les deux
interfaces pilotes :

* L'application de révision (file d'approbation des dossiers) et
  l'interface de clavardage destinée aux demandeurs
* Le projet Foundry de l'agent hébergé (portail Azure, connexion requise)
* Le point de terminaison de l'API Responses de l'agent
* Les points de terminaison MCP `application-server` et `rulebook-server`
* Le groupe de ressources et le registre de conteneurs
* Le site de l'atelier publié sur GitHub Pages

Utilisez toujours la
[page d'accueil du wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Home)
pour obtenir les URL actuelles des interfaces. Les deux applications de
conteneur peuvent recevoir un nouveau nom d'hôte lors d'un
reprovisionnement, et cette page est la seule copie actualisée à chaque
déploiement.

Consultez également la page
[Continuous Test Trends](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Continuous-Test-Trends)
du wiki pour les résultats les plus récents des tests hors ligne, des
contrôles déterministes et des évaluations par un modèle juge.

Les scores du juge sont indicatifs, mais un échec d'invocation réelle ou une
réponse absente bloque la promotion en production. Une erreur renvoyée avec
HTTP 200 ne constitue pas une réponse réussie de l'agent. Vérifiez qu'un cas
synthétique valide atteint la révision par un employé avant de déclarer
l'environnement reconstruit prêt pour une démonstration.

L'interface de clavardage pilote dans [apps/web-chat/](apps/web-chat/) est
déployée séparément et non par
[deploy-and-evaluate.yml](.github/workflows/deploy-and-evaluate.yml).
Son modèle [infra/web-chat.bicep](infra/web-chat.bicep) est appliqué par
une commande directe `az deployment group create` dans l'environnement
Container Apps déjà provisionné par [infra/main.bicep](infra/main.bicep).
Son inscription d'application Entra est créée par
[scripts/setup-web-chat-identity.ps1](scripts/setup-web-chat-identity.ps1).
Comme l'environnement managé est recréé lorsque sa configuration réseau
change, redéployez l'interface et relancez le script d'identité après toute
reconstruction du réseau. Son URL n'est pas une sortie `azd` :
la tâche `promote-production` du flux
[deploy-and-evaluate.yml](.github/workflows/deploy-and-evaluate.yml) lit
les variables de dépôt `WEB_CHAT_APP_NAME` et `WEB_CHAT_URL` applicables
à l'environnement de production pour les inclure dans le tableau
Deployment Links du wiki. Mettez ces variables à jour après tout
redéploiement du clavardage sous un nouveau nom d'hôte.

## Restaurer la démonstration après une suppression complète

Les résultats de la dernière reconstruction et les blocages restants sont
suivis dans le
[ticket #7](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/7).
Consultez ce suivi avant d'utiliser les anciens liens du wiki pour une
démonstration client.

> [!IMPORTANT]
> Un déploiement réussi dans le passé ne signifie pas que la démonstration
> est actuellement accessible. Une suppression complète retire le groupe
> de ressources partagé, le registre, les projets Foundry, les bases de
> dossiers et les interfaces pilotes. Les anciens liens du wiki restent
> historiques jusqu'à la restauration des ressources correspondantes.
> Utilisez uniquement des données synthétiques. Le déploiement ne recrée
> pas les données de dossiers supprimées.

1. Confirmez les approbations de mise en service, l'abonnement et la région
   cibles. Consultez la configuration du dépôt et de ses environnements
   GitHub `staging` et `production`.
2. Recréez le groupe indiqué par `AZURE_RESOURCE_GROUP` et le registre
   indiqué par `MCP_ACR_NAME`. Le
   [flux de déploiement](.github/workflows/deploy-and-evaluate.yml)
   exige leur présence avant de déployer le réseau et de construire les
   images. Rétablissez les autorisations nécessaires à l'identité de
   déploiement au niveau du groupe de ressources, y compris l'attribution
   de rôles et l'accès Foundry. N'activez pas les identifiants
   d'administration du registre.
3. Retirez les valeurs périmées de `AGENT_PRINCIPAL_ID` et `WEB_CHAT_URL`
   des ressources supprimées, dans les variables du dépôt et les
   remplacements propres aux environnements. Conservez les inscriptions
   d'applications Entra et les groupes pilotes et de réviseurs existants.
4. Exécutez [Continuous Validation](.github/workflows/continuous-validation.yml),
   [Web Chat Build](.github/workflows/web-chat-build.yml) et
   [Reviewer App Build](.github/workflows/reviewer-app-build.yml) sur la
   révision à déployer. Les exécutions manuelles des flux d'interfaces
   testent et compilent les applications sans les déployer.
5. Lancez [Deploy and Evaluate](.github/workflows/deploy-and-evaluate.yml)
   pour cette révision. Le flux restaure la préproduction, évalue l'agent
   déployé et attend l'approbation humaine requise avant la promotion en
   production. L'application de révision est incluse lorsque
   `REVIEWER_CLIENT_ID` est configuré.
   Le flux CI doit authentifier Azure CLI et `azd` avec GitHub OIDC :
   les extensions Foundry exigent une connexion native `azd` même lorsque
   `auth.useAzCliAuth` est activé.
6. Pour chaque environnement, récupérez l'identité du nouvel agent hébergé
   dans le projet Foundry actif et vérifiez son existence dans Entra.
   Définissez `AGENT_PRINCIPAL_ID` pour cet environnement et appliquez son
   autorisation d'accès aux données Cosmos avec
   [le module RBAC existant](infra/modules/cosmos-rbac.bicep), ou
   reprovisionnez avec cette nouvelle valeur. Ne réutilisez pas
   l'identité supprimée et ne la remplacez pas par l'identité managée du
   projet.
7. Construisez et déployez séparément le clavardage dans chaque
   environnement Container Apps restauré avec
   [web-chat.bicep](infra/web-chat.bicep). Fournissez le projet Foundry,
   l'étiquette de déploiement et une image épinglée par empreinte pour
   cet environnement. Actualisez les URL de redirection réelles avec
   [setup-web-chat-identity.ps1](scripts/setup-web-chat-identity.ps1) et
   [setup-reviewer-identity.ps1](scripts/setup-reviewer-identity.ps1).
   Mettez à jour `WEB_CHAT_APP_NAME` et `WEB_CHAT_URL` dans l'environnement
   GitHub correspondant, puis les liens de déploiement du wiki.
8. Vérifiez les deux projets Foundry et leurs agents actifs, les deux
   services MCP, la disponibilité et la connexion aux interfaces, les
   réponses bilingues et l'arrivée d'une demande synthétique dans la file
   de révision. Confirmez qu'aucun montant destiné au demandeur n'est
   communiqué sans approbation par un employé. La réussite des tests hors
   ligne ne suffit pas à établir que la démonstration est prête.
