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

---

# TP 2 — Logstash & Analyse de Logs

## Mise en place — Sécurité & Compte dédié

1. **Pourquoi ne pas utiliser le compte `elastic` pour Logstash ?**
   - Par principe du moindre privilège : `elastic` est le super-administrateur avec tous les droits sur l'ensemble du cluster. Si Logstash avait un problème de configuration ou était compromis, il pourrait effacer des index système ou d'autres données. En lui créant un compte dédié `logstash_internal` avec le rôle `logstash_writer`, on limite strictement ses droits aux index `offres` et aux flux `logs-web-*`.

2. **Que se passerait-il si le pipeline `web` tentait d'écrire dans `logs-generic-default` ?**
   - Elasticsearch refuserait l'écriture avec une erreur HTTP `403 Forbidden` (`security_exception`). Le rôle `logstash_writer` n'accorde de droits d'écriture que sur `offres` et `logs-web-*`. Tout autre index ou data stream est immédiatement bloqué.

3. **Pourquoi le mot de passe est-il transmis par variable d'environnement plutôt qu'écrit dans les fichiers `.conf` ?**
   - Pour ne jamais committer de mot de passe en clair dans Git. Les fichiers `.conf` font partie du code source et sont versionnés sur GitHub, alors que le fichier `.env` est ignoré par Git. On injecte donc `${ES_PASSWORD}` à la volée.

---

## Exercice 0 — Premier pipeline Logstash

1. **Quels champs Logstash a-t-il ajoutés à votre phrase ?**
   - `@version` : la version du format interne d'événement de Logstash (`"1"`).
   - `@timestamp` : l'horodatage UTC ISO-8601 de l'événement.
   - `host.hostname` : le nom d'hôte ou l'identifiant du conteneur qui fait tourner Logstash.
   - `event.original` : la copie brute du message non altéré (conforme au standard ECS).
   - *(Le contenu saisi se retrouve quant à lui dans le champ `message`)*.

2. **Que contient `@timestamp` : l'heure de quoi ?**
   - Il contient l'heure exacte à laquelle Logstash **a ingéré/lu** la ligne. Ce n'est pas l'heure de production de l'événement d'origine. Pour les fichiers de logs (qui datent souvent du passé), il est indispensable d'utiliser le filtre `date` pour remplacer ce `@timestamp` par la date réelle du log.

3. **À quoi sert l'option `--path.data /tmp/essai` ?**
   - Logstash pose un verrou exclusif sur son dossier de données (`data/`). En spécifiant un chemin temporaire comme `/tmp/essai`, on évite tout conflit de verrouillage avec un autre conteneur Logstash déjà en cours d'exécution.

---

## Partie 1 — Recharger les offres avec Logstash

### Exercice 1.2 — Premier lancement (sans le filtre mutate)

1. **Les documents sont-ils indexés ?**
   - Non, les documents sont tous rejetés par Elasticsearch.
2. **Quelle erreur Elasticsearch renvoie-t-il, avec quel code HTTP et quel type d'exception ?**
   - Code HTTP : **`400 Bad Request`**
   - Type d'exception : **`strict_dynamic_mapping_exception`** (ou `mapping_parsing_exception`).
3. **Quels noms de champs sont cités ?**
   - Le premier champ cité est **`@timestamp`**, suivi de `@version`, `event`, `host`, `log`. Ce sont les champs techniques que Logstash ajoute d'office à chaque événement.
4. **Faites le lien avec `"dynamic": "strict"` (TP 1, ex. 1.4) :**
   - Dans le TP 1, nous avons configuré l'index `offres` avec la directive `"dynamic": "strict"` pour interdire tout ajout de champ imprévu dans le schéma. Comme ces métadonnées de transport Logstash ne font pas partie du mapping initial de l'index, Elasticsearch respecte scrupuleusement la règle et bloque l'insertion.

---

### Exercice 1.3 — Corriger avec le filtre mutate

1. **Le nombre de documents a-t-il changé ?**
   - Non, il reste exactement à 5 000 documents (`GET offres/_count`).
2. **Et le `_version` de `OFF-00002` ? Pourquoi ?**
   - Le `_version` est passé de 3 à 4. Grâce au paramètre `document_id => "%{id}"`, Logstash transmet l'identifiant métier unique. Elasticsearch met à jour le document existant en place au lieu de créer un doublon (idempotence).
