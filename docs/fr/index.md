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
consignent la livraison approuvée staging v5/production v6 sans remplacer les
échecs historiques. Le programme complet se trouve dans [Ateliers](labs/) :
fondations locales 00–09, surfaces pilotes contrôlées 10–14 et exercices
natifs isolés 15–18. Conservez les environnements déployés.
