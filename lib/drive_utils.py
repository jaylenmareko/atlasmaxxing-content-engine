"""Shared Drive helpers for the engine's intake/pull scripts."""

import json
import sys
from pathlib import Path

import engine_config as cfg

sys.path.insert(0, str(cfg.CONTENT_ENGINE_EXEC))
from google_drive import get_drive_service, upload_file, download_file  # noqa: E402,F401

FOLDER_MIME = "application/vnd.google-apps.folder"


def find_or_create_folder(svc, name: str, parent_id: str) -> str:
    safe = name.replace("'", "\\'")
    q = (f"name='{safe}' and '{parent_id}' in parents "
         f"and mimeType='{FOLDER_MIME}' and trashed=false")
    hits = svc.files().list(q=q, fields="files(id)").execute().get("files", [])
    if hits:
        return hits[0]["id"]
    meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
    created = svc.files().create(body=meta, fields="id").execute()
    print(f"📁 created Drive folder: {name}")
    return created["id"]


def folder_path(svc, *names: str, root: str = "root") -> str:
    """Walk/create a chain of folders, return the last folder's id."""
    parent = root
    for n in names:
        parent = find_or_create_folder(svc, n, parent)
    return parent


def upload_public(local: Path, name: str, folder_id: str, mime: str) -> dict | None:
    """Upload + anyone-with-link read (for =IMAGE()). Returns file metadata."""
    uploaded = upload_file(str(local), name, folder_id, mime)
    if not uploaded:
        return None
    try:
        get_drive_service().permissions().create(
            fileId=uploaded["id"], body={"type": "anyone", "role": "reader"}).execute()
    except Exception as e:
        print(f"⚠️  permission failed on {name}: {e}")
    return uploaded


def copy_into(svc, file_id: str, name: str, folder_id: str) -> str | None:
    """Server-side Drive copy (no download/upload round trip)."""
    try:
        r = svc.files().copy(fileId=file_id, body={"name": name, "parents": [folder_id]},
                             fields="id").execute()
        return r["id"]
    except Exception as e:
        print(f"⚠️  copy failed for {name}: {e}")
        return None


def read_manifest(svc, pool_folder_id: str) -> dict | None:
    q = f"name='manifest.json' and '{pool_folder_id}' in parents and trashed=false"
    hits = svc.files().list(q=q, fields="files(id)").execute().get("files", [])
    if not hits:
        return None
    import io
    from googleapiclient.http import MediaIoBaseDownload
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=hits[0]["id"]))
    done = False
    while not done:
        _, done = dl.next_chunk()
    return json.loads(buf.getvalue().decode("utf-8"))
