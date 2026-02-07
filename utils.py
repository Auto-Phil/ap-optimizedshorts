"""
Helper utilities: logging, quota tracking, database, and email.
"""

import logging
import sqlite3
import smtplib
import json
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import config


# ── Logging ──────────────────────────────────────────────────────────────────

def setup_logger(name: str = "yt_scraper") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler (INFO+)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%H:%M:%S"))
    logger.addHandler(ch)

    # File handler (DEBUG+)
    log_file = config.LOGS_DIR / f"scraper_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"))
    logger.addHandler(fh)

    return logger


log = setup_logger()


# ── Quota tracker ────────────────────────────────────────────────────────────

class QuotaTracker:
    """Tracks YouTube API quota usage for the current day."""

    def __init__(self):
        self._used = 0
        self._limit = config.API_QUOTA_LIMIT - config.API_QUOTA_SAFETY_MARGIN

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        return max(0, self._limit - self._used)

    def consume(self, endpoint: str, count: int = 1):
        cost = config.QUOTA_COST.get(endpoint, 1) * count
        self._used += cost
        log.debug("Quota: +%d (%s) → %d / %d used", cost, endpoint, self._used, self._limit)

    def can_afford(self, endpoint: str, count: int = 1) -> bool:
        cost = config.QUOTA_COST.get(endpoint, 1) * count
        return (self._used + cost) <= self._limit

    def summary(self) -> str:
        return f"Quota used: {self._used} / {self._limit} ({self.remaining} remaining)"


# ── SQLite database for deduplication & status tracking ──────────────────────

def init_db():
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id   TEXT PRIMARY KEY,
            channel_name TEXT,
            first_seen   TEXT,
            last_scraped TEXT,
            status       TEXT DEFAULT 'new',
            data_json    TEXT
        )
    """)
    conn.commit()
    conn.close()


def channel_exists(channel_id: str) -> bool:
    conn = sqlite3.connect(str(config.DB_PATH))
    row = conn.execute("SELECT 1 FROM channels WHERE channel_id = ?", (channel_id,)).fetchone()
    conn.close()
    return row is not None


def upsert_channel(channel_id: str, channel_name: str, data: dict):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.execute("""
        INSERT INTO channels (channel_id, channel_name, first_seen, last_scraped, status, data_json)
        VALUES (?, ?, ?, ?, 'new', ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            last_scraped = excluded.last_scraped,
            data_json    = excluded.data_json
    """, (channel_id, channel_name, now, now, json.dumps(data)))
    conn.commit()
    conn.close()


def update_channel_status(channel_id: str, status: str):
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.execute("UPDATE channels SET status = ? WHERE channel_id = ?", (status, channel_id))
    conn.commit()
    conn.close()


def get_all_channel_ids() -> set:
    conn = sqlite3.connect(str(config.DB_PATH))
    rows = conn.execute("SELECT channel_id FROM channels").fetchall()
    conn.close()
    return {r[0] for r in rows}


# ── Email notification ───────────────────────────────────────────────────────

def send_email_report(subject: str, body: str):
    if not all([config.SMTP_HOST, config.SMTP_USER, config.SMTP_PASSWORD, config.NOTIFICATION_EMAIL]):
        log.debug("Email not configured — skipping notification")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USER
    msg["To"] = config.NOTIFICATION_EMAIL

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Email report sent to %s", config.NOTIFICATION_EMAIL)
    except Exception as e:
        log.error("Failed to send email: %s", e)


# ── Misc helpers ─────────────────────────────────────────────────────────────

def iso_to_seconds(duration_iso: str) -> int:
    """Convert ISO 8601 duration (PT#H#M#S) to total seconds."""
    duration_iso = duration_iso.replace("PT", "")
    hours = minutes = seconds = 0
    if "H" in duration_iso:
        h_part, duration_iso = duration_iso.split("H")
        hours = int(h_part)
    if "M" in duration_iso:
        m_part, duration_iso = duration_iso.split("M")
        minutes = int(m_part)
    if "S" in duration_iso:
        s_part = duration_iso.replace("S", "")
        seconds = int(s_part)
    return hours * 3600 + minutes * 60 + seconds


def days_since(date_str: str) -> int:
    """Return number of days between an ISO date string and now."""
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days
