---
permalink: /fr/labs/lab-13-reviewer-ui
lang: fr
title: "Atelier 13 - L'interface de révision"
description: "Alimenter une file de dossiers locale, se connecter comme réviseur, approuver un dossier et lire la piste de vérification laissée par la décision."
---

> 🇬🇧 **[English version](../../labs/lab-13-reviewer-ui)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 50 minutes |
| **Niveau** | Avancé |
| **Prérequis** | [Atelier 12](lab-12-reviewer-identity.md) complété dans un locataire où vous pouvez vous connecter |

À l'atelier 07, vous jouiez le rôle du réviseur en appelant `ApprovalRepository.approve` depuis une ligne de commande Python. Cet atelier remplace cette approche par l'interface qu'une personne réviseure utilise réellement.

Tout s'exécute ici sur votre poste de travail. Le magasin de dossiers bascule vers SQLite lorsqu'aucun point de terminaison Cosmos n'est configuré, la boucle de révision complète fonctionne donc sans aucun plan de données Azure.

> [!NOTE]
> L'interface de révision est en anglais seulement. Contrairement au clavardage destiné au demandeur, bilingue parce que les demandeurs le sont, cette surface sert des réviseurs internes pendant le pilote et a été délimitée à une seule langue.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Alimenter une file de dossiers locale à partir des données synthétiques versionnées
* Exécuter l'application de révision contre votre enregistrement Entra réel
* Lire un dossier dont le calcul n'a produit aucun montant
* Approuver un dossier et lire l'entrée de vérification écrite par la décision
* Expliquer pourquoi l'identité du réviseur dans la piste de vérification est un identifiant d'objet

## Exercices

### Exercice 13.1 : Lire le repli du magasin de dossiers

```powershell
Select-String -Path src/quote-preparation-agent/case_store.py -Pattern "def build_case_store" -Context 0,12
```

Résultat attendu : la fabrique retourne un magasin adossé à Cosmos lorsque `COSMOS_ENDPOINT` est défini, et un magasin SQLite sinon, avec `:memory:` par défaut à moins que `CASE_STORE_DB_PATH` ne nomme un fichier.

Ce repli est ce qui rend cet atelier possible hors ligne. L'application de révision ignore quel magasin elle a reçu.

### Exercice 13.2 (pratique) : Alimenter la file

`scripts/seed_review_queue.py` parcourt les deux mêmes commandes de magasin que le nœud de composition de l'agent, `create_draft` puis `submit_for_review_with_calculation`, contre le calculateur déterministe réel et les données synthétiques versionnées. Chaque montant écrit provient de `calculate_quote` lisant un référentiel de données. Aucun n'est une valeur littérale dans le script.

```powershell
python scripts/seed_review_queue.py --db-path .local/reviewer-cases.db
```

Résultat attendu : cinq dossiers, chacun rapporté avec son état et son statut de calcul.

```text
CASE-SYN-001: PENDING_REVIEW, calculation READY, 100000 cents
CASE-SYN-002: PENDING_REVIEW, calculation READY, 90000 cents
CASE-SYN-003: PENDING_REVIEW, calculation UNSUPPORTED, no amount
CASE-SYN-004: PENDING_REVIEW, calculation READY, 110000 cents
CASE-SYN-005: PENDING_REVIEW, calculation INCOMPLETE, no amount
```

Deux des cinq ne portent aucun montant. C'est délibéré. Une file où chaque ligne serait tarifée n'exercerait pas le cas que l'interface doit le mieux réussir.

Le script peut être réexécuté sans risque : un dossier déjà existant est ignoré plutôt que dupliqué.

### Exercice 13.3 (pratique) : Compiler et exécuter l'application de révision

```powershell
cd apps/reviewer-app/frontend
npm ci
npm test
npm run build
cd ../..
```

Résultat attendu : les tests de l'interface réussissent et un paquet est écrit dans `dist`. Le JSX est invisible à une vérification de syntaxe, `npm run build` est donc la seule barrière qui détecte un composant mal formé.

Démarrez le service avec votre identifiant client réel de l'atelier 12 :

```powershell
$env:ENTRA_TENANT_ID = '<votre-id-locataire>'
$env:REVIEWER_CLIENT_ID = '<id-client-revision>'
$env:ENVIRONMENT = 'local'
$env:COSMOS_ENDPOINT = ''
$env:CASE_STORE_DB_PATH = (Resolve-Path ../../.local/reviewer-cases.db).Path
python -m uvicorn app:create_app --factory --host 127.0.0.1 --port 8100
```

