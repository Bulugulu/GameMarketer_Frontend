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
   2. Per-game features
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
   3. Screens + global navigation
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
   4. Screenshots & mappings
   ──────────────────────────────── */
CREATE TABLE screenshots (
    screenshot_id UUID PRIMARY KEY        DEFAULT uuid_generate_v4(),
    path          TEXT        NOT NULL UNIQUE,   -- file or URL
    game_id       UUID        REFERENCES games   ON DELETE CASCADE,
    screen_id     INT         REFERENCES screens ON DELETE CASCADE,
    session_id    UUID,
    capture_time  TIMESTAMPTZ,
    caption       TEXT,
    elements      JSONB,                -- [{name,description,type}]
    modal         BOOLEAN DEFAULT FALSE,
    modal_name    TEXT,
    embedding     VECTOR(768),
    sha256        BYTEA UNIQUE
);

-- Performance indexes
CREATE INDEX ix_shots_game_time  ON screenshots (game_id, capture_time);
CREATE INDEX ix_shots_embedding  ON screenshots USING ivfflat (embedding vector_cosine_ops);

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
   5. Feature change log (optional)
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
   6. Single-table feature flow
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