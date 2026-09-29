# Réponses aux questions — TP Elasticsearch & Kibana

## Exercice 0 — Vérifier l'accès au cluster

1. **Les réponses sont-elles identiques d'un outil à l'autre (curl vs Kibana Dev Tools) ?**
   - Oui, on obtient exactement la même réponse JSON. Dev Tools et curl interrogent la même API REST sur le port 9200.

2. **Quel code HTTP obtenez-vous sans authentification, et que dit le message d'erreur ?**
   - On obtient un code **401 Unauthorized** avec l'erreur `security_exception` et le message `"missing authentication credentials for REST request [/]"`.
   - C'est normal : la sécurité est activée (`xpack.security.enabled=true`) et Elasticsearch refuse les accès sans identifiants.

3. **Pourquoi Kibana n'a-t-il pas besoin que vous lui fournissiez le mot de passe à chaque requête ?**
   - On s'est connecté une fois sur l'interface web de Kibana (qui garde notre session active via un cookie), et le serveur Kibana communique directement avec Elasticsearch grâce à son compte interne (`kibana_system`).

---

## Exercice 1.1 — Explorer le cluster

1. **Quelle version d'Elasticsearch tourne ?**
   - La version **9.5.4** (affichée dans le JSON de `GET /`).

2. **Combien de nœuds composent le cluster ?**
   - **1 seul nœud** (`es01`), car on est en configuration de test/labo (`discovery.type=single-node`).

3. **Pourquoi voyez-vous des index commençant par un point (`.`) ?**
   - Ce sont les index système internes d'Elasticsearch et Kibana (ex: `.security` pour les utilisateurs et droits, `.kibana` pour les dashboards). Ils sont cachés par défaut pour ne pas gêner nos données métier.

---

## Exercice 1.2 — Le CRUD

1. **Comment évolue le champ `_version` ?**
   - Création (`PUT`) : `_version: 1`
   - Lecture (`GET`) : `_version: 1` (la lecture ne change rien)
   - Mise à jour (`POST _update`) : `_version: 2`
   - Suppression (`DELETE`) : `_version: 3`
   - C'est un compteur qui s'incrémente à chaque écriture pour gérer la concurrence et éviter d'écraser des modifications en simultané.

2. **Quel identifiant (`_id`) reçoit le document créé par `POST essai/_doc` ?**
   - Il reçoit un identifiant aléatoire de 20 caractères généré automatiquement par Elasticsearch (ex: `sE6bJpIBm3j_8XyG...`).

3. **L'index `essai` existait-il avant le premier `PUT` ? Qu'a fait Elasticsearch ?**
   - Non, il n'existait pas. Elasticsearch l'a créé automatiquement à la volée dès qu'il a reçu le premier document (mapping dynamique).

---

## Exercice 1.3 — Les pièges du mapping dynamique

1. **Quel type reçoit le champ `salaire` ? Et `publication` ?**
   - `salaire` est devenu du `text` (avec sous-champ `keyword`) parce que la valeur du premier document était entre guillemets (`"45000"`).
   - `publication` est bien devenu une `date` car Elasticsearch a reconnu automatiquement le format `2026-08-02`.
   - `actif` est devenu du `text` car la détection automatique de booléen n'est pas active sur les chaînes.

2. **Pourquoi le document 2 (avec `52000` en nombre) est-il accepté sans erreur ?**
   - Elasticsearch fait de la coercition : comme le champ a été créé en `text`, il convertit automatiquement le nombre `52000` en chaîne `"52000"` sans bloquer.

3. **Quelle conséquence pour un tri ou un filtre `salaire > 50000` ?**
   - Le tri se fait par ordre alphabétique au lieu de numérique (par exemple `"100000"` sera classé avant `"50000"` car '1' est avant '5').
   - Les filtres `> 50000` seront faux et on ne pourra pas calculer de moyenne (`avg`).

---

## Exercice 1.4 — Mapping explicite de l'index offres

