# System Architecture Diagram
**YouTube Channel Scraper for Shorts Repurposing Service**

---

## High-Level Architecture

```mermaid
graph TD
    subgraph "External Services"
        YT[YouTube Data API v3<br/>10,000 units/day quota]
        SB[(Supabase Database<br/>PostgreSQL)]
        SMTP[SMTP Server<br/>Email Notifications]
    end

    subgraph "Core Application"
        subgraph "Entry Points"
            CLI1[scraper.py<br/>Main CLI]
            CLI2[manage_leads.py<br/>Lead Management CLI]
            CLI3[migrate_csv_to_supabase.py<br/>CSV Import CLI]
            SCHED[scheduler.py<br/>Daily Automation]
        end

        subgraph "Business Logic Layer"
            API[youtube_api.py<br/>API Wrapper + Quota Tracker]
            PROC[data_processor.py<br/>Filter & Score Engine]
            EXP[export.py<br/>Data Export Handler]
            UTIL[utils.py<br/>DB Client + Helpers]
        end

        subgraph "Configuration"
            CFG[config.py<br/>Settings & Filters]
            ENV[.env<br/>Credentials]
        end

        subgraph "Data Storage"
            CSV[CSV Files<br/>Backup Export]
            LOGS[Log Files<br/>Daily Logs]
        end
    end

    subgraph "Documentation"
        EMAIL[email_sequences.md<br/>5-Email Templates]
        README[README.md<br/>Setup Guide]
        SCHEMA[supabase_schema.sql<br/>DB Schema]
    end

    %% Entry point flows
    CLI1 --> API
    CLI1 --> PROC
    CLI1 --> EXP
    CLI1 --> UTIL
    SCHED --> CLI1
    CLI2 --> UTIL
    CLI3 --> UTIL

    %% Business logic flows
    API --> YT
    API --> CFG
    PROC --> CFG
    EXP --> UTIL
    EXP --> CSV
    UTIL --> SB
    UTIL --> SMTP
    UTIL --> LOGS
    UTIL --> ENV

    %% Configuration dependencies
    CFG --> ENV

    %% Styling
    classDef external fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef entry fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef logic fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef config fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef storage fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef docs fill:#f1f8e9,stroke:#33691e,stroke-width:2px

    class YT,SB,SMTP external
    class CLI1,CLI2,CLI3,SCHED entry
    class API,PROC,EXP,UTIL logic
    class CFG,ENV config
    class CSV,LOGS storage
    class EMAIL,README,SCHEMA docs
```

---

## Detailed Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Scraper as scraper.py
    participant API as youtube_api.py
    participant YouTube as YouTube API
    participant Processor as data_processor.py
    participant Export as export.py
    participant Utils as utils.py
    participant Supabase as Supabase DB

    User->>Scraper: python scraper.py
    Scraper->>Utils: init_db()
    Utils->>Supabase: Verify connection
    Supabase-->>Utils: Connection OK
    
    loop For each niche
        Scraper->>API: search_channels(niche)
        API->>YouTube: search.list
        YouTube-->>API: Channel IDs
        API->>API: Track quota usage
        API-->>Scraper: List of channel IDs
        
        loop For each channel
            Scraper->>API: get_channel_details(id)
            API->>YouTube: channels.list
            YouTube-->>API: Channel metadata
            
            Scraper->>API: get_upload_video_ids(playlist_id)
            API->>YouTube: playlistItems.list
            YouTube-->>API: Video IDs
            
            Scraper->>API: get_video_details(video_ids)
            API->>YouTube: videos.list
            YouTube-->>API: Video metadata
            
            Scraper->>Processor: analyze_channel_videos(videos)
            Processor-->>Scraper: Analysis results
            
            Scraper->>Processor: passes_filters(channel, analysis)
            Processor-->>Scraper: true/false
            
            alt Channel qualifies
                Scraper->>Processor: compute_priority_score(...)
                Processor-->>Scraper: Score (1-10)
                
                Scraper->>Export: build_row(channel, analysis, score)
                Export-->>Scraper: Formatted row
            end
        end
    end
    
    Scraper->>Export: export(qualified_rows)
    Export->>Utils: upsert_channel() for each row
    Utils->>Supabase: INSERT/UPDATE channels
    Supabase-->>Utils: Success
    Export->>Export: export_to_csv() (backup)
    Export-->>Scraper: Export complete
    
    Scraper->>Utils: send_email_report(summary)
    Utils->>Utils: SMTP send
    
    Scraper-->>User: Done - N qualified channels
