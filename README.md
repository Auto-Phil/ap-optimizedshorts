# YouTube Channel Scraper

Finds YouTube creators who are good candidates for a shorts creation service. Searches by niche, filters by subscriber count and content mix, scores leads, and exports to Google Sheets or CSV.

## Setup

### 1. Get a YouTube Data API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable **YouTube Data API v3** under APIs & Services → Library
4. Go to APIs & Services → Credentials → Create Credentials → API Key
5. Copy the key

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your YouTube API key:

```
YOUTUBE_API_KEY=your_key_here
```

### 4. Google Sheets Export (Optional)

If you want results pushed to Google Sheets:

1. In Google Cloud Console, enable the **Google Sheets API** and **Google Drive API**
2. Create a Service Account under Credentials
3. Download the JSON key file as `credentials.json` in the project root
4. Create a Google Sheet and share it with the service account email (found in the JSON file)
5. Set the sheet name in `.env`:
   ```
   GOOGLE_SHEET_NAME=YouTube Scraper Leads
   GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
   ```

If not configured, results automatically export to CSV.

## Usage

### Manual Run (All Niches)

```bash
python scraper.py
```

### Run Specific Niches

```bash
python scraper.py "fitness training" "cooking recipes"
```

### Daily Scheduler

```bash
python scheduler.py
```

This runs the scraper immediately, then again every day at 3:00 AM (configurable in `config.py`).

### Windows Task Scheduler Alternative

1. Open Task Scheduler
2. Create Basic Task → set daily trigger
3. Action: Start a Program
   - Program: `python`
   - Arguments: `scraper.py`
   - Start in: `C:\Users\whitl\_dev\yt scraper`

### Linux/Mac Cron Alternative

```bash
crontab -e
```

Add:

```
0 3 * * * cd /path/to/yt-scraper && python scraper.py >> logs/cron.log 2>&1
```

## Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `MIN_SUBSCRIBERS` | 10,000 | Minimum subscriber count |
| `MAX_SUBSCRIBERS` | 500,000 | Maximum subscriber count |
| `MAX_SHORTS_COUNT` | 5 | Max shorts a channel can have |
| `MIN_LONGFORM_COUNT` | 20 | Min long-form videos required |
| `MAX_DAYS_SINCE_UPLOAD` | 30 | Must have uploaded within N days |
| `MIN_AVG_DURATION_SECONDS` | 480 | Preferred avg video length (8 min) |
| `SEARCH_NICHES` | 11 niches | List of search keywords |
| `MAX_CHANNELS_PER_RUN` | 100 | Max channels to analyze per run |
| `SCHEDULE_TIME` | "03:00" | Daily run time (24h format) |

### Priority Score Weights

The 1-10 priority score uses these weights:

- Subscriber count: 30%
- Engagement rate: 25%
- Upload consistency: 20%
- Views/subscriber ratio: 15%
- Niche fit: 10%

## Output

### CSV Columns

| Column | Description |
|---|---|
| `timestamp` | When the channel was scraped |
| `channel_id` | YouTube channel ID |
| `channel_name` | Channel display name |
| `channel_url` | Direct link to the channel |
| `subscriber_count` | Current subscribers |
| `total_view_count` | Lifetime views |
| `shorts_count` | Videos under 60 seconds |
| `longform_count` | Videos over 60 seconds |
| `last_upload_date` | Date of most recent upload |
| `upload_frequency` | Videos per month |
| `avg_views` | Avg views on last 10 videos |
| `engagement_rate` | (likes + comments) / views % |
| `priority_score` | 1-10 lead quality score |
| `primary_niche` | Search niche that found this channel |
| `contact_email` | Email if publicly available |
| `contact_available` | yes/no |
| `top_video_1-3_title` | Top 3 video titles by views |
| `top_video_1-3_url` | Top 3 video URLs |
| `status` | new / contacted / converted / rejected |

## API Quota

YouTube Data API v3 has a 10,000 unit daily quota. Approximate costs:

| Operation | Cost | Usage |
|---|---|---|
| `search.list` | 100 units | Finding channels by keyword |
| `channels.list` | 1 unit | Getting channel stats |
| `playlistItems.list` | 1 unit | Listing uploads |
| `videos.list` | 1 unit | Getting video details |

A typical run searching 11 niches uses ~1,100 units on search alone, leaving ~8,400 for channel analysis. Each channel costs roughly 5-10 units to fully analyze, so expect 50-100 channels per day.

## File Structure

```
youtube_scraper/
├── .env                  # API keys (not in git)
├── .env.example          # Template
├── .gitignore
├── requirements.txt
├── config.py             # All configurable settings
├── scraper.py            # Main entry point
├── youtube_api.py        # YouTube API wrapper
├── data_processor.py     # Filtering and scoring
├── export.py             # Google Sheets / CSV export
├── scheduler.py          # Daily automation
├── utils.py              # Logging, DB, helpers
├── logs/                 # Daily log files
└── cache/                # SQLite database
```

## Troubleshooting

**"YOUTUBE_API_KEY is not set"**
- Make sure `.env` exists and contains your key
- Make sure `python-dotenv` is installed

**"quotaExceeded" errors**
- You've hit the daily 10,000 unit limit
- Wait until midnight Pacific time for quota reset
- Or request a quota increase in Google Cloud Console

**Google Sheets export fails**
- Verify `credentials.json` exists and is a valid service account key
- Make sure the Google Sheet is shared with the service account email
- Check that Sheets API and Drive API are enabled in your Google Cloud project

**No channels found**
- Try broader search terms in `config.py` → `SEARCH_NICHES`
- Loosen filter criteria (lower `MIN_LONGFORM_COUNT`, raise `MAX_SHORTS_COUNT`)
- Check logs in the `logs/` directory for details

**Rate limiting / 503 errors**
- The scraper automatically retries up to 3 times with backoff
- If persistent, reduce `MAX_CHANNELS_PER_RUN`
