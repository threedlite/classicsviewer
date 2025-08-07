-- Perseus Digital Library Database Schema
-- This database is pre-built and bundled with the Android app
-- Last updated: 2025-08-07
-- 
-- IMPORTANT: This schema must match EXACTLY with:
-- 1. The CREATE TABLE statements in create_perseus_database.py
-- 2. The Room entity definitions in app/src/main/java/com/classicsviewer/app/database/entities/
-- 3. Any mismatch will cause the app to crash on startup with "Pre-packaged database has an invalid schema"

-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id TEXT PRIMARY KEY NOT NULL,              -- e.g., "tlg0012" for Homer
    name TEXT NOT NULL,                        -- Display name
    name_alt TEXT,                             -- Alternative name/Latin transliteration
    language TEXT NOT NULL,                    -- "greek" or "latin"
    has_translations INTEGER DEFAULT 0         -- Whether author has any translations
);

-- Works table  
CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY NOT NULL,              -- e.g., "tlg0012.tlg001" for Iliad
    author_id TEXT NOT NULL,
    title TEXT NOT NULL,                       -- Primary title
    title_alt TEXT,                            -- Alternative title
    title_english TEXT,                        -- English title
    type TEXT,                                 -- Work type (poem, prose, etc.)
    urn TEXT,                                  -- Full CTS URN
    description TEXT,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Books/sections table
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY NOT NULL,              -- e.g., "tlg0012.tlg001.1"
    work_id TEXT NOT NULL,
    book_number INTEGER NOT NULL,
    label TEXT,                                -- Display label (e.g., "Book 1", "Chapter I")
    start_line INTEGER,
    end_line INTEGER,
    line_count INTEGER,
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
);

-- Text lines table
CREATE TABLE IF NOT EXISTS text_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    line_text TEXT NOT NULL,                   -- Plain text for display
    line_xml TEXT,                             -- Original XML with markup
    speaker TEXT,                              -- For dramatic texts
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Translation segments table
CREATE TABLE IF NOT EXISTS translation_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    book_id TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER,                          -- NULL for single-line segments
    translation_text TEXT NOT NULL,
    translator TEXT,                           -- Translator name
    speaker TEXT,                              -- For dramatic texts
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Translation lookup table for complex alignment
CREATE TABLE translation_lookup (
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    segment_id INTEGER NOT NULL,
    PRIMARY KEY (book_id, line_number, segment_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
);

-- Words table for occurrence searching and highlighting
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word TEXT NOT NULL,                        -- Original word form
    word_normalized TEXT NOT NULL,             -- Normalized (no accents, lowercase)
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    word_position INTEGER NOT NULL,            -- 1-based position in line
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Dictionary entries
CREATE TABLE IF NOT EXISTS dictionary_entries (
    id INTEGER PRIMARY KEY NOT NULL,
    headword TEXT NOT NULL,                    -- Dictionary lemma
    headword_normalized TEXT NOT NULL,         -- Normalized for searching
    language TEXT NOT NULL,
    entry_xml TEXT,                            -- Original XML entry
    entry_html TEXT,                           -- HTML formatted for display
    entry_plain TEXT,                          -- Plain text for searching
    source TEXT,                               -- Dictionary source (LSJ, Lewis-Short, etc.)
    CHECK (language IN ('greek', 'latin'))
);

-- Lemma mappings (word forms to dictionary headwords)
CREATE TABLE IF NOT EXISTS lemma_map (
    word_form TEXT NOT NULL,                   -- Inflected form
    word_normalized TEXT NOT NULL,             -- Normalized form
    lemma TEXT NOT NULL,                       -- Dictionary headword
    confidence REAL DEFAULT 1.0,               -- Confidence score
    source TEXT,                               -- Source of mapping
    morph_info TEXT,                           -- Morphological information
    PRIMARY KEY (word_form, lemma)
);

-- Indexes for performance (must match Room entity index names exactly)
CREATE INDEX IF NOT EXISTS idx_authors_language ON authors(language);
CREATE INDEX IF NOT EXISTS idx_works_author ON works(author_id);
CREATE INDEX IF NOT EXISTS idx_books_work ON books(work_id);
CREATE INDEX IF NOT EXISTS idx_text_lines_book ON text_lines(book_id);
CREATE INDEX IF NOT EXISTS idx_translation_segments_book ON translation_segments(book_id);
CREATE INDEX IF NOT EXISTS idx_translation_segments_lines ON translation_segments(book_id, start_line);
CREATE INDEX IF NOT EXISTS index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number);
CREATE INDEX IF NOT EXISTS index_translation_lookup_segment_id ON translation_lookup(segment_id);
CREATE INDEX IF NOT EXISTS idx_words_normalized ON words(word_normalized);
CREATE INDEX IF NOT EXISTS idx_words_book_line ON words(book_id, line_number);
CREATE INDEX IF NOT EXISTS idx_dictionary_headword_normalized ON dictionary_entries(headword_normalized, language);

-- Note: The following indexes exist in create_perseus_database.py but are not expected by Room:
-- CREATE INDEX IF NOT EXISTS idx_lemma_map_word ON lemma_map(word_form)
-- CREATE INDEX IF NOT EXISTS idx_lemma_map_lemma ON lemma_map(lemma)

-- Statistics view
CREATE VIEW IF NOT EXISTS stats AS
SELECT 
    (SELECT COUNT(*) FROM authors) as author_count,
    (SELECT COUNT(*) FROM works) as work_count,
    (SELECT COUNT(*) FROM books) as book_count,
    (SELECT COUNT(*) FROM text_lines) as line_count,
    (SELECT COUNT(*) FROM translation_segments) as translation_count,
    (SELECT COUNT(*) FROM dictionary_entries) as dictionary_count,
    (SELECT COUNT(*) FROM words) as word_count,
    (SELECT COUNT(*) FROM lemma_map) as lemma_count;