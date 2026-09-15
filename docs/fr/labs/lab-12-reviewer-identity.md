---
permalink: /fr/labs/lab-12-reviewer-identity
lang: fr
title: "Atelier 12 - Identité et accès du réviseur"
description: "Enregistrer l'application de révision, accorder le rôle Reviewer via un groupe de sécurité et calculer les URI de redirection avant le déploiement de l'application."
---

> 🇬🇧 **[English version](../../labs/lab-12-reviewer-identity)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 45 minutes |
| **Niveau** | Avancé |
| **Prérequis** | [Atelier 11](lab-11-web-chat.md), un locataire Entra où vous pouvez consentir à des permissions d'application Microsoft Graph |

L'application de révision est la seule surface de ce système qui affiche une prime calculée. Toute sa configuration d'identité découle de ce seul fait.

> [!WARNING]
> Ce laboratoire écrit dans votre locataire Entra. Utilisez un locataire de développement ou bac à sable. Chaque étape est réversible, et l'exercice 12.7 montre comment.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Exécuter `scripts/setup-reviewer-identity.ps1` en mode aperçu puis réellement
* Expliquer pourquoi l'application de révision utilise un rôle d'application alors que le clavardage utilise un groupe
* Calculer l'URI de redirection d'une application conteneurisée avant que celle-ci n'existe
* Accorder le rôle Reviewer à un groupe de sécurité plutôt qu'à des personnes individuelles
* Publier l'identifiant client obtenu comme variable de dépôt pour l'intégration continue

## Exercices

### Exercice 12.1 : Lire le contrat du script

```powershell
Get-Help ./scripts/setup-reviewer-identity.ps1 -Full
```

Résultat attendu : un synopsis, trois paramètres (`RedirectUri`, `TenantId`, `ReviewerGroupId`) et une description indiquant que le script peut être réexécuté sans risque, car il résout l'application par nom d'affichage exact et la met à jour lorsqu'elle existe déjà.

Lisez attentivement le paragraphe sur les permissions. Le script requiert des permissions d'application Microsoft Graph, et un rôle d'abonnement Azure tel que Propriétaire ou Contributeur n'en accorde aucune :

| Opération | Permission Graph |
| --- | --- |
| Créer ou mettre à jour l'application | `Application.ReadWrite.All` |
| Accorder le rôle Reviewer à un groupe | `AppRoleAssignment.ReadWrite.All` |
| Consentir administrativement à la portée Review.Access | `DelegatedPermissionGrant.ReadWrite.All` |

C'est pourquoi l'identité d'intégration continue du dépôt n'exécute pas ce script. Une personne administratrice l'exécute depuis un poste de travail après `az login`.

### Exercice 12.2 (pratique) : Prévisualiser les changements

Le script prend en charge `ShouldProcess`, vous pouvez donc voir ce qu'il ferait avant qu'il ne fasse quoi que ce soit.

```powershell
az login --tenant <votre-id-locataire>
./scripts/setup-reviewer-identity.ps1 -TenantId <votre-id-locataire> -WhatIf
```

Résultat attendu : une description de l'application qui serait créée, nommée `Foundry Quote Preparation Reviewer`, sans aucune écriture dans le locataire.

### Exercice 12.3 (pratique) : Créer l'enregistrement

```powershell
./scripts/setup-reviewer-identity.ps1 -TenantId <votre-id-locataire>
```

Résultat attendu : le script se termine avec le code 0 et affiche l'identifiant client de révision. Notez-le. Réexécuter le script retourne le même identifiant, car l'application est résolue par nom d'affichage plutôt que créée aveuglément.

Inspectez ce qui a été créé :

```powershell
az ad app show --id <id-client-revision> --query "{name:displayName, spa:spa.redirectUris, scopes:api.oauth2PermissionScopes[].value, roles:appRoles[].value}"
```

Résultat attendu : un URI de redirection SPA (`http://localhost:8100`), une portée déléguée (`Review.Access`) et un rôle d'application (`Reviewer`).

### Exercice 12.4 : Comprendre le choix d'un rôle plutôt qu'un groupe

L'atelier 11 montrait le clavardage contrôlant l'accès via `groups`. L'application de révision s'appuie plutôt sur un rôle d'application.

```powershell
az ad sp show --id <id-client-revision> --query "{assignmentRequired:appRoleAssignmentRequired}"
```

Résultat attendu : `appRoleAssignmentRequired` vaut `true`.

Cet indicateur constitue la différence de fond. Lorsque l'attribution est obligatoire, Entra refuse d'émettre un jeton pour cette application à quiconque ne s'est pas vu attribuer le rôle. Une personne non autorisée est donc arrêtée au fournisseur d'identité plutôt qu'à l'application. Une revendication d'appartenance à un groupe, en revanche, est informative : l'application doit penser à la vérifier.

Pour une surface qui révèle une décision tarifée, échouer de façon fermée au fournisseur d'identité constitue la valeur par défaut la plus solide.

### Exercice 12.5 (pratique) : Calculer les URI de redirection déployés

L'interface de révision configure MSAL avec `redirectUri: window.location.origin`.

```powershell
Select-String -Path apps/reviewer-app/frontend/src/main.jsx -Pattern "redirectUri" | Select-Object -ExpandProperty Line
```