1. **Quelle erreur obtenez-vous lors de l'insertion de `"champ_inconnu"` ?**
   - Erreur 400 Bad Request : `strict_dynamic_mapping_exception` disant que l'ajout dynamique de `champ_inconnu` est interdit.

2. **Pourquoi le mode `dynamic: strict` est-il une bonne pratique en production ?**
   - Ça évite la "mapping explosion" (saturation de la mémoire si des champs imprévus arrivent en masse).
   - Ça permet de détecter tout de suite les fautes de frappe dans le code (ex: écrire `slaire` au lieu de `salaire`).

---

## Exercice 2.2 — Idempotence et identifiants

1. **Le nombre de documents a-t-il doublé lors de la seconde exécution sans `--reset` ?**
   - Non, on a toujours exactement 5 000 documents.

2. **Pourquoi fixer `_id` à partir du champ métier `id` est-il essentiel ?**
   - Ça rend l'ingestion idempotente : si on relance le script, Elasticsearch met à jour les offres existantes au lieu d'en créer de nouvelles.

3. **Que se passerait-il avec des identifiants générés automatiquement ?**
   - Elasticsearch créerait de nouveaux IDs à chaque fois et on aurait eu 10 000 documents avec 5 000 doublons.

---

## Exercice 2.3 — Provoquer une erreur de mapping

1. **Combien de documents ont été indexés ? Le lot entier a-t-il été rejeté ou seulement ce document ?**
   - 5 000 documents ont été indexés et 1 seule erreur a été remontée. Seul le document `OFF-99999` avec le champ `prime` a été rejeté, tout le reste du lot a été accepté.

2. **Quel est l'intérêt de `raise_on_error=False` pour un pipeline en production ?**
   - Le script ne plante pas au milieu pour une seule ligne erronée. Le reste continue d'être indexé, et on peut récupérer les erreurs dans une liste pour les traiter à part.

---

## Exercice 3.1 — Voir travailler un analyseur

1. **Quels mots ont complètement disparu avec l'analyseur `french` ?**
   - Les mots "Les", "sur" et "des" ont disparu car ce sont des mots vides (stopwords) français.

2. **Que devient `"l'analyse"` dans les tokens produits par `french` ?**
   - Ça donne un seul token : `"analys"`. L'analyseur a retiré l'élision `l'` et a racinisé le mot.

3. **Que donne l'analyse de `"donnée"` puis `"données"` avec chaque analyseur ? Qu'en déduisez-vous pour la recherche ?**
   - Avec `standard` : on a deux tokens différents (`donnée` et `données`).
   - Avec `french` : les deux donnent le même token racine (`done`).
   - Pour la recherche, c'est super utile car quelqu'un qui cherche au singulier trouvera aussi les offres rédigées au pluriel.

---

## Exercice 3.2 — match contre term

1. **Pourquoi les deux requêtes `term` renvoient-elles 0 résultat ?**
   - Sur `ville`: le champ est en `keyword` (sensible à la casse), et dans la base c'est écrit "Paris" avec une majuscule.
   - Sur `titre`: le champ est en `text` et a été découpé en plusieurs mots. La requête `term` cherche la phrase exacte en un seul bloc, qui n'existe pas telle quelle.

2. **Comment corriger ces deux requêtes ?**
   - Pour la ville : mettre la majuscule `"term": { "ville": "Paris" }`.
   - Pour le titre : utiliser le sous-champ brut non analysé `"term": { "titre.brut": "Data Engineer Senior" }`.

3. **Que change `"operator": "and"` dans la requête `match` sur la description ?**
   - Sans le `and`, c'est un `OR` par défaut (les offres qui ont "projets" OU "bancaires" ressortent, soit 4 190 offres).
   - Avec `and`, il faut obligatoirement les deux mots, ce qui restreint à 393 offres beaucoup plus pertinentes.

---

## Exercice 3.3 — Plusieurs champs, pondération et fautes de frappe

