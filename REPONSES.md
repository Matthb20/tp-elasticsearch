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

---

## Partie 3 — Transformer les logs d'accès

### Exercice 3.2 — Mettre au point le motif (Grok Debugger)

1. **Quels champs sont extraits par le motif `%{COMBINEDAPACHELOG}` ?**
   - `source.address` : adresse IP du client (`203.0.113.123`).
   - `http.request.method` : méthode HTTP (`GET`, `POST`...).
   - `url.original` : chemin de la ressource demandée (`/offres/OFF-01468`).
   - `http.version` : version du protocole HTTP (`1.1`).
   - `http.response.status_code` : code de statut HTTP (`200`, `404`, `500`...).
   - `http.response.body.bytes` : taille du corps de réponse en octets (`43686`).
   - `http.request.referrer` : URL de provenance / référent.
   - `user_agent.original` : chaîne brute du navigateur / user agent.
   - `timestamp` : date et heure brute du serveur web (`23/Sep/2026:00:00:39 +0200`).

2. **Sous quel type apparaît `http.response.status_code` ?**
   - Dans la sortie brute de `grok`, il est extrait sous forme de chaîne de caractères (`string` / texte `"200"`). Mais une fois injecté dans Elasticsearch dans le template `logs-*-*`, il est automatiquement casté en entier (`long`).

3. **Pourquoi `timestamp` doit-il encore être traité ?**
   - Parce que `grok` n'extrait qu'une simple chaîne textuelle non interprétée. Pour qu'Elasticsearch et Kibana puissent classer, filtrer par période et tracer des histogrammes temporels, cette date doit être convertie au format officiel ISO-8601 UTC et enregistrée dans le champ spécial **`@timestamp`** grâce au filtre `date`.

4. **Quel motif extrait `OFF-01468` de l'URL `/offres/OFF-01468/postuler` ?**
   - On définit le motif personnalisé :
     ```text
     pattern_definitions => { "OFFRE_ID" => "OFF-[0-9]{5}" }
     match => { "[url][original]" => "^/offres/%{OFFRE_ID:[labels][offre_id]}" }
     ```
   - Cela capture `OFF-01468` et le stocke proprement dans `labels.offre_id`.

---

### Exercice 3.4 — Vérifier le data stream

1. **Combien de documents (attendu : 20 700) et combien d'échecs de grok (attendu : 0) ?**
   - Nombre total de documents : **20 700** (`GET logs-web-default/_count`).
   - Échecs de grok : **0** (`GET logs-web-default/_count` avec `tags: "_grokparsefailure"` renvoie `0`).

