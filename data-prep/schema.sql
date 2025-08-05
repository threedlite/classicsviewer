-- Perseus Digital Library Database Schema
-- This database is pre-built and bundled with the Android app

-- Metadata table for versioning
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id TEXT PRIMARY KEY,              -- e.g., "tlg0012" for Homer
    name TEXT NOT NULL,               -- Display name
    name_latin TEXT,                  -- Latin transliteration
    language TEXT NOT NULL,           -- "greek" or "latin"
    CHECK (language IN ('greek', 'latin'))
);

-- Works table  
CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY,              -- e.g., "tlg0012.tlg001" for Iliad
    author_id TEXT NOT NULL,
    title TEXT NOT NULL,              -- Primary title
    title_latin TEXT,                 -- Latin title
    title_english TEXT,               -- English title
    work_type TEXT,                   -- "poem", "prose", etc.
    urn TEXT,                         -- Full CTS URN
    description TEXT,
    FOREIGN KEY (author_id) REFERENCES authors(id)
);

-- Books/sections table
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,              -- e.g., "tlg0012.tlg001.1"
    work_id TEXT NOT NULL,
    book_number INTEGER NOT NULL,
    book_label TEXT,                  -- Display label (e.g., "Book 1", "Chapter I")
    line_start INTEGER DEFAULT 1,
    line_end INTEGER,
    line_count INTEGER DEFAULT 0,
    FOREIGN KEY (work_id) REFERENCES works(id)
);

-- Text lines table
CREATE TABLE IF NOT EXISTS text_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    line_text TEXT NOT NULL,          -- Plain text for display
    line_xml TEXT,                    -- Original XML with markup
    speaker TEXT,                     -- For dramatic texts
    FOREIGN KEY (book_id) REFERENCES books(id),
    UNIQUE(book_id, line_number)
);

-- Dictionary entries
CREATE TABLE IF NOT EXISTS dictionary_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headword TEXT NOT NULL,           -- Dictionary lemma
    headword_normalized TEXT NOT NULL, -- Normalized for searching
    language TEXT NOT NULL,
    entry_xml TEXT,                   -- Original XML entry
    entry_html TEXT,                  -- HTML formatted for display
    entry_plain TEXT,                 -- Plain text for searching
    source TEXT,                      -- Dictionary source (LSJ, Lewis-Short, etc.)
    CHECK (language IN ('greek', 'latin'))
);

-- Word forms index for fast lookups
CREATE TABLE IF NOT EXISTS word_forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,               -- Original word form
    word_normalized TEXT NOT NULL,    -- Normalized (no accents, etc.)
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    word_position INTEGER NOT NULL,   -- Position in line (1-based)
    char_start INTEGER,               -- Character position start
    char_end INTEGER,                 -- Character position end
    FOREIGN KEY (book_id) REFERENCES books(id)
);

-- Lemma mappings (pre-computed lemmatization)
CREATE TABLE IF NOT EXISTS lemma_map (
    word_form TEXT NOT NULL,          -- Inflected form
    word_normalized TEXT NOT NULL,    -- Normalized form
    lemma TEXT NOT NULL,              -- Dictionary headword
    confidence REAL DEFAULT 1.0,      -- Confidence score
    source TEXT,                      -- Source of mapping
    PRIMARY KEY (word_form, lemma)
);

-- Full-text search tables
CREATE VIRTUAL TABLE IF NOT EXISTS text_search USING fts5(
    book_id,
    line_number, 
    line_text,
    content=text_lines,
    content_rowid=id,
    tokenize='unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS dictionary_search USING fts5(
    headword,
    entry_plain,
    content=dictionary_entries,
    content_rowid=id,
    tokenize='unicode61'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_authors_language ON authors(language);
CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id);
CREATE INDEX IF NOT EXISTS idx_books_work ON books(work_id);
CREATE INDEX IF NOT EXISTS idx_lines_book_line ON text_lines(book_id, line_number);
CREATE INDEX IF NOT EXISTS idx_lines_book ON text_lines(book_id);
CREATE INDEX IF NOT EXISTS idx_word_forms_normalized ON word_forms(word_normalized);
CREATE INDEX IF NOT EXISTS idx_word_forms_location ON word_forms(book_id, line_number);
CREATE INDEX IF NOT EXISTS idx_dict_headword ON dictionary_entries(headword_normalized, language);
CREATE INDEX IF NOT EXISTS idx_lemma_normalized ON lemma_map(word_normalized);

-- Triggers to maintain FTS
CREATE TRIGGER IF NOT EXISTS text_lines_ai AFTER INSERT ON text_lines
BEGIN
    INSERT INTO text_search(book_id, line_number, line_text)
    VALUES (new.book_id, new.line_number, new.line_text);
END;

CREATE TRIGGER IF NOT EXISTS dictionary_entries_ai AFTER INSERT ON dictionary_entries  
BEGIN
    INSERT INTO dictionary_search(headword, entry_plain)
    VALUES (new.headword, new.entry_plain);
END;

-- Statistics view
CREATE VIEW IF NOT EXISTS stats AS
SELECT 
    (SELECT COUNT(*) FROM authors) as author_count,
    (SELECT COUNT(*) FROM works) as work_count,
    (SELECT COUNT(*) FROM books) as book_count,
    (SELECT COUNT(*) FROM text_lines) as line_count,
    (SELECT COUNT(*) FROM dictionary_entries) as dictionary_count,
    (SELECT COUNT(*) FROM word_forms) as word_count,
    (SELECT COUNT(*) FROM lemma_map) as lemma_count;