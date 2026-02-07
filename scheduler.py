"""
Daily automation scheduler.

Run this script to keep the scraper running on a schedule:
    python scheduler.py

Or set up a system-level scheduler instead:
  - Windows Task Scheduler: trigger python scraper.py daily
  - Linux/Mac cron: 0 3 * * * cd /path/to/project && python scraper.py
"""

import time
import schedule

import config
from utils import log
from scraper import run_scrape


def job():
    log.info("Scheduled scrape starting …")
    try:
        run_scrape()
    except Exception as e:
        log.error("Scheduled scrape failed: %s", e, exc_info=True)


def main():
    log.info("Scheduler started — scraper will run daily at %s", config.SCHEDULE_TIME)
    schedule.every().day.at(config.SCHEDULE_TIME).do(job)

    # Also run once immediately on startup
    log.info("Running initial scrape now …")
    job()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
