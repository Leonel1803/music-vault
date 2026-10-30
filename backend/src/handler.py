"""AWS Lambda entry points for API Gateway HTTP API v2."""

from __future__ import annotations

import os
import time
from typing import Any

from .catalog import handle_catalog
from .common import ApiError, Metrics, emit_metrics, error_response, log, response
from .interactions import handle_interactions
from .library import handle_library


def _table() -> Any:
    import boto3

    table_name = os.environ.get("TABLE_NAME")
    if not table_name:
        raise RuntimeError("TABLE_NAME is required")
    return boto3.resource("dynamodb").Table(table_name)


def catalog_lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return _run(event, context, handle_catalog, "catalog")


def interactions_lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return _run(event, context, handle_interactions, "interactions")


def library_lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return _run(event, context, handle_library, "library")


def _run(event: dict[str, Any], context: Any, handler: Any, service: str) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", "unknown")
    route = event.get("requestContext", {}).get("routeKey", "unknown")
    metrics = Metrics()
    started = time.perf_counter()
    try:
        result = handler(event, _table(), metrics)
    except ApiError as error:
        log("warning", "request_rejected", requestId=request_id, service=service,
            route=route, code=error.code)
        result = error_response(error)
    except Exception as error:
        log("error", "request_failed", requestId=request_id, service=service,
            route=route, errorType=type(error).__name__)
        result = response(500, {
            "error": {"code": "INTERNAL_ERROR", "message": "Ocurrió un error interno."}
        })
    else:
        log("info", "request_completed", requestId=request_id, service=service,
            route=route, statusCode=result["statusCode"])
    emit_metrics(
        service,
        status_code=result["statusCode"],
        latency_ms=(time.perf_counter() - started) * 1000,
        contributions=metrics.contributions,
    )
    return result