3. **Pourquoi a-t-on préféré supprimer ces champs plutôt que d'assouplir le mapping de l'index ?**
   - Pour garantir la pureté du modèle métier. L'index `offres` est un catalogue de recherche fonctionnel destiné aux utilisateurs. Il n'a pas à être alourdi par des données de plomberie technique (`@version`, `@timestamp` d'ingestion, `host.name`), qui augmenteraient inutilement la taille de l'index Lucene.
4. **Pourquoi l'index `offres` doit-il exister avant le premier démarrage de Logstash ?**
   - Dans `offres.conf`, `manage_template` est fixé à `false`. Si l'index n'existait pas, Elasticsearch le créerait au vol avec son mapping dynamique par défaut : nous perdrions le type `geo_point` pour la carte, l'analyseur `french`, et la protection `dynamic: strict`.

---

### Exercice 1.4 — Relancer et tester la mémoire

1. **Combien de fois le fichier a-t-il été lu ?**
   - Il a été relu une fois de plus à chaque redémarrage de Logstash.
2. **Que se passerait-il avec la sincedb par défaut au lieu de `/dev/null` ?**
   - Logstash enregistrerait dans sa base locale (sincedb) l'inœud du fichier et le dernier octet lu. Au redémarrage suivant, voyant que le fichier n'a pas été modifié depuis, il ignorerait le fichier et n'ingérerait rien (0 lecture). L'utilisation de `/dev/null` permet de forcer la relecture à chaque lancement en environnement de test.
3. **Et si `document_id` n'était pas renseigné ?**
   - Elasticsearch attribuerait un identifiant auto-généré aléatoire à chaque document. À chaque ré-exécution ou redémarrage de Logstash, 5 000 nouveaux documents seraient créés en doublon (5 000, 10 000, 15 000 offres...).

---

## Partie 2 — Superviser et fiabiliser

### Exercice 2.1 — Superviser via l'API (port 9600)

1. **Combien de pipelines sont chargés, avec combien de workers chacun ?**
   - **2 pipelines** sont chargés (`offres` et `web`, déclarés dans `pipelines.yml`).
   - Chacun dispose de **8 workers** (`"workers": 8`). Logstash attribue automatiquement un worker par cœur CPU disponible sur la machine pour paralléliser l'exécution des filtres et des sorties.

2. **Que valent `in`, `filtered` et `out` pour `offres`, et que représentent-ils depuis le dernier démarrage ?**
   - Valeurs observées : `"in": 5000`, `"filtered": 5000`, `"out": 5000`.
   - **Ce qu'ils représentent depuis le dernier démarrage :**
     Ce sont des **compteurs cumulatifs volatils (en RAM)** qui sont remis à zéro (`0`) à chaque démarrage du processus Logstash. Ils mesurent le volume d'événements traités sur la session d'exécution en cours :
     - `in` : 5 000 événements reçus de la source (`offres.ndjson`).
     - `filtered` : 5 000 événements passés avec succès à travers les filtres (`mutate`).
     - `out` : 5 000 événements sortis et acquittés par Elasticsearch.
     - L'égalité `in == filtered == out == 5000` prouve que sur cette session, 100 % des documents ont été traités sans perte, sans rejet et sans mise en attente (aucun drop).

3. **Quel plugin du pipeline consomme le plus de temps (`duration_in_millis`) ?**
   - En observant la décomposition des plugins :
     - Input `file` : ~519 ms
     - Filter `mutate` : 3 482 ms (~3,5 s)
     - Output `elasticsearch` : **24 515 ms** (~24,5 s)
   - C'est très nettement la **sortie `elasticsearch`** qui consomme l'essentiel du temps (~87 %). Le filtre `mutate` travaille en pure mémoire locale CPU, tandis que l'output Elasticsearch effectue des transferts réseau HTTP par lots (`bulk`) et doit attendre l'acquittement d'écriture et d'indexation Lucene sur disque par le cluster.

---

### Exercice 2.2 — Isoler les documents rejetés (Dead Letter Queue)

1. **Le document `OFF-99999` est-il dans l'index ? Où se trouve-t-il ?**
   - Non, il n'est pas dans l'index Elasticsearch (`GET offres/_doc/OFF-99999` renvoie `found: false`, et le count reste à 5 000).
   - Il se trouve stocké sur disque dans le répertoire de la Dead Letter Queue : `/usr/share/logstash/data/dead_letter_queue/offres/1.log`.

2. **Quelle raison de refus est enregistrée dans `[@metadata][dead_letter_queue]` ?**
   - La raison enregistrée est :
     `"status: 400, error: {"type": "strict_dynamic_mapping_exception", "reason": "mapping set to strict, dynamic introduction of [prime] within [_doc] is not allowed"}"`.
   - Elasticsearch a rejeté le document car le champ `"prime"` est absent du mapping explicite et l'index est verrouillé en `dynamic: strict`.

3. **Comparez avec `raise_on_error=False` dans `ingest.py` : qu'apporte la DLQ en plus ?**
   - Dans `ingest.py`, `raise_on_error=False` se contente d'éviter le plantage du script en stockant temporairement les erreurs dans une variable Python. Dès que le script se termine, les données rejetées sont perdues si on n'a pas développé manuellement un système de stockage.
   - La DLQ de Logstash est une solution industrielle intégrée :
     - Les documents rejetés et leurs causes sont **sécurisés et persistés sur disque**.
     - Les métadonnées complètes de l'erreur (code HTTP, stack d'erreur Elasticsearch, horodatage, ID de plugin) sont jointes au document.
     - Logstash fournit un plugin d'entrée dédié (`input { dead_letter_queue { ... } }`) qui permet de rejouer et retraiter cette file automatiquement avec gestion d'offsets, sans aucune perte de données.

