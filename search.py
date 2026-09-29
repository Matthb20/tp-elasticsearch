"""Mini-défi — moteur de recherche d'offres en ligne de commande.

Attendu :
  python search.py "développeur python"
  python search.py "données spark" --ville Lyon --contrat CDI --salaire-min 45000
  python search.py "kubernetes" --autour "43.6108,3.8767" --rayon 50km --teletravail partiel
"""

from __future__ import annotations

import argparse

from es_client import INDEX, get_client


def construire_requete(args: argparse.Namespace) -> dict:
    """Construit une requête bool combinant texte, filtres et distance."""
    must = [
        {
            "multi_match": {
                "query": args.texte,
                "fields": [
                    "titre^3",
                    "competences.texte^2",
                    "description",
                ],
                "fuzziness": "AUTO",
            }
        }
    ]

    filters = []
    if args.ville:
        filters.append({"term": {"ville": args.ville}})
    if args.contrat:
        filters.append({"term": {"contrat": args.contrat}})
    if args.teletravail:
        filters.append({"term": {"teletravail": args.teletravail}})
    if args.salaire_min is not None:
        filters.append({"range": {"salaire_max": {"gte": args.salaire_min}}})
    if args.autour:
        lat_str, lon_str = args.autour.split(",")
        filters.append(
            {
                "geo_distance": {
                    "distance": args.rayon,
                    "localisation": {
                        "lat": float(lat_str.strip()),
                        "lon": float(lon_str.strip()),
                    },
                }
            }
        )

    return {"bool": {"must": must, "filter": filters}}


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("texte")
    p.add_argument("--ville")
    p.add_argument(
        "--contrat",
        choices=["CDI", "CDD", "Alternance", "Freelance", "Stage"],
    )
    p.add_argument("--teletravail", choices=["aucun", "partiel", "total"])
    p.add_argument("--salaire-min", type=int)
    p.add_argument("--autour", help="lat,lon")
    p.add_argument("--rayon", default="30km")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--taille", type=int, default=10)
    args = p.parse_args()

    es = get_client()

    from_ = (args.page - 1) * args.taille
    size = args.taille
    highlight = {"fields": {"description": {}}}
    aggs = {
        "villes": {"terms": {"field": "ville", "size": 5}},
        "contrats": {"terms": {"field": "contrat", "size": 5}},
        "competences": {"terms": {"field": "competences", "size": 5}},
    }

    resp = es.search(
        index=INDEX,
        query=construire_requete(args),
        from_=from_,
        size=size,
        highlight=highlight,
        aggs=aggs,
    )

    total = resp["hits"]["total"]["value"]
    print(f"\n{'=' * 70}")
    print(f"Résultats trouvés : {total} offres (Page {args.page})")
    print(f"{'=' * 70}\n")

    hits = resp["hits"]["hits"]
    if not hits:
        print("Aucune offre ne correspond aux critères demandés.")

    for hit in hits:
        doc = hit["_source"]
        score = hit["_score"]
        salaire = ""
        if "salaire_min" in doc and "salaire_max" in doc:
            salaire = f" | {doc['salaire_min']:,} - {doc['salaire_max']:,} €"

        print(f"[{score:.2f}] {doc['titre']} chez {doc['entreprise']}")
        print(
            f"       {doc['ville']} | {doc['contrat']} | Télétravail : {doc['teletravail']}{salaire}"
        )

        # Extrait surligné
        if "highlight" in hit and "description" in hit["highlight"]:
            snippet = " ... ".join(hit["highlight"]["description"])
            print(f"       Extrait : {snippet}")
        print()

    # Affichage des facettes
    print(f"{'-' * 70}")
    print("Facettes (sur l'ensemble des résultats correspondants) :")
    for nom, bloc in resp.get("aggregations", {}).items():
        buckets = bloc.get("buckets", [])
        valeurs = [f"{b['key']} ({b['doc_count']})" for b in buckets]
        print(f"  * {nom.capitalize()} : {', '.join(valeurs)}")
    print(f"{'-' * 70}\n")


if __name__ == "__main__":
    main()
