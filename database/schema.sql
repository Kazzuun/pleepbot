CREATE TABLE IF NOT EXISTS channels (
    twitch_id   TEXT NOT NULL,
    channel     TEXT NOT NULL UNIQUE,
    log_only    INTEGER DEFAULT 0 CHECK (log_only IN (0, 1)),
    joined      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (twitch_id)
);

CREATE TABLE IF NOT EXISTS users (
    twitch_id   TEXT NOT NULL,
    username    TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'default',
    no_pings    INTEGER NOT NULL DEFAULT 0 CHECK (no_pings IN (0, 1)),
    notes       TEXT DEFAULT NULL,
    added       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (twitch_id)
);

CREATE TABLE IF NOT EXISTS optouts (
    twitch_id   TEXT NOT NULL,
    username    TEXT NOT NULL,
    command     TEXT NOT NULL,
    PRIMARY KEY (twitch_id, command)
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER,
    channel     TEXT NOT NULL, 
    sender      TEXT NOT NULL,
    message     TEXT NOT NULL, 
    sent_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id              INTEGER,
    channel         TEXT NOT NULL,
    sender          TEXT NOT NULL,
    target          TEXT NOT NULL,
    type            TEXT NOT NULL,
    message         TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scheduled_at    TEXT DEFAULT NULL,
    sent            INTEGER DEFAULT 0 CHECK (sent IN (0, 1)),
    cancelled       INTEGER DEFAULT 0 CHECK (cancelled IN (0, 1)),
    processed_at    TEXT DEFAULT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS fortunes(
    id          INTEGER NOT NULL,
    fortune     TEXT NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS blocked_words(
    word        TEXT NOT NULL,
    blocked_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (word)
);

CREATE TABLE IF NOT EXISTS fish(
    twitch_id   TEXT NOT NULL,
    username    TEXT NOT NULL,
    fish_count  INTEGER NOT NULL DEFAULT 0,
    exp         INTEGER NOT NULL DEFAULT 0,
    last_fished TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (twitch_id)
);
