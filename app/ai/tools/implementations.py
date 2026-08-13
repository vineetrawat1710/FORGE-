from __future__ import annotations

from uuid import UUID

from app.ai.context.context_builder import AIContext
from app.ai.tools.base import AITool
from app.models.request import Request
from app.models.user import User
from app.services.collection_service import CollectionService
from app.services.environment_service import EnvironmentService
from app.services.execution_service import ExecutionService
from app.services.request_service import RequestService


class ExecuteRequestTool:
    name = "execute_request"

    def __init__(self, execution_service: ExecutionService):
        self.execution_service = execution_service

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]:
        request_id = UUID(str(arguments["request_id"]))
        user_id = UUID(str(context.user["id"]))
        user = User(id=user_id, username=str(context.user.get("username", "ai")), email=f"{user_id.hex}@local", password_hash="ai-tool")
        execution = self.execution_service.execute_sync(user, request_id)
        return execution.model_dump()


class SearchRequestsTool:
    name = "search_requests"

    def __init__(self, request_service: RequestService):
        self.request_service = request_service

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]:
        query = str(arguments.get("query", "")).lower()
        user_id = UUID(str(context.user["id"]))
        return {"requests": [r.name for r in self.request_service.repository.list_by_user(user_id) if query in r.name.lower() or query in r.url.lower()]}


class SearchCollectionsTool:
    name = "search_collections"

    def __init__(self, collection_service: CollectionService):
        self.collection_service = collection_service

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]:
        query = str(arguments.get("query", "")).lower()
        user_id = UUID(str(context.user["id"]))
        return {"collections": [c.name for c in self.collection_service.repository.list_by_user(user_id) if query in c.name.lower()]}


class GenerateDocumentationTool:
    name = "generate_documentation"

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]:
        return {"markdown": f"## {context.request['name'] if context.request else 'Request'}"}


class GenerateCodeTool:
    name = "generate_code"

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]:
        language = str(arguments.get("language", "curl"))
        return {"language": language, "code": f"curl -X {context.request['method']} '{context.request['url']}'" if context.request else ""}


class ExplainResponseTool:
    name = "explain_response"

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]:
        status_code = int(arguments.get("status_code", 0))
        headers = arguments.get("headers") or {}
        body = str(arguments.get("body") or "")
        if status_code == 401:
            if any("www-authenticate" in str(key).lower() for key in headers):
                explanation = "The request was unauthorized and the server returned an authentication challenge."
            else:
                explanation = "The request was unauthorized, likely because credentials or tokens are invalid."
        elif status_code >= 400:
            explanation = "The request failed with a client or server error."
        else:
            explanation = "The response was successful."
        if body and status_code >= 400:
            explanation = f"{explanation} The response body suggests an error was returned."
        return {"explanation": explanation}


class EnvironmentLookupTool:
    name = "environment_lookup"

    def __init__(self, environment_service: EnvironmentService):
        self.environment_service = environment_service

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]:
        key = str(arguments["key"])
        user_id = UUID(str(context.user["id"]))
        environment = self.environment_service.get_active_environment(user_id)
        value = (environment.variables or {}).get(key, {})
        return {"key": key, "value": value.get("value") if isinstance(value, dict) else value}
