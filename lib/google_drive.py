#!/usr/bin/env python3
"""
Google Drive API execution script.
Handles authentication and common Drive operations.
"""

import os
import sys
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes determine what access we request
SCOPES = [
    'https://www.googleapis.com/auth/drive',  # Full Drive access (read + write)
]

# Paths relative to Workflow root
WORKFLOW_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = WORKFLOW_ROOT / 'credentials.json'
TOKEN_PATH = WORKFLOW_ROOT / 'token.json'


def authenticate():
    """
    Authenticate with Google Drive API.
    Opens browser for OAuth on first run, then saves token for reuse.
    Returns authenticated credentials.
    """
    creds = None

    # Load existing token if available
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # If no valid credentials, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                print(f"Error: credentials.json not found at {CREDENTIALS_PATH}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return creds


def get_drive_service():
    """Get authenticated Drive API service."""
    creds = authenticate()
    return build('drive', 'v3', credentials=creds)


def list_files(max_results=25, folder_id=None, query=None):
    """
    List files from Google Drive.

    Args:
        max_results: Maximum number of files to return
        folder_id: Optional folder ID to list contents of
        query: Optional query string (Drive API query format)

    Returns:
        List of file dictionaries with id, name, mimeType, modifiedTime
    """
    service = get_drive_service()

    # Build query
    q_parts = []
    if folder_id:
        q_parts.append(f"'{folder_id}' in parents")
    if query:
        q_parts.append(query)

    q = ' and '.join(q_parts) if q_parts else None

    try:
        results = service.files().list(
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)",
            q=q,
            orderBy="modifiedTime desc"
        ).execute()

        return results.get('files', [])

    except HttpError as error:
        print(f"Error listing files: {error}")
        return []


def get_file_info(file_id):
    """Get detailed info about a specific file."""
    service = get_drive_service()
    try:
        return service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, modifiedTime, size, parents, webViewLink"
        ).execute()
    except HttpError as error:
        print(f"Error getting file info: {error}")
        return None


def list_folders():
    """List all folders in Drive."""
    return list_files(
        max_results=100,
        query="mimeType='application/vnd.google-apps.folder'"
    )


def download_file(file_id, destination_path):
    """
    Download a file from Google Drive.

    Args:
        file_id: The ID of the file to download
        destination_path: Local path to save the file

    Returns:
        True if successful, False otherwise
    """
    import io
    from googleapiclient.http import MediaIoBaseDownload

    service = get_drive_service()

    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        with open(destination_path, 'wb') as f:
            f.write(fh.read())

        return True

    except HttpError as error:
        print(f"Error downloading file: {error}")
        return False


def upload_file(local_path, filename=None, folder_id=None, mime_type=None):
    """
    Upload a file to Google Drive.

    Args:
        local_path: Path to the local file to upload
        filename: Name for the file in Drive (defaults to local filename)
        folder_id: Optional folder ID to upload into
        mime_type: Optional MIME type (auto-detected if not provided)

    Returns:
        File metadata dict if successful, None otherwise
    """
    from googleapiclient.http import MediaFileUpload
    import mimetypes

    service = get_drive_service()
    local_path = Path(local_path)

    if not local_path.exists():
        print(f"Error: File not found: {local_path}")
        return None

    if not filename:
        filename = local_path.name

    if not mime_type:
        mime_type, _ = mimetypes.guess_type(str(local_path))
        if not mime_type:
            mime_type = 'application/octet-stream'

    file_metadata = {'name': filename}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    try:
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        return file

    except HttpError as error:
        print(f"Error uploading file: {error}")
        return None


def format_file_list(files):
    """Format file list for display."""
    if not files:
        return "No files found."

    output = []
    for f in files:
        mime = f.get('mimeType', 'unknown')
        # Simplify mime type for display
        if 'folder' in mime:
            ftype = '📁 Folder'
        elif 'document' in mime:
            ftype = '📄 Doc'
        elif 'spreadsheet' in mime:
            ftype = '📊 Sheet'
        elif 'presentation' in mime:
            ftype = '📽️  Slides'
        elif 'pdf' in mime:
            ftype = '📕 PDF'
        elif 'image' in mime:
            ftype = '🖼️  Image'
        else:
            ftype = '📎 File'

        output.append(f"{ftype}  {f['name']}")
        output.append(f"       ID: {f['id']}")

    return '\n'.join(output)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Google Drive operations')
    parser.add_argument('command', choices=['list', 'folders', 'info', 'upload'],
                       help='Command to run')
    parser.add_argument('--max', type=int, default=25,
                       help='Max results for list command')
    parser.add_argument('--folder', type=str,
                       help='Folder ID to list contents of')
    parser.add_argument('--id', type=str,
                       help='File ID for info command')
    parser.add_argument('--file', type=str,
                       help='Local file path for upload command')
    parser.add_argument('--name', type=str,
                       help='Filename in Drive for upload command')

    args = parser.parse_args()

    if args.command == 'list':
        files = list_files(max_results=args.max, folder_id=args.folder)
        print(format_file_list(files))

    elif args.command == 'folders':
        folders = list_folders()
        print(format_file_list(folders))

    elif args.command == 'info':
        if not args.id:
            print("Error: --id required for info command")
            sys.exit(1)
        info = get_file_info(args.id)
        if info:
            print(json.dumps(info, indent=2))

    elif args.command == 'upload':
        if not args.file:
            print("Error: --file required for upload command")
            sys.exit(1)
        result = upload_file(
            local_path=args.file,
            filename=args.name,
            folder_id=args.folder
        )
        if result:
            print(json.dumps(result, indent=2))
