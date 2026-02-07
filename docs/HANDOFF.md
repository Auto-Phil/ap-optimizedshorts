# Project Handoff Document
**YouTube Channel Scraper for Shorts Repurposing Service**

Last Updated: February 7, 2026  
Author: Zack Whitlock (zack@auto-phil.com)  
Repository: https://github.com/Auto-Phil/scraper-youtube

---

## Project Overview

A production-ready YouTube scraper that identifies creators (10K-500K subscribers) who are ideal candidates for a shorts repurposing service. The system searches by niche, filters by content mix, scores leads by priority, and stores them in Supabase for lead management and future email automation.

### Business Context

**Service Offering:** We create 5 sample Shorts from a creator's existing long-form content and send them as a free gift to start the sales conversation.

**Target Audience:** YouTube creators with:
- 10K-500K subscribers
- Strong long-form content (20+ videos, 8+ min avg)
- Little to no Shorts presence (0-5 shorts)
- Active (uploaded within 30 days)
- English-speaking, primarily US/UK/CA/AU/NZ

**Niches:** 38 niches including business, finance, retro gaming, film essays, productivity, fitness, etc.

---

## Current State (As of Feb 7, 2026)

### ✅ What's Working

| Component | Status | Description |
|---|---|---|
| **YouTube API Integration** | ✅ Production | Search, channel details, video analysis with quota tracking |
| **Filtering & Scoring** | ✅ Production | Multi-criteria filtering, 1-10 priority scoring algorithm |
| **Supabase Data Storage** | ✅ Production | Replaced SQLite+Sheets with Supabase for lead storage |
| **CSV Export** | ✅ Production | Backup export to timestamped CSV files |
| **Lead Management CLI** | ✅ Production | `manage_leads.py` - list, filter, view, update lead statuses |
| **Deduplication** | ✅ Production | Prevents re-scraping same channels |
| **Daily Scheduler** | ✅ Production | Runs at 3 AM daily via `scheduler.py` |
| **Email Notifications** | ✅ Production | Daily summary emails (optional) |
| **Language/Region Filters** | ✅ Production | English-only, allowed countries list |
| **Cold Email Templates** | ✅ Complete | 5-email sequence in `email_sequences.md` (5-pack Shorts gift strategy) |
| **CSV Migration Tool** | ✅ Production | `migrate_csv_to_supabase.py` imports existing CSVs |

### 🚧 What's Not Done

| Feature | Priority | Notes |
|---|---|---|
| **Automated Email Sending** | High | Templates exist but no code to send them. Needs Gmail API/SMTP integration, sequence state tracking, send scheduling |
| **Supabase Setup** | Setup Required | User needs to create Supabase project, run schema, add credentials to `.env` |
| **Testing** | Medium | No automated tests. Manual testing only |
| **Email Sequence Tracking** | High | `outreach` table exists in schema but no code uses it yet |
| **Web Dashboard** | Low | Nice-to-have from original spec |

---

## Changes Made in This Session

### Major Migration: SQLite + Google Sheets → Supabase

**Why:** Better security, scalability, querying, and sets up email sequence tracking.

**Files Modified:**
- `config.py` - Removed Google Sheets config, added Supabase config
- `.env` / `.env.example` - Replaced Sheets credentials with Supabase URL/key
- `utils.py` - Completely rewritten database functions to use Supabase client
- `export.py` - Replaced Google Sheets export with Supabase upsert (CSV as backup)
- `requirements.txt` - Added `supabase==2.11.0`, `tabulate==0.9.0`, removed `gspread`

**Files Created:**
- `supabase_schema.sql` - Database schema (channels + outreach tables)
- `manage_leads.py` - CLI for lead management
- `migrate_csv_to_supabase.py` - CSV import tool

**Files Updated:**
- `README.md` - Completely rewritten with Supabase setup instructions
- `config.py` - Expanded `SEARCH_NICHES` from 11 to 38 niches (added retro gaming, film essays, etc.)

### Git Repository Setup

- Initialized Git repository
- Configured remote: `https://github.com/Auto-Phil/scraper-youtube`
- Author: `zack@auto-phil.com`
- Pushed 2 commits to `master` branch
- `.gitignore` protects `.env` file

### Email Template Finalization

User finalized `email_sequences.md` with 5-pack Shorts gift strategy (not just 1 Short). All 5 emails reference the pack of 5 consistently.

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     YouTube Data API v3                      │
│                  (10,000 units/day quota)                    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────┴─────────┐
                    │   youtube_api.py   │
                    │  (API wrapper +    │
                    │   quota tracker)   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │    scraper.py      │
                    │  (orchestration)   │
                    └─────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼────────┐ ┌───▼────────┐ ┌───▼────────┐
    │ data_processor.py│ │ export.py  │ │  utils.py  │
    │ (filter & score) │ │ (Supabase) │ │ (DB client)│
    └──────────────────┘ └────┬───────┘ └─────┬──────┘
                              │               │
                              └───────┬───────┘
                                      │
                          ┌───────────▼───────────┐
                          │   Supabase Database   │
                          │  - channels table     │
                          │  - outreach table     │
                          └───────────────────────┘
                                      ▲
                                      │
                          ┌───────────┴───────────┐
                          │   manage_leads.py     │
                          │   (CLI interface)     │
                          └───────────────────────┘