1. **Quel paramètre rattrape la faute de frappe sur `"kubernetis"` ? Comment fonctionne-t-il ?**
   - C'est `"fuzziness": "AUTO"`.
   - Il calcule la distance de Levenshtein (le nombre de lettres à corriger). Comme il n'y a qu'une lettre de différence entre "kubernetis" et "kubernetes", l'erreur est rattrapée.

2. **Comment évolue le score et l'ordre des résultats avec le poids `titre^3` ?**
   - Les offres qui ont les mots dans le titre reçoivent un score 3 fois plus fort et remontent tout en haut de la liste.

---

## Exercice 3.4 — Requête bool

1. **Comparaison des scores avec et sans le bloc `should` :**
   - Avec `should`, les offres qui ont la compétence "Elasticsearch" gagnent des points bonus et passent en premier.
   - Sans `should`, toutes les offres sélectionnées restent au même niveau de score.

2. **Pourquoi placer les critères exacts dans `filter` plutôt que dans `must` ?**
   - Les filtres sont mis en cache mémoire par Elasticsearch, donc les requêtes suivantes sont plus rapides.
   - Ça ne pollue pas le score : être en CDI ou à Toulouse est une condition obligatoire oui/non, pas une mesure de pertinence textuelle.

---

## Exercice 3.5 — Recherche géographique

- La clause `geo_distance` filtre bien les offres dans le rayon de 20 km autour de Montpellier.
- Le tri `_geo_distance` les classe de la plus proche à la plus lointaine, et la distance exacte en km apparaît dans le tableau `sort` de chaque résultat.

---

## Exercice 3.6 — Pagination et surlignage

1. **Pourquoi `from + size` est-il limité à 10 000 par défaut ?**
   - C'est pour éviter le problème du Deep Paging : si on demande une page très lointaine, les shards doivent charger et trier des milliers de documents en mémoire vive, ce qui peut saturer la RAM du cluster.

2. **Quelle API utiliser au-delà de 10 000 ?**
   - On utilise `search_after` avec un Point in Time (PIT), qui fonctionne comme un curseur sans recharger tout l'historique.

---

## Exercice 4.1 — Offres et salaire moyen par ville

1. **Quelle ville a le salaire moyen le plus élevé ?**
   - C'est Paris (~57 442 €), suivie de Grenoble (~53 046 €).

2. **Sur combien d'offres la moyenne est-elle calculée ?**
   - Sur 3 389 offres (seuls les CDI et CDD ont un salaire renseigné, Elasticsearch ignore les champs absents pour la moyenne).

3. **Quelle erreur obtient-on en remplaçant `"ville"` par `"titre"`, et comment corriger ?**
   - On a une `illegal_argument_exception` car `titre` est de type `text` (fielddata désactivé pour protéger la mémoire).
   - Pour corriger, on utilise le sous-champ keyword : `"titre.brut"`.

---

## Exercice 4.2 — Publications par mois et par contrat

- L'agrégation `date_histogram` regroupe bien par mois sur `date_publication`, et la sous-agrégation permet de voir la part de CDI, CDD, etc. mois par mois.

---

## Exercice 4.3 — Tranches de salaire et statistiques d'expérience

- L'agrégation `range` sépare bien les salaires (< 40k : 484 offres, 40-55k : 1 363 offres, >= 55k : 1 542 offres).
- L'agrégation `stats` sur l'expérience donne : min 0 an, max 15 ans et une moyenne d'environ 5,9 ans.

---

## Exercice 4.4 — Requête + Agrégation

1. **Résultats pour « Data Engineer » (919 offres) :**
   - Top 5 compétences : Python (634), SQL (611), Airflow (315), Spark (313), Kafka (312).
   - Télétravail le plus fréquent : partiel (558 offres).

2. **L'agrégation porte-t-elle sur tout l'index ou seulement sur la requête ?**
   - Elle porte uniquement sur les 919 offres qui correspondent au `match` "Data Engineer".
   - La clause `query` filtre les documents en premier, puis l'agrégation calcule ses stats sur ce résultat.