Résultat attendu : `Application startup complete`. Définir `COSMOS_ENDPOINT` à une chaîne vide force la branche SQLite même si un point de terminaison Cosmos se trouve exporté dans votre interpréteur.

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:8100/api/config' -UseBasicParsing | Select-Object -ExpandProperty Content
```

Résultat attendu : du JSON portant l'identifiant de locataire, l'identifiant client, la portée `Review.Access`, le rôle `Reviewer` et un environnement `local`.

### Exercice 13.4 (pratique) : Se connecter

Ouvrez `http://localhost:8100` dans un navigateur.

> [!IMPORTANT]
> Utilisez `localhost` et non `127.0.0.1`. Ce sont des origines différentes, et seul `http://localhost:8100` est un URI de redirection enregistré.

![L'application de révision avant la connexion, affichant la marque Foundry Case Review, une étiquette Local Pilot, le titre « Reviews start with access. », un avis ambre de simulation d'entraînement et un bouton de connexion Microsoft](/assets/images/reviewer-sign-in.png)

Résultat attendu : une barrière d'accès sans aucune donnée de dossier derrière elle. Connectez-vous avec un compte que vous avez ajouté au groupe de réviseurs à l'atelier 12.

Si Entra rejette la connexion, le message vous indique quelle étape de l'atelier 12 revisiter. Une discordance d'URI de redirection est un problème d'enregistrement. Un message indiquant que l'application n'est pas attribuée à l'utilisateur est l'indicateur `appRoleAssignmentRequired` qui fait son travail.

### Exercice 13.5 : Lire la file

![La file de révision listant cinq dossiers en attente avec les colonnes dossier, état, révision, préparateur, heure de soumission et prime ; deux lignes indiquent Not priced](/assets/images/reviewer-queue.png)

Résultat attendu : cinq lignes à l'état `PENDING_REVIEW`. Trois affichent une prime en dollars canadiens. Deux affichent `Not priced` avec la raison en dessous, `unsupported` pour CASE-SYN-003 et `incomplete` pour CASE-SYN-005.

Le préparateur de chaque ligne est `AGENT-INTAKE`. Aucune ligne n'a encore de réviseur.

### Exercice 13.6 (pratique) : Ouvrir un dossier tarifé

Sélectionnez CASE-SYN-001.

![La vue détaillée de CASE-SYN-001 affichant l'état PENDING_REVIEW, une prime de 1 000,00 $ CA par année d'entraînement, les identifiants de règles, la version de référentiel training-1, trois boutons de décision et une piste de vérification à deux entrées](/assets/images/reviewer-case-detail.png)

Résultat attendu : le panneau de calcul affiche la prime, la devise, la période, un statut `READY`, les identifiants de règles qui ont produit le chiffre et la version du référentiel.

Voici le montant que le demandeur n'a jamais vu à l'atelier 11. Notez ce qui l'accompagne : on ne présente pas au réviseur un nombre isolé, mais les identifiants de règles et la version de référentiel qui l'ont généré, ce qui rend le chiffre vérifiable plutôt que simplement lisible.

La piste de vérification compte déjà deux entrées, `CREATE_DRAFT` et `SUBMIT`, toutes deux attribuées à `AGENT-INTAKE`.

### Exercice 13.7 (pratique) : Ouvrir un dossier non tarifé

Revenez à la file et sélectionnez CASE-SYN-003.

![La vue détaillée de CASE-SYN-003 affichant Not priced avec la raison unsupported, un statut UNSUPPORTED, aucun identifiant de règle et un enjeu UNSUPPORTED_INPUT](/assets/images/reviewer-case-not-priced.png)

Résultat attendu : la prime indique `Not priced`, le statut est `UNSUPPORTED`, les identifiants de règles valent `None` et le champ des enjeux nomme `UNSUPPORTED_INPUT`.

Les boutons de décision demeurent actifs. Une personne réviseure peut tout de même agir sur un dossier que le calculateur a refusé de tarifer, ce qui est le comportement correct : un dossier non tarifable requiert malgré tout une issue humaine plutôt que de rester bloqué dans la file.

