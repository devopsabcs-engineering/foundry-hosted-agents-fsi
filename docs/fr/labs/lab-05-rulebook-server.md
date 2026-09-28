---
permalink: /fr/labs/lab-05-rulebook-server
lang: fr
title: "Atelier 05 - Le serveur MCP de référentiel"
description: "Exécuter le serveur de référentiel en lecture seule et confirmer qu'il ne sert que la table de tarifs synthétique épinglée."
---

> 🇬🇧 **[English version](../../labs/lab-05-rulebook-server)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 20 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 00](lab-00-setup.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Expliquer pourquoi `mcp/rulebook-server` s'exécute indépendamment de `apps/workshop` et de l'agent, sans exécution partagée
* Confirmer que le serveur n'expose qu'un seul outil, `get_rulebook(rulebook_id)`
* Démarrer le serveur localement et l'interroger pour l'identifiant de référentiel épinglé et un identifiant inconnu
* Expliquer pourquoi le référentiel servi porte toujours `"authority": "WORKSHOP_AUTHORS_ONLY"`

## Exercices

### Exercice 5.1 : Lire le serveur

Ouvrez `mcp/rulebook-server/main.py` et `mcp/rulebook-server/rulebook_data_loader.py`. Notez que `get_rulebook` compare le `rulebook_id` demandé au champ `id` de l'unique référentiel épinglé, `RULEBOOK-SYN-ON`, et retourne un objet explicite `{"rulebookId": ..., "error": "rulebook not found"}` pour toute autre valeur.

### Exercice 5.2 : Exécuter les tests existants

```powershell
python -m pytest mcp/rulebook-server/tests -v
```

Résultat attendu : tous les tests réussissent, reflétant la couverture de l'atelier 04 pour la recherche de référentiel.

### Exercice 5.3 (pratique) : Démarrer le serveur et l'interroger

```powershell
python mcp/rulebook-server/main.py
```

Le serveur écoute sur `http://0.0.0.0:8002` par défaut. Laissez-le fonctionner, puis dans un second terminal, appelez-le par MCP :

```powershell
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client('http://localhost:8002/mcp') as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print('outils :', [t.name for t in tools.tools])
            for rulebook_id in ('RULEBOOK-SYN-ON', 'RULEBOOK-DOES-NOT-EXIST'):
                result = await session.call_tool('get_rulebook', {'rulebook_id': rulebook_id})
                print(rulebook_id, '->', result.content[0].text)

asyncio.run(main())
"
```

Résultat attendu : l'identifiant de référentiel épinglé retourne le référentiel complet, y compris ses tables `baseCents`, `planAddOnCents` et le texte d'avis `en-CA`/`fr-CA`. L'identifiant inconnu retourne un champ `error` explicite. La console du serveur affiche une ligne `get_rulebook(...) -> found` ou `-> rulebook not found` par appel. Arrêtez le serveur avec `Ctrl+C` une fois terminé.

## Liste de vérification

* [ ] `pytest mcp/rulebook-server/tests -v` réussit
* [ ] Le `rulebookId` épinglé retourne exactement le contenu du référentiel
* [ ] Un `rulebookId` inconnu retourne un résultat `error` explicite, pas une exception
* [ ] Vous pouvez énoncer ce que `"authority": "WORKSHOP_AUTHORS_ONLY"` communique à quiconque lit ces données

## Vérification des connaissances

* Pourquoi ce serveur ne sert-il qu'un seul identifiant de référentiel plutôt qu'une table de recherche pour plusieurs référentiels ?
* Si une nouvelle version de référentiel était épinglée demain, qu'est-ce qui devrait changer dans le fichier de données de ce serveur pour que `get_rulebook` la retourne ?

## Étapes suivantes

Poursuivez avec l'[Atelier 06 : L'agent LangGraph](lab-06-agent-graph.md).
