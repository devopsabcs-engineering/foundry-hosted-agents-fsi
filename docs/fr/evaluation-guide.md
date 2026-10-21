---
lang: fr
layout: default
title: Évaluer les agents de soumission dans Microsoft Foundry
description: Guide pratique des contrats déterministes, juges natifs, calibration, essais répétés, contrôles de livraison et suivi opérationnel.
nav_order: 21
---

[English](../evaluation-guide.md) | [Atelier pratique 19](labs/lab-19-evaluation-engineering.md) |
[PowerPoint FR](../assets/decks/foundry-evaluation-engineering-fr.pptx) |
[PowerPoint EN](../assets/decks/foundry-evaluation-engineering-en.pptx)

## Choisir la preuve avant l'évaluateur

Une évaluation mesure un contrat explicite; elle n'exige pas nécessairement
un LLM. Commencez par la décision : vérifier le calcul, empêcher
l'auto-approbation, détecter un prix inventé ou juger le choix d'un outil.
Ces questions exigent des oracles différents.

Le graphe de soumission déployé est **déterministe**, pas un tarificateur LLM.
`INTAKE`, `REFERENCE_LOOKUP` et `COMPOSITION` utilisent des données validées,
des MCP en lecture seule, un calculateur pur et un état persistant.
Les messages au demandeur sont des modèles bilingues bornés. Les **juges**
natifs utilisent des LLM : leurs notes peuvent varier même si la réponse de
l'agent ne change pas. Les démonstrations isolées File Search, compétences et
mémoire ne deviennent pas des dépendances du graphe parce qu'elles se trouvent
dans le même projet. Consultez l'[architecture](architecture.md).

Toutes les données et tous les montants sont synthétiques et non contraignants :
aucun vrai tarif, renseignement client, envoi ou acte de souscription.
La rédaction a utilisé une assistance IA; aucun assistant de code n'est requis
pour l'apprenant.

| Propriété | Test de contrat déterministe | Évaluation stochastique |
| --- | --- | --- |
| Oracle | Montant/état exact, schéma, prédicat de politique | Grille, étiquette humaine, juge modèle ou résultat échantillonné |
| Exemple | `INCOMPLETE` implique aucun montant | L'accusé explique-t-il clairement la prochaine étape? |
| Répétition | Entrées et état contrôlés doivent reproduire le résultat | Les échantillons estiment une distribution |
| Sens d'un échec | Invariant violé, défaut du test ou de l'infrastructure | Qualité insuffisante, désaccord du juge ou panne de service |
| Contrôle adapté | Blocage pour calcul, autorisation, schéma, divulgation | Seuils calibrés, segments, incertitude et révision humaine |
| Coût | Généralement local et rapide | Inférence, appels juge, latence et conservation des preuves |

Ces catégories ne sont pas deux frameworks exclusifs. Un test unitaire peut
cibler un composant stochastique; une évaluation d'agent peut utiliser du code
déterministe. Un service déterministe peut échouer à cause du réseau, du RBAC,
de la concurrence ou de l'état. Température zéro et graine ne garantissent pas
des résultats LLM identiques après une évolution du modèle ou de l'infrastructure.

## Progression pour l'agent de soumission

| Niveau | Question et cas | Mécanisme | Déduction interdite |
| --- | --- | --- | --- |
| 0 | Données valides? `READY`, `UNSUPPORTED`, `INCOMPLETE`, ID invalide | Schéma et tests du calculateur | Schéma valide signifie réponse exacte |
| 1 | Flux sûr? révision/ETag, auto-approbation, nouvelle tentative | Contrat du dépôt et API reviewer | Accusé signifie persistance ou approbation |
| 2 | Réponse sûre? EN/FR, sans montant, injection | Contrôle déterministe 13 cas et vérification native | Transport simulé signifie déploiement réel |
| 3 | Accusé utile et fondé? cinq cas par langue | Juges natifs coherence, groundedness, task adherence | Bonne note prouve calcul ou outils |
| 4 | Juge fiable? faux prix/approbation, contexte non pertinent | Contrôles positifs/négatifs étiquetés | Réponse fluide signifie réponse vraie |
| 5 | Qualité stable? répétitions, cas rares, référence/candidat appariés | Données/grille figées, résultats par cas, incertitude | Cinq cas verts garantissent l'absence de régression |
| 6 | Système sûr dans le temps? resoumission, rôles, traces | UI/API authentifiées, identité réelle, télémétrie | Ligne portail ou trace demandée prouve l'ingestion |