2. **Quel est le nom de l'index caché (*backing index*) qui contient les données, et que signifie chaque partie de ce nom ?**
   - Nom de l'index : **`.ds-logs-web-default-2026.10.01-000001`**
   - Signification de chaque partie :
     - `.ds-` : indique un index interne caché géré automatiquement par un Data Stream.
     - `logs` : le type de données (*type*).
     - `web` : le nom du jeu de données / source (*dataset*).
     - `default` : l'espace de nommage logique (*namespace*).
     - `2026.10.01` : date de création de l'index en UTC.
     - `000001` : numéro de génération du rollover ILM (s'incrémente lors d'un cycle de vie d'index).

3. **Le premier événement est-il daté du 23/09/2026 à 00:00:39 (+02:00), soit 22:00:39 UTC la veille ?**
   - Oui, la requête de tri `sort: [{"@timestamp": "asc"}]` affiche exactement :
     `"@timestamp": "2026-09-22T22:00:39.000Z"`.
   - Le filtre `date` a parfaitement appliqué le décalage `+0200` pour normaliser l'horodatage en UTC standard.

4. **Quel type a reçu `http.response.status_code`, et pourquoi est-ce important pour la suite ?**
   - Il a reçu le type **`long`** (nombre entier).
   - C'est indispensable pour l'enquête et les dashboards afin de :
     - Faire des filtres numériques d'intervalle (ex: `http.response.status_code >= 500` pour toutes les erreurs serveur 5xx).
     - Calculer des formules statistiques (ex: taux d'erreur serveur avec `count(kql='http.response.status_code >= 500') / count()`).

5. **Quel `index.mode` est utilisé ?**
   - Le mode utilisé est **`logsdb`**.
   - C'est le mode haute performance d'Elasticsearch 9 dédié aux logs temporels, qui optimise le stockage, l'indexation et la compression sur disque.

---

### Exercice 3.5 — Rejouer sans doublon ?

1. **Que constatez-vous en redémarrant Logstash, et pourquoi le problème ne se posait-il pas pour `offres` ?**
   - En redémarrant avec `sincedb_path => "/dev/null"` et sans `document_id`, Logstash relit l'intégralité du fichier et le nombre de documents passe à **41 400** (tous les logs sont insérés en doublon).
   - Pour l'index `offres`, le problème ne se posait pas car nous avions fixé `document_id => "%{id}"` sur un index classique, ce qui écrasait en place (*upsert*) les documents existants sans créer de doublon.

2. **Peut-on mettre à jour ou remplacer un document dans un data stream ?**
   - **NON.** Par définition, un Data Stream Elasticsearch est conçu pour des flux d'événements temporels en **ajout seul (append-only)** (`op_type: create`). Elasticsearch n'autorise pas la mise à jour ou le remplacement direct de documents dans un data stream.

3. **Proposez deux solutions pour pouvoir rejouer ce fichier sans doublon :**
   - **Solution 1 (Gestion de sincedb) :** Ne pas désactiver sincedb (retirer `/dev/null`) pour que Logstash mémorise l'inœud du fichier et le dernier octet lu sur disque, évitant ainsi de relire des lignes déjà ingérées.
   - **Solution 2 (Déduplication par empreinte numérique - `fingerprint`) :** Utiliser le filtre `fingerprint` dans Logstash pour générer un hash SHA-256 unique basé sur la ligne (ex: IP + URL + date) stocké dans `[@metadata][fingerprint]`. Cela permettrait de filtrer les doublons avant l'envoi ou d'écrire dans un index dédupliqué.

---

## Partie 4 — Enquête dans Kibana

### Exercice 4.1 — Vue d'ensemble du trafic

1. **Quelle est la répartition des requêtes par code HTTP ?**
   - `200` (Succès) : **17 805** (86,01 %)
   - `201` (Création - candidatures) : **1 492** (7,21 %)
   - `404` (Non trouvé) : **508** (2,45 %)
   - `304` (Cache non modifié) : **488** (2,36 %)
   - `503` (Service indisponible) : **402** (1,94 %)
   - `500` (Erreur interne) : **5** (0,02 %)
   - Total : **20 700** requêtes.

2. **Quelle est la répartition par méthode HTTP ?**
   - `GET` : **19 208** requêtes (92,79 %)
   - `POST` : **1 492** requêtes (7,21 %) — correspondent exactement aux soumissions de candidatures (`/postuler`).

3. **Quel est le volume moyen de requêtes par jour ?**
   - Sur les 7 jours complets analysés (du 23 au 29 septembre 2026), le site enregistre en moyenne **2 957 requêtes par jour** (allant de 2 589 à 3 292 requêtes quotidiennes).

---

### Exercice 4.2 — L'incident de production

1. **Jour et créneau précis de l'incident :**
   - **Jour :** Lundi **28 septembre 2026**.
   - **Créneau horaire UTC :** De **12:00:00Z à 12:45:00Z**.
   - **Créneau en heure locale (Paris, UTC+2) :** De **14h00 à 14h45** (un après-midi).
   - En resserrant par pas de 5 minutes, les erreurs démarrent pile à 12h00 et s'arrêtent net à 12h45 (9 tranches consécutives d'environ 45 erreurs).

2. **Les URL touchées, et celles qui ne l'ont pas été :**
   - **URL touchées :** Exclusivement les endpoints d'API de recherche d'offres : `/api/offres?ville=...&page=...` (concernant toutes les villes : Bordeaux, Lyon, Lille, Paris, Nantes, Montpellier, Toulouse).
   - **URL non touchées :** Le reste du site fonctionnait normalement : page d'accueil (`/`), pages de recherche web (`/recherche`), fiches individuelles d'offres (`/offres/OFF-...`), et fichiers statiques (`/static/app.js`).

3. **Nombre de réponses en erreur et durée :**
   - Nombre d'erreurs : **402 réponses `503 Service Unavailable`** (ainsi que 5 erreurs 500 ponctuelles).
   - Durée exacte : **45 minutes**.

4. **Comportement des clients pendant l'incident :**
   - Le volume de requêtes vers l'API est resté soutenu et régulier pendant toute la panne (~45 requêtes toutes les 5 minutes).
   - **Explication :** Les clients (applications mobiles, scripts front-end ou utilisateurs rafraîchissant leur page) mettaient en œuvre des mécanismes de réessai automatique (*retry loop*) face au code 503, maintenant une charge constante jusqu'à la remise en service du service API à 14h45.

---

### Exercice 4.3 — L'activité suspecte (Cybersécurité)

1. **Adresse IP à l'origine de la rafale de 404 :**
   - Adresse IP : **`203.0.113.66`** (à elle seule, elle génère **300 réponses 404**).

2. **Moment et durée de cette activité :**
   - **Date :** Samedi **26 septembre 2026**.
   - **Créneau :** De **01:12:00Z à 01:16:59Z** (soit de **03h12 à 03h17 du matin** en heure locale de Paris).
   - **Durée :** Exactement **5 minutes** (cadence de 1 requête par seconde).

3. **Les URL demandées : que cherchait ce robot ?**
   - URL scannées : `/admin` (59 fois), `/.git/config` (55 fois), `/.env` (53 fois), `/phpmyadmin/` (46 fois), `/server-status` (44 fois), `/wp-login.php` (43 fois).
   - **Intention :** C'est un scan automatisé de vulnérabilités et de fuites d'informations sensibles (*reconnaissance / credential harvesting*). Le robot cherchait à voler le code source via un dossier Git exposé, à dérober des mots de passe dans un fichier `.env`, ou à trouver des interfaces d'administration non protégées (WordPress, phpMyAdmin).

4. **Son `user_agent.original` : comment le distinguer d'un navigateur ?**
   - Chaîne user-agent : **`Mozilla/5.0 zgrab/0.x`**.
   - **Distinction :** Bien qu'il tente d'imiter un navigateur avec le préfixe `Mozilla/5.0`, il contient le mot explicite **`zgrab/0.x`** (un scanner de bannières réseau open source). De plus, il ne mentionne aucun moteur de rendu moderne (Gecko, WebKit) ni aucun système d'exploitation réel.

5. **D'où viennent les autres erreurs 404 ? Sont-elles inquiétantes ?**
   - Les 208 autres erreurs 404 ciblent des URL du type `/offres/OFF-09223`, `/offres/OFF-09347`, etc.
   - **Explication :** L'index `offres` ne contient que les offres de `OFF-00001` à `OFF-05000`. Ces requêtes correspondent à de vrais candidats cliquant sur d'anciennes offres supprimées, des annonces expirées ou des favoris obsolètes.
   - **Conclusion :** Elles ne sont absolument pas inquiétantes : c'est le cycle de vie normal d'un site d'emploi.

---

### Exercice 4.4 — Les 10 offres les plus consultées

Top 10 des offres les plus consultées (requêtes `GET` avec statut `200`) et détails récupérés dans l'index `offres` :

| Identifiant (`labels.offre_id`) | Nombre de vues | Titre du poste | Ville | Contrat |
| :--- | :---: | :--- | :--- | :--- |
| **OFF-04662** | 8 | Développeur Front-end Senior | Bordeaux | Freelance |
| **OFF-03141** | 7 | Développeur Python Confirmé | Bordeaux | CDI |
| **OFF-01153** | 7 | Développeur Java Confirmé | Toulouse | Freelance |
| **OFF-03145** | 6 | Data Engineer Lead | Montpellier | CDI |
| **OFF-01275** | 6 | Administrateur Bases de Données Lead | Paris | CDI |
| **OFF-01660** | 6 | Architecte Cloud Senior | Lyon | CDI |
| **OFF-03524** | 6 | Développeur Python (Alternance) | Toulouse | Alternance |
| **OFF-00901** | 6 | Développeur Java Junior | Paris | CDI |
| **OFF-03923** | 6 | Architecte Cloud Confirmé | Lyon | CDI |
| **OFF-03126** | 6 | Administrateur Bases de Données Junior | Lyon | CDI |

*Requête Dev Tools utilisée : `GET offres/_search` avec filtre `ids` sur ces 10 identifiants.*

---

### Exercice 4.5 — Analyse de l'audience (OS et Navigateurs)

1. **Part du trafic provenant d'appareils mobiles (`user_agent.os.name`) :**
   - **Android :** 4 056 requêtes (19,6 %)
   - **iOS :** 4 099 requêtes (19,8 %)
   - **Part mobile totale :** **8 155 requêtes sur 20 700**, soit **39,4 %** du trafic global.
   - Le reste du trafic provient de systèmes desktop : Mac OS X (4 150), Windows (4 058), Linux (4 037), et le scanner zgrab (300).

2. **Les 3 navigateurs les plus utilisés (`user_agent.name`) :**
   - **1. Safari / Mobile Safari :** 8 249 requêtes combinées (4 150 desktop + 4 099 mobile).
   - **2. Chrome / Chrome Mobile :** 8 114 requêtes combinées (4 058 desktop + 4 056 mobile).
   - **3. Firefox :** 4 037 requêtes (uniquement sur desktop Linux).

---

## Partie 5 — Tableau de bord et restitution

### Description des 6 panneaux du tableau de bord « Site de recrutement — trafic »

Le tableau de bord a été conçu dans Kibana avec **Lens** et **Maps** à partir de la data view `logs-web-*` (et `offres` pour la cartographie) sur la période d'observation du 23 au 30 septembre 2026. Les 6 panneaux requis par la consigne sont intégrés et nommés comme suit :

1. **Panneau « Requêtes » (affiché *Nombre de requete*) :**
   - **Type :** Indicateur métrique (Metric Lens).
   - **Mesure :** `Count of records` (nombre total d'événements).
   - **Résultat :** **20 700** requêtes traitées sur la semaine d'analyse.

2. **Panneau « Taux d'erreur serveur » :**
   - **Type :** Indicateur métrique avec formule personnalisée (Metric Lens).
   - **Formule Lens :**
     ```text
     count(kql='http.response.status_code >= 500') / count()
     ```
   - **Formatage :** Pourcentage avec 2 décimales.
   - **Résultat :** **1,97 %** (soit 407 réponses 5xx sur 20 700 requêtes). Ce taux globalement bas masque en réalité un incident critique concentré dans le temps.

3. **Panneau « Trafic dans le temps » (affiché *Trafic dans le temps par statut HTTP*) :**
   - **Type :** Barres empilées (Stacked Bar Chart Lens).
   - **Axe horizontal (X) :** `@timestamp` découpé en intervalles automatiques / 3 heures.
   - **Axe vertical (Y) :** `Count of records`.
   - **Décomposition (Breakdown) :** `http.response.status_code`.
   - **Analyse visuelle :** Le trafic standard apparaît en vert (code 200) à hauteur d'environ 300 à 450 req / bloc. L'incident du lundi 28 septembre ressort immédiatement sous forme d'un bloc distinctif culminant à 402 réponses `503`.

4. **Panneau « Offres les plus consultées » :**
   - **Type :** Tableau (Data Table Lens).
   - **Lignes :** Top 10 des valeurs du champ `labels.offre_id`.
   - **Métrique :** `Count of records`.
   - **Résultat :** Met en évidence les annonces attirant le plus grand nombre de candidats (menées par `OFF-04662` avec 8 vues, et `OFF-03141` / `OFF-01153` avec 7 vues).

5. **Panneau « Navigateurs » (affiché *Répartition des navigateurs*) :**
   - **Type :** Anneau (Donut Chart Lens).
   - **Tranches :** Top 5 des valeurs de `user_agent.name`.
   - **Résultat :** Répartition équilibrée entre Mobile Safari (19,8 %), Firefox (19,5 %), Chrome (19,6 %), Chrome Mobile (19,59 %) et Safari desktop (19,6 %). Le scanner `zgrab` ne représente que 1,45 % et se retrouve hors du top 5.

6. **Panneau « Offres par ville » (affiché *Carte des offres par ville*) :**
   - **Type :** Carte interactive (Maps).
   - **Source de données :** Data view `offres`.
   - **Couche géographique :** Points basés sur le champ `localisation` (type `geo_point`).
   - **Visualisation :** Positionnement géographique des 5 000 offres d'emploi sur le territoire métropolitain français (Paris, Lyon, Toulouse, Bordeaux, Lille, Nantes, Montpellier, etc.).

---

### Captures d'écran fournies

1. `captures/tableau-de-bord.png` : Vue d'ensemble nominale du tableau de bord complet (20 700 requêtes, 1,97 % d'erreur, répartition globale).
2. `captures/tableau-de-bord-interactivite.png` : Vue démontrant l'interactivité par clic sur le code `503` (402 requêtes isolées, taux d'erreur à 100 %, panneau de carte titré).