### Exercice 13.8 (pratique) : Approuver un dossier

Revenez à CASE-SYN-001 et choisissez Approve.

![L'étape de confirmation pour l'approbation de CASE-SYN-001, indiquant que l'approbation enregistre la décision de prime et ne peut être annulée, avec les boutons Confirm approve et Cancel](/assets/images/reviewer-approve-confirm.png)

Résultat attendu : une étape de confirmation plutôt qu'une écriture immédiate. L'approbation enregistre une décision de prime et ne peut être annulée, l'interface demande donc une confirmation.

Reject et Send back for revision confirment également, mais offrent en plus un code de raison facultatif. Approve n'en offre pas, car une approbation n'est pas un constat à expliquer.

Confirmez.

![CASE-SYN-001 après approbation, affichant une bannière indiquant recorded as APPROVED, un identifiant d'objet de réviseur, une section de décision indiquant que le dossier ne peut plus être tranché et une troisième entrée de vérification pour APPROVE](/assets/images/reviewer-case-approved.png)

Résultat attendu : l'état devient `APPROVED`, le champ du réviseur se remplit d'un identifiant d'objet, les boutons de décision sont remplacés par une phrase expliquant que le dossier ne peut plus être tranché, et une troisième entrée de vérification apparaît consignant la transition de `PENDING_REVIEW` à `APPROVED` contre votre identité.

### Exercice 13.9 : Lire la piste de vérification

Comparez les trois entrées. Les deux premières nomment `AGENT-INTAKE`. La troisième nomme un identifiant global unique.

Cet identifiant est votre identifiant d'objet Entra, tiré de la revendication `oid` du jeton vérifié plutôt que de quoi que ce soit envoyé par le navigateur. Un nom d'affichage peut changer et une adresse de courriel peut être réattribuée, mais un identifiant d'objet demeure stable pour la durée de vie du compte, ce qui est la propriété dont un enregistrement de vérification a besoin.

La séparation que vous avez appliquée à l'atelier 03 est maintenant visible de bout en bout : l'identité qui a préparé le dossier et celle qui l'a tranché sont différentes, et les deux sont consignées.

Vérifiez le journal du service dans votre terminal uvicorn :

```text
reviewer_decision command=approve case=CASE-SYN-001 revision=1 reason=None
```

Résultat attendu : une ligne de décision structurée accompagnant le journal de requête HTTP. La décision est consignée dans le magasin de dossiers et dans le journal applicatif.

### Exercice 13.10 : Nettoyer

```powershell
# Dans le terminal qui exécute uvicorn
Ctrl+C
```

```powershell
Remove-Item .local/reviewer-cases.db -Force
```

Le répertoire `.local/` figure dans `.gitignore`, la base alimentée n'est donc jamais versionnée. Réexécutez l'exercice 13.2 chaque fois que vous souhaitez une file fraîche.

## Liste de vérification

* [ ] Cinq dossiers ont été alimentés, dont deux sans montant
* [ ] `npm test` et `npm run build` réussissent dans `apps/reviewer-app/frontend`
* [ ] `/api/config` rapporte le rôle `Reviewer` et un environnement `local`
* [ ] Vous vous êtes connecté par `http://localhost:8100` et avez atteint la file
* [ ] CASE-SYN-001 affiche une prime, des identifiants de règles et une version de référentiel
* [ ] CASE-SYN-003 affiche `Not priced` avec son enjeu nommé
* [ ] L'approbation de CASE-SYN-001 a écrit une troisième entrée de vérification portant votre identifiant d'objet

## Vérification des connaissances

* Pourquoi l'application de révision fonctionne-t-elle sans aucun point de terminaison Cosmos configuré ?
* Pourquoi la piste de vérification conserve-t-elle un identifiant d'objet plutôt qu'un nom d'affichage ?
* Pourquoi les boutons de décision sont-ils actifs sur un dossier que le calculateur n'a pas pu tarifer ?
* Le demandeur n'a vu aucun montant à l'atelier 11 et vous en avez vu un ici. Où, dans le pipeline, cette divergence prend-elle naissance ?
* Pourquoi l'approbation n'offre-t-elle aucun code de raison alors que le rejet et la révision en offrent un ?

## Étapes suivantes

Poursuivez avec l'[Atelier 14 : Exploitation du pilote](lab-14-pilot-operations.md).