4. **Décrivez en trois étapes comment vous corrigeriez et réinjecteriez ce document :**
   - **Étape 1 (Diagnostic) :** Inspecter les messages de la DLQ avec un pipeline de lecture pour identifier la cause exacte (champ imprévu, mauvais format de date, etc.).
   - **Étape 2 (Remédiation) :**
     - Si le champ est une anomalie/erreur de saisie : créer un pipeline de correction avec un filtre `mutate { remove_field => ["prime"] }`.
     - Si le champ est une nouvelle information métier légitime : faire évoluer le mapping dans Elasticsearch (`PUT offres/_mapping` avec la nouvelle propriété `"prime": { "type": "integer" }`).
   - **Étape 3 (Réinjection) :** Exécuter un pipeline de réinjection (`input { dead_letter_queue { ... commit_offsets => true } }` vers `output { elasticsearch { ... } }`) pour réindexer les documents corrigés et vider la DLQ.

---

### Exercice 2.3 — Pourquoi deux pipelines ?

1. **Si le fichier `pipelines.yml` n'était pas monté, combien de pipelines Logstash chargerait-il ?**
   - Logstash chargerait **un seul et unique pipeline** (appelé `main`).

2. **Dans ce cas, que deviendrait une offre lue dans `offres.ndjson` ? Et une ligne de log d'accès ?**
   - En l'absence d'isolation, tous les fichiers de configuration du dossier `pipeline/` sont fusionnés : chaque entrée alimente toutes les sorties.
   - Une offre lue dans `offres.ndjson` serait envoyée à la fois dans l'index `offres` et dans le data stream `logs-web-default` (provoquant des erreurs de typage et polluant les logs d'accès).
   - Une ligne de log d'accès serait envoyée vers `logs-web-default` et tenterait aussi d'être indexée dans `offres`, où elle se ferait immédiatement rejeter par la règle `dynamic: strict`.

3. **Citez deux autres avantages à isoler les pipelines :**
   - **Indépendance des réglages et des performances :** Chaque pipeline peut avoir son propre nombre de workers, sa propre taille de batch et sa propre stratégie de mémoire (ex: file persistée sur disque pour les logs critiques, file en RAM pour les offres).
   - **Résilience et isolation des pannes :** Si le pipeline `web` subit un ralentissement ou un blocage (ex: saturation réseau ou parsing grok lourd), le pipeline `offres` continue de fonctionner à pleine vitesse sans impact.

---

### Exercice 2.4 — Ne rien perdre (file persistée)

1. **Avec la file en mémoire, que deviennent les événements en cas d'arrêt brutal (`docker kill`) ?**
   - Tous les événements déjà lus depuis la source mais encore en transit dans les filtres ou en attente d'envoi vers Elasticsearch sont **définitivement perdus**.

2. **Quel réglage change ce comportement, et quelle garantie obtient-on ?**
   - Le réglage est : `queue.type: persisted` (dans `logstash.yml` ou par variable d'environnement).
   - Avec cette option, chaque événement lu est écrit sur disque avant d'être traité. On obtient la garantie de livraison **« au moins une fois »** (*at least once delivery*) : en cas de panne, les événements sont rejoués au redémarrage.

3. **Pourquoi le `document_id` de la partie 1 devient-il alors indispensable ?**
   - Avec la garantie « au moins une fois », un événement déjà transmis juste avant un crash peut être renvoyé une deuxième fois au redémarrage.
   - En fournissant un identifiant déterministe (`document_id => "%{id}"`), Elasticsearch procède à une mise à jour (*upsert*) du document existant au lieu de créer un doublon. L'idempotence transforme ainsi le « au moins une fois » en un résultat **« exactement une fois »** (*exactly once*) effectif dans la base.
