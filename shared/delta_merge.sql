-- Merge one extended-delta part into the on-device full database.
--
-- The single source of the merge statements: the build's desktop round trip
-- (data-prep/assemble_database.py) and the Android installer both run exactly
-- these, so what is proven on the desktop is what the phone does.
--
-- Contract (ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md, section 7):
--   * the part is ATTACHed as `part`; the target is `main`;
--   * PRAGMA foreign_keys is OFF for the whole merge (INSERT OR REPLACE on
--     authors is a delete plus an insert, and ON DELETE CASCADE would take the
--     author's works with it);
--   * ids are the extended DB's and are inserted as they are; a primary key
--     conflict is a hard error, never OR IGNORE;
--   * one statement per line group, run in this order (FK-safe); the caller
--     wraps each in its own transaction and checkpoints between them.
INSERT OR REPLACE INTO main.authors (id, name, name_alt, language, has_translations)
    SELECT id, name, name_alt, language, has_translations FROM part.authors;
INSERT INTO main.works (id, author_id, title, title_alt, title_english, type, urn, description)
    SELECT id, author_id, title, title_alt, title_english, type, urn, description FROM part.works;
INSERT INTO main.books (id, work_id, book_number, label, start_line, end_line, line_count)
    SELECT id, work_id, book_number, label, start_line, end_line, line_count FROM part.books;
INSERT INTO main.text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker)
    SELECT id, book_id, line_number, sequence_number, line_text, line_xml, speaker FROM part.text_lines;
INSERT INTO main.translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
    SELECT id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker FROM part.translation_segments;
INSERT INTO main.milestone_line_ranges (work_id, milestone, start_line, end_line)
    SELECT work_id, milestone, start_line, end_line FROM part.milestone_line_ranges;
INSERT INTO main.words (id, word, book_id, line_number, sequence_number, word_position)
    SELECT id, word, book_id, line_number, sequence_number, word_position FROM part.words;
INSERT INTO main.dictionary_entries (id, headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source)
    SELECT id, headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source FROM part.dictionary_entries WHERE language <> 'system';
INSERT INTO main.lemma_map (id, word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info)
    SELECT id, word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info FROM part.lemma_map;
INSERT INTO main.normalization_patterns (id, language, pattern, replacement, description, priority)
    SELECT id, language, pattern, replacement, description, priority FROM part.normalization_patterns;
INSERT INTO main.prefix_assimilation_rules (id, language, base_prefix, assimilated_form, meaning, phonological_rule, priority, examples)
    SELECT id, language, base_prefix, assimilated_form, meaning, phonological_rule, priority, examples FROM part.prefix_assimilation_rules;
INSERT INTO main.translation_lookup (book_id, line_number, segment_id)
    SELECT book_id, line_number, segment_id FROM part.translation_lookup;
