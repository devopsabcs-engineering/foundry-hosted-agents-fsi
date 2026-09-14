---
permalink: /fr/labs/lab-07-run-agent
lang: fr
title: "Atelier 07 - Exécuter l'agent de bout en bout"
description: "Exécuter l'agent local contre une donnée synthétique, lire son message bilingue borné destiné au demandeur, puis agir comme réviseur humain."
---

> 🇬🇧 **[English version](../../labs/lab-07-run-agent)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 30 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 06](lab-06-agent-graph.md) |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Exécuter l'interface en ligne de commande de l'agent de bout en bout contre une donnée synthétique, sans appel à Azure ni à Foundry hébergé
* Confirmer que le message destiné au demandeur ne contient jamais de montant, de table de référentiel ni de champ réservé au réviseur
* Agir comme réviseur humain contre le même `ApprovalRepository`, puisqu'aucune interface de révision n'existe encore
* Confirmer qu'une référence de dossier invalide produit un message de refus borné plutôt qu'une exception levée

## Exercices

### Exercice 7.1 : Exécuter l'interface en ligne de commande sur une donnée connue

```powershell
python src/quote-preparation-agent/main.py CASE-SYN-001
```

Résultat attendu : un objet JSON avec les clés `en-CA` et `fr-CA`, chacune contenant une phrase bilingue informant le demandeur que sa requête a été soumise pour révision par un employé. Aucun montant, champ de référentiel ni identifiant de réviseur n'apparaît nulle part dans la sortie.

### Exercice 7.2 (pratique) : Confirmer directement l'état du flux de travail

L'interface en ligne de commande n'affiche que le message destiné au demandeur. Appelez `run_case` directement pour inspecter l'état complet, y compris `workflow_state`.

```powershell
python -c "
import sys
sys.path.insert(0, 'src/quote-preparation-agent')
from main import run_case

final_state = run_case('CASE-SYN-001')
print('workflow_state:', final_state['workflow_state'])
print('draft_case_id:', final_state['draft_case_id'])
print('applicant_message:', final_state['applicant_message'])
"
```

Résultat attendu : `workflow_state` vaut `PENDING_REVIEW`. Le dossier a été créé et soumis pour révision, mais rien dans le code de l'agent lui-même ne l'a approuvé ou rejeté.

### Exercice 7.3 (pratique) : Agir comme réviseur humain

Comme aucune interface de révision n'existe encore dans ce projet, une personne réviseure agit directement contre `ApprovalRepository`. Partagez une même instance de dépôt entre l'exécution de l'agent et votre étape de révision afin qu'elles opèrent sur le même dossier.

```powershell
python -c "
import sys
sys.path.insert(0, 'src/quote-preparation-agent')
sys.path.insert(0, 'apps/workshop')
from main import run_case
from approval_repository import ApprovalRepository

repo = ApprovalRepository()
final_state = run_case('CASE-SYN-001', repository=repo, preparer_id='AGENT-INTAKE')
print('après l\\'exécution de l\\'agent :', final_state['workflow_state'])

record = repo.approve(final_state['draft_case_id'], reviewer_id='EMP-REVIEWER-01')
print('après la révision humaine :', record.state)
"
```

Résultat attendu : l'état passe de `PENDING_REVIEW` à `APPROVED`, et l'identifiant du réviseur (`EMP-REVIEWER-01`) diffère de celui de la personne préparatrice (`AGENT-INTAKE`) utilisé par l'agent.

### Exercice 7.4 : Exécuter contre une référence de dossier invalide

```powershell
python src/quote-preparation-agent/main.py "NOT-A-VALID-CASE-ID"
```

Résultat attendu : un message bilingue indiquant que la requête n'a pas pu être traitée parce que la référence de dossier était invalide, sans exception levée et sans dossier créé dans le dépôt d'approbation.

## Liste de vérification

* [ ] L'exercice 7.1 affiche un message bilingue sans aucun montant
* [ ] L'exercice 7.2 confirme que `workflow_state` vaut `PENDING_REVIEW` immédiatement après l'exécution de l'agent
* [ ] L'exercice 7.3 approuve le dossier en tant que réviseur distinct, le faisant passer à `APPROVED`
* [ ] L'exercice 7.4 retourne le message de refus borné pour une référence de dossier invalide

## Vérification des connaissances

* Pourquoi l'agent s'arrête-t-il à `PENDING_REVIEW` plutôt que de trancher lui-même le dossier ?
* Que se passerait-il à l'exercice 7.3 si vous appeliez `repo.approve` avec `reviewer_id='AGENT-INTAKE'` plutôt qu'un réviseur distinct ?

## Étapes suivantes

Poursuivez avec l'[Atelier 08 : Suite d'évaluation](lab-08-evaluations.md).
