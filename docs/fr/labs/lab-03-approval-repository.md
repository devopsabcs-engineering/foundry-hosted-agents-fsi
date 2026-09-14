---
permalink: /fr/labs/lab-03-approval-repository
lang: fr
title: "Atelier 03 - Dépôt d'approbation et machine à états"
description: "Parcourir la machine à états DRAFT à PENDING_REVIEW à APPROVED/REJECTED et prouver que l'auto-approbation est impossible."
---

> 🇬🇧 **[English version](../../labs/lab-03-approval-repository)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 40 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 01](lab-01-fixtures-schema.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Décrire la machine à états d'`ApprovalRepository` : DRAFT, PENDING_REVIEW, APPROVED, REJECTED
* Expliquer pourquoi la personne qui révise un dossier ne peut jamais être celle qui l'a préparé
* Déclencher et intercepter vous-même une `SelfApprovalError`
* Confirmer qu'une révision d'un dossier déjà tranché le remet à DRAFT et efface la décision précédente

## Exercices

### Exercice 3.1 : Lire la machine à états

Ouvrez `apps/workshop/approval_repository.py` et lisez le docstring du module ainsi que la classe `ApprovalRepository`. Repérez :

* `create_draft` crée un dossier en état `DRAFT` à la révision 1
* `submit_for_review` fait passer `DRAFT` à `PENDING_REVIEW`
* `approve` et `reject` appellent tous deux la méthode privée `_decide`, qui fait passer `PENDING_REVIEW` à `APPROVED` ou `REJECTED`
* `revise` crée une nouvelle révision à partir de n'importe quel état, la remettant à `DRAFT` et effaçant le réviseur ainsi que l'horodatage d'approbation

### Exercice 3.2 : Exécuter les tests existants

```powershell
python -m pytest apps/workshop/tests/test_approval_repository.py -v
```

Résultat attendu : tous les tests réussissent, couvrant l'ensemble de la machine à états et le comportement d'invalidation de révision.

### Exercice 3.3 (pratique) : Déclencher un refus d'auto-approbation

Dans un shell Python, créez une ébauche avec une personne préparatrice, soumettez-la pour révision, puis tentez de l'approuver avec cette même personne comme réviseure.

```powershell
python -c "
import sys
sys.path.insert(0, 'apps/workshop')
from approval_repository import ApprovalRepository, SelfApprovalError

repo = ApprovalRepository()
repo.create_draft('CASE-LAB-001', preparer_id='EMP-001')
repo.submit_for_review('CASE-LAB-001', actor_id='EMP-001')

try:
    repo.approve('CASE-LAB-001', reviewer_id='EMP-001')
    print('INATTENDU : l\\'auto-approbation a réussi')
except SelfApprovalError as exc:
    print(f'Bloqué comme prévu : {exc}')

record = repo.approve('CASE-LAB-001', reviewer_id='EMP-002')
print(f'Approuvé par un réviseur distinct : state={record.state}')
"
```

Résultat attendu : le premier appel à `approve` lève `SelfApprovalError`. Le second appel, avec un `reviewer_id` différent, réussit et rapporte `state=APPROVED`.

### Exercice 3.4 (pratique) : Réviser un dossier approuvé

En poursuivant dans la même session de shell, appelez `repo.revise('CASE-LAB-001', actor_id='EMP-001')` et inspectez l'enregistrement retourné.

Résultat attendu : `state` est revenu à `DRAFT`, `revision` a été incrémenté, et `reviewer_id`/`approved_at` sont effacés. L'approbation précédente ne s'applique plus à la nouvelle révision.

## Liste de vérification

* [ ] `pytest apps/workshop/tests/test_approval_repository.py -v` réussit
* [ ] Vous avez déclenché et intercepté `SelfApprovalError` avec un `reviewer_id` égal au `preparer_id` du dossier
* [ ] Un `reviewer_id` distinct a approuvé le même dossier avec succès
* [ ] `revise` après `APPROVED` a remis le dossier à `DRAFT` et effacé le réviseur ainsi que l'horodatage d'approbation

## Vérification des connaissances

* Pourquoi `_decide` vérifie-t-il `reviewer_id == record.preparer_id` avant de vérifier l'état actuel du dossier ?
* Que se passe-t-il si vous appelez `approve` deux fois de suite avec le même `reviewer_id` sur un dossier déjà approuvé ? Relisez `_decide` si vous n'êtes pas certain.

## Étapes suivantes

Poursuivez avec l'[Atelier 04 : Le serveur MCP d'application](lab-04-application-server.md).
