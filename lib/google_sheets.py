#!/usr/bin/env python3
"""
Google Sheets API execution script.
Handles reading and writing to Google Sheets.
"""

import sys
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes - need both drive and sheets access (read + write)
SCOPES = [
    'https://www.googleapis.com/auth/drive',  # Full drive access for creating files
    'https://www.googleapis.com/auth/spreadsheets',  # Full access for read/write
]

# Paths relative to Workflow root
WORKFLOW_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = WORKFLOW_ROOT / 'credentials.json'
TOKEN_PATH = WORKFLOW_ROOT / 'token_sheets.json'  # Separate token for sheets scope


def authenticate():
    """
    Authenticate with Google Sheets API.
    Opens browser for OAuth on first run, then saves token for reuse.
    """
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                print(f"Error: credentials.json not found at {CREDENTIALS_PATH}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return creds


def get_sheets_service():
    """Get authenticated Sheets API service."""
    creds = authenticate()
    return build('sheets', 'v4', credentials=creds)


def get_spreadsheet_info(spreadsheet_id):
    """
    Get spreadsheet metadata including sheet names.
    """
    service = get_sheets_service()
    try:
        result = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        return result
    except HttpError as error:
        print(f"Error getting spreadsheet info: {error}")
        return None


def read_sheet(spreadsheet_id, range_name=None):
    """
    Read data from a Google Sheet.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_name: Optional range like 'Sheet1!A1:Z100'. If None, reads first sheet.

    Returns:
        List of rows (each row is a list of cell values)
    """
    service = get_sheets_service()

    try:
        # If no range specified, get sheet names first and use the first one
        if not range_name:
            info = get_spreadsheet_info(spreadsheet_id)
            if info and info.get('sheets'):
                first_sheet = info['sheets'][0]['properties']['title']
                range_name = first_sheet
            else:
                range_name = 'Sheet1'

        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        return result.get('values', [])

    except HttpError as error:
        print(f"Error reading sheet: {error}")
        return []


def write_column(spreadsheet_id, sheet_name, column_letter, values, start_row=1):
    """
    Write values to a specific column.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: Name of the sheet
        column_letter: Column letter (e.g., 'E')
        values: List of values to write (one per row)
        start_row: Row number to start writing (1-indexed)

    Returns:
        Number of cells updated
    """
    service = get_sheets_service()

    # Format values for API (each value needs to be in a list)
    body = {
        'values': [[v] for v in values]
    }

    range_name = f"{sheet_name}!{column_letter}{start_row}:{column_letter}{start_row + len(values) - 1}"

    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        return result.get('updatedCells', 0)

    except HttpError as error:
        print(f"Error writing to sheet: {error}")
        return 0


def create_spreadsheet(title, folder_id=None):
    """
    Create a new Google Spreadsheet.

    Args:
        title: Title of the new spreadsheet
        folder_id: Optional folder ID to create the spreadsheet in

    Returns:
        Spreadsheet ID if successful, None otherwise
    """
    service = get_sheets_service()

    try:
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        result = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = result.get('spreadsheetId')

        # Move to folder if specified
        if folder_id and spreadsheet_id:
            from googleapiclient.discovery import build as drive_build
            creds = authenticate()
            drive_service = drive_build('drive', 'v3', credentials=creds)
            # Get current parents
            file = drive_service.files().get(fileId=spreadsheet_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            # Move to new folder
            drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()

        return spreadsheet_id

    except HttpError as error:
        print(f"Error creating spreadsheet: {error}")
        return None


def write_range(spreadsheet_id, range_name, values):
    """
    Write values to a range in a Google Sheet.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_name: Range like 'Sheet1!A1:E10'
        values: 2D list of values to write

    Returns:
        Number of cells updated
    """
    service = get_sheets_service()

    body = {
        'values': values
    }

    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

        return result.get('updatedCells', 0)

    except HttpError as error:
        print(f"Error writing to sheet: {error}")
        return 0


def delete_sheet_tab(spreadsheet_id, sheet_name):
    """
    Delete a sheet tab from a spreadsheet.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: Name of the sheet tab to delete

    Returns:
        True if successful, False otherwise
    """
    service = get_sheets_service()

    try:
        # First get the sheet ID from the name
        info = get_spreadsheet_info(spreadsheet_id)
        sheet_id = None
        for sheet in info.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                sheet_id = sheet['properties']['sheetId']
                break

        if sheet_id is None:
            print(f"Sheet '{sheet_name}' not found")
            return False

        # Delete the sheet
        request = {
            'requests': [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request
        ).execute()

        return True

    except HttpError as error:
        print(f"Error deleting sheet: {error}")
        return False


def copy_spreadsheet(source_id, new_title, folder_id=None):
    """
    Copy an existing spreadsheet.

    Args:
        source_id: ID of the spreadsheet to copy
        new_title: Title for the new copy
        folder_id: Optional folder ID to place the copy in

    Returns:
        New spreadsheet ID if successful, None otherwise
    """
    creds = authenticate()
    drive_service = build('drive', 'v3', credentials=creds)

    try:
        body = {'name': new_title}
        if folder_id:
            body['parents'] = [folder_id]

        result = drive_service.files().copy(
            fileId=source_id,
            body=body
        ).execute()

        return result.get('id')

    except HttpError as error:
        print(f"Error copying spreadsheet: {error}")
        return None


def format_sheet_data(rows, max_col_width=40):
    """Format sheet data for terminal display."""
    if not rows:
        return "No data found."

    # Calculate column widths
    num_cols = max(len(row) for row in rows)
    col_widths = [0] * num_cols

    for row in rows:
        for i, cell in enumerate(row):
            cell_str = str(cell)[:max_col_width]
            col_widths[i] = max(col_widths[i], len(cell_str))

    # Format output
    output = []
    for row_idx, row in enumerate(rows):
        formatted_cells = []
        for i in range(num_cols):
            cell = str(row[i])[:max_col_width] if i < len(row) else ''
            formatted_cells.append(cell.ljust(col_widths[i]))
        output.append(' | '.join(formatted_cells))

        # Add separator after header
        if row_idx == 0:
            output.append('-+-'.join('-' * w for w in col_widths))

    return '\n'.join(output)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Google Sheets operations')
    parser.add_argument('command', choices=['info', 'read'],
                       help='Command to run')
    parser.add_argument('--id', type=str, required=True,
                       help='Spreadsheet ID')
    parser.add_argument('--range', type=str,
                       help='Range to read (e.g., Sheet1!A1:Z100)')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON instead of formatted table')

    args = parser.parse_args()

    if args.command == 'info':
        info = get_spreadsheet_info(args.id)
        if info:
            print(f"Title: {info.get('properties', {}).get('title', 'Unknown')}")
            print(f"Sheets:")
            for sheet in info.get('sheets', []):
                props = sheet.get('properties', {})
                print(f"  - {props.get('title')} ({props.get('gridProperties', {}).get('rowCount', '?')} rows)")

    elif args.command == 'read':
        rows = read_sheet(args.id, args.range)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(format_sheet_data(rows))
