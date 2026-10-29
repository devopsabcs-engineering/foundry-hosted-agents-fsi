---
lang: fr
layout: default
title: Accueil
description: Atelier pratique et bilingue pour héberger un agent synthétique de préparation de soumissions d'assurance auto sur Microsoft Foundry Hosted Agents.
nav_order: 0
permalink: /fr/
---

> 🇬🇧 **[English version](../)**

Bienvenue dans l'**Atelier Foundry Hosted Agents pour les services
financiers**, un atelier pratique et bilingue adapté du dépôt
[`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents).
Vous construirez et hébergerez un agent synthétique de préparation de
soumissions d'assurance auto en Ontario sur Microsoft Foundry Hosted
Agents, appuyé par des serveurs d'outils MCP en lecture seule, un
calculateur déterministe et une étape d'approbation obligatoire avant tout
aperçu destiné au demandeur.

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de cet atelier est synthétique
> et non contraignant. Rien ici ne représente un produit, un tarif ou une
> police Desjardins réel, et aucun organisme de réglementation ni assureur
> n'a révisé ou approuvé ce contenu.

## Ce que vous allez construire

Vous provisionnerez les services MCP en lecture seule pour l'application
et le référentiel de règles, puis déploierez un agent LangGraph qui valide
un identifiant de dossier synthétique et lit sa donnée d'exemple. Un calculateur
déterministe produit le calcul et une ébauche est persistée pour révision.
Le canal demandeur retourne des messages bilingues bornés, sans montants
ni champs réservés au réviseur. L'application bilingue de révision lit les
instantanés de calcul et consigne les décisions autorisées des employés.

## Architecture et frontières

Consultez l'[architecture](architecture.md) pour les trois étapes du graphe,
les transports MCP locaux/hébergés, Cosmos privé et les autorisations distinctes
du clavardage et de la révision. Calcul et persistance ont lieu dans
`COMPOSITION`, pas dans des étapes supplémentaires. Les exercices natifs
File Search, compétences et mémoire utilisent des moteurs opérateur isolés;
ils ne sont pas automatiquement rattachés à l'agent de soumissions.

## Parcours de l'apprenant

Le parcours par défaut de ces ateliers ne nécessite pas GitHub Copilot ni
aucun autre assistant de programmation par IA. Lorsque les auteurs de
l'atelier ont utilisé un outil assisté par IA pour rédiger ou réviser un
contenu, cette assistance est indiquée dans le fichier concerné plutôt que
présentée comme faisant partie du parcours de l'apprenant.

## Ateliers

Pour la démo Azure conservée et les suivis de la séance 2, consultez les
[fonctions natives Foundry](native-showcase.md).

Les [preuves de livraison](showcase-evidence.md#livraison-approuvée-actuelle)
consignent la livraison approuvée staging v7/production v8 sur `42c627c` sans remplacer les
échecs historiques. Le programme complet se trouve dans [Ateliers](labs/) :
fondations locales 00–09, surfaces pilotes contrôlées 10–14 et exercices
natifs isolés 15–18. Conservez les environnements déployés.

Poursuivez avec le [guide d'ingénierie des évaluations](evaluation-guide.md)
et l'[Atelier 19](labs/lab-19-evaluation-engineering.md) : dix exercices
sur tests déterministes/stochastiques, portail et SDK Foundry, jeux indépendants,
calibration des juges, incertitude et non-régression avec état.
Les [37 diapositives françaises](../assets/decks/foundry-evaluation-engineering-fr.pptx)
et [anglaises](../assets/decks/foundry-evaluation-engineering-en.pptx)
incluent les notes de formation pour une séance de 3 à 4 heures.

Suivez les captures conservées de l'Exercice 19.4 sans lancer un nouvel essai.
Pour le parcours de pratique distinct, téléchargez les contrôles synthétiques
rédigés [français](../assets/datasets/portal-practice-fr-CA.jsonl) ou
[anglais](../assets/datasets/portal-practice-en-CA.jsonl), pas des réponses agent
capturées. Téléversement et soumission payante exigent une autorisation distincte.

## Observabilité Langfuse facultative

Le [guide Langfuse et Foundry](langfuse-integration.md) compare le parcours natif
d'observabilité/évaluation à l'exporteur OTLP facultatif limité aux métadonnées.
Les [preuves du pilote](langfuse-pilot-evidence.md#projet-et-trace) contiennent
des captures authentifiées et une ingestion synthétique locale à la VM, pas un
export depuis Foundry distant ni une réception correspondante dans Azure.
L'export de production reste désactivé. La dernière observation d'alimentation
confirme la désallocation à `2026-10-28T20:34:18Z`, pas une nouvelle vérification de santé.
