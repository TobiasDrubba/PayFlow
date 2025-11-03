from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.data.repositories.payment_repository import SessionLocal
from app.domain.services.auth_service import get_current_user
from app.integrations.mail_service import (
    remove_mailgun_cached_file_for_user,  # <-- new import
)
from app.integrations.mail_service import (
    cache_mailgun_form_attachments,
    get_mailgun_cached_files_for_user,
    import_cached_mailgun_zips,
)

router = APIRouter(prefix="/api/mailgun", tags=["mailgun"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/inbound")
async def mailgun_inbound_endpoint(request: Request):
    """
    Endpoint to receive Mailgun inbound POSTs containing encrypted zip attachments.
    Delegates processing and caching to the service layer.
    """
    form = await request.form()
    try:
        username, saved = cache_mailgun_form_attachments(form)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "status": "cached",
        "username": username,
        "cached_files": len(saved),
    }


@router.get("/cache")
def get_mailgun_cached_files(current_user=Depends(get_current_user)):
    """
    Return cached Mailgun attachments for the authenticated user.
    Delegates retrieval to the service layer.
    """
    return get_mailgun_cached_files_for_user(current_user)


class MailgunCachedImportItem(BaseModel):
    filename: str
    password: str
    type: str


class MailgunCachedImportRequest(BaseModel):
    items: List[MailgunCachedImportItem]


@router.post("/import_cached")
async def import_cached_mailgun_files(
    req: MailgunCachedImportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Frontend calls this endpoint with a list of {filename, password?, type}.
    Tries to unzip each named cached zip using given password and import files.
    """
    items_as_dicts = [i.model_dump() for i in req.items]
    result = await import_cached_mailgun_zips(items_as_dicts, db, current_user)
    if result.get("imported", 0) == 0 and result.get("errors"):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=400, content={"detail": result["errors"]})
    return result


@router.delete("/cache")
def delete_mailgun_cached_file(
    filename: str = Query(..., description="Filename to remove from cache"),
    current_user=Depends(get_current_user),
):
    """
    Remove a cached mailgun attachment (by filename) for the current user.
    """
    try:
        remove_mailgun_cached_file_for_user(current_user, filename)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"removed": filename}
