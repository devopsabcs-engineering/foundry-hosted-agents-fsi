---
permalink: /fr/labs/lab-11-web-chat
lang: fr
title: "Atelier 11 - L'interface de clavardage du demandeur"
description: "Exécuter localement le clavardage destiné au demandeur, lire sa barrière d'accès et prouver que cette surface ne peut jamais afficher une prime."
---

> 🇬🇧 **[English version](../../labs/lab-11-web-chat)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 40 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 10](lab-10-azure-foundation.md), Node.js 20 ou plus récent |

À l'atelier 07, vous avez lu le message destiné au demandeur sous forme de JSON brut dans un terminal. `apps/web-chat` est la surface pour laquelle ce message est écrit. Il s'agit d'un service FastAPI qui sert une application React monopage compilée, et c'est le seul endroit où une personne demandeuse interagit avec le système.

La contrainte que vous avez prouvée aux ateliers 02 et 07 dispose maintenant d'une interface à défendre : le demandeur ne voit jamais de prime.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Exécuter localement le service et l'interface du clavardage
* Décrire les quatre variables d'environnement sans lesquelles l'application refuse de démarrer
* Expliquer comment l'appartenance à un groupe, et non un rôle d'application, contrôle l'accès au clavardage
* Retracer comment une charge utile bilingue de l'agent est réduite à une seule langue pour l'affichage
* Expliquer pourquoi une exécution locale s'arrête à la barrière d'accès alors que l'origine déployée ne s'y arrête pas

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

```powershell
cd apps/web-chat/frontend
npm ci
npm test
npm run build
cd ../../..
```

Résultat attendu : `npm test` exécute les suites `node --test` de `apps/web-chat/frontend/tests` et réussit. `npm run build` écrit un paquet compilé dans `apps/web-chat/frontend/dist`, que le service monte à la racine `/` lorsqu'il est présent.

### Exercice 11.3 (pratique) : Exécuter l'application localement

Les valeurs d'identité ci-dessous sont des espaces réservés. Elles suffisent à démarrer le processus et à afficher la barrière d'accès, ce qui est tout ce dont cet exercice a besoin.

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

Résultat attendu : la zone de rédaction est désactivée, la barre latérale indique `Not signed in` et le pied de page porte l'avis de données d'entraînement synthétiques. Cet avis fait partie de la mise en page plutôt que d'un message, il ne peut donc pas être masqué par défilement ni déplacé par la sortie de l'agent.

### Exercice 11.5 (pratique) : Retracer les contrôles d'autorisation

Ouvrez `apps/web-chat/auth.py` et lisez `PilotAuth.verify`.

```powershell
Select-String -Path apps/web-chat/auth.py -Pattern "raise HTTPException" | Select-Object -ExpandProperty Line
```

Résultat attendu : sept chemins de rejet, couvrant un en-tête manquant, un point de terminaison de clés inaccessible, une signature invalide et quatre contrôles de revendications. La signature du jeton est validée contre les clés publiées du locataire, puis les revendications sont vérifiées en séquence :

| Revendication | Exigence |
| --- | --- |
| `tid` | Correspond au locataire configuré |
| `azp` | Correspond à l'identifiant client configuré |
| `scp` | Contient `Chat.Access` |
| `groups` | Contient l'identifiant du groupe pilote configuré |

Ce dernier contrôle distingue cette application de celle de révision de l'atelier 12. L'accès au clavardage est accordé par appartenance à un groupe de sécurité. L'accès à la révision est accordé par attribution d'un rôle d'application. Les deux sont appliqués côté serveur à chaque requête.

Exécutez les tests du service pour voir ces chemins exercés :

```powershell
$env:PYTHONPATH = 'apps/web-chat'
python -m pytest apps/web-chat/tests -v
```

Résultat attendu : les suites d'autorisation et d'application réussissent. L'affectation de `PYTHONPATH` est obligatoire, car ces tests importent `app` et `auth` comme modules de premier niveau, et le pipeline définit la même variable pour la même raison.

### Exercice 11.6 (pratique) : Prouver que la surface ne peut pas afficher de prime

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

Résultat attendu : chaque appel retourne la phrase de la langue demandée. `content_text` ne lit que le champ `text` d'un bloc de contenu, aucun autre champ d'une charge utile de l'agent ne peut donc atteindre la transcription.

Confirmez maintenant où réside réellement le montant. À l'atelier 07, l'agent s'est arrêté à `PENDING_REVIEW` sans jamais placer de chiffre dans `applicant_message`, et à l'atelier 13 vous verrez ce même chiffre apparaître dans l'interface de révision. La prime n'est pas dissimulée au demandeur par un filtre qui pourrait être mal configuré. Elle n'est jamais écrite dans le canal du demandeur au départ.

### Exercice 11.7 : Comprendre ce qu'une exécution locale ne peut pas faire

Envoyer un message exige deux choses dont votre exécution locale ne dispose pas : un `AGENT_ENDPOINT` actif soutenu par un agent hébergé déployé, et un enregistrement d'application dont l'URI de redirection pointe vers votre origine locale.

Le clavardage déployé dispose des deux. `scripts/setup-web-chat-identity.ps1` enregistre les origines déployées aux côtés de `http://localhost:8000`, la connexion fonctionne donc sur l'adresse déployée alors que les valeurs d'identité fictives de l'exercice 11.2 ne le permettent pas.

`infra/web-chat.bicep` est appliqué hors bande (pas via `deploy-and-evaluate.yml`), et uniquement dans le groupe de ressources de production -- il n'existe aucun déploiement de clavardage en préproduction (staging).

```powershell
az containerapp show --name foundry-quote-chat --resource-group $env:AZURE_RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" --output tsv
```

Résultat attendu : un nom d'hôte se terminant par `azurecontainerapps.io`. Ouvrez-le dans un navigateur et connectez-vous avec un compte membre du groupe pilote. L'URL courante est aussi toujours tenue à jour dans le [tableau des liens de déploiement du wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Home).

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
* [ ] Vous avez localisé les quatre contrôles de revendications dans `PilotAuth.verify`
* [ ] `python -m pytest apps/web-chat/tests` réussit avec `PYTHONPATH` défini à `apps/web-chat`

## Vérification des connaissances

* Pourquoi `/api/config` expose-t-il l'identifiant client mais pas l'identifiant du groupe pilote ?
* Pourquoi `AGENT_ENDPOINT` est-il restreint aux hôtes se terminant par `.services.ai.azure.com` ?
* Le clavardage utilise l'appartenance à un groupe et l'application de révision utilise un rôle d'application. Qu'apporte un rôle d'application qu'un groupe n'apporte pas ?
* Si `content_text` reçoit une charge utile dont le champ `text` est une chaîne simple plutôt qu'une table de langues, que retourne-t-il ?

## Étapes suivantes

Poursuivez avec l'[Atelier 12 : Identité et accès du réviseur](lab-12-reviewer-identity.md).