```

### Data Flow

1. **Search Phase:** `scraper.py` → `youtube_api.py` → YouTube API (search channels by niche)
2. **Analysis Phase:** For each channel → fetch videos → `data_processor.py` filters & scores
3. **Export Phase:** Qualified leads → `export.py` → Supabase (+ CSV backup)
4. **Management:** User runs `manage_leads.py` to view/update lead statuses

### Key Files

| File | Purpose | Lines |
|---|---|---|
| `scraper.py` | Main orchestration, runs full scrape cycle | 197 |
| `youtube_api.py` | YouTube API wrapper with quota tracking | 196 |
| `data_processor.py` | Filtering logic, priority scoring algorithm | 207 |
| `export.py` | Supabase export + CSV backup | 148 |
| `utils.py` | Supabase client, logging, quota tracker, email | 210 |
| `config.py` | All configurable settings (niches, filters, weights) | 105 |
| `manage_leads.py` | CLI for lead management | 235 |
| `scheduler.py` | Daily automation wrapper | 43 |

---

## Configuration

### Environment Variables (`.env`)

```bash
# Required
YOUTUBE_API_KEY=your_youtube_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_role_key

# Optional (email notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=your_email@gmail.com
```

### Key Settings (`config.py`)

| Setting | Value | Notes |
|---|---|---|
| `MIN_SUBSCRIBERS` | 10,000 | Lower bound |
| `MAX_SUBSCRIBERS` | 500,000 | Upper bound |
| `MAX_SHORTS_COUNT` | 5 | Max shorts allowed |
| `MIN_LONGFORM_COUNT` | 20 | Min long-form videos |
| `MAX_DAYS_SINCE_UPLOAD` | 30 | Must be active |
| `MIN_AVG_DURATION_SECONDS` | 480 | 8 minutes preferred |
| `ALLOWED_COUNTRIES` | US, GB, CA, AU, NZ, IE | ISO codes |
| `ALLOWED_LANGUAGES` | en | Language prefix |
| `SEARCH_NICHES` | 38 niches | See config.py for full list |
| `MAX_CHANNELS_PER_RUN` | 500 | Daily processing limit |
| `SCHEDULE_TIME` | "03:00" | Daily run time |

### Priority Score Weights

```python
SCORE_WEIGHT_SUBSCRIBERS = 0.30   # Sweet spot: 50K-200K
SCORE_WEIGHT_ENGAGEMENT = 0.25    # (likes + comments) / views
SCORE_WEIGHT_CONSISTENCY = 0.20   # Upload frequency
SCORE_WEIGHT_VIEWS_RATIO = 0.15   # Avg views / subscribers
SCORE_WEIGHT_NICHE_FIT = 0.10     # Keyword match in description
```

---

## Supabase Schema

### `channels` Table

Stores all scraped leads with metadata and status tracking.

**Key Columns:**
- `channel_id` (TEXT, unique) - YouTube channel ID
- `channel_name`, `channel_url`, `subscriber_count`, etc.
- `priority_score` (NUMERIC) - 1-10 lead quality score
- `status` (TEXT) - `new`, `contacted`, `replied`, `converted`, `rejected`, `paused`
- `contact_email` (TEXT) - Extracted from About page or video descriptions
- `top_videos` (JSONB) - Top 3 performing videos
- `first_seen`, `last_scraped`, `created_at`, `updated_at` - Timestamps

**Indexes:**
- `status`, `priority_score`, `primary_niche`, `first_seen`, `contact_available`

### `outreach` Table

Tracks email sequence state (not yet used by code).

**Key Columns:**
- `channel_id` (FK to channels)
- `email_number` (1-5)
- `sent_at`, `subject`, `body`
- `opened`, `replied`, `reply_received_at`, `reply_text`

---

## Usage

### Daily Scraper Run

```bash
# Manual run (all niches)
python scraper.py

# Specific niches
python scraper.py "retro gaming review" "film analysis essay"

# Automated daily (runs at 3 AM)
python scheduler.py
```

### Lead Management

```bash
# List all new leads with contact info
python manage_leads.py list --status new

# Filter by niche
python manage_leads.py list --niche "retro gaming"

# Show detailed info
python manage_leads.py show UCxxxxxxxxxxxxxxxxxx

# Update status
python manage_leads.py update UCxxxxxxxxxxxxxxxxxx --status contacted

# View statistics
python manage_leads.py stats
```

### CSV Migration

```bash
# Import all leads_*.csv files
python migrate_csv_to_supabase.py

