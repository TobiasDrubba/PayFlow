import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime as _dt
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.domain.services.payment_service import import_payment_files_service

# In-memory cache:
# key = username (derived from recipient or sender), value = list of metadata dicts
MAILGUN_ATTACHMENT_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def _derive_username_from_recipient(recipient: Any) -> str:
    if not recipient:
        raise ValueError("No recipient provided to derive username")
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


def extract_wechat_download_url(html: str) -> Optional[str]:
    """
    Extract WeChat Pay download URL from email HTML/text.
    Only URLs matching known WeChat Pay domains are returned.
    """
    pattern = r"""https://
    (?:tenpay\.wechatpay\.cn|wx\.tenpay\.com|
    file\.api\.weixin\.qq\.com)/[^\s\"'>]+"""
    match = re.search(pattern, html)
    return match.group(0) if match else None


def sanitize_subject_for_filename(subject: str) -> str:
    """
    Convert email subject into safe filename and append .zip if missing
    """
    if not subject:
        subject = f"wechatpay_{int(_dt.utcnow().timestamp())}"
    sanitized = re.sub(r"[^\w\-_. ]", "_", subject).strip()
    if not sanitized.lower().endswith(".zip"):
        sanitized += ".zip"
    return sanitized


def download_zip_to_tempfile(url: str, filename: str) -> str:
    """
    Downloads the given URL to a temporary file and returns the path
    """
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        raise ValueError(f"Failed to download file from {url}: {e}")

    # Ensure .zip suffix
    _, ext = os.path.splitext(filename)
    if not ext:
        filename += ".zip"

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    os.close(tmp_fd)
    try:
        with open(tmp_path, "wb") as f:
            f.write(resp.content)
    except Exception as e:
        os.remove(tmp_path)
        raise ValueError(f"Failed to save downloaded file: {e}")
    return tmp_path