```

---

## Component Breakdown

### 1. Entry Points

| Component | Purpose | Key Functions |
|---|---|---|
| **scraper.py** | Main orchestration - runs full scrape cycle | `run_scrape()`, `main()` |
| **scheduler.py** | Daily automation wrapper | `job()`, runs at 3 AM |
| **manage_leads.py** | CLI for lead management | `list_leads()`, `show_lead()`, `update_lead_status()`, `show_stats()` |
| **migrate_csv_to_supabase.py** | Import existing CSV data | `migrate_csv_file()` |

### 2. Business Logic Layer

| Component | Purpose | Key Functions |
|---|---|---|
| **youtube_api.py** | YouTube API wrapper with quota tracking | `search_channels()`, `get_channel_details()`, `get_upload_video_ids()`, `get_video_details()` |
| **data_processor.py** | Filtering and scoring engine | `analyze_channel_videos()`, `passes_filters()`, `compute_priority_score()` |
| **export.py** | Data export to Supabase + CSV | `export_to_supabase()`, `export_to_csv()`, `build_row()` |
| **utils.py** | Supabase client, logging, helpers | `get_supabase_client()`, `upsert_channel()`, `update_channel_status()`, `send_email_report()` |

### 3. Configuration

| Component | Purpose |
|---|---|
| **config.py** | All settings: filters, niches, weights, paths |
| **.env** | Credentials: YouTube API key, Supabase URL/key, SMTP |

### 4. Data Storage

| Component | Purpose |
|---|---|
| **Supabase** | Primary data store (channels + outreach tables) |
| **CSV Files** | Backup export (leads_YYYYMMDD.csv) |
| **Log Files** | Daily logs (logs/scraper_YYYYMMDD.log) |

---

## Database Schema

```mermaid
erDiagram
    CHANNELS ||--o{ OUTREACH : "has"
    
    CHANNELS {
        bigserial id PK
        text channel_id UK "YouTube channel ID"
        text channel_name
        text channel_url
        integer subscriber_count
        bigint total_view_count
        integer total_video_count
        integer shorts_count
        integer longform_count
        timestamptz last_upload_date
        numeric upload_frequency
        integer avg_views
        integer avg_duration_seconds
        numeric engagement_rate
        numeric priority_score "1-10 lead quality"
        text primary_niche
        text country
        text language
        text contact_email
        boolean contact_available
        jsonb top_videos "Top 3 videos"
        text status "new|contacted|replied|converted|rejected|paused"
        timestamptz first_seen
        timestamptz last_scraped
        timestamptz created_at
        timestamptz updated_at
    }
    
    OUTREACH {
        bigserial id PK
        text channel_id FK
        integer email_number "1-5"
        timestamptz sent_at
        text subject
        text body
        boolean opened
        boolean replied
        timestamptz reply_received_at
        text reply_text
        timestamptz created_at
    }
```

---

## Priority Scoring Algorithm

```mermaid
graph LR
    subgraph "Input Metrics"
        A[Subscriber Count]
        B[Engagement Rate]
        C[Upload Frequency]
        D[Views/Subs Ratio]
        E[Niche Fit]
    end
    
    subgraph "Normalization"
        A --> A1[Sweet Spot Curve<br/>50K-200K = 10]
        B --> B1[Linear Scale<br/>5% = 10]
        C --> C1[Linear Scale<br/>4/month = 10]
        D --> D1[Linear Scale<br/>10% = 10]
        E --> E1[Keyword Match<br/>in description]
    end
    
    subgraph "Weighted Sum"
        A1 -->|30%| W[Priority Score]
        B1 -->|25%| W
        C1 -->|20%| W
        D1 -->|15%| W
        E1 -->|10%| W
    end
    
    W --> OUT[1-10 Score]
```

**Formula:**
```
score = (
    subscriber_score * 0.30 +
    engagement_score * 0.25 +
    consistency_score * 0.20 +
    views_ratio_score * 0.15 +
    niche_fit_score * 0.10
)
```

---

## API Quota Management

```mermaid
graph TD
    START[Daily Quota: 10,000 units] --> SEARCH
    
    subgraph "Search Phase"
        SEARCH[Search 38 niches<br/>38 × 100 = 3,800 units]
    end
    
    SEARCH --> REMAINING[Remaining: 6,200 units]
    
    subgraph "Analysis Phase"
        REMAINING --> CHANNEL[Per Channel:<br/>1 + 1-2 + 1-5 = 3-8 units]
        CHANNEL --> CAPACITY[Capacity:<br/>6,200 ÷ 6 avg = ~1,000 channels]
    end
    
    CAPACITY --> FILTER[Apply Filters]
    FILTER --> QUALIFIED[Expected Output:<br/>50-100 qualified channels]
    
    style START fill:#e1f5ff
    style QUALIFIED fill:#c8e6c9
```

---

## Filtering Pipeline

```mermaid
graph TD
    START[Channel Found] --> SUB{Subscribers<br/>10K-500K?}
    SUB -->|No| REJECT1[❌ Reject]
    SUB -->|Yes| COUNTRY{Country in<br/>allowed list?}
    
    COUNTRY -->|No| REJECT2[❌ Reject]
    COUNTRY -->|Yes| LANG{Language<br/>starts with 'en'?}
    
    LANG -->|No| REJECT3[❌ Reject]
    LANG -->|Yes| FETCH[Fetch Videos]
    
    FETCH --> SHORTS{Shorts count<br/>≤ 5?}
    SHORTS -->|No| REJECT4[❌ Reject]
    SHORTS -->|Yes| LONG{Long-form<br/>≥ 20?}
    
    LONG -->|No| REJECT5[❌ Reject]
    LONG -->|Yes| ACTIVE{Uploaded in<br/>last 30 days?}
    
    ACTIVE -->|No| REJECT6[❌ Reject]
    ACTIVE -->|Yes| SCORE[Calculate<br/>Priority Score]
    
    SCORE --> EXPORT[✅ Export to<br/>Supabase]
    
    style START fill:#e3f2fd
    style EXPORT fill:#c8e6c9
    style REJECT1 fill:#ffcdd2
    style REJECT2 fill:#ffcdd2
    style REJECT3 fill:#ffcdd2
    style REJECT4 fill:#ffcdd2
    style REJECT5 fill:#ffcdd2
    style REJECT6 fill:#ffcdd2
```

---

## Architecture Summary

### 1. Architecture Style
**Monolithic CLI Application** with external service integrations (YouTube API, Supabase, SMTP).

- Single Python codebase
- Modular design with clear separation of concerns
- Stateless execution (all state in Supabase)
- Scheduled batch processing (daily runs)

### 2. Key Components

**Entry Layer:**
- `scraper.py` - Main orchestrator
- `manage_leads.py` - Lead management interface
- `scheduler.py` - Automation wrapper

**Business Logic:**
- `youtube_api.py` - API client with quota tracking
- `data_processor.py` - Filtering and scoring algorithms
- `export.py` - Multi-destination export handler
- `utils.py` - Shared utilities and database client

**Data Layer:**
- Supabase (primary) - PostgreSQL with REST API
- CSV files (backup) - Local timestamped exports
- Log files - Daily operation logs

### 3. Data Flow

1. **Search Phase:** Query YouTube API for channels matching niche keywords
2. **Deduplication:** Check Supabase for existing channel IDs
3. **Analysis Phase:** For each new channel, fetch videos and compute metrics
4. **Filtering Phase:** Apply multi-criteria filters (subscribers, shorts count, activity, etc.)
5. **Scoring Phase:** Calculate 1-10 priority score using weighted algorithm
6. **Export Phase:** Upsert to Supabase + write CSV backup
7. **Notification Phase:** Send email summary (optional)

### 4. Notable Patterns

**Quota Management:**
- Centralized `QuotaTracker` class monitors API usage
- Pre-flight checks before expensive operations
- Graceful degradation when quota exhausted

**Error Handling:**
- Retry logic with exponential backoff for transient failures
- Continue-on-error for individual channel failures
- Comprehensive logging at DEBUG and INFO levels

**Deduplication:**
- Supabase unique constraint on `channel_id`
- In-memory set for fast duplicate checking during run
- Upsert pattern updates existing records on re-scrape

**Configuration:**
- All settings centralized in `config.py`
- Environment-specific values in `.env`
- Easy to adjust filters without code changes

**Extensibility:**
- `outreach` table ready for email automation
- Status field supports workflow states
- Modular design allows adding new export destinations

---

## Future Architecture Considerations

### Email Automation System (Next Phase)

```mermaid
graph TD
    subgraph "Email Automation (Future)"
        CRON[Daily Cron Job]
        SENDER[email_sender.py]
        TEMPLATES[email_sequences.md]
        GMAIL[Gmail API / SMTP]
    end
    
    CRON --> SENDER
    SENDER --> SB[(Supabase)]
    SENDER --> TEMPLATES
    SENDER --> GMAIL
    
    SB --> |Query leads ready<br/>for next email| SENDER
    SENDER --> |Record send| SB
    
    style CRON fill:#fff3e0
    style SENDER fill:#f3e5f5
    style TEMPLATES fill:#e8f5e9
```

**Design Notes:**
- Separate `email_sender.py` module
- Template rendering with Jinja2 or simple string replacement
- State machine: new → email1 → email2 → ... → email5
- Respect timing gaps (2 days, 4 days, 5 days)
- Rate limiting (50 emails/day per mailbox)
- Reply detection via IMAP (optional)

---

**End of Architecture Document**
