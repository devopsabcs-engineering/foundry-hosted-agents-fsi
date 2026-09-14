---
permalink: /fr/labs/lab-09-teardown
lang: fr
title: "Atelier 09 - Démantèlement"
description: "Arrêter les processus locaux démarrés, nettoyer tout état sur disque et confirmer qu'il n'y a rien à supprimer dans Azure."
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
* Confirmer que cet atelier n'a provisionné aucune ressource Azure, et qu'il n'y a donc aucun démantèlement infonuagique à exécuter

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

### Exercice 9.4 : Confirmer qu'il n'y a aucun démantèlement infonuagique

Cet atelier ne provisionne jamais d'infrastructure Azure. Chaque composant des ateliers 00 à 08 s'exécute localement : le calculateur et le dépôt d'approbation sont du Python pur avec SQLite, les serveurs MCP s'exécutent comme processus locaux, et l'agent s'exécute en processus sans aucun appel à Foundry hébergé. Il n'existe aucun groupe de ressources, ressource d'abonnement ni environnement `azd` créé par cet atelier à supprimer.

## Liste de vérification

* [ ] Tout processus de serveur MCP démarré aux ateliers 04-05 a été arrêté
* [ ] Votre environnement virtuel Python est désactivé
* [ ] Tout fichier SQLite sur disque créé pour vos expérimentations avec le dépôt d'approbation a été retiré
* [ ] Vous avez confirmé qu'il n'existe aucune ressource Azure pour cet atelier à supprimer

## Vérification des connaissances

* Pourquoi `ApprovalRepository` utilise-t-il `:memory:` par défaut plutôt qu'un chemin de fichier ?
* Si une phase future de ce projet ajoute un déploiement hébergé, qu'est-ce que ce laboratoire de démantèlement devrait acquérir qu'il n'a pas besoin aujourd'hui ?

## Étapes suivantes

Vous avez terminé l'atelier bilingue de préparation de soumissions. Retournez à l'[index des ateliers](index.md) ou à la [page d'accueil de l'atelier](../index.md) pour le programme complet.
