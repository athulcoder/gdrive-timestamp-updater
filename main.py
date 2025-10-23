#!/usr/bin/env python3
"""
gdrive-timestamp-updater: CLI tool to set 'modifiedTime' on a Google Drive folder
and its contents using a Service Account.

Usage examples:
  # Using env var for credentials:
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
  python main.py --recursive --dry-run 1euqMiuoKLH... 2025-10-20T09:20:25.000Z

  # Passing credentials explicitly:
  python main.py -c /home/me/key.json --recursive 1euqMiuoKLH... 2025-10-20T09:20:25.000Z
"""

import argparse
import logging
import os
import sys
import time
import random
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_MIME = 'application/vnd.google-apps.folder'
DEFAULT_RETRIES = 5


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update Google Drive 'modifiedTime' for a folder and its files."
    )
    parser.add_argument(
        '-c', '--credentials',
        help="Path to service account JSON file. If omitted, GOOGLE_APPLICATION_CREDENTIALS env var will be used."
    )
    parser.add_argument(
        '-r', '--recursive', action='store_true',
        help="Recursively update nested subfolders and files."
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="Don't perform updates; print what would be changed."
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help="Verbose logging (debug)."
    )
    parser.add_argument(
        'folder_id',
        help="Drive folder ID (the long id from the folder's URL)."
    )
    parser.add_argument(
        'modified_time',
        help="New modified time in RFC3339 format (e.g. 2025-10-20T09:20:25.000Z)."
    )
    return parser.parse_args()


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s %(levelname)s: %(message)s',
        level=level
    )


def validate_rfc3339(ts: str) -> bool:
    """Very small validator for RFC3339 'Z' format timestamps we expect."""
    for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            datetime.strptime(ts, fmt)
            return True
        except ValueError:
            continue
    return False


def build_service(credentials_path: str):
    """Create Drive v3 service using given service account JSON path."""
    if not credentials_path:
        raise ValueError("No credentials provided. Set --credentials or GOOGLE_APPLICATION_CREDENTIALS env var.")

    if not os.path.isfile(credentials_path):
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return service


def retryable_update(service, file_id: str, body: dict, fields: str, dry_run: bool = False, max_retries: int = DEFAULT_RETRIES):
    """Update file metadata with retries & exponential backoff (for 429/5xx)."""
    if dry_run:
        logging.info("[dry-run] Would update %s with %s", file_id, body)
        return None

    backoff_base = 1
    for attempt in range(max_retries):
        try:
            resp = service.files().update(
                fileId=file_id,
                body=body,
                fields=fields,
                supportsAllDrives=True
            ).execute()
            return resp
        except HttpError as e:
            status = None
            try:
                status = int(e.resp.status)
            except Exception:
                pass

            # Retry on rate-limit & server errors
            if status in (429, 500, 503):
                sleep_for = backoff_base * (2 ** attempt) + random.random()
                logging.warning("Transient error (%s). Retry %d/%d after %.1fs...", status, attempt + 1, max_retries, sleep_for)
                time.sleep(sleep_for)
                continue
            else:
                logging.error("Non-retryable HttpError: %s", e)
                raise
    raise RuntimeError("Max retries exceeded for file update.")


def list_children(service, parent_id: str):
    """List direct children of a folder (id, name, mimeType). Handles pagination."""
    children = []
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{parent_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=1000,
            supportsAllDrives=True,
            pageToken=page_token
        ).execute()
        children.extend(response.get('files', []))
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    return children


def update_folder_and_contents(service, folder_id: str, new_time: str, recursive: bool, dry_run: bool):
    """Update folder then its contents; optionally recurses into subfolders."""
    logging.info("Updating folder id=%s → %s", folder_id, new_time)

    # Update the folder itself
    folder_resp = retryable_update(
        service,
        folder_id,
        body={'modifiedTime': new_time},
        fields='id, name, modifiedTime',
        dry_run=dry_run
    )
    if folder_resp:
        logging.info("Updated folder: %s → %s", folder_resp.get('name'), folder_resp.get('modifiedTime'))

    # Walk children
    queue = [folder_id]
    visited = set()

    while queue:
        current_folder = queue.pop(0)
        if current_folder in visited:
            continue
        visited.add(current_folder)

        children = list_children(service, current_folder)
        if not children:
            logging.debug("No children in folder %s", current_folder)
            continue

        for c in children:
            cid = c['id']
            cname = c.get('name', '<unknown>')
            cmime = c.get('mimeType', '')

            if cmime == FOLDER_MIME:
                # Update the subfolder's modifiedTime
                logging.info("Folder child: %s (%s) — updating modifiedTime", cname, cid)
                retryable_update(
                    service,
                    cid,
                    body={'modifiedTime': new_time},
                    fields='id, name, modifiedTime',
                    dry_run=dry_run
                )
                if recursive:
                    queue.append(cid)
            else:
                # Regular file — update modifiedTime
                logging.info("File: %s (%s) — updating modifiedTime", cname, cid)
                retryable_update(
                    service,
                    cid,
                    body={'modifiedTime': new_time},
                    fields='id, name, modifiedTime',
                    dry_run=dry_run
                )

    logging.info("All done.")


def main():
    args = parse_args()
    setup_logging(args.verbose)

    # Validate timestamp
    if not validate_rfc3339(args.modified_time):
        logging.error("Invalid modified_time. Provide RFC3339 like: 2025-10-20T09:20:25.000Z")
        sys.exit(2)

    # Determine credentials path
    cred_path = args.credentials or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not cred_path:
        logging.error("No credentials path provided. Use --credentials or set GOOGLE_APPLICATION_CREDENTIALS.")
        sys.exit(2)

    try:
        service = build_service(cred_path)
    except Exception as e:
        logging.exception("Failed to build Drive service: %s", e)
        sys.exit(1)

    try:
        # First, update the given folder itself (and then optionally contents)
        update_folder_and_contents(
            service=service,
            folder_id=args.folder_id,
            new_time=args.modified_time,
            recursive=args.recursive,
            dry_run=args.dry_run
        )
    except HttpError as e:
        logging.exception("Google Drive API error: %s", e)
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error: %s", e)
        sys.exit(1)


if __name__ == '__main__':
    main()
