"""
Main scraper orchestration: search → filter → analyze → score → export.
"""

import sys
from datetime import datetime

import config
from utils import (
    log, QuotaTracker, init_db, channel_exists,
    upsert_channel, get_all_channel_ids, send_email_report,
)
from youtube_api import YouTubeAPI
from data_processor import analyze_channel_videos, passes_filters, compute_priority_score
from export import build_row, export


def run_scrape(niches: list[str] | None = None):
    """
    Execute one full scrape cycle.

    1. Search each niche for channels.
    2. Filter by subscriber count.
    3. Fetch video data and compute shorts/longform split.
    4. Apply all filters.
    5. Score qualifying channels.
    6. Export results.
    """
    start = datetime.now()
    log.info("=" * 60)
    log.info("Scraper run started at %s", start.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    init_db()
    quota = QuotaTracker()
    api = YouTubeAPI(quota)

    niches = niches or config.SEARCH_NICHES
    known_ids = get_all_channel_ids()
    candidate_ids: list[tuple[str, str]] = []  # (channel_id, niche)
    qualified_rows: list[dict] = []
    stats = {"searched": 0, "new_candidates": 0, "analyzed": 0, "qualified": 0, "skipped_dup": 0}

    # ── Phase 1: Search ──────────────────────────────────────────────────
    log.info("Phase 1: Searching %d niches …", len(niches))
    for niche in niches:
        if not quota.can_afford("search.list"):
            log.warning("Quota low — stopping search phase")
            break

        ids = api.search_channels(niche, max_results=config.SEARCH_RESULTS_PER_NICHE)
        stats["searched"] += len(ids)

        for cid in ids:
            if cid in known_ids:
                stats["skipped_dup"] += 1
                continue
            candidate_ids.append((cid, niche))
            known_ids.add(cid)

    stats["new_candidates"] = len(candidate_ids)
    log.info("Phase 1 complete: %d total IDs, %d new candidates, %d duplicates skipped",
             stats["searched"], stats["new_candidates"], stats["skipped_dup"])
    log.info(quota.summary())

    # ── Phase 2: Analyze each candidate ──────────────────────────────────
    log.info("Phase 2: Analyzing up to %d candidates …", min(len(candidate_ids), config.MAX_CHANNELS_PER_RUN))

    for i, (channel_id, niche) in enumerate(candidate_ids[:config.MAX_CHANNELS_PER_RUN]):
        if quota.remaining < 10:
            log.warning("Quota nearly exhausted — stopping analysis")
            break

        log.info("[%d/%d] Analyzing channel %s …", i + 1, min(len(candidate_ids), config.MAX_CHANNELS_PER_RUN), channel_id)

        try:
            # Get channel details
            channel = api.get_channel_details(channel_id)
            if not channel:
                log.debug("  Could not fetch channel details — skipping")
                continue

            # Quick language/region check before expensive video fetch
            country = channel.get("country", "")
            lang = channel.get("default_language", "")
            if config.ALLOWED_COUNTRIES and country and country not in config.ALLOWED_COUNTRIES:
                log.debug("  Country '%s' not in allowed list — skipping", country)
                continue
            if config.ALLOWED_LANGUAGES and lang and not any(lang.startswith(a) for a in config.ALLOWED_LANGUAGES):
                log.debug("  Language '%s' not in allowed list — skipping", lang)
                continue

            # Quick subscriber check before expensive video fetch
            subs = channel["subscriber_count"]
            if subs < config.MIN_SUBSCRIBERS or subs > config.MAX_SUBSCRIBERS:
                log.debug("  Subscriber count %d outside range — skipping", subs)
                continue

            # Fetch videos
            video_ids = api.get_upload_video_ids(
                channel["uploads_playlist_id"],
                max_items=config.MAX_VIDEOS_TO_SCAN,
            )
            if not video_ids:
                log.debug("  No videos found — skipping")
                continue

            videos = api.get_video_details(video_ids)
            analysis = analyze_channel_videos(videos)
            stats["analyzed"] += 1

            # Apply filters
            if not passes_filters(channel, analysis):
                log.debug("  Did not pass filters — skipping")
                continue

            # Score
            score = compute_priority_score(channel, analysis, niche)
            row = build_row(channel, analysis, score, niche)
            qualified_rows.append(row)
            stats["qualified"] += 1

            # Save to local DB
            upsert_channel(channel_id, channel["channel_name"], row)

            log.info("  ✓ QUALIFIED — %s | subs=%d shorts=%d longform=%d score=%.1f",
                     channel["channel_name"], subs, analysis["shorts_count"],
                     analysis["longform_count"], score)

        except Exception as e:
            log.error("  Error processing channel %s: %s", channel_id, e, exc_info=True)
            continue

    log.info(quota.summary())

    # ── Phase 3: Export ──────────────────────────────────────────────────
    log.info("Phase 3: Exporting %d qualified channels …", len(qualified_rows))

    # Sort by priority score descending
    qualified_rows.sort(key=lambda r: r["priority_score"], reverse=True)
    destination = export(qualified_rows)

    # ── Summary ──────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    summary = (
        f"Scraper run completed in {elapsed:.0f}s\n"
        f"  Channels searched:  {stats['searched']}\n"
        f"  Duplicates skipped: {stats['skipped_dup']}\n"
        f"  New candidates:     {stats['new_candidates']}\n"
        f"  Channels analyzed:  {stats['analyzed']}\n"
        f"  Channels qualified: {stats['qualified']}\n"
        f"  Exported to:        {destination}\n"
        f"  {quota.summary()}"
    )
    log.info("\n%s", summary)

    # Build top channels list for email
    top_channels = ""
    for i, row in enumerate(qualified_rows[:5], 1):
        subs_k = int(row.get("subscriber_count", 0)) // 1000
        eng = row.get("engagement_rate", 0)
        top_channels += f"  {i}. {row['channel_name']} ({subs_k}K subscribers, {eng}% engagement)\n"

    # Send email if configured (clean language to avoid spam filters)
    date_str = datetime.now().strftime("%B %d, %Y")
    email_body = (
        f"Hi,\n\n"
        f"Here is your daily YouTube channel report for {date_str}.\n\n"
        f"Results:\n"
        f"  - {stats['qualified']} new channels identified\n"
        f"  - {stats['analyzed']} channels reviewed\n"
        f"  - Exported to: {destination}\n\n"
    )
    if top_channels:
        email_body += f"Top channels found today:\n{top_channels}\n"
    email_body += "Full details are available in your export file.\n"

    send_email_report(
        subject=f"Daily YouTube Channel Report - {datetime.now().strftime('%b %d')}",
        body=email_body,
    )

    return qualified_rows


def main():
    """CLI entry point. Usage: python scraper.py [niche1] [niche2] ..."""
    niches = sys.argv[1:] if len(sys.argv) > 1 else None
    if niches:
        log.info("Running with custom niches: %s", niches)
    results = run_scrape(niches)
    print(f"\nDone — {len(results)} qualified channels found.")


if __name__ == "__main__":
    main()
