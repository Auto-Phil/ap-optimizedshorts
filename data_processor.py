"""
Filtering, scoring, and analysis of scraped channel data.
"""

from datetime import datetime, timezone
from typing import Optional

import config
from utils import log, days_since


def analyze_channel_videos(videos: list[dict]) -> dict:
    """
    Given a list of video detail dicts, compute:
      - shorts_count, longform_count
      - last_upload_date
      - upload_frequency (videos per month)
      - avg_duration (seconds, long-form only)
      - avg_views, avg_likes, avg_comments (recent N videos)
      - engagement_rate
      - top 3 performing videos
    """
    if not videos:
        return _empty_analysis()

    # Sort newest first
    videos.sort(key=lambda v: v["published_at"], reverse=True)

    shorts = [v for v in videos if v["duration_seconds"] <= 60]
    longform = [v for v in videos if v["duration_seconds"] > 60]

    last_upload = videos[0]["published_at"] if videos else ""

    # Upload frequency: estimate from date range of all videos
    upload_freq = _upload_frequency(videos)

    # Average duration of long-form content
    avg_duration = 0
    if longform:
        avg_duration = sum(v["duration_seconds"] for v in longform) / len(longform)

    # Recent videos for engagement stats
    recent = videos[:config.RECENT_VIDEOS_FOR_STATS]
    avg_views = sum(v["view_count"] for v in recent) / len(recent) if recent else 0
    avg_likes = sum(v["like_count"] for v in recent) / len(recent) if recent else 0
    avg_comments = sum(v["comment_count"] for v in recent) / len(recent) if recent else 0

    engagement_rate = 0.0
    total_views = sum(v["view_count"] for v in recent)
    if total_views > 0:
        total_engagement = sum(v["like_count"] + v["comment_count"] for v in recent)
        engagement_rate = round(total_engagement / total_views * 100, 4)

    # Top 3 by views
    top_videos = sorted(videos, key=lambda v: v["view_count"], reverse=True)[:3]
    top3 = [{"title": v["title"], "url": v["url"], "views": v["view_count"]} for v in top_videos]

    # Look for contact email in recent video descriptions
    emails_from_descriptions = set()
    for v in videos[:3]:
        from youtube_api import YouTubeAPI
        email = YouTubeAPI._extract_email(v.get("description", ""))
        if email:
            emails_from_descriptions.add(email)

    return {
        "shorts_count": len(shorts),
        "longform_count": len(longform),
        "last_upload_date": last_upload,
        "upload_frequency": upload_freq,
        "avg_duration_seconds": round(avg_duration),
        "avg_views": round(avg_views),
        "avg_likes": round(avg_likes),
        "avg_comments": round(avg_comments),
        "engagement_rate": engagement_rate,
        "top_3_videos": top3,
        "emails_from_descriptions": list(emails_from_descriptions),
    }


def passes_filters(channel: dict, analysis: dict) -> bool:
    """Return True if the channel meets all criteria."""
    # Language / region check (run first — cheap, no API cost)
    country = channel.get("country", "")
    lang = channel.get("default_language", "")
    if config.ALLOWED_COUNTRIES and country:
        if country not in config.ALLOWED_COUNTRIES:
            log.debug("  ✗ Country '%s' not in allowed list", country)
            return False
    if config.ALLOWED_LANGUAGES and lang:
        if not any(lang.startswith(a) for a in config.ALLOWED_LANGUAGES):
            log.debug("  ✗ Language '%s' not in allowed list", lang)
            return False

    subs = channel.get("subscriber_count", 0)
    if subs < config.MIN_SUBSCRIBERS or subs > config.MAX_SUBSCRIBERS:
        log.debug("  ✗ Subs %d outside range", subs)
        return False

    if analysis["shorts_count"] > config.MAX_SHORTS_COUNT:
        log.debug("  ✗ Too many shorts (%d)", analysis["shorts_count"])
        return False

    if analysis["longform_count"] < config.MIN_LONGFORM_COUNT:
        log.debug("  ✗ Not enough long-form (%d)", analysis["longform_count"])
        return False

    if analysis["last_upload_date"]:
        days = days_since(analysis["last_upload_date"])
        if days > config.MAX_DAYS_SINCE_UPLOAD:
            log.debug("  ✗ Last upload %d days ago", days)
            return False
    else:
        log.debug("  ✗ No upload date found")
        return False

    return True


def compute_priority_score(channel: dict, analysis: dict, niche: str) -> float:
    """
    Compute a 1-10 priority score based on weighted criteria.
    Higher is better.
    """
    subs = channel.get("subscriber_count", 0)
    engagement = analysis.get("engagement_rate", 0)
    frequency = analysis.get("upload_frequency", 0)
    avg_views = analysis.get("avg_views", 0)

    # Subscriber score: sweet spot around 50k-200k
    if subs <= 0:
        sub_score = 0
    elif subs < 50_000:
        sub_score = subs / 50_000 * 7  # Up to 7
    elif subs <= 200_000:
        sub_score = 7 + (subs - 50_000) / 150_000 * 3  # 7–10
    else:
        sub_score = 10 - (subs - 200_000) / 300_000 * 3  # Taper off
    sub_score = max(0, min(10, sub_score))

    # Engagement score: >5% is excellent
    eng_score = min(10, engagement / 5 * 10) if engagement > 0 else 0

    # Consistency score: 4+ videos/month is great
    freq_score = min(10, frequency / 4 * 10) if frequency > 0 else 0

    # Views/subs ratio: higher ratio = better reach
    views_ratio = avg_views / subs if subs > 0 else 0
    ratio_score = min(10, views_ratio / 0.10 * 10)  # 10% ratio = perfect 10

    # Niche fit: check if niche keyword appears in channel description
    desc = channel.get("description", "").lower()
    niche_keywords = niche.lower().split()
    matches = sum(1 for kw in niche_keywords if kw in desc)
    niche_score = min(10, matches / max(1, len(niche_keywords)) * 10)

    score = (
        sub_score * config.SCORE_WEIGHT_SUBSCRIBERS
        + eng_score * config.SCORE_WEIGHT_ENGAGEMENT
        + freq_score * config.SCORE_WEIGHT_CONSISTENCY
        + ratio_score * config.SCORE_WEIGHT_VIEWS_RATIO
        + niche_score * config.SCORE_WEIGHT_NICHE_FIT
    )

    return round(max(1, min(10, score)), 1)


def _upload_frequency(videos: list[dict]) -> float:
    """Estimate videos per month from a list of videos."""
    if len(videos) < 2:
        return 0

    dates = []
    for v in videos:
        try:
            dt = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
            dates.append(dt)
        except (ValueError, KeyError):
            continue

    if len(dates) < 2:
        return 0

    dates.sort()
    span_days = (dates[-1] - dates[0]).days
    if span_days <= 0:
        return 0

    months = span_days / 30.0
    return round(len(dates) / months, 1)


def _empty_analysis() -> dict:
    return {
        "shorts_count": 0,
        "longform_count": 0,
        "last_upload_date": "",
        "upload_frequency": 0,
        "avg_duration_seconds": 0,
        "avg_views": 0,
        "avg_likes": 0,
        "avg_comments": 0,
        "engagement_rate": 0,
        "top_3_videos": [],
        "emails_from_descriptions": [],
    }
