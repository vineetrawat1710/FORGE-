from __future__ import annotations

import shlex
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from app.core.exceptions import ImportParseError, ImportValidationError
from app.utils.postman_parser import ParsedRequest


def parse_curl_command(content: str) -> ParsedRequest:
    try:
        tokens = shlex.split(content, posix=True)
    except ValueError as exc:
        raise ImportParseError("Invalid cURL command.") from exc
    if not tokens or tokens[0] != "curl":
        raise ImportValidationError("Input must start with curl.")

    method = "GET"
    url = None
    headers = []
    body = None
    auth = None

    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token in {"-X", "--request"} and i + 1 < len(tokens):
            method = tokens[i + 1].upper()
            i += 2
            continue
        if token in {"-H", "--header"} and i + 1 < len(tokens):
            header = tokens[i + 1]
            if ":" in header:
                key, value = header.split(":", 1)
                headers.append({"key": key.strip(), "value": value.strip(), "enabled": True})
                if key.lower() == "authorization":
                    auth = {"type": "bearer", "token": value.strip().removeprefix("Bearer ").strip()}
            i += 2
            continue
        if token in {"-d", "--data", "--data-raw", "--data-binary", "--data-ascii"} and i + 1 < len(tokens):
            body = {"mode": "raw", "raw": tokens[i + 1]}
            if method == "GET":
                method = "POST"
            i += 2
            continue
        if token.startswith("http://") or token.startswith("https://"):
            url = token
            i += 1
            continue
        i += 1

    if url is None:
        raise ImportValidationError("cURL command must include a URL.")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ImportValidationError("Only http and https URLs are supported.")
    query_parameters = [{"key": key, "value": value, "enabled": True} for key, value in parse_qsl(parsed.query, keep_blank_values=True)]
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", parsed.fragment))
    return ParsedRequest(
        name=f"{method} {parsed.path or '/'}",
        method=method,
        url=clean_url,
        headers=headers,
        query_parameters=query_parameters,
        body=body,
        authorization=auth,
        description=None,
    )
