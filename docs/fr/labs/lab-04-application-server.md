---
permalink: /fr/labs/lab-04-application-server
lang: fr
title: "Atelier 04 - Le serveur MCP d'application"
description: "Exécuter le serveur d'application en lecture seule et confirmer qu'il n'expose que get_application, en rejetant les identifiants de données inconnus."
---

> 🇬🇧 **[English version](../../labs/lab-04-application-server)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 25 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 00](lab-00-setup.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Expliquer pourquoi `mcp/application-server` s'exécute indépendamment de `apps/workshop` et de l'agent, sans exécution partagée
* Confirmer que le serveur n'expose qu'un seul outil, `get_application(fixture_id)`
* Démarrer le serveur localement et l'interroger pour un identifiant connu et un identifiant inconnu
* Confirmer que le serveur n'expose jamais un comportement capable d'écriture

## Exercices

### Exercice 4.1 : Lire le serveur

Ouvrez `mcp/application-server/main.py` et `mcp/application-server/application_data_loader.py`. Notez que `get_application` recherche une donnée par identifiant parmi celles chargées au démarrage et retourne un objet explicite `{"fixtureId": ..., "error": "fixture not found"}` pour tout identifiant qu'il ne reconnaît pas, plutôt que de lever une exception ou de retourner un résultat vide.

### Exercice 4.2 : Exécuter les tests existants

```powershell
python -m pytest mcp/application-server/tests -v
```

Résultat attendu : tous les tests réussissent, y compris les cas pour une donnée connue, un identifiant inconnu et une vérification qu'aucun autre outil n'est enregistré sur ce serveur.

### Exercice 4.3 (pratique) : Démarrer le serveur et l'interroger

Dans un premier terminal, démarrez le serveur :

```powershell
python mcp/application-server/main.py
```

Le serveur écoute sur `http://0.0.0.0:8001` avec le transport streamable-http par défaut. Laissez-le fonctionner, puis dans un second terminal, appelez-le par MCP comme le fait l'agent :

```powershell
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client('http://localhost:8001/mcp') as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print('outils :', [t.name for t in tools.tools])
            for fixture_id in ('CASE-SYN-001', 'CASE-SYN-999'):
                result = await session.call_tool('get_application', {'fixture_id': fixture_id})
                print(fixture_id, '->', result.content[0].text)

asyncio.run(main())
"
```

Résultat attendu dans le second terminal : `outils : ['get_application']`, puis l'identifiant connu retourne le contenu `input` de la donnée et l'identifiant inconnu retourne un champ `error` explicite, jamais une exception levée ni une donnée fabriquée.

Revenez au premier terminal. Chaque appel apparaît dans la console du serveur :

```text
Processing request of type ListToolsRequest
Processing request of type CallToolRequest
get_application('CASE-SYN-001') -> found
Processing request of type CallToolRequest
get_application('CASE-SYN-999') -> fixture not found
```

Arrêtez le serveur avec `Ctrl+C` une fois terminé.

## Liste de vérification

* [ ] `pytest mcp/application-server/tests -v` réussit
* [ ] Un `fixtureId` connu retourne exactement l'entrée de la donnée
* [ ] Un `fixtureId` inconnu retourne un résultat `error` explicite, pas une exception
* [ ] Vous avez confirmé que le serveur n'expose aucun outil autre que `get_application`

## Vérification des connaissances

* Pourquoi ce serveur charge-t-il ses données une seule fois au démarrage plutôt que de lire le disque à chaque appel ?
* Que se passerait-il si `get_application` levait une exception pour un identifiant inconnu plutôt que de retourner un objet d'erreur ?

## Étapes suivantes

Poursuivez avec l'[Atelier 05 : Le serveur MCP de référentiel](lab-05-rulebook-server.md).
