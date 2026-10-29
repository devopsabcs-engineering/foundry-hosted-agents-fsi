---
permalink: /fr/labs/lab-11-web-chat
lang: fr
title: "Atelier 11 - L'interface de clavardage du demandeur"
description: "Exécuter localement le clavardage destiné au demandeur, lire sa barrière d'accès et retracer le contrat borné sans prime."
---

> 🇬🇧 **[English version](../../labs/lab-11-web-chat.md)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 40 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 10](lab-10-azure-foundation.md), Node.js 22, environnement Python de l'atelier 00 réactivé |

À l'atelier 07, vous avez lu le message destiné au demandeur sous forme de JSON brut dans un terminal. `apps/web-chat` est la surface pour laquelle ce message est écrit. Il s'agit d'un service FastAPI qui sert une application React monopage compilée, et c'est le seul endroit où une personne demandeuse interagit avec le système.

La contrainte que vous avez prouvée aux ateliers 02 et 07 dispose maintenant d'une interface à défendre : le demandeur ne voit jamais de prime.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Exécuter localement le service et l'interface du clavardage
* Décrire les quatre variables d'environnement sans lesquelles l'application refuse de démarrer
* Expliquer comment l'appartenance à un groupe, et non un rôle d'application, contrôle l'accès au clavardage
* Retracer comment une charge utile bilingue de l'agent est réduite à une seule langue pour l'affichage
* Distinguer le parcours avec espaces réservés d'un client local entièrement configuré

## Exercices

### Exercice 11.1 : Lire le contrat de démarrage

```powershell
Select-String -Path apps/web-chat/app.py -Pattern "os.environ\[" | Select-Object -ExpandProperty Line
```

Résultat attendu : quatre variables obligatoires, `AGENT_ENDPOINT`, `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID` et `PILOT_GROUP_ID`. Les trois valeurs d'identité sont analysées avec `uuid.UUID()`, donc une valeur malformée échoue au démarrage plutôt qu'à la première requête.

`AGENT_ENDPOINT` est validé plus strictement que les autres :

```powershell
Select-String -Path apps/web-chat/app.py -Pattern "must be a Foundry HTTPS endpoint" -Context 3,0
```

Résultat attendu : le protocole doit être `https` et l'hôte doit se terminer par `.services.ai.azure.com`. L'application ne sera pas dirigée vers une adresse arbitraire.

### Exercice 11.2 (pratique) : Compiler l'interface

Depuis la racine et dans l'environnement virtuel actif, installez les
dépendances de ce service avant de compiler l'interface :

```powershell
python -m pip install -r apps/web-chat/requirements.txt
cd apps/web-chat/frontend
npm ci
npm test
npm run build
cd ../../..
```

Résultat attendu : `npm test` exécute les suites `node --test` de `apps/web-chat/frontend/tests` et réussit. `npm run build` écrit un paquet compilé dans `apps/web-chat/frontend/dist`, que le service monte à la racine `/` lorsqu'il est présent.

### Exercice 11.3 (pratique) : Exécuter l'application localement

Identités et URL ci-dessous sont des espaces réservés non fonctionnels.
Ils passent les contrôles de format et affichent seulement la barrière d'accès;
`/stream` n'est pas la route Responses réelle de l'agent.

```powershell
cd apps/web-chat
$env:ENTRA_TENANT_ID = '00000000-0000-0000-0000-000000000000'
$env:ENTRA_CLIENT_ID = '00000000-0000-0000-0000-000000000001'
$env:PILOT_GROUP_ID = '00000000-0000-0000-0000-000000000002'
$env:AGENT_ENDPOINT = 'https://example-project.services.ai.azure.com/api/projects/demo/agents/quote-preparation/stream'
python -m uvicorn app:create_app --factory --host 127.0.0.1 --port 8200
```

Résultat attendu : uvicorn affiche `Application startup complete`. Il n'existe aucun objet `app` au niveau du module dans `apps/web-chat/app.py`, l'indicateur `--factory` est donc obligatoire.

Dans un deuxième terminal :

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:8200/api/config' -UseBasicParsing | Select-Object -ExpandProperty Content
```

Résultat attendu : un document JSON avec `tenantId`, `clientId`, `scope` et `environment`. La portée est dérivée sous la forme `api://<clientId>/Chat.Access`. Remarquez ce qui est absent : l'identifiant du groupe pilote n'atteint jamais le navigateur, parce que le navigateur n'est pas ce qui l'applique.

