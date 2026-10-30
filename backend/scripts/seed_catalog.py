"""Load fictional starter catalog records into a development DynamoDB table."""

from __future__ import annotations

import argparse
import os
import re
from datetime import date
from typing import Any


STARTER_DATA = [
    {
        "id": "artist-marea",
        "name": "Marea Norte",
        "albumId": "album-luz",
        "albumTitle": "Luz de Fondo",
        "songId": "song-ventana",
        "title": "Ventana Abierta",
        "genre": "indie",
        "durationSeconds": 214,
    },
    {
        "id": "artist-cobalto",
        "name": "Cobalto Azul",
        "albumId": "album-ciudad",
        "albumTitle": "Ciudad Lenta",
        "songId": "song-domingo",
        "title": "Domingo Eléctrico",
        "genre": "electronic",
        "durationSeconds": 198,
    },
    {
        "id": "artist-lumbre",
        "name": "Lumbre Trío",
        "albumId": "album-patio",
        "albumTitle": "Patio Interior",
        "songId": "song-patio",
        "title": "Patio Interior",
        "genre": "jazz",
        "durationSeconds": 242,
    },
]


try:
    from catalog_data import expand
except ImportError:  # cuando se importa como paquete
    from scripts.catalog_data import expand

STARTER_DATA = STARTER_DATA + expand()


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def records(data_set: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for data in data_set or STARTER_DATA:
        artist = {
            "PK": f"ARTIST#{data['id']}",
            "SK": "METADATA",
            "id": data["id"],
            "name": data["name"],
            "GSI1PK": "ENTITY#ARTIST",
            "GSI1SK": f"{normalize(data['name'])}#{data['id']}",
        }
        album = {
            "PK": f"ALBUM#{data['albumId']}",
            "SK": "METADATA",
            "id": data["albumId"],
            "title": data["albumTitle"],
            "artistId": data["id"],
            "artistName": data["name"],
            "releaseDate": date(2024, 1, 1).isoformat(),
            "GSI1PK": "ENTITY#ALBUM",
            "GSI1SK": f"{normalize(data['albumTitle'])}#{data['albumId']}",
        }
        song = {
            "PK": f"SONG#{data['songId']}",
            "SK": "METADATA",
            "id": data["songId"],
            "title": data["title"],
            "artistId": data["id"],
            "artistName": data["name"],
            "albumId": data["albumId"],
            "albumTitle": data["albumTitle"],
            "genre": data["genre"],
            "durationSeconds": data["durationSeconds"],
            "GSI1PK": "ENTITY#SONG",
            "GSI1SK": f"{normalize(data['title'])}#{data['songId']}",
        }
        genre_relation = {
            "PK": f"GENRE#{normalize(data['genre'])}",
            "SK": f"SONG#{data['songId']}",
            "GSI1PK": f"GENRE#{normalize(data['genre'])}",
            "GSI1SK": f"{normalize(data['title'])}#{data['songId']}",
            "id": data["songId"],
            "songId": data["songId"],
            "title": data["title"],
            "artistName": data["name"],
            "albumTitle": data["albumTitle"],
            "genre": data["genre"],
        }
        items.extend([artist, album, song, genre_relation])
    return items


def relations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows that let the API list an artist's albums and an album's songs by partition."""
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        if item["SK"] != "METADATA":
            continue
        if item["PK"].startswith("ALBUM#"):
            rows[(f"ARTIST#{item['artistId']}", f"ALBUM#{item['id']}")] = {
                "PK": f"ARTIST#{item['artistId']}",
                "SK": f"ALBUM#{item['id']}",
                "id": item["id"],
                "title": item["title"],
                "artistId": item["artistId"],
                "artistName": item["artistName"],
                "releaseDate": item.get("releaseDate", ""),
            }
        elif item["PK"].startswith("SONG#"):
            rows[(f"ALBUM#{item['albumId']}", f"SONG#{item['id']}")] = {
                "PK": f"ALBUM#{item['albumId']}",
                "SK": f"SONG#{item['id']}",
                **{key: item[key] for key in (
                    "id", "title", "artistId", "artistName", "albumId",
                    "albumTitle", "genre", "durationSeconds") if key in item},
            }
    return list(rows.values())


def load_data(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return STARTER_DATA
    import json

    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", default=os.environ.get("TABLE_NAME"))
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2",
    )
    parser.add_argument(
        "--data",
        help="Ruta de un JSON con una lista de objetos como STARTER_DATA (artista, álbum y canción por fila).",
    )
    args = parser.parse_args()
    if not args.table:
        parser.error("Indica --table o define TABLE_NAME.")

    import boto3

    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)
    base = records(load_data(args.data))
    rows = base + relations(base)
    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for item in rows:
            batch.put_item(Item=item)
    print(f"Se cargaron {len(rows)} elementos de catálogo en {args.table}.")


if __name__ == "__main__":
    main()
