---
permalink: /fr/labs/
lang: fr
title: "Ateliers"
description: "Le programme de dix-neuf ateliers pour l'atelier synthétique de préparation de soumissions d'assurance auto en Ontario."
---

> 🇬🇧 **[English version](../../labs/)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ces ateliers est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Programme des ateliers

Progressez dans les ateliers en ordre. Chacun s'appuie sur le code et les données introduits par les ateliers précédents.

Les ateliers 00 à 09 s'exécutent entièrement sur votre poste de travail. Les ateliers 10 à 14 ajoutent les surfaces du pilote : la fondation Azure, les deux interfaces web, la configuration d'identité qui les soutient et le pipeline qui les maintient honnêtes.

Les ateliers 15 à 18 ajoutent des exercices natifs isolés avec des contrôles
de preuve explicites. Certains exigent des prérequis approuvés ou des artefacts
natifs conservés; consignez les prérequis manquants comme bloqués sans inventer
de résultats. Gardez staging v2 et production v3 déployés pour poursuivre.

### Fondations locales

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
| [09](lab-09-teardown.md) | Démantèlement | Arrêter les processus locaux et nettoyer l'état sur disque que vous avez créé |

### Les surfaces du pilote

| Atelier | Titre | Ce que vous ferez |
| --- | --- | --- |
| [10](lab-10-azure-foundation.md) | Provisionner la fondation Azure | Lire et compiler les modèles Bicep, et comprendre pourquoi le réseau est déployé séparément |
| [11](lab-11-web-chat.md) | L'interface de clavardage du demandeur | Exécuter le clavardage et prouver que cette surface ne peut jamais afficher une prime |
| [12](lab-12-reviewer-identity.md) | Identité et accès du réviseur | Enregistrer l'application de révision, accorder le rôle Reviewer et calculer les URI de redirection |
| [13](lab-13-reviewer-ui.md) | L'interface de révision | Alimenter une file, se connecter, approuver un dossier et lire la piste de vérification |
| [14](lab-14-pilot-operations.md) | Exploitation du pilote | Exécuter le pipeline de validation, lire la porte d'évaluation et parcourir les protections du démantèlement |

### Fonctions natives

| Atelier | Titre | Ce que vous ferez |
| --- | --- | --- |
| [15](lab-15-native-files-generation.md) | Fichiers et génération native | Téléverser la référence synthétique, télécharger les QnA natifs et diagnostiquer les anciens échecs |
| [16](lab-16-native-search-invoice.md) | File Search et factures | Vérifier citations et refus bilingues, puis examiner champs et ancrage de facture native |
| [17](lab-17-native-skills-memory.md) | Compétences et frontières mémoire | Prouver la consommation isolée et distinguer namespaces mémoire conditionnels et autorisation |
| [18](lab-18-native-evaluation-traces.md) | Évaluation et rejeu des traces | Comparer les juges réels, conserver les contrôles échoués et exiger l'ingestion avant rejeu |

Le [guide natif](../native-showcase.md) conserve preuves historiques et limites.
Ces ateliers n'autorisent ni déploiement, ni changement d'accès, ni démantèlement.

## Étapes suivantes

Commencez par l'[Atelier 00 : Configuration](lab-00-setup.md).
