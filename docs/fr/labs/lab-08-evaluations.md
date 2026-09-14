---
permalink: /fr/labs/lab-08-evaluations
lang: fr
title: "Atelier 08 - Suite d'évaluation"
description: "Explorer le jeu de données de référence et les vérifications déterministes qui contrôlent l'arithmétique, l'approbation et la parité linguistique."
---

> 🇬🇧 **[English version](../../labs/lab-08-evaluations)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 30 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 02](lab-02-calculator.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Repérer le jeu de données de référence bilingue anglais/français et la porte d'évaluation déterministe
* Nommer les catégories que la porte d'évaluation est conçue pour vérifier : arithmétique, preuve, exactitude de l'état d'approbation, résistance à l'injection, gestion des données manquantes, isolation des dossiers et parité linguistique
* Exécuter la porte d'évaluation contre l'implémentation de ce dépôt
* Écrire votre propre petite vérification déterministe qui reflète la catégorie arithmétique, à l'échelle de ce que vous avez construit aux ateliers 01 et 02

## Exercices

### Exercice 8.1 : Repérer les artefacts d'évaluation

```powershell
Test-Path eval/golden-dataset.jsonl
Test-Path eval/evaluation_gate.py
```

`eval/` contient le jeu de données de référence bilingue et la porte d'évaluation qui le vérifie contre le calculateur, le dépôt d'approbation et les serveurs MCP de ce projet. Si l'un des chemins retourne `False` dans votre copie, la suite d'évaluation n'est pas encore arrivée ; poursuivez avec l'exercice 8.3, qui n'en dépend pas.

### Exercice 8.2 : Exécuter la porte d'évaluation

Si les deux chemins de l'exercice 8.1 ont retourné `True` :

```powershell
python eval/evaluation_gate.py --dataset eval/golden-dataset.jsonl
```

Résultat attendu : la porte rapporte la réussite de chaque vérification requise. Elle est conçue pour qu'un juge de qualité ne puisse jamais annuler un échec arithmétique ou d'état d'approbation ; un cas requis manquant ou ignoré fait échouer l'exécution d'emblée.

### Exercice 8.3 (pratique) : Écrire votre propre vérification arithmétique

Que `eval/` existe déjà ou non dans votre copie, vous pouvez écrire le même type de vérification que la porte d'évaluation effectue pour l'arithmétique, à l'échelle des données de l'atelier 01.

```powershell
python -c "
import json, pathlib, sys
sys.path.insert(0, 'apps/workshop')
from calculator import calculate_quote

failures = []
for path in sorted(pathlib.Path('data/synthetic/fixtures').glob('*.json')):
    fixture = json.loads(path.read_text())
    actual = calculate_quote(fixture['input'], fixture['rulebook'])
    expected = fixture['expectedCalculation']
    if actual != expected:
        failures.append((path.name, actual, expected))

if failures:
    for name, actual, expected in failures:
        print(f'ÉCART {name}: obtenu={actual} attendu={expected}')
else:
    print('Toutes les données correspondent à leur expectedCalculation.')
"
```

Résultat attendu : chaque donnée correspond exactement à son `expectedCalculation`, affichant une seule ligne de confirmation.

## Liste de vérification

* [ ] Vous avez repéré, ou confirmé l'absence de, `eval/golden-dataset.jsonl` et `eval/evaluation_gate.py`
* [ ] S'il est présent, `eval/evaluation_gate.py` a rapporté la réussite de chaque vérification requise
* [ ] Votre vérification de l'exercice 8.3 confirme que `calculate_quote` correspond à `expectedCalculation` pour chaque donnée
* [ ] Vous pouvez nommer les sept catégories que la porte d'évaluation complète est conçue pour couvrir

## Vérification des connaissances

* Pourquoi un juge de qualité ne doit-il jamais pouvoir annuler un échec arithmétique ou d'état d'approbation dans cette porte ?
* Au-delà de l'arithmétique, quelles catégories de défauts le jeu de données de référence doit-il couvrir au minimum pour les données manquantes et une tentative d'approbation non autorisée ?

## Étapes suivantes

Poursuivez avec l'[Atelier 09 : Démantèlement](lab-09-teardown.md).
