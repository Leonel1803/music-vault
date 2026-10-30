"""Authenticated personal library handlers (Lambda: library)."""

from __future__ import annotations

from typing import Any

from .collection import handle_collection, request_parts
from .common import ApiError, Metrics, user_sub


def handle_library(event: dict[str, Any], table: Any, metrics: Metrics | None = None) -> dict[str, Any]:
    method, segments, query = request_parts(event)
    sub = user_sub(event)
    if len(segments) < 2 or segments[0] != "me" or segments[1] != "library":
        raise ApiError(404, "NOT_FOUND", "No se encontró la ruta solicitada.")
    return handle_collection(method, segments, table, sub, query, "LIBRARY")
