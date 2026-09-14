---
permalink: /fr/labs/lab-02-calculator
lang: fr
title: "Atelier 02 - Le calculateur déterministe"
description: "Retracer la fonction pure calculate_quote et prouver qu'elle n'invente jamais un montant pour une entrée qu'elle ne peut résoudre."
---

> 🇬🇧 **[English version](../../labs/lab-02-calculator)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 30 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 01](lab-01-fixtures-schema.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Retracer l'ordre de résolution de `calculate_quote` dans `apps/workshop/calculator.py` : référentiel indisponible, incompatibilité de version, champs manquants, valeurs non prises en charge, puis résultat prêt
* Énoncer les quatre statuts de calcul que le calculateur peut retourner
* Ajouter un nouveau cas de test et confirmer qu'il réussit
* Prouver qu'un référentiel sans correspondance produit un code d'incident, jamais un montant inventé

## Exercices

### Exercice 2.1 : Lire l'ordre de résolution

Ouvrez `apps/workshop/calculator.py` et lisez `calculate_quote` du début à la fin. Notez l'ordre dans lequel la fonction vérifie les conditions :

1. `rulebook is None` retourne `EVIDENCE_UNAVAILABLE`
2. Une incompatibilité de version du référentiel (quand `expected_rulebook_version` est fourni) retourne `EVIDENCE_UNAVAILABLE` avec `RULE_VERSION_MISMATCH`
3. Toute absence de `jurisdiction`, `vehicleClass` ou `plan` retourne `INCOMPLETE` avec un incident par champ manquant
4. Une juridiction autre que `ON`, ou un `vehicleClass`/`plan` absent des tables `baseCents`/`planAddOnCents` du référentiel, retourne `UNSUPPORTED`
5. Sinon, la fonction additionne `baseCents[vehicleClass] + planAddOnCents[plan]` et retourne `READY`

### Exercice 2.2 : Exécuter les tests existants

```powershell
python -m pytest apps/workshop/tests/test_calculator.py -v
```

Résultat attendu : tous les tests réussissent, y compris celui qui affirme le résultat exact de 100000 cents pour `case-syn-001`.

### Exercice 2.3 (pratique) : Ajouter un nouveau cas de test

Ajoutez un test à `apps/workshop/tests/test_calculator.py` affirmant qu'un véhicule `SEDAN` avec le régime `TRAINING_BASIC` se résout exactement à 90000 cents, en utilisant la même forme de référentiel que les tests existants. Relancez le fichier et confirmez que votre nouveau test réussit avec les autres.

### Exercice 2.4 (pratique) : Prouver la règle du montant jamais inventé

Dans un shell Python, construisez un dictionnaire de référentiel copié de `data/synthetic/rulebook.json`, retirez la clé `"SEDAN"` de `baseCents`, puis appelez `calculate_quote` avec une entrée `SEDAN` contre ce référentiel modifié.

```powershell
python -c "
import json, pathlib, sys
sys.path.insert(0, 'apps/workshop')
from calculator import calculate_quote

rulebook = json.loads(pathlib.Path('data/synthetic/rulebook.json').read_text())
del rulebook['baseCents']['SEDAN']
result = calculate_quote({'jurisdiction': 'ON', 'vehicleClass': 'SEDAN', 'plan': 'TRAINING_BASIC'}, rulebook)
print(result)
"
```

Résultat attendu : `status` vaut `UNSUPPORTED`, `amountCents` vaut `null`, et `issues` contient `UNSUPPORTED_INPUT`. Aucun montant n'est retourné, même si `TRAINING_BASIC` est un régime reconnu.

## Liste de vérification

* [ ] `pytest apps/workshop/tests/test_calculator.py -v` réussit, y compris votre test de l'exercice 2.3
* [ ] Vous pouvez énumérer de mémoire les quatre statuts de calcul
* [ ] L'exercice 2.4 confirme qu'un référentiel incomplet retourne `UNSUPPORTED_INPUT`, jamais un montant
* [ ] Vous pouvez expliquer, sans regarder le code, pourquoi la vérification de disponibilité du référentiel s'exécute avant celle des champs manquants

## Vérification des connaissances

* Pourquoi le calculateur vérifie-t-il l'absence de référentiel avant de vérifier les champs manquants ?
* Quelle devise et quelle période porte chaque résultat `READY`, et d'où proviennent ces valeurs ?

## Étapes suivantes

Poursuivez avec l'[Atelier 03 : Dépôt d'approbation et machine à états](lab-03-approval-repository.md).
