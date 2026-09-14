---
permalink: /fr/labs/
lang: fr
title: "Ateliers"
description: "Le programme de dix ateliers pour l'atelier synthétique de préparation de soumissions d'assurance auto en Ontario."
---

> 🇬🇧 **[English version](../../labs/)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ces ateliers est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Programme des ateliers

Progressez dans les ateliers en ordre. Chacun s'appuie sur le code et les données introduits par les ateliers précédents.

| Atelier | Titre | Ce que vous ferez |
| --- | --- | --- |
| [00](lab-00-setup.md) | Configuration | Créer un environnement virtuel, installer les dépendances et exécuter les suites de tests existantes |
| [01](lab-01-fixtures-schema.md) | Données et schéma | Explorer les données synthétiques et le schéma JSON qui encadre leur forme |
| [02](lab-02-calculator.md) | Le calculateur déterministe | Retracer `calculate_quote` et prouver qu'il n'invente jamais un montant |
| [03](lab-03-approval-repository.md) | Dépôt d'approbation et machine à états | Parcourir la machine à états DRAFT à PENDING_REVIEW à APPROVED/REJECTED |
| [04](lab-04-application-server.md) | Le serveur MCP d'application | Exécuter le service MCP `get_application` en lecture seule |
| [05](lab-05-rulebook-server.md) | Le serveur MCP de référentiel | Exécuter le service MCP `get_rulebook` en lecture seule |
| [06](lab-06-agent-graph.md) | L'agent LangGraph | Retracer le superviseur et ses trois spécialistes séquentiels |
| [07](lab-07-run-agent.md) | Exécuter l'agent de bout en bout | Exécuter l'agent contre une donnée, puis agir comme réviseur humain |
| [08](lab-08-evaluations.md) | Suite d'évaluation | Explorer le jeu de données de référence et la porte d'évaluation déterministe |
| [09](lab-09-teardown.md) | Démantèlement | Arrêter les processus locaux et confirmer qu'il n'y a aucun démantèlement infonuagique |

## Étapes suivantes

Commencez par l'[Atelier 00 : Configuration](lab-00-setup.md).