def cache_mailgun_form_attachments(form) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Process a Mailgun inbound multipart form, persist file attachments to temp files,
    and cache metadata in MAILGUN_ATTACHMENT_CACHE.

    Returns (username, saved_metadata_list).

    Raises ValueError if no attachments found and no downloadable WeChat ZIP.
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
                continue

    # Auto-download WeChat ZIP if no attachments found
    if not saved:
        html_content = form.get("body-html") or form.get("stripped-html") or ""
        url = extract_wechat_download_url(html_content)
        if url:
            subject = form.get("subject", "")
            filename = sanitize_subject_for_filename(subject)
            tmp_path = download_zip_to_tempfile(url, filename)
            meta = {
                "filename": filename,
                "path": tmp_path,
                "content_type": "application/zip",
                "received_at": _dt.utcnow(),
                "mailgun_field": "download_link",
            }
            saved.append(meta)

    if not saved:
        raise ValueError("No attachments or downloadable files found in Mailgun POST")

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
    username = _derive_cache_username_from_user(current_user)
    errors: List[str] = []
    wrappers: List[Any] = []
    types_list: List[str] = []
    tmpdirs: List[str] = []
    processed_cache_entries: List[Dict[str, Any]] = []

    if not items:
        return {"imported": 0, "errors": ["No items provided"]}

    cache_list = MAILGUN_ATTACHMENT_CACHE.get(username, [])

    for raw_item in items:
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

        tmpdir = tempfile.mkdtemp()
        tmpdirs.append(tmpdir)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Determine which compression methods this runtime supports
                supported_types = {getattr(zipfile, "ZIP_STORED", 0)}
                try:
                    import zlib  # type: ignore

                    if zlib:
                        pass
                except Exception:
                    pass
                else:
                    supported_types.add(getattr(zipfile, "ZIP_DEFLATED", 8))
                try:
                    import bz2  # type: ignore

                    if bz2:
                        pass
                except Exception:
                    pass
                else:
                    supported_types.add(getattr(zipfile, "ZIP_BZIP2", 12))
                try:
                    import lzma  # type: ignore

                    if lzma:
                        pass
                except Exception:
                    pass
                else:
                    supported_types.add(getattr(zipfile, "ZIP_LZMA", 14))

                # Inspect archive entries for unsupported compression methods
                unsupported = set()
                for info in zf.infolist():
                    if info.compress_type not in supported_types:
                        unsupported.add(info.compress_type)

                # try pyzipper for AES-encrypted zips (method 99)
                pwd_bytes = bytes(pwd, "utf-8") if pwd else None
                if unsupported:
                    # Commonly 99 indicates AES/encrypted zip entries
                    if unsupported == {99}:
                        # Try pyzipper if available
                        try:
                            import pyzipper  # type: ignore
                        except Exception:
                            errors.append(
                                f"{fname}: Install 'pyzipper' to extract such archives."
                            )
                            shutil.rmtree(tmpdir, ignore_errors=True)
                            tmpdirs.pop()
                            continue
                        try:
                            # attempt extraction with pyzipper
                            with pyzipper.AESZipFile(zip_path, "r") as za:
                                if pwd_bytes:
                                    za.pwd = pwd_bytes
                                za.extractall(tmpdir)
                        except RuntimeError as er:
                            em = str(er).lower()
                            if "password" in em or "encrypted" in em:
                                errors.append(
                                    f"{fname}: failed to unzip (bad password)"
                                )
                            else:
                                errors.append(
                                    f"{fname}: pyzipper unzip runtime error: {er}"
                                )
                            shutil.rmtree(tmpdir, ignore_errors=True)
                            tmpdirs.pop()
                            continue
                        except Exception as e:
                            errors.append(f"{fname}: pyzipper extraction failed: {e}")
                            shutil.rmtree(tmpdir, ignore_errors=True)
                            tmpdirs.pop()
                            continue
                    else:
                        errors.append(
                            f"{fname}: zip contains unsupported "
                            f"compression methods: {sorted(list(unsupported))}"
                        )
                        shutil.rmtree(tmpdir, ignore_errors=True)
                        tmpdirs.pop()
                        continue

                # If we reach here use zipfile for extraction;
                # if we already used pyzipper above, files are in tmpdir
                if not unsupported:
                    # Check for encryption (flag bit 0x1)
                    is_encrypted = any(info.flag_bits & 0x1 for info in zf.infolist())
                    if is_encrypted and not pwd_bytes:
                        errors.append(
                            f"{fname}: zip is encrypted but no password provided"
                        )
                        shutil.rmtree(tmpdir, ignore_errors=True)
                        tmpdirs.pop()
                        continue

                    # Try extraction; if a RuntimeError occurs, classify it properly
                    try:
                        if pwd_bytes:
                            zf.extractall(tmpdir, pwd=pwd_bytes)
                        else:
                            zf.extractall(tmpdir)
                    except RuntimeError as er:
                        em = str(er).lower()
                        if "password" in em or "encrypted" in em:
                            errors.append(f"{fname}: failed to unzip (bad password)")
                        else:
                            errors.append(f"{fname}: unzip runtime error: {er}")
                        shutil.rmtree(tmpdir, ignore_errors=True)
                        tmpdirs.pop()
                        continue
                    except zipfile.BadZipFile:
                        errors.append(f"{fname}: not a zip or corrupted")
                        shutil.rmtree(tmpdir, ignore_errors=True)
                        tmpdirs.pop()
                        continue

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

            processed_cache_entries.append(match)
        except Exception as e:
            errors.append(f"{fname}: unzip error: {e}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            if tmpdir in tmpdirs:
                tmpdirs.remove(tmpdir)
            continue

    if not wrappers:
        return {"imported": 0, "errors": errors}

    try:
        import_result = await import_payment_files_service(
            wrappers, types_list, db, current_user.id
        )
    except Exception as e:
        for w in wrappers:
            try:
                w.file.close()
            except Exception:
                pass
        for td in tmpdirs:
            shutil.rmtree(td, ignore_errors=True)
        return {"imported": 0, "errors": errors + [f"Import internal error: {e}"]}

    for w in wrappers:
        try:
            w.file.close()
        except Exception:
            pass
    for td in tmpdirs:
        shutil.rmtree(td, ignore_errors=True)

    imported = import_result.get("imported", 0)
    import_errors = import_result.get("errors", []) or []
    errors.extend(import_errors)

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
        if remaining:
            MAILGUN_ATTACHMENT_CACHE[username] = remaining
        else:
            MAILGUN_ATTACHMENT_CACHE.pop(username, None)

    return {"imported": imported, "errors": errors}


def remove_mailgun_cached_file_for_user(current_user: Any, filename: str) -> None:
    username = _derive_cache_username_from_user(current_user)
    entries = MAILGUN_ATTACHMENT_CACHE.get(username, [])
    match = None
    for e in entries:
        if e.get("filename") == filename:
            match = e
            break
    if not match:
        raise ValueError(f"{filename}: not found in cache for user {username}")
    path = match.get("path")
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    try:
        entries.remove(match)
    except Exception:
        pass
    if entries:
        MAILGUN_ATTACHMENT_CACHE[username] = entries
    else:
        MAILGUN_ATTACHMENT_CACHE.pop(username, None)