---

### Interactivité et filtrage croisé (Cross-filtering)

L'interactivité du tableau de bord a été validée :
- Un clic direct sur la couleur correspondant au code **`503`** (ou sur le pic du 28 septembre) applique instantanément un filtre global KQL `http.response.status_code: 503` à tous les panneaux.
- **Effets immédiats constatés :**
  - Le panneau « Nombre de requêtes » s'ajuste à **402**.
  - Le panneau « Taux d'erreur serveur » monte à **100 %**.
  - Le tableau « Offres les plus consultées » se vide (car les erreurs 503 ciblaient les endpoints d'API généraux `/api/offres?...` et non des pages de fiches d'offres individuelles comportant un `labels.offre_id`).

---

### Question Bonus — Règle d'alerte (Alerting Kibana)

1. **Pourquoi la règle d'alerte ne se déclenche-t-elle pas sur ces logs ?**
   - Le moteur d'alerte de Kibana (*Kibana Alerting Framework*) est conçu pour la supervision en production temps réel. Il planifie des requêtes périodiques en interrogeant une fenêtre temporelle glissante par rapport à l'heure système courante : **`now - 5m` à `now`**.
   - Dans le cadre de ce TP, le jeu de données généré est historique (les événements sont datés du **23 au 30 septembre 2026**). Au moment où la règle tourne aujourd'hui, elle filtre sur l'intervalle `[now - 5 minutes ; now]` qui ne contient aucun document. La condition `count >= 50` évalue donc toujours `0` et l'alerte reste silencieuse.

