"""Authenticated social interactions: favorites, ratings and reviews (Lambda: interactions)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .collection import handle_collection, request_parts
from .common import (
    ApiError,
    Metrics,
    clean_text,
    json_body,
    parse_rating,
    public_item,
    rating_summary,
    response,
    user_sub,
    validate_id,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_song(table: Any, song_id: str) -> None:
    song = table.get_item(Key={"PK": f"SONG#{song_id}", "SK": "METADATA"}).get("Item")
    if not song:
        raise ApiError(404, "NOT_FOUND", "No se encontró la canción solicitada.")


def _adjust_summary(table: Any, song_id: str, total_delta: int, count_delta: int) -> dict[str, Any]:
    result = table.update_item(
        Key={"PK": f"SONG#{song_id}", "SK": "METADATA"},
        UpdateExpression="ADD ratingSum :total, ratingCount :count",
        ExpressionAttributeValues={":total": total_delta, ":count": count_delta},
        ConditionExpression="attribute_exists(PK)",
        ReturnValues="UPDATED_NEW",
    )
    attributes = result.get("Attributes", {})
    return rating_summary(attributes.get("ratingSum"), attributes.get("ratingCount"))


def _rating(method: str, event: dict[str, Any], table: Any, sub: str, song_id: str, metrics: Metrics | None) -> dict[str, Any]:
    key = {"PK": f"SONG#{song_id}", "SK": f"RATING#{sub}"}
    if method == "GET":
        item = table.get_item(Key=key).get("Item")
        return response(200, {"item": public_item(item) if item else None})
    if method == "PUT":
        rating = parse_rating(json_body(event).get("rating"))
        _require_song(table, song_id)
        previous = table.put_item(
            Item={**key, "songId": song_id, "rating": rating, "updatedAt": _now()},
            ReturnValues="ALL_OLD",
        ).get("Attributes")
        old_rating = int(previous["rating"]) if previous else 0
        summary = _adjust_summary(table, song_id, rating - old_rating, 0 if previous else 1)
        if metrics:
            metrics.contribution()
        return response(200, {"item": {"songId": song_id, "rating": rating}, **summary})
    if method == "DELETE":
        previous = table.delete_item(Key=key, ReturnValues="ALL_OLD").get("Attributes")
        if previous:
            _adjust_summary(table, song_id, -int(previous["rating"]), -1)
        return response(204, {})
    raise ApiError(404, "NOT_FOUND", "No se encontró la ruta solicitada.")


def _review(method: str, event: dict[str, Any], table: Any, sub: str, song_id: str, metrics: Metrics | None) -> dict[str, Any]:
    key = {"PK": f"SONG#{song_id}", "SK": f"REVIEW#{sub}"}
    if method == "GET":
        item = table.get_item(Key=key).get("Item")
        return response(200, {"item": public_item(item) if item else None})
    if method == "PUT":
        body = json_body(event)
        text = clean_text(body.get("text"), "text", min_length=1, max_length=1000)
        author = clean_text(body.get("authorName") or "Anónimo", "authorName", min_length=1, max_length=40)
        _require_song(table, song_id)
        now = _now()
        result = table.update_item(
            Key=key,
            UpdateExpression=(
                "SET songId = :song, #text = :text, authorName = :author, "
                "updatedAt = :now, createdAt = if_not_exists(createdAt, :now)"
            ),
            ExpressionAttributeNames={"#text": "text"},
            ExpressionAttributeValues={":song": song_id, ":text": text, ":author": author, ":now": now},
            ReturnValues="ALL_NEW",
        )
        if metrics:
            metrics.contribution()
        return response(200, {"item": public_item(result["Attributes"])})
    if method == "DELETE":
        table.delete_item(Key=key)
        return response(204, {})
    raise ApiError(404, "NOT_FOUND", "No se encontró la ruta solicitada.")


def handle_interactions(event: dict[str, Any], table: Any, metrics: Metrics | None = None) -> dict[str, Any]:
    method, segments, query = request_parts(event)
    sub = user_sub(event)
    if len(segments) < 2 or segments[0] != "me":
        raise ApiError(404, "NOT_FOUND", "No se encontró la ruta solicitada.")
    resource = segments[1]

    if resource == "favorites":
        return handle_collection(method, segments, table, sub, query, "FAVORITE")
    if resource in ("ratings", "reviews") and len(segments) == 3:
        song_id = validate_id(segments[2], "songId")
        handler = _rating if resource == "ratings" else _review
        return handler(method, event, table, sub, song_id, metrics)
    raise ApiError(404, "NOT_FOUND", "No se encontró la ruta solicitada.")