### Exercice 11.4 : Lire la barrière d'accès

Ouvrez `http://localhost:8200` dans un navigateur.

![Le clavardage du demandeur avant la connexion, affichant le titre « Quotes start with access. », un bouton de connexion Microsoft, une zone de message désactivée et un avis de données synthétiques]({{ "/assets/images/web-chat-sign-in.png" | relative_url }})

Résultat attendu : la zone de rédaction est désactivée, la barre latérale indique `Non connecté` (ou `Not signed in` en anglais) et le pied de page porte l'avis de données d'entraînement synthétiques. Cet avis fait partie de la mise en page plutôt que d'un message, il ne peut donc pas être masqué par défilement ni déplacé par la sortie de l'agent.

Les cinq requêtes synthétiques (`CASE-SYN-001` à `CASE-SYN-005`) apparaissent
après connexion et confirmation d'appartenance côté serveur. Les espaces
réservés ne permettent pas cette connexion. Utilisez le clavardage déployé ou
un client local entièrement configuré avec l'origine `localhost:8000` enregistrée.

Si vous sélectionnez tout de même **Se connecter avec Microsoft**, Entra ID rejette la demande avec `AADSTS900021: Requested tenant identifier '00000000-...' is not valid`. C'est attendu : le navigateur transmet le locataire fictif reçu de `/api/config` directement à la page de connexion Entra ID.

> [!TIP]
> Pour vous connecter localement, redémarrez uvicorn avec les vraies valeurs `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID` et `PILOT_GROUP_ID` du clavardage déployé (`az containerapp show -n <web-chat-app> -g <resource-group> --query "properties.template.containers[0].env"`), utilisez `--port 8000` et ouvrez `http://localhost:8000`. C'est la seule URI de redirection locale enregistrée par `scripts/setup-web-chat-identity.ps1`, et `127.0.0.1` ne lui correspond pas. Votre compte doit aussi être membre du groupe pilote, sinon `/api/me` retourne 403 et les requêtes de démonstration restent masquées.
>
> Remplacez aussi `AGENT_ENDPOINT` par la vraie URL `/agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1` sous le projet cible. L'identité Azure locale du service doit avoir l'accès Foundry autorisé.

### Exercice 11.5 (pratique) : Retracer les contrôles d'autorisation

Pour les exercices 11.5–11.7, utilisez un second terminal à la racine avec
le même environnement virtuel actif; laissez uvicorn dans son terminal.
Ouvrez `apps/web-chat/auth.py` et lisez `PilotAuth.verify`.

```powershell
Select-String -Path apps/web-chat/auth.py -Pattern "raise HTTPException" | Select-Object -ExpandProperty Line
```

Résultat attendu : sept chemins de rejet. La validation JWT contrôle signature,
émetteur, audience et revendications temporelles/d'identité obligatoires.
Les contrôles applicatifs exigent aussi :

| Revendication | Exigence |
| --- | --- |
| `tid` | Correspond au locataire configuré |
| `azp` | Correspond à l'identifiant client configuré |
| `scp` | Contient `Chat.Access` |
| `groups` | Contient l'identifiant du groupe pilote configuré |
| `oid` | Chaîne non vide identifiant le compte authentifié |

Le contrôle de groupe distingue cette application de la révision de l'atelier
12, autorisée par rôle d'application. Ces contrôles sont appliqués côté serveur
à chaque requête.

Exécutez les tests du service pour voir ces chemins exercés :

```powershell
$env:PYTHONPATH = 'apps/web-chat'
python -m pytest apps/web-chat/tests -v
```

Résultat attendu : les suites d'autorisation et d'application réussissent. L'affectation de `PYTHONPATH` est obligatoire, car ces tests importent `app` et `auth` comme modules de premier niveau, et le pipeline définit la même variable pour la même raison.

### Exercice 11.6 (pratique) : Retracer le contrat sans prime

L'agent émet du contenu bilingue, et le service le réduit à une seule langue avant qu'il n'atteigne le navigateur.

```powershell
python -c "
import sys
sys.path.insert(0, 'apps/web-chat')
from app import content_text

payload = {'text': {'en-CA': 'Your request was submitted for employee review.', 'fr-CA': 'Votre demande a ete soumise pour revision.'}}
print(repr(content_text(payload, 'en-CA')))
print(repr(content_text(payload, 'fr-CA')))
"
```

