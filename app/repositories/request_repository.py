from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.request import Request, RequestAuthorization, RequestExecutionHistory, RequestHeader, RequestQueryParameter


class RequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, request: Request) -> Request:
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_by_id(self, request_id: UUID) -> Request | None:
        stmt = (
            select(Request)
            .options(selectinload(Request.headers), selectinload(Request.query_parameters), selectinload(Request.authorization))
            .where(Request.id == request_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_history_item(self, history_id: UUID) -> RequestExecutionHistory | None:
        stmt = select(RequestExecutionHistory).where(RequestExecutionHistory.id == history_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_user(self, user_id: UUID) -> list[Request]:
        stmt = select(Request).where(Request.user_id == user_id).order_by(Request.created_at.desc())
        return list(self.db.execute(stmt).scalars())

    def delete(self, request: Request) -> None:
        self.db.delete(request)
        self.db.commit()

    def add_headers(self, request_id: UUID, headers: list[RequestHeader]) -> None:
        for header in headers:
            header.request_id = request_id
            self.db.add(header)
        self.db.commit()

    def add_query_parameters(self, request_id: UUID, query_parameters: list[RequestQueryParameter]) -> None:
        for query_parameter in query_parameters:
            query_parameter.request_id = request_id
            self.db.add(query_parameter)
        self.db.commit()

    def set_authorization(self, request_id: UUID, authorization: RequestAuthorization | None) -> None:
        if authorization is not None:
            authorization.request_id = request_id
            self.db.add(authorization)
        self.db.commit()

    def replace_headers(self, request_id: UUID, headers: list[RequestHeader]) -> None:
        self.db.execute(delete(RequestHeader).where(RequestHeader.request_id == request_id))
        for header in headers:
            header.request_id = request_id
            self.db.add(header)
        self.db.commit()

    def replace_query_parameters(self, request_id: UUID, query_parameters: list[RequestQueryParameter]) -> None:
        self.db.execute(delete(RequestQueryParameter).where(RequestQueryParameter.request_id == request_id))
        for query_parameter in query_parameters:
            query_parameter.request_id = request_id
            self.db.add(query_parameter)
        self.db.commit()

    def replace_authorization(self, request_id: UUID, authorization: RequestAuthorization | None) -> None:
        self.db.execute(delete(RequestAuthorization).where(RequestAuthorization.request_id == request_id))
        if authorization is not None:
            authorization.request_id = request_id
            self.db.add(authorization)
        self.db.commit()

    def create_history(self, history: RequestExecutionHistory) -> RequestExecutionHistory:
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def list_history(
        self,
        request_id: UUID,
        search: str | None = None,
        status_code: int | None = None,
        execution_status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RequestExecutionHistory], int]:
        stmt = select(RequestExecutionHistory).where(RequestExecutionHistory.request_id == request_id)
        count_stmt = select(func.count()).select_from(RequestExecutionHistory).where(RequestExecutionHistory.request_id == request_id)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(RequestExecutionHistory.error.ilike(pattern) | RequestExecutionHistory.response_snapshot.ilike(pattern))
            count_stmt = count_stmt.where(RequestExecutionHistory.error.ilike(pattern) | RequestExecutionHistory.response_snapshot.ilike(pattern))
        if status_code is not None:
            stmt = stmt.where(RequestExecutionHistory.status_code == status_code)
            count_stmt = count_stmt.where(RequestExecutionHistory.status_code == status_code)
        if execution_status:
            stmt = stmt.where(RequestExecutionHistory.execution_status == execution_status)
            count_stmt = count_stmt.where(RequestExecutionHistory.execution_status == execution_status)
        total = self.db.execute(count_stmt).scalar_one()
        items = list(self.db.execute(stmt.order_by(RequestExecutionHistory.executed_at.desc()).limit(limit).offset(offset)).scalars())
        return items, total

    def list_global_history(
        self,
        user_id: UUID,
        search: str | None = None,
        methods: list[str] | None = None,
        status_classes: list[str] | None = None,
        duration_min: int | None = None,
        duration_max: int | None = None,
        date_min: datetime | None = None,
        collection_id: UUID | None = None,
        environment_id: UUID | None = None,
        execution_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RequestExecutionHistory], int]:
        stmt = select(RequestExecutionHistory).where(RequestExecutionHistory.user_id == user_id)
        count_stmt = select(func.count()).select_from(RequestExecutionHistory).where(RequestExecutionHistory.user_id == user_id)
        
        # If filtering by collection_id or environment_id, we need to join with Request
        # Note: If the request was deleted, it won't match these filters, which is expected.
        if collection_id or environment_id:
            stmt = stmt.outerjoin(Request, RequestExecutionHistory.request_id == Request.id)
            count_stmt = count_stmt.outerjoin(Request, RequestExecutionHistory.request_id == Request.id)
            
            if collection_id:
                stmt = stmt.where(Request.collection_id == collection_id)
                count_stmt = count_stmt.where(Request.collection_id == collection_id)
            if environment_id:
                stmt = stmt.where(Request.environment_id == environment_id)
                count_stmt = count_stmt.where(Request.environment_id == environment_id)

        if methods and len(methods) > 0:
            method_conditions = []
            for method in methods:
                # Use ILIKE to support both Postgres and SQLite without database-specific JSON functions or casting Text columns
                method_conditions.append(RequestExecutionHistory.request_snapshot.ilike(f'%"method": "{method}"%'))
                method_conditions.append(RequestExecutionHistory.request_snapshot.ilike(f'%"method":"{method}"%'))
            
            if method_conditions:
                stmt = stmt.where(or_(*method_conditions))
                count_stmt = count_stmt.where(or_(*method_conditions))

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                RequestExecutionHistory.error.ilike(pattern) | 
                RequestExecutionHistory.request_snapshot.ilike(pattern) | 
                RequestExecutionHistory.response_snapshot.ilike(pattern)
            )
            count_stmt = count_stmt.where(
                RequestExecutionHistory.error.ilike(pattern) | 
                RequestExecutionHistory.request_snapshot.ilike(pattern) | 
                RequestExecutionHistory.response_snapshot.ilike(pattern)
            )
            
        if status_classes and len(status_classes) > 0:
            status_conditions = []
            for status_class in status_classes:
                if status_class == '2xx':
                    status_conditions.append(RequestExecutionHistory.status_code.between(200, 299))
                elif status_class == '3xx':
                    status_conditions.append(RequestExecutionHistory.status_code.between(300, 399))
                elif status_class == '4xx':
                    status_conditions.append(RequestExecutionHistory.status_code.between(400, 499))
                elif status_class == '5xx':
                    status_conditions.append(RequestExecutionHistory.status_code.between(500, 599))
                elif status_class == 'failed':
                    status_conditions.append(RequestExecutionHistory.execution_status == 'failed')
            if status_conditions:
                stmt = stmt.where(or_(*status_conditions))
                count_stmt = count_stmt.where(or_(*status_conditions))
                
        if duration_min is not None:
            stmt = stmt.where(RequestExecutionHistory.duration_ms >= duration_min)
            count_stmt = count_stmt.where(RequestExecutionHistory.duration_ms >= duration_min)
            
        if duration_max is not None:
            stmt = stmt.where(RequestExecutionHistory.duration_ms <= duration_max)
            count_stmt = count_stmt.where(RequestExecutionHistory.duration_ms <= duration_max)
            
        if date_min is not None:
            stmt = stmt.where(RequestExecutionHistory.executed_at >= date_min)
            count_stmt = count_stmt.where(RequestExecutionHistory.executed_at >= date_min)
            
        if execution_status:
            stmt = stmt.where(RequestExecutionHistory.execution_status == execution_status)
            count_stmt = count_stmt.where(RequestExecutionHistory.execution_status == execution_status)
            
        total = self.db.execute(count_stmt).scalar_one()
        items = list(self.db.execute(stmt.order_by(RequestExecutionHistory.executed_at.desc()).limit(limit).offset(offset)).scalars())
        return items, total
