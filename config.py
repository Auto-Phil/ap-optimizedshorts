"""
Configuration settings for the YouTube channel scraper.
Modify these values to adjust search criteria, filtering, and behavior.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
CACHE_DIR = BASE_DIR / "cache"
DB_PATH = CACHE_DIR / "channels.db"
EXPORT_DIR = BASE_DIR

LOGS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# --- YouTube API ---
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
# Daily quota limit for YouTube Data API v3
API_QUOTA_LIMIT = 10_000
# Reserve some quota for retries / overhead
API_QUOTA_SAFETY_MARGIN = 500

# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# --- Email (optional notifications) ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")

# --- Channel filter criteria ---
MIN_SUBSCRIBERS = 10_000
MAX_SUBSCRIBERS = 500_000
MAX_SHORTS_COUNT = 5
MIN_LONGFORM_COUNT = 20
MAX_DAYS_SINCE_UPLOAD = 30        # Must have uploaded within this many days
MIN_AVG_DURATION_SECONDS = 480    # 8 minutes preferred

# --- Language / Region filter ---
# Only include channels from these countries (ISO 3166-1 alpha-2 codes)
# Empty list = no country filter. Channels with no country set are always included.
ALLOWED_COUNTRIES = ["US", "GB", "CA", "AU", "NZ", "IE"]
# Only include channels whose default language starts with one of these codes
# Empty list = no language filter. Channels with no language set are always included.
ALLOWED_LANGUAGES = ["en"]

# --- Search configuration ---
SEARCH_NICHES = [
    # --- Original niches ---
    "business tips",
    "personal finance advice",
    "productivity tips",
    "fitness training",
    "cooking recipes tutorial",
    "tech reviews",
    "education tutorial",
    "self improvement motivation",
    "digital marketing tips",
    "real estate investing",
    "entrepreneurship advice",
    # --- Film / TV essay niches ---
    "film analysis essay",
    "film critique essay",
    "movie breakdown essay",
    "movie video essay",
    "movie retrospective",
    "horror film essay",
    "superhero movie analysis",
    "animated movie analysis",
    "cinema analysis",
    "tv show video essay",
    "tv show analysis",
    # --- Retro gaming niches ---
    "retro gaming review",
    "retro game analysis",
    "retro game history",
    "old game review commentary",
    "ps1 ps2 game review",
    "forgotten games retrospective",
    "obscure video game review",
    "video game essay",
    "gaming nostalgia",
    # --- Professional / explainer niches ---
    "accounting explained",
    "bookkeeping tutorial",
    "legal advice",
    "psychology explained",
    "therapist explains",
    # --- Home / real estate niches ---
    "home renovation",
    "house flipping",
]

# Maximum number of search results per niche keyword (max 50 per API call)
SEARCH_RESULTS_PER_NICHE = 50

# Maximum channels to fully process per daily run
MAX_CHANNELS_PER_RUN = 500

# Maximum videos to scan per channel for shorts detection / stats
MAX_VIDEOS_TO_SCAN = 200

# Number of recent videos to use for engagement calculation
RECENT_VIDEOS_FOR_STATS = 10

# --- Priority score weights (must sum to 1.0) ---
SCORE_WEIGHT_SUBSCRIBERS = 0.30
SCORE_WEIGHT_ENGAGEMENT = 0.25
SCORE_WEIGHT_CONSISTENCY = 0.20
SCORE_WEIGHT_VIEWS_RATIO = 0.15
SCORE_WEIGHT_NICHE_FIT = 0.10

# --- Retry / rate-limit ---
API_MAX_RETRIES = 3
API_RETRY_DELAY_SECONDS = 5

# --- Scheduler ---
SCHEDULE_TIME = "03:00"  # 24-hour format, daily run time

# --- Quota costs (YouTube Data API v3) ---
# https://developers.google.com/youtube/v3/determine_quota_cost
QUOTA_COST = {
    "search.list": 100,
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
}
