from uuid import UUID

import json

from fastapi import APIRouter, Depends, Body, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.import_export import ExportResponse, ImportSummary
from app.schemas.user import UserResponse
from app.services.import_export_service import ImportExportService

router = APIRouter(prefix="/api/v1", tags=["import-export"])


@router.post("/import/postman", response_model=ImportSummary, status_code=status.HTTP_201_CREATED)
def import_postman(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
    content: str = Body(...),
    collection_name: str | None = Body(default=None),
) -> ImportSummary:
    return ImportExportService(db).import_postman(current_user, content, collection_name=collection_name)


@router.post("/import/openapi", response_model=ImportSummary, status_code=status.HTTP_201_CREATED)
def import_openapi(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
    content: str = Body(...),
    collection_name: str | None = Body(default=None),
) -> ImportSummary:
    return ImportExportService(db).import_openapi(current_user, content, collection_name=collection_name)


@router.post("/import/curl", response_model=ImportSummary, status_code=status.HTTP_201_CREATED)
def import_curl(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
    content: str = Body(...),
    collection_id: UUID | None = Body(default=None),
) -> ImportSummary:
    return ImportExportService(db).import_curl(current_user, content, collection_id=collection_id)


@router.get("/export/postman/{collection_id}", response_model=ExportResponse)
def export_postman(
    collection_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportResponse:
    payload = ImportExportService(db).export_postman(current_user, collection_id)
    return ExportResponse(format="postman", filename=f"{collection_id}.postman.json", content=json.dumps(payload, indent=2))


@router.get("/export/openapi/{collection_id}", response_model=ExportResponse)
def export_openapi(
    collection_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportResponse:
    payload = ImportExportService(db).export_openapi(current_user, collection_id)
    return ExportResponse(format="openapi", filename=f"{collection_id}.openapi.json", content=json.dumps(payload, indent=2))


@router.get("/export/curl/{request_id}", response_model=ExportResponse)
def export_curl(
    request_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportResponse:
    content = ImportExportService(db).export_curl(current_user, request_id)
    return ExportResponse(format="curl", filename=f"{request_id}.sh", content=content)