Résultat attendu : chaque appel retourne la langue demandée. `content_text`
ne lit que `text`, mais c'est un sélecteur de langue, pas un filtre de prix.
Un montant présent dans une chaîne arbitraire ne serait pas supprimé.

À l'atelier 07, le graphe s'arrête à `PENDING_REVIEW` sans montant dans
`applicant_message`; l'atelier 13 montre le calcul dans la révision.
La frontière repose sur les gabarits demandeur bornés du graphe et le
convertisseur de réponses hébergées, pas sur ce sélecteur. Conservez leurs
tests de régression et ceux du flux de clavardage; cette démonstration seule
ne prouve pas l'innocuité d'une sortie arbitraire.

### Exercice 11.7 : Comprendre ce qu'une exécution locale ne peut pas faire

Le parcours fictif manque d'un `AGENT_ENDPOINT` réel, d'un enregistrement
avec la bonne origine et d'une identité Azure autorisée côté service.
Un client local possédant ces trois éléments peut envoyer des messages.

`scripts/setup-web-chat-identity.ps1` enregistre les origines approuvées et
`http://localhost:8000`. Les espaces réservés de l'exercice 11.3 ne permettent
une authentification à aucune de ces origines.

`infra/web-chat.bicep` est appliqué hors bande, pas via `deploy-and-evaluate.yml`. Le clavardage existe en staging et en production. Conservez la configuration d'environnement et d'identité de chaque application; limitez la mise à jour à l'image sans changement d'infrastructure prévu. Consultez les [versions et digests vérifiés](../showcase-evidence.md#livraison-approuvée-actuelle).

```powershell
# Charger les valeurs de l'environnement azd (AZURE_RESOURCE_GROUP et autres) dans cette session
azd env get-values | ForEach-Object { if ($_ -match '^([^=]+)="?(.*?)"?$') { Set-Item "env:$($Matches[1])" $Matches[2] } }
az containerapp show --name foundry-quote-chat --resource-group $env:AZURE_RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" --output tsv
```

Résultat attendu : nom d'hôte en `azurecontainerapps.io`. Connectez-vous avec
un membre du groupe pilote. Le [tableau du wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Home)
publie aussi les URL; vérifiez sa livraison source et sa fraîcheur.

> [!NOTE]
> Le nom d'hôte change chaque fois que l'environnement d'applications conteneurisées est recréé, ce que couvre l'atelier 14. Si la connexion échoue avec une discordance d'URI de redirection, l'enregistrement est périmé plutôt que mal configuré ; réexécutez `scripts/setup-web-chat-identity.ps1` avec le nom de domaine courant.

Une exécution locale enseigne tout de même la partie la plus importante ici. La barrière d'accès, le point de terminaison de configuration et la réduction linguistique s'exercent tous sans aucun déploiement, et ce sont là les limites sur lesquelles une personne révisant le système poserait des questions.

Arrêtez le service lorsque vous avez terminé.

```powershell
# Dans le terminal qui exécute uvicorn
Ctrl+C
```

## Liste de vérification

* [ ] `npm test` et `npm run build` réussissent dans `apps/web-chat/frontend`
* [ ] Le service démarre avec `--factory` et affiche `Application startup complete`
* [ ] `/api/config` retourne une portée `api://<clientId>/Chat.Access` et omet l'identifiant du groupe pilote
* [ ] Le navigateur affiche une zone de rédaction désactivée et une barre latérale `Not signed in` avant l'authentification
* [ ] Vous avez localisé les contrôles de locataire, client, portée, groupe et identifiant d'objet
* [ ] `python -m pytest apps/web-chat/tests` réussit avec `PYTHONPATH` défini à `apps/web-chat`

## Vérification des connaissances

* Pourquoi `/api/config` expose-t-il l'identifiant client mais pas l'identifiant du groupe pilote ?
* Pourquoi `AGENT_ENDPOINT` est-il restreint aux hôtes se terminant par `.services.ai.azure.com` ?
* Le clavardage utilise l'appartenance à un groupe et l'application de révision utilise un rôle d'application. Qu'apporte un rôle d'application qu'un groupe n'apporte pas ?
* Si `content_text` reçoit une charge utile dont le champ `text` est une chaîne simple plutôt qu'une table de langues, que retourne-t-il ?

## Étapes suivantes

Poursuivez avec l'[Atelier 12 : Identité et accès du réviseur](lab-12-reviewer-identity.md).