2. **Comment testeriez-vous cette règle d'alerte ?**
   - **Procédure de test :**
     1. Injecter dans le flux de logs une salve d'événements factices portant l'horodatage courant de la machine. Par exemple, avec un script bash ou curl qui génère 60 lignes avec la date du jour `$(date "+%d/%b/%Y:%H:%M:%S %z")` et un code HTTP `503` :
        ```bash
        for i in {1..60}; do
          echo "192.168.1.1 - - [$(date '+%d/%b/%Y:%H:%M:%S %z')] \"GET /api/offres HTTP/1.1\" 503 124 \"-\" \"curl/8.0\"" >> data/access.log
        done
        ```
     2. Logstash lit ces nouvelles lignes via le pipeline `web`, les transforme et les indexe dans `logs-web-default` avec un `@timestamp` compris dans les 5 dernières minutes.
     3. Au cycle suivant d'évaluation (ex: 1 minute plus tard), la règle détecte 60 erreurs `5xx` dans la fenêtre `now-5m`, franchit le seuil de 50 et déclenche l'action configurée (*Server log* écrivant dans les journaux de Kibana ou envoi d'une notification).

---

### Synthèse de restitution — Rapport d'incident pour l'équipe d'exploitation

**Destinataire :** Équipe d'exploitation & Production  
**Objet :** Rapport post-mortem — Incident de production du 28/09/2026

#### 1. Chronologie et détection
- **Début de l'incident :** Lundi 28 septembre 2026 à 14h00 locale (12:00:00 UTC).
- **Fin de l'incident :** Lundi 28 septembre 2026 à 14h45 locale (12:45:00 UTC).
- **Durée totale :** 45 minutes consécutives.
- **Volume d'impact :** **402 requêtes en échec critique HTTP 503 (Service Unavailable)**.

#### 2. Périmètre et surface touchée
- **Composant défaillant :** L'API backend de recherche d'offres (`/api/offres?ville=...&page=...`).
- **Services non impactés :** La consultation des pages d'accueil, les fiches détaillées d'offres (`/offres/OFF-...`) et les assets statiques sont restés 100 % opérationnels.
- **Comportement des clients :** Les applications et navigateurs ont déclenché des boucles de réessai automatique (*retries*), maintenant une charge constante d'environ 45 requêtes par tranche de 5 minutes sur l'API sans engorger le réseau.

#### 3. Incident de sécurité collatéral (Activité suspecte)
- En amont de l'incident, le samedi 26 septembre à 03h12 (heure locale), un scanner automatisé (`203.0.113.66`, User-Agent `Mozilla/5.0 zgrab/0.x`) a conduit une attaque de reconnaissance de 5 minutes (300 requêtes 404 à 1 req/s) ciblant des chemins sensibles (`/.env`, `/.git/config`, `/admin`, `/wp-login.php`, `/phpmyadmin/`).
- **Conclusion sécurité :** Aucun fichier sensible n'a été divulgué (toutes les requêtes ont été rejetées en 404).

#### 4. Recommandations et actions correctives
1. **Supervision & Alerting :** Déployer la règle d'alerte Kibana seuil 5xx (> 50 erreurs / 5 min) connectée au canal d'astreinte (Slack/PagerDuty) pour réduire le temps de détection (MTTD) de 45 minutes à moins de 5 minutes.
2. **Résilience backend :** Mettre en place un circuit-breaker et un cache intermédiaire sur l'endpoint `/api/offres` pour éviter l'indisponibilité totale en cas de panne temporaire du service sous-jacent.
3. **Sécurité périmétrique :** Bloquer au niveau du WAF / reverse-proxy les signatures de scanners de vulnérabilités (`zgrab`) et le probing des fichiers cachés (`/.env`, `/.git`).
