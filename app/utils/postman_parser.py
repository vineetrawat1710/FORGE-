from __future__ import annotations

import json
from dataclasses import dataclass, field

import yaml

from app.core.exceptions import ImportParseError, ImportValidationError


@dataclass
class ParsedRequest:
    name: str
    method: str
    url: str
    headers: list[dict[str, str | bool]] = field(default_factory=list)
    query_parameters: list[dict[str, str | bool]] = field(default_factory=list)
    body: dict[str, str] | None = None
    authorization: dict[str, str] | None = None
    description: str | None = None


@dataclass
class ParsedCollection:
    name: str
    description: str | None
    base_url: str | None
    variables: dict[str, dict[str, object]]
    requests: list[ParsedRequest]


def _load_document(content: str) -> dict:
    try:
        if content.lstrip().startswith("{"):
            return json.loads(content)
        return yaml.safe_load(content)
    except Exception as exc:
        raise ImportParseError("Invalid Postman collection document.") from exc


def parse_postman_collection(content: str) -> ParsedCollection:
    doc = _load_document(content)
    info = doc.get("info") or {}
    if not isinstance(info, dict) or "name" not in info:
        raise ImportValidationError("Invalid Postman collection: missing info.name.")
    variables: dict[str, dict[str, object]] = {}
    for item in doc.get("variable", []) or []:
        if not isinstance(item, dict) or "key" not in item:
            continue
        variables[str(item["key"])] = {"value": item.get("value"), "secret": False}

    requests: list[ParsedRequest] = []

    def walk_items(items):
        for item in items or []:
            if "item" in item:
                walk_items(item.get("item"))
                continue
            request = item.get("request") or {}
            url = request.get("url") or {}
            raw_url = url if isinstance(url, str) else url.get("raw")
            if not raw_url:
                continue
            headers = [{"key": h.get("key", ""), "value": h.get("value", ""), "enabled": h.get("disabled") is not True} for h in request.get("header", []) if isinstance(h, dict)]
            query_parameters = []
            if isinstance(url, dict):
                for qp in url.get("query", []) or []:
                    if isinstance(qp, dict) and qp.get("key"):
                        query_parameters.append({"key": qp["key"], "value": qp.get("value", ""), "enabled": qp.get("disabled") is not True})
            body = None
            if isinstance(request.get("body"), dict):
                mode = request["body"].get("mode")
                if mode in {"raw", "urlencoded", "graphql", "file"}:
                    body = {"mode": mode, "raw": request["body"].get("raw", "")}
            auth = None
            if isinstance(request.get("auth"), dict):
                auth = request["auth"]
            requests.append(
                ParsedRequest(
                    name=item.get("name") or "Imported Request",
                    method=str(request.get("method") or "GET").upper(),
                    url=raw_url,
                    headers=headers,
                    query_parameters=query_parameters,
                    body=body,
                    authorization=auth,
                    description=request.get("description") if isinstance(request.get("description"), str) else None,
                )
            )

    walk_items(doc.get("item", []))
    return ParsedCollection(name=info["name"], description=info.get("description"), base_url=None, variables=variables, requests=requests)
