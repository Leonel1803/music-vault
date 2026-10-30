"""Shared logic for per-user song collections (favorites and library)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .common import (
    ApiError,
    decode_cursor,
    encode_cursor,
    page_size,
    public_items,
    query_parameters,
    response,
    validate_id,
)


def handle_collection(
    method: str,
    segments: list[str],
    table: Any,
    sub: str,
    query: dict[str, str],
    kind: str,
) -> dict[str, Any]:
    """Serve /me/<collection> and /me/<collection>/{songId} for one collection kind."""
    if len(segments) == 2 and method == "GET":
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :prefix)",
            "ExpressionAttributeValues": {":pk": f"USER#{sub}", ":prefix": f"{kind}#"},
            "Limit": page_size(query),
        }
        cursor = decode_cursor(query.get("cursor"))
        if cursor:
            kwargs["ExclusiveStartKey"] = cursor
        result = table.query(**kwargs)
        return response(200, {
            "items": public_items(result.get("Items", [])),
            "nextCursor": encode_cursor(result.get("LastEvaluatedKey")),
        })

    if len(segments) == 3:
        song_id = validate_id(segments[2], "songId")
        key = {"PK": f"USER#{sub}", "SK": f"{kind}#{song_id}"}
        if method == "PUT":
            song = table.get_item(Key={"PK": f"SONG#{song_id}", "SK": "METADATA"}).get("Item")
            if not song:
                raise ApiError(404, "NOT_FOUND", "No se encontró la canción solicitada.")
            table.put_item(Item={
                **key,
                "songId": song_id,
                "title": song.get("title", ""),
                "artistName": song.get("artistName", ""),
                "albumTitle": song.get("albumTitle", ""),
                "genre": song.get("genre", ""),
                "createdAt": datetime.now(timezone.utc).isoformat(),
            })
            return response(204, {})
        if method == "DELETE":
            table.delete_item(Key=key)
            return response(204, {})
    raise ApiError(404, "NOT_FOUND", "No se encontró la ruta solicitada.")


def request_parts(event: dict[str, Any]) -> tuple[str, list[str], dict[str, str]]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    segments = [part for part in event.get("rawPath", "").strip("/").split("/") if part]
    return method, segments, query_parameters(event)
