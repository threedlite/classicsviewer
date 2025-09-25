-- Perseus Texts Database Schema
-- Exact schema from current database

CREATE TABLE authors (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    name_alt TEXT,
    language TEXT NOT NULL,
    has_translations INTEGER DEFAULT 0
);

CREATE TABLE works (
    id TEXT PRIMARY KEY NOT NULL,
    author_id TEXT NOT NULL,
    title TEXT NOT NULL,
    title_alt TEXT,
    title_english TEXT,
    type TEXT,
    urn TEXT,
    description TEXT,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

CREATE TABLE books (
    id TEXT PRIMARY KEY NOT NULL,
    work_id TEXT NOT NULL,
    book_number INTEGER NOT NULL,
    label TEXT,
    start_line INTEGER,
    end_line INTEGER,
    line_count INTEGER,
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
);

CREATE TABLE text_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    line_text TEXT NOT NULL,
    line_xml TEXT,
    speaker TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE translation_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    book_id TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER,
    sequence_number INTEGER,
    translation_text TEXT NOT NULL,
    translator TEXT,
    speaker TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE words (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word TEXT NOT NULL,
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    word_position INTEGER NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE milestone_line_ranges (
    work_id TEXT,
    milestone TEXT,
    start_line INTEGER,
    end_line INTEGER,
    PRIMARY KEY (work_id, milestone)
);

CREATE TABLE dictionary_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    headword TEXT NOT NULL,
    headword_normalized_ultra TEXT,
    language TEXT NOT NULL,
    entry_xml TEXT,
    entry_html TEXT,
    entry_plain TEXT,
    source TEXT
);

CREATE TABLE lemma_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word_form TEXT NOT NULL,
    word_form_normalized_ultra TEXT,
    lemma TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source TEXT,
    morph_info TEXT
);

CREATE TABLE translation_lookup (
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    segment_id INTEGER NOT NULL,
    PRIMARY KEY (book_id, line_number, segment_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_authors_language ON authors(language);
CREATE INDEX idx_works_author ON works(author_id);
CREATE INDEX idx_books_work ON books(work_id);
CREATE INDEX idx_text_lines_book ON text_lines(book_id);
CREATE INDEX idx_text_lines_sequence ON text_lines(book_id, sequence_number);
CREATE INDEX idx_words_word ON words(word);
CREATE INDEX idx_words_book_line_seq ON words(book_id, line_number, sequence_number);
CREATE INDEX idx_translation_segments_book ON translation_segments(book_id);
CREATE INDEX idx_translation_segments_lines ON translation_segments(book_id, start_line);
CREATE INDEX idx_dictionary_headword ON dictionary_entries(headword, language);
CREATE INDEX idx_dictionary_headword_ultra ON dictionary_entries(headword_normalized_ultra, language);
CREATE INDEX idx_lemma_map_word ON lemma_map(word_form);
CREATE INDEX idx_lemma_map_word_ultra ON lemma_map(word_form_normalized_ultra);
CREATE INDEX idx_lemma_map_lemma ON lemma_map(lemma);
CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number);
CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id);