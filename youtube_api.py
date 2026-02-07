"""
YouTube Data API v3 wrapper with quota management and retry logic.
"""

import re
import time
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
from utils import log, QuotaTracker, iso_to_seconds, days_since


class YouTubeAPI:
    """Thin wrapper around the YouTube Data API v3."""

    def __init__(self, quota: QuotaTracker):
        if not config.YOUTUBE_API_KEY:
            raise RuntimeError("YOUTUBE_API_KEY is not set — check your .env file")
        self.youtube = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)
        self.quota = quota

    # ── generic retry helper ─────────────────────────────────────────────

    def _call(self, request, endpoint: str, quota_count: int = 1):
        """Execute an API request with retry and quota tracking."""
        if not self.quota.can_afford(endpoint, quota_count):
            log.warning("Quota exhausted — cannot call %s", endpoint)
            return None

        for attempt in range(1, config.API_MAX_RETRIES + 1):
            try:
                response = request.execute()
                self.quota.consume(endpoint, quota_count)
                return response
            except HttpError as e:
                if e.resp.status == 403 and "quotaExceeded" in str(e):
                    log.error("YouTube API quota exceeded")
                    return None
                if e.resp.status in (500, 503) and attempt < config.API_MAX_RETRIES:
                    log.warning("Retryable error (%s), attempt %d/%d",
                                e.resp.status, attempt, config.API_MAX_RETRIES)
                    time.sleep(config.API_RETRY_DELAY_SECONDS * attempt)
                    continue
                log.error("YouTube API error on %s: %s", endpoint, e)
                return None
            except Exception as e:
                log.error("Unexpected error on %s: %s", endpoint, e)
                return None
        return None

    # ── search ───────────────────────────────────────────────────────────

    def search_channels(self, query: str, max_results: int = 50) -> list[str]:
        """Search for channels by keyword. Returns list of channel IDs."""
        channel_ids = []
        page_token = None

        while len(channel_ids) < max_results:
            if not self.quota.can_afford("search.list"):
                break

            request = self.youtube.search().list(
                q=query,
                type="channel",
                part="snippet",
                maxResults=min(50, max_results - len(channel_ids)),
                pageToken=page_token,
            )
            response = self._call(request, "search.list")
            if not response:
                break

            for item in response.get("items", []):
                channel_ids.append(item["snippet"]["channelId"])

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        log.info("Search '%s' → %d channel IDs", query, len(channel_ids))
        return channel_ids

    # ── channel details ──────────────────────────────────────────────────

    def get_channel_details(self, channel_id: str) -> Optional[dict]:
        """Fetch channel statistics and metadata."""
        request = self.youtube.channels().list(
            id=channel_id,
            part="snippet,statistics,contentDetails,brandingSettings",
        )
        response = self._call(request, "channels.list")
        if not response or not response.get("items"):
            return None

        item = response["items"][0]
        snippet = item["snippet"]
        stats = item["statistics"]
        uploads_playlist = item["contentDetails"]["relatedPlaylists"]["uploads"]

        # Try to extract email from description
        description = snippet.get("description", "")
        email = self._extract_email(description)

        return {
            "channel_id": channel_id,
            "channel_name": snippet.get("title", ""),
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
            "description": description,
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "total_view_count": int(stats.get("viewCount", 0)),
            "total_video_count": int(stats.get("videoCount", 0)),
            "uploads_playlist_id": uploads_playlist,
            "contact_email": email,
            "country": snippet.get("country", ""),
            "default_language": snippet.get("defaultLanguage", ""),
            "published_at": snippet.get("publishedAt", ""),
        }

    # ── videos from uploads playlist ─────────────────────────────────────

    def get_upload_video_ids(self, playlist_id: str, max_items: int = 200) -> list[str]:
        """Fetch video IDs from a channel's uploads playlist."""
        video_ids = []
        page_token = None

        while len(video_ids) < max_items:
            if not self.quota.can_afford("playlistItems.list"):
                break

            request = self.youtube.playlistItems().list(
                playlistId=playlist_id,
                part="contentDetails",
                maxResults=min(50, max_items - len(video_ids)),
                pageToken=page_token,
            )
            response = self._call(request, "playlistItems.list")
            if not response:
                break

            for item in response.get("items", []):
                video_ids.append(item["contentDetails"]["videoId"])

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return video_ids

    # ── video details (batch) ────────────────────────────────────────────

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """Fetch details for a batch of videos (up to 50 at a time)."""
        all_videos = []

        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            if not self.quota.can_afford("videos.list"):
                break

            request = self.youtube.videos().list(
                id=",".join(batch),
                part="snippet,contentDetails,statistics",
            )
            response = self._call(request, "videos.list")
            if not response:
                break

            for item in response.get("items", []):
                snippet = item["snippet"]
                stats = item.get("statistics", {})
                duration_seconds = iso_to_seconds(item["contentDetails"]["duration"])

                all_videos.append({
                    "video_id": item["id"],
                    "title": snippet.get("title", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "duration_seconds": duration_seconds,
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "url": f"https://www.youtube.com/watch?v={item['id']}",
                    "description": snippet.get("description", ""),
                })

        return all_videos

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_email(text: str) -> str:
        """Find the first email address in a block of text."""
        match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        return match.group(0) if match else ""
