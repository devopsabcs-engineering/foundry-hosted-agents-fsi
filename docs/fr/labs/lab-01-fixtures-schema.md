---
permalink: /fr/labs/lab-01-fixtures-schema
lang: fr
title: "Atelier 01 - Données et schéma"
description: "Explorer les données synthétiques de préparation de soumission et le schéma JSON draft-07 qui encadre leurs formes de calcul et de flux de travail."
---

> 🇬🇧 **[English version](../../labs/lab-01-fixtures-schema)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 20 minutes |
| **Niveau** | Débutant |
| **Prérequis** | [Atelier 00](lab-00-setup.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Décrire les cinq données synthétiques de `data/synthetic/fixtures/` et le statut de calcul que chacune produit
* Expliquer comment `data/synthetic/quote-contract.schema.json` utilise `if`/`then`/`else` pour lier le statut d'un calcul à ses champs `amountCents` et `issues`
* Expliquer comment le schéma lie l'état de flux de travail d'un dossier à son champ `approvedRevision`
* Valider vous-même chaque donnée synthétique par rapport au schéma

## Exercices

### Exercice 1.1 : Lire l'ensemble des données synthétiques

Ouvrez chaque fichier de `data/synthetic/fixtures/` et notez son `fixtureId`, son `input` et son `expectedCalculation.status` :

| Donnée | Catégorie de véhicule | Régime | Statut attendu |
| --- | --- | --- | --- |
| case-syn-001.json | COMPACT | TRAINING_EXTENDED | READY (100000 cents) |
| case-syn-002-sedan.json | SEDAN | TRAINING_BASIC | READY |
| case-syn-003-unsupported.json | UNKNOWN | TRAINING_BASIC | UNSUPPORTED |
| case-syn-004-revision.json | SEDAN | TRAINING_EXTENDED | READY (draftRevision 2) |
| case-syn-005-missing-plan.json | COMPACT | null | INCOMPLETE |

Chaque donnée porte `"dataClass": "SYNTHETIC_ONLY"` et le même référentiel `RULEBOOK-SYN-ON`, épinglé à `"authority": "WORKSHOP_AUTHORS_ONLY"`.

### Exercice 1.2 : Lire la logique conditionnelle du schéma

Ouvrez `data/synthetic/quote-contract.schema.json` et trouvez le bloc `if`/`then`/`else` de la définition `calculation`. Quand `status` vaut `READY`, le schéma exige un `amountCents` non nul, exactement trois `ruleIds` et zéro `issues`. Pour tout autre statut, il exige un `amountCents` nul et au moins un code d'incident. Trouvez la règle équivalente pour `workflow` : un état `APPROVED` exige un `approvedRevision` non nul, alors que tout autre état l'exige nul.

### Exercice 1.3 : Valider les données par rapport au schéma

```powershell
python -c "
import json, pathlib
from jsonschema import validate

schema = json.loads(pathlib.Path('data/synthetic/quote-contract.schema.json').read_text())
for path in sorted(pathlib.Path('data/synthetic/fixtures').glob('*.json')):
    fixture = json.loads(path.read_text())
    validate(instance=fixture, schema=schema)
    print(f'{path.name}: OK')
"
```

Résultat attendu : chaque donnée affiche `OK`, sans qu'aucune `ValidationError` ne soit levée.

### Exercice 1.4 (pratique) : Expliquer les cas non pris en charge et de révision

Répondez, dans vos propres mots, en vous appuyant uniquement sur le contenu des données et le schéma :

1. Pourquoi `case-syn-003-unsupported.json` produit-il `UNSUPPORTED` plutôt que `INCOMPLETE`, alors que chaque champ d'entrée est présent ?
2. `case-syn-004-revision.json` a `draftRevision: 2`. Que cela indique-t-il sur l'historique de ce dossier, et pourquoi le schéma rejetterait-il `draftRevision: 2` combiné à `approvedRevision: null` si l'état de flux de travail était `APPROVED` ?

## Liste de vérification

* [ ] Vous pouvez nommer les cinq données et le statut de calcul que chacune est censée produire
* [ ] Le script de l'exercice 1.3 affiche `OK` pour chaque donnée sans erreur de validation
* [ ] Vous pouvez expliquer pourquoi une catégorie de véhicule inconnue produit `UNSUPPORTED` plutôt qu'un incident de champ manquant
* [ ] Vous pouvez expliquer la règle du schéma de l'exercice 1.2 exigeant `approvedRevision` pour `APPROVED`

## Vérification des connaissances

* Quelle donnée est conçue pour exercer l'invalidation de révision, et quel numéro de champ a changé pour le signaler ?
* Quelle valeur porte `rulebook.authority` sur chaque donnée, et pourquoi cela importe-t-il pour une personne qui lit ces données ?

## Étapes suivantes

Poursuivez avec l'[Atelier 02 : Le calculateur déterministe](lab-02-calculator.md).
