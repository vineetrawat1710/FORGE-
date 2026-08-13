from __future__ import annotations

import json

import yaml

from app.core.exceptions import ImportParseError, ImportValidationError
from app.utils.postman_parser import ParsedCollection, ParsedRequest


def _load_document(content: str) -> dict:
    try:
        if content.lstrip().startswith("{"):
            return json.loads(content)
        return yaml.safe_load(content)
    except Exception as exc:
        raise ImportParseError("Invalid OpenAPI document.") from exc


def parse_openapi_document(content: str) -> ParsedCollection:
    doc = _load_document(content)
    if not isinstance(doc, dict) or "openapi" not in doc or "paths" not in doc:
        raise ImportValidationError("Invalid OpenAPI document.")
    info = doc.get("info") or {}
    title = info.get("title") or "Imported OpenAPI"
    base_url = None
    servers = doc.get("servers") or []
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict):
            base_url = first.get("url")
    requests: list[ParsedRequest] = []
    for path, methods in doc.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, spec in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            if not isinstance(spec, dict):
                continue
            headers = []
            params = []
            for param in spec.get("parameters", []) or []:
                if not isinstance(param, dict) or param.get("name") is None:
                    continue
                target = headers if param.get("in") == "header" else params
                item = {"key": str(param["name"]), "value": str(param.get("example") or ""), "enabled": True}
                target.append(item)
            body = None
            if isinstance(spec.get("requestBody"), dict):
                content_map = spec["requestBody"].get("content") or {}
                if isinstance(content_map, dict) and content_map:
                    media_type = next(iter(content_map))
                    body = {"mode": "raw", "raw": json.dumps(content_map[media_type].get("example", {}))}
            requests.append(
                ParsedRequest(
                    name=spec.get("summary") or spec.get("operationId") or f"{method.upper()} {path}",
                    method=method.upper(),
                    url=path,
                    headers=headers,
                    query_parameters=params,
                    body=body,
                    authorization=None,
                    description=spec.get("description"),
                )
            )
    return ParsedCollection(name=title, description=info.get("description"), base_url=base_url, variables={}, requests=requests)
