/* ────────────────────────────────
   1. Reference tables
   ──────────────────────────────── */
CREATE TABLE games (
    game_id     UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT        NOT NULL UNIQUE,
    genre       TEXT,
    keywords    TEXT[],
    context     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE taxonomy (
    taxon_id    SERIAL      PRIMARY KEY,
    parent_id   INT         REFERENCES taxonomy(taxon_id),
    level       TEXT        NOT NULL
                 CHECK (level IN ('category','feature','subfeature')),
    name        TEXT        NOT NULL UNIQUE,
    description TEXT
);

/* ────────────────────────────────
   2. Video tracking system
   ──────────────────────────────── */
CREATE TABLE videos (
    video_id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id             UUID        REFERENCES games ON DELETE CASCADE,
    video_path          TEXT        NOT NULL,           -- Local path to video file
    youtube_url         TEXT        UNIQUE,             -- YouTube URL if applicable
    upload_date         TIMESTAMPTZ,                    -- When video was uploaded/created
    duration_seconds    INTEGER,                        -- Total video duration
    title               TEXT,                           -- Video title
    description         TEXT,                           -- Video description
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_video_path UNIQUE (video_path)
);

-- Performance indexes for video queries
CREATE INDEX ix_videos_game_id ON videos (game_id);
CREATE INDEX ix_videos_upload_date ON videos (upload_date);
CREATE INDEX ix_videos_youtube_url ON videos (youtube_url) WHERE youtube_url IS NOT NULL;

/* ────────────────────────────────
   3. Per-game features
   ──────────────────────────────── */
CREATE TABLE features_game (
    feature_id   SERIAL      PRIMARY KEY,
    game_id      UUID        REFERENCES games ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    description  TEXT,
    first_seen   TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    ui_flow      TEXT,                       -- optional free-text
    CONSTRAINT uq_game_feature UNIQUE (game_id, name)
);

CREATE TABLE taxon_features_xref (
    taxon_id    INT  REFERENCES taxonomy      ON DELETE CASCADE,
    feature_id  INT  REFERENCES features_game ON DELETE CASCADE,
    confidence  REAL CHECK (confidence BETWEEN 0 AND 1),
    PRIMARY KEY (taxon_id, feature_id)
);

/* ────────────────────────────────
   4. Screens + global navigation
   ──────────────────────────────── */
CREATE TABLE screens (
    screen_id    SERIAL PRIMARY KEY,
    game_id      UUID REFERENCES games ON DELETE CASCADE,
    screen_name  TEXT,
    description  TEXT,
    first_seen   TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    layout_hash  BYTEA UNIQUE
);

CREATE TABLE screen_feature_xref (
    screen_id   INT REFERENCES screens        ON DELETE CASCADE,
    feature_id  INT REFERENCES features_game  ON DELETE CASCADE,
    PRIMARY KEY (screen_id, feature_id)
);

CREATE TABLE screenflow_xref (
    from_screen_id  INT REFERENCES screens ON DELETE CASCADE,
    to_screen_id    INT REFERENCES screens ON DELETE CASCADE,
    action_label    TEXT,               -- NULL for passive-video flows
    ordinal         INT,
    PRIMARY KEY (from_screen_id, to_screen_id, ordinal)
);

/* ────────────────────────────────
   5. Screenshots & mappings (updated with video tracking)
   ──────────────────────────────── */
CREATE TABLE screenshots (
    screenshot_id           UUID PRIMARY KEY        DEFAULT uuid_generate_v4(),
    path                    TEXT        NOT NULL UNIQUE,   -- file or URL
    game_id                 UUID        REFERENCES games   ON DELETE CASCADE,
    screen_id               INT         REFERENCES screens ON DELETE CASCADE,
    session_id              UUID,
    capture_time            TIMESTAMPTZ,
    caption                 TEXT,
    elements                JSONB,                -- [{name,description,type}]
    modal                   BOOLEAN DEFAULT FALSE,
    modal_name              TEXT,
    embedding               VECTOR(768),
    sha256                  BYTEA UNIQUE,
    -- Video tracking columns (added via migration)
    screenshot_timestamp    TIMESTAMPTZ,          -- When screenshot was captured
    video_timestamp_seconds INTEGER               -- Position in video (seconds from start)
);

-- Performance indexes
CREATE INDEX ix_shots_game_time  ON screenshots (game_id, capture_time);
CREATE INDEX ix_shots_embedding  ON screenshots USING ivfflat (embedding vector_cosine_ops);
-- Video tracking indexes
CREATE INDEX ix_shots_video_timestamp ON screenshots (video_timestamp_seconds) WHERE video_timestamp_seconds IS NOT NULL;
CREATE INDEX ix_shots_screenshot_timestamp ON screenshots (screenshot_timestamp) WHERE screenshot_timestamp IS NOT NULL;

/* ────────────────────────────────
   6. Screenshot-Video cross-reference table
   ──────────────────────────────── */
CREATE TABLE screenshot_video_xref (
    screenshot_id           UUID REFERENCES screenshots ON DELETE CASCADE,
    video_id                UUID REFERENCES videos ON DELETE CASCADE,
    video_timestamp_seconds INTEGER NOT NULL,        -- Position in video where screenshot was taken
    confidence              REAL CHECK (confidence BETWEEN 0 AND 1) DEFAULT 1.0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (screenshot_id, video_id)
);

-- Performance indexes for video-screenshot relationships
CREATE INDEX ix_screenshot_video_timestamp ON screenshot_video_xref (video_id, video_timestamp_seconds);
CREATE INDEX ix_screenshot_video_confidence ON screenshot_video_xref (confidence) WHERE confidence < 1.0;

CREATE TABLE screenshot_feature_xref (
    screenshot_id UUID REFERENCES screenshots   ON DELETE CASCADE,
    feature_id    INT  REFERENCES features_game ON DELETE CASCADE,
    confidence    REAL CHECK (confidence BETWEEN 0 AND 1),
    first_tagged  TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (screenshot_id, feature_id)
);

CREATE TABLE taxon_screenshots_xref (
    taxon_id       INT  REFERENCES taxonomy    ON DELETE CASCADE,
    screenshot_id  UUID REFERENCES screenshots ON DELETE CASCADE,
    confidence     REAL CHECK (confidence BETWEEN 0 AND 1),
    PRIMARY KEY (taxon_id, screenshot_id)
);

/* ────────────────────────────────
   7. Feature change log (optional)
   ──────────────────────────────── */
CREATE TABLE feature_updates (
    update_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_id       INT REFERENCES features_game ON DELETE CASCADE,
    change_time      TIMESTAMPTZ DEFAULT now(),
    description      TEXT,
    screenshots_old  UUID[],   -- arrays are fine for prototype diffs
    screenshots_new  UUID[]
);

/* ────────────────────────────────
   8. Single-table feature flow
   ──────────────────────────────── */
CREATE TABLE feature_flow_step (
    flow_id        UUID DEFAULT uuid_generate_v4(),
    feature_id     INT  REFERENCES features_game ON DELETE CASCADE,
    step_index     INT,                         -- 0 = header row
    screenshot_id  UUID REFERENCES screenshots, -- NULL for header
    action_label   TEXT,
    session_id     UUID,
    title          TEXT,
    notes          TEXT,
    PRIMARY KEY (flow_id, step_index),
    CHECK ( (step_index = 0) = (screenshot_id IS NULL) )
);

/* ────────────────────────────────
   9. Video Tracking System Overview
   ──────────────────────────────── */

-- Complete traceability chain: videos → screenshots → features
-- 
-- Key relationships:
-- 1. videos table: Stores video metadata and YouTube URLs
-- 2. screenshots.video_timestamp_seconds: Direct timestamp in video
-- 3. screenshot_video_xref: Many-to-many relationship for complex cases
-- 4. Enhanced analytics: Can now track feature evolution over video timeline
--
-- Example queries:
--
-- Find all screenshots from a specific video timeframe:
-- SELECT s.* FROM screenshots s 
-- JOIN screenshot_video_xref svx ON s.screenshot_id = svx.screenshot_id
-- WHERE svx.video_id = $video_id 
-- AND svx.video_timestamp_seconds BETWEEN $start_time AND $end_time;
--
-- Get video timeline for a specific feature:
-- SELECT v.title, svx.video_timestamp_seconds, s.path 
-- FROM videos v
-- JOIN screenshot_video_xref svx ON v.video_id = svx.video_id
-- JOIN screenshots s ON svx.screenshot_id = s.screenshot_id
-- JOIN screenshot_feature_xref sfx ON s.screenshot_id = sfx.screenshot_id
-- JOIN features_game fg ON sfx.feature_id = fg.feature_id
-- WHERE fg.name = $feature_name
-- ORDER BY v.upload_date, svx.video_timestamp_seconds;