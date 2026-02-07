"""
Export results to Google Sheets (primary) or CSV (fallback).
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

import config
from utils import log


# Column order for export
COLUMNS = [
    "timestamp",
    "channel_id",
    "channel_name",
    "channel_url",
    "subscriber_count",
    "total_view_count",
    "total_video_count",
    "shorts_count",
    "longform_count",
    "last_upload_date",
    "upload_frequency",
    "avg_views",
    "avg_duration_seconds",
    "engagement_rate",
    "priority_score",
    "primary_niche",
    "country",
    "language",
    "contact_email",
    "contact_available",
    "top_video_1_title",
    "top_video_1_url",
    "top_video_2_title",
    "top_video_2_url",
    "top_video_3_title",
    "top_video_3_url",
    "status",
]


def build_row(channel: dict, analysis: dict, score: float, niche: str) -> dict:
    """Build a flat dict ready for export from channel + analysis data."""
    top3 = analysis.get("top_3_videos", [])

    # Merge emails: prefer channel about-page email, fall back to description emails
    email = channel.get("contact_email", "")
    if not email:
        desc_emails = analysis.get("emails_from_descriptions", [])
        email = desc_emails[0] if desc_emails else ""

    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "channel_id": channel["channel_id"],
        "channel_name": channel["channel_name"],
        "channel_url": channel["channel_url"],
        "subscriber_count": channel["subscriber_count"],
        "total_view_count": channel["total_view_count"],
        "total_video_count": channel["total_video_count"],
        "shorts_count": analysis["shorts_count"],
        "longform_count": analysis["longform_count"],
        "last_upload_date": analysis["last_upload_date"],
        "upload_frequency": analysis["upload_frequency"],
        "avg_views": analysis["avg_views"],
        "avg_duration_seconds": analysis["avg_duration_seconds"],
        "engagement_rate": analysis["engagement_rate"],
        "priority_score": score,
        "primary_niche": niche,
        "country": channel.get("country", ""),
        "language": channel.get("default_language", ""),
        "contact_email": email,
        "contact_available": "yes" if email else "no",
        "top_video_1_title": top3[0]["title"] if len(top3) > 0 else "",
        "top_video_1_url": top3[0]["url"] if len(top3) > 0 else "",
        "top_video_2_title": top3[1]["title"] if len(top3) > 1 else "",
        "top_video_2_url": top3[1]["url"] if len(top3) > 1 else "",
        "top_video_3_title": top3[2]["title"] if len(top3) > 2 else "",
        "top_video_3_url": top3[2]["url"] if len(top3) > 2 else "",
        "status": "new",
    }
    return row


def export_to_google_sheets(rows: list[dict]) -> bool:
    """Append rows to a Google Sheet. Returns True on success."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        log.warning("gspread not installed — falling back to CSV")
        return False

    creds_path = Path(config.GOOGLE_SHEETS_CREDENTIALS_FILE)
    if not creds_path.exists():
        log.warning("Google Sheets credentials file not found at %s — falling back to CSV", creds_path)
        return False

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
        gc = gspread.authorize(creds)

        # Open or create the sheet
        try:
            sheet = gc.open(config.GOOGLE_SHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sheet = gc.create(config.GOOGLE_SHEET_NAME)
            log.info("Created new Google Sheet: %s", config.GOOGLE_SHEET_NAME)

        worksheet = sheet.sheet1

        # Add header if sheet is empty
        existing = worksheet.get_all_values()
        if not existing:
            worksheet.append_row(COLUMNS)

        # Append each row
        for row in rows:
            values = [str(row.get(col, "")) for col in COLUMNS]
            worksheet.append_row(values)

        log.info("Exported %d rows to Google Sheet '%s'", len(rows), config.GOOGLE_SHEET_NAME)
        return True

    except Exception as e:
        log.error("Google Sheets export failed: %s", e)
        return False


def export_to_csv(rows: list[dict]) -> str:
    """Append rows to a timestamped CSV file. Returns the file path."""
    date_str = datetime.now().strftime("%Y%m%d")
    csv_path = config.EXPORT_DIR / f"leads_{date_str}.csv"

    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)

    log.info("Exported %d rows to %s", len(rows), csv_path)
    return str(csv_path)


def export(rows: list[dict]) -> str:
    """
    Try Google Sheets first; fall back to CSV.
    Returns a description of where the data was exported.
    """
    if not rows:
        log.info("No rows to export")
        return "No data to export"

    if export_to_google_sheets(rows):
        return f"Google Sheet '{config.GOOGLE_SHEET_NAME}'"

    path = export_to_csv(rows)
    return f"CSV file: {path}"