## Pas à pas dans le portail Foundry

Les expériences **nouveau Foundry** et classique diffèrent. Les libellés,
évaluateurs et fonctions en préversion dépendent du projet, de la région et
du rôle. Le [guide officiel](https://learn.microsoft.com/azure/foundry/how-to/evaluate-generative-ai-app)
fait autorité pour la navigation; ne mélangez pas les deux expériences.

1. Ouvrez le projet **staging** conservé dans [ai.azure.com](https://ai.azure.com).
   Vérifiez compte, projet et locataire. Le suffixe `-poc` désigne la production.
   Ne créez pas de ressource et n'élargissez pas les rôles pour réussir l'atelier.
2. Ouvrez l'agent et vérifiez sa version et son état. L'onglet **Evaluation**
   est visible dans son interface actuelle. Le parcours **Evaluate** au niveau
   projet, décrit dans la documentation, permet aussi de démarrer.
3. Choisissez la cible. Une cible agent l'appelle; un jeu de réponses téléversé
   juge des réponses déjà capturées. Réutilisez celles-ci pour isoler la
   variabilité du juge. La compatibilité d'une cible hébergée/personnalisée doit
   être vérifiée; elle n'est pas présumée.
4. Préparez un petit JSONL ou CSV synthétique : ID stable, question, réponse,
   faits indépendants/référence. Le JSONL bilingue du dépôt est un **format
   source** à convertir pour son exécuteur SDK. Le portail peut exiger un
   jeu de réponses aplati différent.
5. Mappez chaque champ explicitement. Groundedness reçoit le `context` de
   confiance, pas la réponse candidate comme vérité. Task adherence reçoit des
   messages de tâche et une réponse structurée compatible, dans une seule langue.
6. Sélectionnez les évaluateurs disponibles et un déploiement juge existant et
   approuvé. Examinez version/catalogue et seuil de réussite. Les échelles et
   champs requis ne sont pas identiques pour tous les évaluateurs.
7. Nommez l'essai : environnement, version observée, langue, révision du jeu,
   numéro d'essai. Conservez définition/configuration exactes et plafond de coût.
8. Lancez le petit pilote. Attendez un état terminal puis vérifiez nombre de
   lignes, erreurs, exclusions et chaque métrique. Une panne du service n'est
   ni une note de qualité nulle ni une preuve acceptable incomplète.
9. Inspectez les lignes individuelles, notes hautes/basses, explications,
   étiquettes humaines et contrôles volontairement faux. Exportez résultats,
   IDs, empreintes et configuration juge.
10. Comparez uniquement des expériences compatibles. Si le portail n'exprime pas
    le mapping, l'export ou les répétitions nécessaires, utilisez le SDK vérifié.
    N'inventez pas de bouton et n'affaiblissez pas le protocole.

Ne téléversez pas de jeton, dossier privé, configuration brute ou chaîne de
connexion. Les preuves restent dans `.local` ignoré par Git, avec conservation
et suppression définies.

## Pas à pas avec le SDK natif du dépôt

L'[Atelier 19](labs/lab-19-evaluation-engineering.md) fournit les commandes
PowerShell et résultats attendus. La livraison vérifiée utilise
`azure-ai-projects` **2.6.0**, `openai` **3.6.0** et `azure-identity` **1.25.3**.
Consultez le [guide SDK actuel](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation)
avant toute mise à niveau : les contrats en préversion évoluent.

1. Validez et convertissez `eval/applicant-message-dataset.jsonl` avec
   `eval/convert_judge_dataset.py`, séparément pour `en-CA` et `fr-CA`.
2. Vérifiez la version déployée avant la capture. `--version` dans
   `eval/run_judge_evaluation.py` est une **étiquette observée, pas un routage
   épinglé**. L'URL appelle le déploiement courant. Réservez une fenêtre stable
   et revérifiez ensuite; invalidez les essais contaminés.
3. Capturez les vraies réponses. L'exécuteur rejette un corps d'erreur HTTP 200,
   une réponse vide ou la langue absente avant de lancer un juge.
4. Construisez `evaluation_query` et `task_query` à partir des faits indépendants.
   Séparez injection non fiable et instructions de confiance.
5. Créez la définition par `AIProjectClient.get_openai_client()` et
   `client.evals.create`, puis l'essai par `client.evals.runs.create`.
6. Attendez avec délai maximal, récupérez toutes les pages et conservez les
   résultats complets. L'exécuteur enregistre aussi captures, résumé et identité.
7. Validez la complétude indépendamment des seuils. Examinez erreur/corrélation
   du service avant une nouvelle tentative bornée et autorisée.

Mapping réellement utilisé par l'exécuteur épinglé :

```python
criterion = {
    "type": "azure_ai_evaluator",
    "name": "groundedness",
    "evaluator_name": "builtin.groundedness",
    "initialization_parameters": {"deployment_name": "gpt-4o-mini"},
    "data_mapping": {
        "query": "{{item.evaluation_query}}",
        "context": "{{item.context}}",
        "response": "{{item.response}}",
    },
}
```

Il s'agit d'un extrait de configuration, pas d'un script complet.
N'inventez pas `azure_ai_groundedness`. Le code épinglé utilise
`deployment_name`; une documentation plus récente peut montrer `model` ou
des types enveloppes. Vérifiez SDK installé et catalogue choisi avant de
mélanger des versions. Task adherence utilise les messages `task_query` et
les `output_items` normalisés dans la langue choisie, pas ce mapping texte.

L'enveloppe inline est :

```python
data_source = {
    "type": "jsonl",
    "source": {
        "type": "file_content",
        "content": [{"item": {"query": "example", "response": "captured answer"}}],
    },
}
```

Votre définition exige son schéma et tous ses champs, absents de cet extrait
minimal. Pour un grand jeu, suivez le parcours compatible
[téléversement/référence fichier](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-datasets).
Remplacer `file_content` par `file_id` exige d'abord une vraie référence
fichier/jeu compatible dans le projet.

### Des API apparentées mais non interchangeables

| Surface | Usage | Limite |
| --- | --- | --- |
| Portail Foundry | Exploration, mapping, inspection humaine | Préversions et libellés variables |
| Projects SDK et Evals natif | Définitions/essais cloud reproductibles, CI | Automatisation vérifiée ici |
| `azure-ai-evaluation` | `evaluate()` local et classes évaluateurs | API distincte encore documentée; non importée par cet exécuteur |
| Juges code/chaîne | Schéma, prédicat exact, correspondance simple | Texte exact souvent mauvais oracle sémantique |
| Juges prompt/grille | Sens, ancrage, respect de tâche | Calibration humaine/négative indispensable |
| Évaluation agent/processus | Outils, arguments, trajectoire, résultat de tâche | Véritable trajectoire compatible requise |

Références : [évaluateurs intégrés](https://learn.microsoft.com/azure/foundry/concepts/built-in-evaluators),
[agents](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/agent-evaluators),
[évaluateurs personnalisés](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/custom-evaluators).
Enregistrement ou accusé fluide ne prouvent pas un processus correct.

## Concevoir un jeu capable de détecter une régression

Utilisez une matrice : langue × statut de calcul/flux × entrée invalide ×
injection × révision/état initial × rôle. Commencez par les cinq cas demandeur,
puis ajoutez cas limites revus et jeu de réserve indépendant.

Chaque ligne conserve ID stable, segment, question, faits indépendants, résultat
observable attendu, comportements interdits, étiquette humaine et version source.
Pour le flux, ajoutez état initial, rôle, révision et transition attendue.
Un générateur synthétique propose des cas; un spécialiste valide vérité et
couverture avant d'en faire un oracle.

* Séparez développement/calibration et réserve. Ne réglez pas continuellement
  prompts/seuils sur un jeu censé être inédit.
* Ajoutez incidents et frontières, pas seulement des paraphrases heureuses.
* Évaluez EN et FR séparément; la moyenne peut masquer une régression française.
* Gardez calcul/schéma/autorisations déterministes même si un LLM propose les tests.
* Isolez l'état. Une nouvelle invocation peut tester un doublon ou une transition
  plutôt que le premier traitement. Ne videz jamais la file de démonstration.
  Utilisez un magasin jetable approuvé et documentez instantané/initialisation.

## Calibrer le juge avant de lui faire confiance

Étiquetez humainement les accusés valides, fausses approbations, prix divulgués,
faits inventés, mentions absentes, mauvaise langue et réponses élégantes mais
fausses. Définissez l'attendu **par métrique** : une réponse fausse mais fluide
peut réussir coherence et échouer groundedness/task adherence.

Mesurez fausses acceptations, faux rejets et accord humain par métrique/segment.
Examinez désaccords et ambiguïtés. Conservez identité/version/seuils et contrôles
échoués. Évitez la réponse candidate comme référence, les étiquettes
référence/candidat révélées au juge et les instructions malveillantes qui
tentent de redéfinir sa grille.

Les [contrôles historiques](labs/lab-18-native-evaluation-traces.md) comprennent
une mauvaise réponse acceptée par deux juges d'ancrage. C'est un faux positif,
pas un succès. Combinez prédicats de politique et révision humaine; ne
réétiquetez pas un contrôle pour rendre le tableau vert.

## Répétitions et comparaison équitable

Distinguez deux expériences :

1. **Variabilité de génération** : captures répétées avec mêmes entrées et état
   initial contrôlé. Conservez chaque réponse et son identifiant.
2. **Variabilité du juge** : notes répétées des **mêmes réponses sauvegardées**.
   Relancer tout l'exécuteur change aussi les captures et n'isole donc pas le juge.

Commencez par un petit pilote autorisé, par exemple trois essais par langue.
Dimensionnez ensuite selon risque toléré, variance et budget. Prédéclarez les
règles d'arrêt; ne vous arrêtez pas au premier résultat vert. Présentez
distributions par cas, segment et essai, pas seulement une moyenne globale.

À titre illustratif, 5/5 succès Bernoulli indépendants donne un intervalle Wilson
bilatéral 95 % d'environ **0,57 à 1,00**. Ce n'est pas la perfection démontrée.
Les notes répétées du même cas/juge sont corrélées, pas de nouveaux clients
indépendants. Pour une comparaison réaliste, utilisez une analyse appariée par
cas ou un bootstrap par grappes conservant langues/répétitions d'un même cas,
et une révision experte des préjudices rares. Aucun agrégat ne remplace un
invariant de sécurité violé.

Figez IDs, données/état, langue, faits, grille, version évaluateur, version
modèle juge et configuration d'échantillonnage. Masquez/randomisez l'ordre si
possible. Conservez distributions, transitions réussite/échec et effets
pratiquement significatifs. Changer jeu, juge ou évaluateur exige une nouvelle
référence, pas une revendication d'amélioration.

## Exécution efficace et politique de livraison

Utilisez les preuves fiables les moins coûteuses d'abord :

1. Contrats locaux schéma/calculateur/dépôt/API à chaque changement pertinent.
2. Petit contrôle déterministe avant tout juge payant.
3. Segments modifiés ciblés et contrôles négatifs calibrés.
4. Petits juges natifs EN/FR avec plafonds explicites de coût/durée.
5. Réserve plus large, répétitions/trajectoires pour changements risqués ou planifiés.
6. Acceptation staging, frontières d'identité et promotion protégée.

Réutilisez les **captures** pour travailler sur le juge. Cachez seulement si
entrées, état, modèle, grille et évaluateur concordent; indiquez la réutilisation,
qui n'est pas une nouvelle inférence. Borner la concurrence évite le bruit de quota.
Estimez cas × langues × essais × évaluateurs, puis ajoutez taille des jetons,
nouvelles tentatives et requêtes internes pour approuver le budget.

Politique actuelle du dépôt :

| Condition | Comportement existant |
| --- | --- |
| Échec déterministe | Production bloquée |
| Erreur d'appel ou preuve native incomplète/non notée | Production bloquée |
| Notes complètes sous le taux CLI demandé | CLI en échec; notes conservées comme consultatives |
| Preuves EN/FR complètes absentes | Contrôle distinct de complétude bloquant |
| Approbation protégée absente | Job production en attente |
| Échec invocation200/mémoire403 du reviewer | Étape de déploiement en échec |

`--minimum-pass-rate 1.0` est une proportion de cas réussis, **pas** un seuil
métrique 1/5. `continue-on-error` pour le juge consultatif ne permet pas
d'ignorer une panne. Un contrôle qualité plus strict exige calibration,
changement explicite de politique et approbation. L'atelier ne change ni
politique ni comportement applicatif.

La [livraison 39527950931](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39527950931)
a rencontré des erreurs natives sans ligne notée. Le contrôle a bloqué.
L'opérateur autorisé a relancé uniquement le job échoué au même code; les
preuves EN/FR complètes ont précédé la promotion. Conservez les échecs :
ne relancez pas une qualité insuffisante jusqu'à obtenir un succès fortuit.

## Diagnostic et suivi

| Observation | Investigation | Mauvaise conclusion |
| --- | --- | --- |
| 401/403 | Appelant, audience, portée projet, moindre privilège, propagation | Élargir les rôles ou retirer l'authentification |
| 429/délai | Quota, concurrence approuvée, temporisation, santé service | Qualité modèle nulle |
| `SystemError`, aucune ligne | IDs/corrélation, panne, tentative bornée autorisée | Ignorer la complétude |
| Bonne note, mauvaise réponse | Contexte indépendant, grille, fuite et calibration | La note prouve la sécurité |
| Note candidate inférieure | Résultats appariés/incertitude, configuration figée | Toute petite baisse est une régression |
| Trajectoire/traces absentes | Schéma pris en charge et ingestion réelle | Un ID réponse prouve les étapes |
| Cas répété différent | Révision, acteur, état, isolation/reset | Toute variation vient d'un LLM |

En exploitation, séparez disponibilité/erreurs et qualité : latence, coût/usage,
dérive des entrées, segments linguistiques/statuts, corrections humaines,
violations et échecs de révision. Transformez les incidents revus en tests
versionnés. Les données réelles exigent des contrôles de confidentialité et
conservation approuvés; l'atelier reste synthétique.

## Liste de livraison

Remettez jeu/matrice versionnés, calibration humaine et réserve, identités
exactes source/déploiement/modèle/évaluateur/grille, captures et IDs natifs,
complétude/qualité, incertitude et écarts par cas, coûts/latence, incidents
triés et décision du responsable. Utilisez la
[fiche Atelier 19](labs/lab-19-evaluation-engineering.md#exercice-1910-rédiger-la-recommandation-de-livraison)
et le [PowerPoint](../assets/decks/foundry-evaluation-engineering-fr.pptx)
pour distinguer ce que les preuves démontrent de leurs limites.
