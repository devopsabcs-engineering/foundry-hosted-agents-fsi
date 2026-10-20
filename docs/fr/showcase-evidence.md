---
layout: default
title: Preuves de la démonstration native
description: Reprise des générations natives, versions réellement exécutées et captures des applications déployées.
---

[English](../showcase-evidence.md) | [Guide natif](native-showcase.md) | [Laboratoires](labs/index.md)

## État du déploiement

Preuves recueillies le 2026-10-20 UTC. Les environnements restent déployés.
Le dernier code fusionné est `349f6ed3abe783c99f457c8f6d5d5b56b3122726`.
Ses images ont été publiées, mais cela ne prouve pas leur déploiement.
Les requêtes SDK adressées séparément aux deux projets confirment toujours
l'agent staging version 2 et production version 3. Le dernier déploiement complet
vérifié reste [39293980605, tentative 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39293980605).
Le dernier code n'est **pas** confirmé comme déployé.

Les images réellement exécutées sont identiques entre staging et production :
chat `sha256:ccfab1bc368463602c5b5f85cc6b93cde242e9a03c7b3000a6cf8cee007fce70`,
révision staging `foundry-quote-chat-staging--p5occpg` et production
`foundry-quote-chat--zdpiuid`; reviewer
`sha256:5882f2e3ef0ff0884b53387e10a981d7f5591e7c23a8229bc038afad151d1b01`,
révision staging `foundry-quote-reviewer-staging--0000002` et production
`foundry-quote-reviewer--k1qw0tn`.

La promotion attend les approbations de mise en production et le contrôle
GitHub existant. Aucun rôle supplémentaire, contournement d'authentification,
service Search, modèle d'embedding ou démantèlement n'a été effectué.

## Reprise des deux générations échouées

Les échecs historiques restent visibles. Deux nouvelles opérations natives les
remplacent avec une référence autonome de 19 881 octets contenant 26 leçons
techniques. Une simple répétition avec l'ancien contenu avait aussi échoué.

| Opération historique | Cause réelle | Remplacement réussi | Lignes téléchargées |
| --- | --- | --- | --- |
| `datagen-4e74a27bd5f24a87a08ea35ad788c8cb` | Moins de 1 Ko | `datagen-a866fd3be0104ae4b6ec4808b76cbec2` | 6 |
| `datagen-af8399a33bd7477b8279591b5a408c7a` | Contexte insuffisamment autonome | `datagen-afe38ec64fb744a09e845119139e4064` | 5 |

Dans Foundry Data generation, cherchez
`showcase-synthetic-dataset-recovered-v3` et
`showcase-synthetic-dataset-v2-recovered-v3`. Les deux ont atteint `succeeded`.
Leur fichier source est `file-21aee188caff46979b16bf3abc40beb1`.
La valeur 15 est un maximum demandé, pas une quantité garantie.

| Fichier produit | SHA-256 téléchargé |
| --- | --- |
| `file-b9923ced057f450eaa8347bf7e68dfae-dg` | `82efe086958d8756bfa5612573b5e1c02d7cebaf5948bfed0457d97bd91f07d4` |
| `file-9c7c0515bfea4f73a12deb4a6de40142-dg` | `0f99391d6ce77d2a5e0b1e25e6fbf9bd55e1eeebdfc310ebf2a3a30364b1ea69` |

Le CLI a vérifié la provenance des sorties natives avant téléchargement.
Les exemples nécessitent une révision humaine; aucun entraînement n'a été lancé.
Suivez le [laboratoire de génération](labs/lab-15-native-files-generation.md)
pour reproduire les étapes avec vos propres identifiants.

## Captures authentiques des applications

Ces captures montrent les pages déployées sans connexion. Elles ne prouvent
ni une conversation authentifiée, ni une approbation employé, ni la promotion
du dernier code. Elles ne contiennent ni données de demandeur ni jetons.

### Chat staging

Capture `2026-10-20T01:22Z` du
[chat staging](https://foundry-quote-chat-staging.victorioussand-be863134.eastus2.azurecontainerapps.io).

![Le chat staging exige une connexion Microsoft avant de permettre un message](../assets/evidence/staging-chat-fr.png)

### Révision employé en production

Capture `2026-10-20T01:22Z` du
[reviewer production](https://foundry-quote-reviewer.gentleplant-e170129b.eastus2.azurecontainerapps.io).

![Le reviewer production exige une connexion Microsoft avant toute action employé](../assets/evidence/production-reviewer-en.png)

### Captures Foundry en attente

Le navigateur intégré n'est pas connecté à Foundry. Les preuves API sont réelles,
mais ne remplacent pas des captures du portail. Un onglet de projet authentifié
partagé permettra de capturer générations, index, skills, évaluations et traces
sans divulguer les détails du compte.

## Limites de qualité natives

File Search a vérifié six réponses citées et deux refus exacts `OUT_OF_CORPUS`.
Il ne s'agit ni de Foundry IQ ni d'un nouvel outil de l'agent hébergé.
Le skill du projet a été consommé par un runtime opérateur isolé dans les deux
ordres linguistiques.

L'évaluateur de retrieval a séparé les contrôles pertinents et non pertinents,
5/1. Groundedness v18 et groundedness_pro v8 ont accepté une réponse connue
comme erronée sur l'autorisation : leurs contrôles négatifs ont donc échoué.
Ce n'est pas un gain de qualité démontré. L'export local de traces a reçu
HTTP 403; un flush réussi n'a pas été présenté comme une ingestion.

Consultez le [guide natif](native-showcase.md) et la
[documentation Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/).
