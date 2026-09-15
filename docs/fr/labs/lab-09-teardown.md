---
permalink: /fr/labs/lab-09-teardown
lang: fr
title: "Atelier 09 - Démantèlement"
description: "Arrêter les processus locaux démarrés, nettoyer tout état sur disque et confirmer que les ateliers locaux n'ont rien provisionné dans Azure."
---

> 🇬🇧 **[English version](../../labs/lab-09-teardown)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

Prévoyez 10 minutes. Complétez ce laboratoire même si l'exercice d'un laboratoire précédent n'a pas entièrement réussi.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Arrêter tout processus de serveur MCP démarré aux ateliers 04 et 05
* Retirer tout état sur disque créé pendant vos expérimentations avec le dépôt d'approbation
* Confirmer que les ateliers 00 à 08 n'ont provisionné aucune ressource Azure, et qu'il n'y a donc encore aucun démantèlement infonuagique à exécuter

## Exercices

### Exercice 9.1 : Arrêter tout serveur MCP en cours d'exécution

Si un terminal de l'atelier 04 ou 05 fait toujours tourner `python mcp/application-server/main.py` ou `python mcp/rulebook-server/main.py`, arrêtez-le.

```powershell
# Dans le terminal où le serveur s'exécute
Ctrl+C
```

Si vous avez démarré un serveur dans une tâche en arrière-plan à la place, arrêtez-la explicitement :

```powershell
Get-Job | Where-Object { $_.Command -match 'application-server|rulebook-server' } | Stop-Job
```

### Exercice 9.2 : Désactiver l'environnement virtuel

```powershell
deactivate
```

### Exercice 9.3 (pratique) : Retirer toute base de données d'approbation sur disque

`ApprovalRepository` utilise par défaut une base de données SQLite en mémoire (`:memory:`), donc rien ne persiste au redémarrage d'un processus, sauf si vous avez explicitement transmis un chemin de fichier dans un laboratoire précédent. Si c'est le cas, retirez ce fichier maintenant.

```powershell
if (Test-Path .\lab-approvals.db) { Remove-Item .\lab-approvals.db -Force }
```

Ajustez le chemin si vous avez utilisé un autre nom de fichier aux ateliers 03 ou 07.

### Exercice 9.4 : Confirmer qu'il n'y a pas encore de démantèlement infonuagique

Les ateliers 00 à 08 ne provisionnent jamais d'infrastructure Azure. Chaque composant s'exécute localement : le calculateur et le dépôt d'approbation sont du Python pur avec SQLite, les serveurs MCP s'exécutent comme processus locaux, et l'agent s'exécute en processus sans aucun appel à Foundry hébergé. Il n'existe aucun groupe de ressources, ressource d'abonnement ni environnement `azd` créé par ces ateliers à supprimer.

Cela change à partir de l'atelier 10, où les surfaces du pilote introduisent une fondation Azure, un enregistrement d'application Entra et un flux de démantèlement dédié. Chacun de ces ateliers nettoie ce qu'il a créé.

## Liste de vérification

* [ ] Tout processus de serveur MCP démarré aux ateliers 04-05 a été arrêté
* [ ] Votre environnement virtuel Python est désactivé
* [ ] Tout fichier SQLite sur disque créé pour vos expérimentations avec le dépôt d'approbation a été retiré
* [ ] Vous avez confirmé que les ateliers locaux n'ont créé aucune ressource Azure à supprimer

## Vérification des connaissances

* Pourquoi `ApprovalRepository` utilise-t-il `:memory:` par défaut plutôt qu'un chemin de fichier ?
* L'atelier 14 introduit un flux de démantèlement qui refuse de supprimer son propre groupe de ressources. Qu'est-ce que cela suggère sur le regroupement des ressources du pilote ?

## Étapes suivantes

Vous avez terminé la moitié locale de l'atelier. Poursuivez avec l'[Atelier 10 : Provisionner la fondation Azure](lab-10-azure-foundation.md), qui introduit les surfaces du pilote et l'infrastructure qui les soutient.
