import os
import shutil
import tempfile
import zipfile
from datetime import datetime as _dt
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Tuple

from fastapi import UploadFile

# typing for DB session
from sqlalchemy.orm import Session

# reuse existing import logic from payment_service
from app.domain.services.payment_service import import_payment_files_service

# In-memory cache:
# key = username (derived from recipient or sender), value = list of metadata dicts
MAILGUN_ATTACHMENT_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def _derive_username_from_recipient(recipient: Any) -> str:
    if not recipient:
        return "unknown_user"
    primary = str(recipient).split(",")[0].strip()
    username = primary.split("@")[0] if "@" in primary else primary
    username = username.split("+")[0]
    return username


def _derive_cache_username_from_user(current_user: Any) -> str:
    candidate = getattr(current_user, "email", None) or getattr(
        current_user, "username", None
    )
    if candidate:
        s = str(candidate)
        if "@" in s:
            local = s.split(",")[0].strip().split("@")[0]
            return local.split("+")[0]
        return s
    uid = getattr(current_user, "id", None)
    return f"user_{uid}" if uid is not None else "unknown_user"


def cache_mailgun_form_attachments(form) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Process a Mailgun inbound multipart form, persist file attachments to temp files,
    and cache metadata in MAILGUN_ATTACHMENT_CACHE.

    Returns (username, saved_metadata_list).

    Raises ValueError if no attachments found.
    """
    recipient = (
        form.get("recipient") or form.get("to") or form.get("To") or form.get("sender")
    )
    username = _derive_username_from_recipient(recipient)

    saved = []
    for key, value in form.multi_items():
        if hasattr(value, "filename") and value.filename:
            upload: UploadFile = value  # type: ignore
            filename = upload.filename
            try:
                _, ext = os.path.splitext(filename)
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    try:
                        shutil.copyfileobj(upload.file, tmp)
                    finally:
                        try:
                            upload.file.close()
                        except Exception:
                            pass
                    tmp_path = tmp.name

                meta = {
                    "filename": filename,
                    "path": tmp_path,
                    "content_type": getattr(upload, "content_type", None),
                    "received_at": _dt.utcnow(),
                    "mailgun_field": key,
                }
                saved.append(meta)
            except Exception:
                # Continue on individual file errors
                continue

    if not saved:
        raise ValueError("No attachments found in Mailgun POST")

    MAILGUN_ATTACHMENT_CACHE.setdefault(username, []).extend(saved)
    return username, saved


def get_mailgun_cached_files_for_user(current_user: Any) -> Dict[str, Any]:
    """
    Return sanitized cached metadata for a given user object (suitable for frontend).
    Does not expose filesystem paths.
    """
    username = _derive_cache_username_from_user(current_user)
    entries = MAILGUN_ATTACHMENT_CACHE.get(username, [])
    files = []
    for m in entries:
        received = m.get("received_at")
        if not received:
            received = "unknown"
        files.append(
            {
                "filename": m.get("filename"),
                "content_type": m.get("content_type"),
                "received_at": received.isoformat()
                if hasattr(received, "isoformat")
                else str(received),
                "mailgun_field": m.get("mailgun_field"),
            }
        )
    return {"username": username, "cached_files": len(entries), "files": files}


async def import_cached_mailgun_zips(
    items: Iterable[Any], db: Session, current_user: Any
) -> Dict[str, Any]:
    """
    items: iterable of dict-like objects with keys: filename, password (optional), type
    Returns: {"imported": int, "errors": [str,...]}
    """
    username = _derive_cache_username_from_user(current_user)
    errors: List[str] = []
    wrappers: List[Any] = []  # objects with .file and .filename
    types_list: List[str] = []
    tmpdirs: List[str] = []
    processed_cache_entries: List[Dict[str, Any]] = []

    if not items:
        return {"imported": 0, "errors": ["No items provided"]}

    cache_list = MAILGUN_ATTACHMENT_CACHE.get(username, [])

    for raw_item in items:
        # accept plain dicts or Pydantic-like objects (fallback to attribute access)
        if isinstance(raw_item, dict):
            item = raw_item
        else:
            if hasattr(raw_item, "model_dump"):
                item = raw_item.model_dump()
            else:
                item = {
                    "filename": getattr(raw_item, "filename", None),
                    "password": getattr(raw_item, "password", None),
                    "type": getattr(raw_item, "type", None),
                }

        fname = item.get("filename")
        pwd = item.get("password") or ""
        ptype = item.get("type")
        if not fname or not ptype:
            errors.append(f"{fname or '<unknown>'}: missing filename or type")
            continue

        # Find a matching cached entry by filename
        match = None
        for e in cache_list:
            if e.get("filename") == fname:
                match = e
                break
        if not match:
            errors.append(f"{fname}: not found in cache")
            continue

        zip_path = match.get("path")
        if not zip_path or not os.path.exists(zip_path):
            errors.append(f"{fname}: cached file missing on disk")
            continue

        # Extract into temp dir using provided password (if any)
        tmpdir = tempfile.mkdtemp()
        tmpdirs.append(tmpdir)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                try:
                    pwd_bytes = bytes(pwd, "utf-8") if pwd else None
                    if pwd_bytes:
                        zf.extractall(tmpdir, pwd=pwd_bytes)
                    else:
                        zf.extractall(tmpdir)
                except RuntimeError:
                    errors.append(f"{fname}: failed to unzip (bad password)")
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    tmpdirs.pop()
                    continue
                except zipfile.BadZipFile:
                    errors.append(f"{fname}: not a zip or corrupted")
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    tmpdirs.pop()
                    continue

            # Walk extracted files and prepare wrappers
            any_extracted = False
            for root, _, filenames in os.walk(tmpdir):
                for file in filenames:
                    any_extracted = True
                    fp = os.path.join(root, file)
                    try:
                        fobj = open(fp, "rb")
                    except Exception as e:
                        errors.append(
                            f"{fname}: failed to open extracted file {file}: {e}"
                        )
                        continue
                    wrappers.append(SimpleNamespace(file=fobj, filename=file))
                    types_list.append(ptype)

            if not any_extracted:
                errors.append(f"{fname}: zip opened but no files extracted")
                continue

            # Mark for removal from cache on successful import later
            processed_cache_entries.append(match)
        except Exception as e:
            errors.append(f"{fname}: unzip error: {e}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            if tmpdir in tmpdirs:
                tmpdirs.remove(tmpdir)
            continue

    if not wrappers:
        # No files prepared for import
        return {"imported": 0, "errors": errors}

    # Use existing import logic (async) provided by payment_service
    try:
        import_result = await import_payment_files_service(
            wrappers, types_list, db, current_user.id
        )
    except Exception as e:
        # Ensure we close wrapper files and cleanup tmpdirs
        for w in wrappers:
            try:
                w.file.close()
            except Exception:
                pass
        for td in tmpdirs:
            shutil.rmtree(td, ignore_errors=True)
        return {"imported": 0, "errors": errors + [f"Import internal error: {e}"]}

    # Close wrapper files and cleanup extracted tmpdirs
    for w in wrappers:
        try:
            w.file.close()
        except Exception:
            pass
    for td in tmpdirs:
        shutil.rmtree(td, ignore_errors=True)

    # Merge errors returned from import_result
    imported = import_result.get("imported", 0)
    import_errors = import_result.get("errors", []) or []
    errors.extend(import_errors)

    # If some imports succeeded, remove from cache and delete zip files
    if imported > 0 and processed_cache_entries:
        remaining = MAILGUN_ATTACHMENT_CACHE.get(username, [])
        for entry in processed_cache_entries:
            try:
                if entry in remaining:
                    remaining.remove(entry)
                path = entry.get("path")
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            except Exception:
                pass
        # update or remove cache key
        if remaining:
            MAILGUN_ATTACHMENT_CACHE[username] = remaining
        else:
            MAILGUN_ATTACHMENT_CACHE.pop(username, None)

    return {"imported": imported, "errors": errors}
