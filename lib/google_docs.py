#!/usr/bin/env python3
"""
Google Docs API execution script.
Handles authentication and common Docs operations.
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

# Scopes - using broader scopes from existing token
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
]

# Paths relative to Workflow root
WORKFLOW_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = WORKFLOW_ROOT / 'credentials.json'
TOKEN_PATH = WORKFLOW_ROOT / 'token.json'


def authenticate():
    """
    Authenticate with Google Docs API.
    Uses existing token if available and valid.
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


def get_docs_service():
    """Get authenticated Docs API service."""
    creds = authenticate()
    return build('docs', 'v1', credentials=creds)


def append_text(doc_id, text):
    """
    Append text to the end of a Google Doc.

    Args:
        doc_id: The document ID
        text: Text content to append

    Returns:
        True if successful, False otherwise
    """
    service = get_docs_service()

    try:
        # Get document to find end index
        doc = service.documents().get(documentId=doc_id).execute()
        end_index = doc['body']['content'][-1]['endIndex'] - 1

        # Insert text at the end
        requests = [
            {
                'insertText': {
                    'location': {'index': end_index},
                    'text': text
                }
            }
        ]

        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()

        print(f"Successfully appended {len(text)} characters to document")
        return True

    except HttpError as error:
        print(f"Error appending to document: {error}")
        return False


def get_document(doc_id):
    """Get document content."""
    service = get_docs_service()
    try:
        return service.documents().get(documentId=doc_id).execute()
    except HttpError as error:
        print(f"Error getting document: {error}")
        return None


def create_document(title, folder_id=None):
    """
    Create a new Google Doc, optionally in a specific folder.

    Args:
        title: Title of the new document
        folder_id: Optional folder ID to place the document in

    Returns:
        Document ID if successful, None otherwise
    """
    from google.oauth2.credentials import Credentials

    creds = authenticate()
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    try:
        # Create the document
        doc = docs_service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        print(f"Created document with ID: {doc_id}")

        # Move to folder if specified
        if folder_id:
            # Get current parents
            file = drive_service.files().get(fileId=doc_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))

            # Move the file to the new folder
            drive_service.files().update(
                fileId=doc_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            print(f"Moved document to folder: {folder_id}")

        return doc_id
    except HttpError as error:
        print(f"Error creating document: {error}")
        return None


def add_script_tab(doc_id, title, body, index=None):
    """
    Add a new native tab to a Google Doc and write body text into it.

    Used by the JiYu scripts archive: each approved script gets its own tab,
    titled like "S1 Row 312 dark spots fade fast".

    Args:
        doc_id: The document ID
        title: Tab title (the user-visible name in the tab rail)
        body: Text to write into the new tab
        index: Optional zero-based position among root tabs. Defaults to the
               end (append after existing tabs).

    Returns:
        The new tab's tabId if successful, None otherwise.
    """
    service = get_docs_service()

    try:
        # Snapshot existing root tab IDs so we can identify the new one
        doc = service.documents().get(
            documentId=doc_id, includeTabsContent=True).execute()
        existing = doc.get('tabs', [])
        existing_ids = {t['tabProperties']['tabId'] for t in existing}
        if index is None:
            index = len(existing)

        # Create the tab
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [
                {'addDocumentTab': {
                    'tabProperties': {'title': title, 'index': index}}}
            ]}
        ).execute()

        # Re-fetch and find the newly created tab by diffing IDs
        doc = service.documents().get(
            documentId=doc_id, includeTabsContent=True).execute()
        new_tabs = [t for t in doc.get('tabs', [])
                    if t['tabProperties']['tabId'] not in existing_ids]
        if not new_tabs:
            print("Error: tab was not created")
            return None
        new_id = new_tabs[0]['tabProperties']['tabId']

        # Write the body into the new tab (tab body starts at index 1)
        if body:
            service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': [
                    {'insertText': {
                        'location': {'index': 1, 'tabId': new_id},
                        'text': body}}
                ]}
            ).execute()

        print(f"Created tab '{title}' (tabId={new_id}), wrote {len(body or '')} chars")
        return new_id

    except HttpError as error:
        print(f"Error adding script tab: {error}")
        return None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Google Docs operations')
    parser.add_argument('command', choices=['append', 'get', 'create', 'add-tab'],
                       help='Command to run')
    parser.add_argument('doc_id', nargs='?',
                       help='Document ID (required for append/get/add-tab)')
    parser.add_argument('text', nargs='?',
                       help='Text to append (append), title (create), or tab title (add-tab)')
    parser.add_argument('body', nargs='?',
                       help='Body text to write into the tab (add-tab only)')

    args = parser.parse_args()

    if args.command == 'append':
        if not args.doc_id or not args.text:
            print("Error: doc_id and text required for append command")
            sys.exit(1)
        append_text(args.doc_id, args.text)

    elif args.command == 'get':
        if not args.doc_id:
            print("Error: doc_id required for get command")
            sys.exit(1)
        doc = get_document(args.doc_id)
        if doc:
            print(json.dumps(doc, indent=2))

    elif args.command == 'create':
        title = args.doc_id or "Untitled Document"  # Use first positional as title
        create_document(title)

    elif args.command == 'add-tab':
        if not args.doc_id or not args.text:
            print("Error: doc_id and tab title required for add-tab command")
            sys.exit(1)
        add_script_tab(args.doc_id, args.text, args.body or "")