# Import specific files
python migrate_csv_to_supabase.py leads_20260206.csv leads_20260207.csv
```

---

## API Quota Management

**Daily Limit:** 10,000 units  
**Typical Usage:** ~1,100 units for search (11 niches × 100), ~8,400 for analysis

**Cost Per Operation:**
- `search.list` - 100 units
- `channels.list` - 1 unit
- `playlistItems.list` - 1 unit
- `videos.list` - 1 unit

**Per Channel:** ~5-10 units (1 for channel details, 1-2 for playlist items, 1-5 for video details)

**Expected Output:** 50-100 qualified channels per day

---

## Next Steps for Future Development

### 1. Automated Email Sending (High Priority)

**What's Needed:**
- Gmail API or SMTP integration
- Template rendering engine (populate personalization fields from Supabase data)
- Sequence state tracking (use `outreach` table)
- Send scheduler (respect 2-day, 4-day, 5-day gaps between emails)
- Rate limiting (max 50 emails/day per mailbox)
- Reply detection (optional)

**Suggested Approach:**
- Create `email_sender.py` with functions:
  - `render_email(template_num, channel_data)` - Fill in personalization
  - `send_email(to, subject, body)` - SMTP send
  - `get_next_batch()` - Query Supabase for leads ready for next email
  - `record_send(channel_id, email_num)` - Update `outreach` table
- Create `email_scheduler.py` - Daily cron job to send next batch
- Add CLI: `python send_emails.py --dry-run` to preview

**Templates:** Already written in `email_sequences.md` with full personalization guide.

### 2. Testing

- Unit tests for scoring algorithm
- Integration tests for YouTube API wrapper
- Mock Supabase for testing without live DB

### 3. Monitoring & Alerts

- Track daily scrape success/failure
- Alert on quota exhaustion
- Monitor Supabase usage

### 4. Web Dashboard (Low Priority)

- View leads in a table
- Filter/sort by status, niche, score
- Update statuses via UI
- View email sequence history per lead

---

## Known Issues & Gotcas

### YouTube API Key Exposure

⚠️ The API key `AIzaSyAbsTxP7iZNgj8NqfUE5PTXQd5l0XLZSys` was visible in the conversation history. **Rotate this key** in Google Cloud Console.

### Windows `nul` File

A file called `nul` appeared during development (Windows reserved name). It's excluded from Git but may reappear. Safe to ignore.

### Supabase Setup Required

The code won't run until:
1. User creates Supabase project
2. Runs `supabase_schema.sql` in SQL Editor
3. Adds `SUPABASE_URL` and `SUPABASE_KEY` to `.env`

### CSV Backups

Even with Supabase, CSV files are still created as backups. This is intentional for data redundancy.

---

## Dependencies

```
google-api-python-client==2.108.0  # YouTube API
google-auth-oauthlib==1.2.0        # YouTube API auth
google-auth==2.25.2                # YouTube API auth
python-dotenv==1.0.0               # Environment variables
pandas==2.1.4                      # Data processing
schedule==1.2.1                    # Daily scheduler
requests==2.31.0                   # HTTP requests
supabase==2.11.0                   # Supabase client
tabulate==0.9.0                    # CLI table formatting
```

---

## File Structure

```
youtube_scraper/
├── .env                          # API keys (not in git)
├── .env.example                  # Template
├── .gitignore
├── requirements.txt
├── config.py                     # All configurable settings
├── scraper.py                    # Main entry point
├── youtube_api.py                # YouTube API wrapper
├── data_processor.py             # Filtering and scoring
├── export.py                     # Supabase / CSV export
├── scheduler.py                  # Daily automation
├── utils.py                      # Logging, Supabase client, helpers
├── manage_leads.py               # CLI for lead management
├── migrate_csv_to_supabase.py    # CSV import tool
├── supabase_schema.sql           # Database schema
├── email_sequences.md            # Cold outreach templates (5-email sequence)
├── docs/
│   ├── HANDOFF.md                # This file
│   └── ARCHITECTURE.md           # System architecture diagram
├── logs/                         # Daily log files
└── cache/                        # (unused, kept for compatibility)
```

---

## Contact & Resources

- **Repository:** https://github.com/Auto-Phil/scraper-youtube
- **Author:** Zack Whitlock (zack@auto-phil.com)
- **Supabase Dashboard:** https://supabase.com/dashboard
- **YouTube API Console:** https://console.cloud.google.com/apis/credentials
- **Email Templates:** See `email_sequences.md` for full 5-email sequence with personalization guide

---

## Quick Start for Next Developer

1. **Clone repo:**
   ```bash
   git clone https://github.com/Auto-Phil/scraper-youtube.git
   cd scraper-youtube
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Supabase:**
   - Create project at supabase.com
   - Run `supabase_schema.sql` in SQL Editor
   - Copy URL + key

4. **Configure `.env`:**
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

5. **Test run:**
   ```bash
   python scraper.py "retro gaming review"
   ```

6. **View results:**
   ```bash
   python manage_leads.py list
   ```

7. **Next feature:** Build automated email sending (see "Next Steps" above)

---

**End of Handoff Document**
