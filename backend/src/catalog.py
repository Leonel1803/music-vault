"""Public catalog query handlers."""

from __future__ import annotations

from typing import Any

from .common import (
    ApiError,
    decode_cursor,
    encode_cursor,
    page_size,
    public_item,
    public_items,
    query_parameters,
    response,
    validate_id,
)


_ENTITY_TYPES = ("artists", "albums", "songs")
_ENTITY_PREFIX = {"artists": "ARTIST", "albums": "ALBUM", "songs": "SONG"}


def _normalized(value: str) -> str:
    value = value.strip().casefold()
    if len(value) > 80:
        raise ApiError(400, "VALIDATION_ERROR", "El parámetro q no puede exceder 80 caracteres.")
    return value


def _list_items(table: Any, entity: str, query: dict[str, str]) -> dict[str, Any]:
    limit = page_size(query)
    cursor = decode_cursor(query.get("cursor"))
    q = _normalized(query.get("q", ""))
    if q and len(q) < 2:
        raise ApiError(400, "VALIDATION_ERROR", "El parámetro q requiere al menos 2 caracteres.")

    if entity == "songs" and query.get("genre"):
        genre = _normalized(query["genre"])
        if not genre or len(genre) > 60:
            raise ApiError(400, "VALIDATION_ERROR", "El parámetro genre no es válido.")
        kwargs: dict[str, Any] = {
            "IndexName": "GSI1",
            "KeyConditionExpression": "GSI1PK = :pk",
            "ExpressionAttributeValues": {
                ":pk": f"GENRE#{genre}",
            },
            "Limit": limit,
        }
        if q:
            kwargs["KeyConditionExpression"] += " AND begins_with(GSI1SK, :prefix)"
            kwargs["ExpressionAttributeValues"][":prefix"] = q
    else:
        kwargs = {
            "IndexName": "GSI1",
            "KeyConditionExpression": "GSI1PK = :pk",
            "ExpressionAttributeValues": {":pk": f"ENTITY#{_ENTITY_PREFIX[entity]}"},
            "Limit": limit,
        }
        if q:
            kwargs["KeyConditionExpression"] += " AND begins_with(GSI1SK, :prefix)"
            kwargs["ExpressionAttributeValues"][":prefix"] = q
    if cursor:
        kwargs["ExclusiveStartKey"] = cursor
    result = table.query(**kwargs)
    return {
        "items": public_items(result.get("Items", [])),
        "nextCursor": encode_cursor(result.get("LastEvaluatedKey")),
    }


def _list_partition(table: Any, partition: str, prefix: str, query: dict[str, str]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
        "ExpressionAttributeValues": {":pk": partition, ":prefix": prefix},
        "Limit": page_size(query),
    }
    cursor = decode_cursor(query.get("cursor"))
    if cursor:
        kwargs["ExclusiveStartKey"] = cursor
    result = table.query(**kwargs)
    return {
        "items": public_items(result.get("Items", [])),
        "nextCursor": encode_cursor(result.get("LastEvaluatedKey")),
    }


# (collection, child segment) -> (partition prefix, sort-key prefix)
_RELATIONS = {
    ("artists", "albums"): ("ARTIST", "ALBUM#"),
    ("albums", "songs"): ("ALBUM", "SONG#"),
    ("songs", "reviews"): ("SONG", "REVIEW#"),
}


def handle_catalog(event: dict[str, Any], table: Any, metrics: Any = None) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    segments = [part for part in path.strip("/").split("/") if part]
    query = query_parameters(event)

    if len(segments) == 1 and segments[0] in _ENTITY_TYPES and method == "GET":
        if segments[0] != "songs" and "genre" in query:
            raise ApiError(400, "VALIDATION_ERROR", "genre solo aplica al catálogo de canciones.")
        return response(200, _list_items(table, segments[0], query))

    if len(segments) == 2 and segments[0] in _ENTITY_TYPES and method == "GET":
        entity, entity_id = segments
        safe_id = validate_id(entity_id, f"{entity[:-1]}Id")
        result = table.get_item(
            Key={"PK": f"{_ENTITY_PREFIX[entity]}#{safe_id}", "SK": "METADATA"}
        )
        item = result.get("Item")
        if not item:
            raise ApiError(404, "NOT_FOUND", "No se encontró el recurso solicitado.")
        return response(200, {"item": public_item(item)})

    if len(segments) == 3 and method == "GET" and (segments[0], segments[2]) in _RELATIONS:
        partition_prefix, sort_prefix = _RELATIONS[(segments[0], segments[2])]
        parent_id = validate_id(segments[1], f"{segments[0][:-1]}Id")
        return response(200, _list_partition(table, f"{partition_prefix}#{parent_id}", sort_prefix, query))

    if len(segments) == 1 and segments[0] == "search" and method == "GET":
        q = _normalized(query.get("q", ""))
        if len(q) < 2:
            raise ApiError(400, "VALIDATION_ERROR", "El parámetro q requiere al menos 2 caracteres.")
        limit = page_size(query)
        genre = _normalized(query.get("genre", "")) if query.get("genre") else ""
        results = []
        entity_limit = max(1, (limit + len(_ENTITY_TYPES) - 1) // len(_ENTITY_TYPES))
        for entity in _ENTITY_TYPES:
            partition = f"GENRE#{genre}" if entity == "songs" and genre else (
                f"ENTITY#{_ENTITY_PREFIX[entity]}"
            )
            result = table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :pk AND begins_with(GSI1SK, :prefix)",
                ExpressionAttributeValues={":pk": partition, ":prefix": q},
                Limit=entity_limit,
            )
            for item in result.get("Items", []):
                display_name = item.get("title") or item.get("name") or ""
                results.append({**public_item(item), "entityType": entity, "displayName": display_name})
        return response(200, {"items": results[:limit], "nextCursor": None})

    raise ApiError(404, "NOT_FOUND", "No se encontró la ruta solicitada.")
