---
permalink: /fr/labs/lab-06-agent-graph
lang: fr
title: "Atelier 06 - L'agent LangGraph"
description: "Retracer le superviseur et ses trois spécialistes séquentiels : accueil, recherche de référence et composition."
---

> 🇬🇧 **[English version](../../labs/lab-06-agent-graph)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 35 minutes |
| **Niveau** | Avancé |
| **Prérequis** | [Atelier 02](lab-02-calculator.md), [Atelier 03](lab-03-approval-repository.md), [Atelier 04](lab-04-application-server.md), [Atelier 05](lab-05-rulebook-server.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Nommer les trois étapes séquentielles de l'agent : accueil, recherche de référence, composition
* Expliquer la règle de routage du superviseur dans `decide_next_step`, y compris le court-circuit pour une référence de dossier invalide
* Expliquer pourquoi `toolbox.py` appelle les fonctions d'outils MCP des ateliers 04/05 directement en processus plutôt que d'ouvrir une session client réseau
* Confirmer que le code de l'agent lui-même n'appelle jamais `approve`, `reject` ou `revise` sur le dépôt d'approbation

## Exercices

### Exercice 6.1 : Lire la logique de routage du superviseur

Ouvrez `src/quote-preparation-agent/graph.py` et lisez `decide_next_step`. Le superviseur visite toujours `intake` en premier. Si l'accueil a jugé la référence de dossier valide, il route ensuite vers `reference_lookup` ; si l'accueil l'a jugée invalide, il saute directement à `composition` afin que celle-ci puisse tout de même produire un message de refus borné. Une fois la composition terminée, le graphe se termine.

### Exercice 6.2 : Comprendre pourquoi les appels de la boîte à outils sont en processus

Ouvrez `src/quote-preparation-agent/toolbox.py` et lisez le docstring du module. Il explique que cette phase appelle `get_application` et `get_rulebook` en chargeant directement le `main.py` de chaque serveur MCP, plutôt que d'ouvrir une `ClientSession` du SDK Python `mcp` contre un serveur en cours d'exécution. Cela garde les tests rapides et sans port ouvert, tout en exerçant exactement les fonctions que chaque serveur expose via MCP. Notez également que `approve`, `reject`, `revise` et `open_training_preview` ne sont volontairement jamais importés ici : seule une personne réviseure humaine peut les appeler.

### Exercice 6.3 : Exécuter les tests existants

```powershell
python -m pytest src/quote-preparation-agent/tests/test_toolbox.py -v
```

Résultat attendu : tous les tests réussissent, confirmant que les enveloppes de la boîte à outils appellent correctement le calculateur, le dépôt d'approbation et les deux serveurs MCP.

### Exercice 6.4 (pratique) : Injecter un modèle de substitution

`build_graph` dans `graph.py` accepte un paramètre optionnel `model`, dont la valeur par défaut est `default_model`, qui ne fait aucun appel réseau. Construisez le graphe avec votre propre substitut et confirmez que la note du nœud d'accueil le reflète.

```powershell
python -c "
import sys
sys.path.insert(0, 'src/quote-preparation-agent')
from graph import build_graph

def my_stub_model(prompt: str) -> str:
    return f'[lab-06-stub] {prompt}'

graph = build_graph(model=my_stub_model)
result = graph.invoke({
    'case_id': 'CASE-SYN-001',
    'preparer_id': 'AGENT-INTAKE',
    'rulebook_id': 'RULEBOOK-SYN-ON',
    'intake_complete': False,
    'lookup_complete': False,
    'composition_complete': False,
})
print(result['intake_note'])
"
```

Résultat attendu : la note affichée commence par `[lab-06-stub]`, confirmant que le paramètre `model` est un véritable point d'extension et non une valeur figée.

## Liste de vérification

* [ ] `pytest src/quote-preparation-agent/tests/test_toolbox.py -v` réussit
* [ ] Vous pouvez nommer les trois étapes séquentielles et expliquer le court-circuit pour une référence de dossier invalide
* [ ] Vous avez repéré le docstring de la boîte à outils expliquant le choix des appels MCP en processus
* [ ] Le texte de votre modèle de substitut de l'exercice 6.4 est apparu dans la sortie du graphe

## Vérification des connaissances

* Pourquoi `toolbox.py` n'importe-t-il jamais `approve`, `reject`, `revise` ou `open_training_preview` depuis le dépôt d'approbation ?
* Qu'est-ce qui devrait changer dans `toolbox.py` pour que cet agent appelle un serveur MCP déployé plutôt qu'une fonction en processus ?

## Étapes suivantes

Poursuivez avec l'[Atelier 07 : Exécuter l'agent de bout en bout](lab-07-run-agent.md).