Résultat attendu : la redirection correspond à l'origine de la page, sans barre oblique finale ni chemin. Un URI enregistré doit donc correspondre exactement à l'origine.

L'origine d'une application conteneurisée est son nom joint au domaine par défaut de son environnement. L'atelier 10 a montré que le nom de l'application de révision est déterministe, et le domaine de l'environnement se lit depuis Azure :

```powershell
az containerapp env list --query "[].{name:name, rg:resourceGroup, domain:properties.defaultDomain}" -o table
```

Résultat attendu : une ligne par environnement d'applications conteneurisées. Construisez l'origine sous la forme `https://<nom-application-revision>.<domaine-par-defaut>`.

Enregistrez-la aux côtés de l'URI local. Le script fusionne la nouvelle valeur avec celles déjà enregistrées, exécuter le script une fois par environnement accumule donc les valeurs plutôt que de les remplacer :

```powershell
./scripts/setup-reviewer-identity.ps1 -TenantId <votre-id-locataire> -RedirectUri 'https://foundry-quote-reviewer.<domaine-production>'
./scripts/setup-reviewer-identity.ps1 -TenantId <votre-id-locataire> -RedirectUri 'https://foundry-quote-reviewer-staging.<domaine-preproduction>'
az ad app show --id <id-client-revision> --query "spa.redirectUris"
```

Résultat attendu : trois URI, les deux origines déployées et `http://localhost:8100`. Toute valeur autre que l'origine locale doit être en HTTPS, et le script rejette tout le reste.

Conserver l'URI local enregistré est intentionnel. L'atelier 13 exécute l'application de révision sur votre poste de travail contre l'enregistrement réel, ce qui ne fonctionne que tant que `http://localhost:8100` demeure valide.

### Exercice 12.6 (pratique) : Accorder le rôle via un groupe

Attribuez le rôle à un groupe plutôt qu'à des personnes. L'appartenance change ensuite sans toucher à l'enregistrement de l'application.

```powershell
az ad group create --display-name 'Foundry Quote Preparation Reviewers' --mail-nickname 'foundry-quote-reviewers'
$groupId = az ad group show --group 'Foundry Quote Preparation Reviewers' --query id -o tsv
./scripts/setup-reviewer-identity.ps1 -TenantId <votre-id-locataire> -ReviewerGroupId $groupId
```

Résultat attendu : le rôle Reviewer est attribué avec un `principalType` valant `Group`.

Ajoutez-vous au groupe afin de pouvoir vous connecter à l'atelier 13 :

```powershell
$me = az ad signed-in-user show --query id -o tsv
az ad group member add --group $groupId --member-id $me
az role assignment list --assignee $me --query "[].roleDefinitionName" -o tsv
```

Résultat attendu : votre compte est membre. Notez que le rôle Reviewer est un rôle d'application et non un rôle de ressource Azure, il n'apparaît donc pas dans `az role assignment list`. Confirmez-le plutôt sur le principal de service :

```powershell
az ad sp show --id <id-client-revision> --query "appRoles[?value=='Reviewer']"
```

### Exercice 12.7 : Publier l'identifiant client et nettoyer

L'intégration continue lit l'identifiant client depuis une variable de dépôt. Le modèle Bicep de l'atelier 10 ignore entièrement le module de révision lorsqu'elle est absente.

```powershell
gh variable set REVIEWER_CLIENT_ID --body '<id-client-revision>'
gh variable list
```

Résultat attendu : `REVIEWER_CLIENT_ID` apparaît dans la liste. Il s'agit d'une variable plutôt que d'un secret, car un identifiant client public n'est pas une donnée d'authentification.

Lorsque vous aurez terminé l'atelier 13 et souhaiterez retirer ce que ce laboratoire a créé :

```powershell
az ad app delete --id <id-client-revision>
az ad group delete --group 'Foundry Quote Preparation Reviewers'
gh variable delete REVIEWER_CLIENT_ID
```

## Liste de vérification

* [ ] `-WhatIf` a prévisualisé l'enregistrement sans écrire dans le locataire
* [ ] L'enregistrement expose la portée `Review.Access` et le rôle `Reviewer`
* [ ] `appRoleAssignmentRequired` vaut `true`
* [ ] `spa.redirectUris` contient les deux origines déployées et `http://localhost:8100`
* [ ] Le rôle Reviewer est attribué à un groupe, et vous êtes membre de ce groupe
* [ ] `REVIEWER_CLIENT_ID` est publié comme variable de dépôt

## Vérification des connaissances

* Pourquoi une identité OIDC GitHub Actions disposant du rôle Propriétaire sur l'abonnement peut-elle tout de même échouer à exécuter ce script ?
* Qu'est-ce qui échouerait si un URI de redirection était enregistré sous la forme `https://<hote>/` avec une barre oblique finale ?
* Pourquoi le script fusionne-t-il les URI de redirection au lieu de les remplacer ?
* Pourquoi un identifiant client est-il publié comme variable de dépôt plutôt que comme secret ?

## Étapes suivantes

Poursuivez avec l'[Atelier 13 : L'interface de révision](lab-13-reviewer-ui.md).
