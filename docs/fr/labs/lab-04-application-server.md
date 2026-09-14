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

Le serveur écoute sur `http://0.0.0.0:8001` avec le transport streamable-http par défaut. Laissez-le fonctionner, puis dans un second terminal, appelez `get_application` directement en important la même fonction d'outil que le serveur expose :

```powershell
python -c "
import sys
sys.path.insert(0, 'mcp/application-server')
from main import get_application

print(get_application('CASE-SYN-001'))
print(get_application('CASE-SYN-999'))
"
```

Résultat attendu : l'identifiant connu retourne le contenu `input` de la donnée ; l'identifiant inconnu retourne un champ `error` explicite, jamais une exception levée ni une donnée fabriquée. Arrêtez le serveur avec `Ctrl+C` une fois terminé.

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
