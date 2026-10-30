"""Shared HTTP API, validation, and logging helpers."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


_LOGGER = logging.getLogger("music_vault")
_LOGGER.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class ApiError(Exception):
    """An expected error that can safely be returned to an API caller."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def log(level: str, message: str, **fields: Any) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
        **fields,
    }
    getattr(_LOGGER, level.lower())(json.dumps(record, separators=(",", ":"), default=str))


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store",
        },
        "body": "" if status_code == 204 else json.dumps(body, ensure_ascii=False, default=_json_default),
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return str(value)


def error_response(error: ApiError) -> dict[str, Any]:
    return response(error.status_code, {
        "error": {"code": error.code, "message": error.message}
    })


def validate_id(value: str | None, name: str = "id") -> str:
    if not value or not _ID_PATTERN.fullmatch(value):
        raise ApiError(400, "VALIDATION_ERROR", f"El parámetro {name} no es válido.")
    return value


def page_size(query: dict[str, str]) -> int:
    raw = query.get("limit", str(DEFAULT_PAGE_SIZE))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, "VALIDATION_ERROR", "El parámetro limit debe ser un entero.") from exc
    if not 1 <= value <= MAX_PAGE_SIZE:
        raise ApiError(400, "VALIDATION_ERROR", "El parámetro limit debe estar entre 1 y 100.")
    return value


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        result = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if not isinstance(result, dict) or not result:
            raise ValueError("cursor must be a non-empty object")
        return result
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ApiError(400, "VALIDATION_ERROR", "El parámetro cursor no es válido.") from exc


def encode_cursor(key: dict[str, Any] | None) -> str | None:
    if not key:
        return None
    raw = json.dumps(key, separators=(",", ":"), default=str).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def query_parameters(event: dict[str, Any]) -> dict[str, str]:
    params = event.get("queryStringParameters") or {}
    if not isinstance(params, dict):
        raise ApiError(400, "VALIDATION_ERROR", "Los parámetros de consulta no son válidos.")
    return {str(key): str(value) for key, value in params.items() if value is not None}


def user_sub(event: dict[str, Any]) -> str:
    try:
        claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
        sub = claims.get("sub")
    except (KeyError, TypeError):
        sub = None
    if not isinstance(sub, str) or not sub:
        raise ApiError(401, "UNAUTHORIZED", "Se requiere una sesión válida.")
    return sub

_INTERNAL_KEYS = frozenset({"PK", "SK", "GSI1PK", "GSI1SK"})
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_BODY_BYTES = 8192
METRICS_NAMESPACE = "MusicVault"


def public_item(item: dict[str, Any]) -> dict[str, Any]:
    """Remove DynamoDB key attributes and derive the public rating summary."""
    result = {key: value for key, value in item.items() if key not in _INTERNAL_KEYS}
    total = result.pop("ratingSum", None)
    count = result.pop("ratingCount", None)
    is_song = str(item.get("PK", "")).startswith("SONG#") and item.get("SK") == "METADATA"
    if is_song or count is not None:
        result.update(rating_summary(total, count))
    return result


def rating_summary(total: Any, count: Any) -> dict[str, Any]:
    votes = int(count or 0)
    average = round(float(total or 0) / votes, 1) if votes > 0 else None
    return {"ratingAverage": average, "ratingCount": votes}


def public_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [public_item(item) for item in items]


def json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if not raw:
        raise ApiError(400, "VALIDATION_ERROR", "El cuerpo de la solicitud es obligatorio.")
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise ApiError(400, "VALIDATION_ERROR", "El cuerpo de la solicitud no es válido.") from exc
    if len(raw.encode("utf-8")) > MAX_BODY_BYTES:
        raise ApiError(400, "VALIDATION_ERROR", "El cuerpo de la solicitud es demasiado grande.")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "VALIDATION_ERROR", "El cuerpo debe ser JSON válido.") from exc
    if not isinstance(body, dict):
        raise ApiError(400, "VALIDATION_ERROR", "El cuerpo debe ser un objeto JSON.")
    return body


def clean_text(value: Any, name: str, *, min_length: int, max_length: int) -> str:
    if not isinstance(value, str):
        raise ApiError(400, "VALIDATION_ERROR", f"El campo {name} debe ser texto.")
    text = _CONTROL_CHARS.sub("", value).strip()
    if not min_length <= len(text) <= max_length:
        raise ApiError(
            400,
            "VALIDATION_ERROR",
            f"El campo {name} debe tener entre {min_length} y {max_length} caracteres.",
        )
    return text


def parse_rating(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ApiError(400, "VALIDATION_ERROR", "La calificación debe ser un entero entre 1 y 5.")
    return value


class Metrics:
    """Collects CloudWatch Embedded Metric Format values for one invocation."""

    def __init__(self) -> None:
        self.contributions = 0

    def contribution(self, amount: int = 1) -> None:
        self.contributions += amount


def emit_metrics(
    service: str,
    *,
    status_code: int,
    latency_ms: float,
    contributions: int = 0,
) -> None:
    """Write one EMF record to stdout; CloudWatch turns it into custom metrics."""
    values: dict[str, tuple[float, str]] = {
        "Requests": (1, "Count"),
        "ServerErrors": (1 if status_code >= 500 else 0, "Count"),
        "LatencyMs": (round(latency_ms, 2), "Milliseconds"),
    }
    if contributions:
        values["Contributions"] = (contributions, "Count")
    record: dict[str, Any] = {
        "_aws": {
            "Timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": METRICS_NAMESPACE,
                "Dimensions": [["Service"]],
                "Metrics": [{"Name": name, "Unit": unit} for name, (_, unit) in values.items()],
            }],
        },
        "Service": service,
    }
    record.update({name: value for name, (value, _) in values.items()})
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")