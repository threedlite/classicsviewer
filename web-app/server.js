const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const cookieParser = require('cookie-parser');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());
app.use('/static', express.static(path.join(__dirname, 'public')));

// View engine setup
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Database connection - use full DB for web app with all features
const dbPath = process.env.DB_PATH || path.join(__dirname, '..', 'data-prep', 'perseus_texts_full.db');
let db = null;

// Greek text ultra-normalization function (matches Android app)
function normalizeGreekUltra(text) {
    if (!text) return '';

    // Remove punctuation
    let noPunctuation = text.replace(/[,;.·:!?]/g, '');

    // NFD normalization to separate base characters from diacritics
    let normalized = noPunctuation.normalize('NFD');

    // Remove combining marks (diacritics)
    let noCombining = '';
    for (let i = 0; i < normalized.length; i++) {
        const char = normalized[i];
        const code = char.charCodeAt(0);
        // Skip combining diacritical marks
        if (!((code >= 0x0300 && code <= 0x036F) || (code >= 0x1AB0 && code <= 0x1AFF) ||
              (code >= 0x1DC0 && code <= 0x1DFF) || (code >= 0x20D0 && code <= 0x20FF) ||
              (code >= 0xFE20 && code <= 0xFE2F))) {
            noCombining += char;
        }
    }

    // Convert to lowercase
    let lowercased = noCombining.toLowerCase();

    // Replace final sigma with regular sigma
    let normalizedSigma = lowercased.replace(/ς/g, 'σ');

    // Keep only Greek letters
    let greekOnly = '';
    for (let i = 0; i < normalizedSigma.length; i++) {
        const char = normalizedSigma[i];
        const code = char.charCodeAt(0);
        // Greek and Coptic (0370-03FF) or Greek Extended (1F00-1FFF)
        if ((code >= 0x0370 && code <= 0x03FF) || (code >= 0x1F00 && code <= 0x1FFF)) {
            if (/[a-zA-Zα-ωΑ-Ω]/.test(char)) { // Is a letter
                greekOnly += char;
            }
        }
    }

    return greekOnly;
}

// Latin text normalization function
function normalizeLatin(text) {
    if (!text) return '';

    // Remove punctuation
    let noPunctuation = text.replace(/[,;.·:!?]/g, '');

    // NFD normalization to separate base characters from diacritics (for macrons)
    let normalized = noPunctuation.normalize('NFD');

    // Remove combining marks (macrons, etc.)
    let noCombining = '';
    for (let i = 0; i < normalized.length; i++) {
        const char = normalized[i];
        const code = char.charCodeAt(0);
        // Skip combining diacritical marks
        if (!((code >= 0x0300 && code <= 0x036F) || (code >= 0x1AB0 && code <= 0x1AFF) ||
              (code >= 0x1DC0 && code <= 0x1DFF) || (code >= 0x20D0 && code <= 0x20FF) ||
              (code >= 0xFE20 && code <= 0xFE2F))) {
            noCombining += char;
        }
    }

    // Convert to lowercase and handle V/U conversion
    let lowercased = noCombining.toLowerCase();
    let normalized_text = lowercased.replace(/v/g, 'u'); // Classical Latin convention

    return normalized_text;
}

// Sanskrit text normalization function
function normalizeSanskrit(text) {
    if (!text) return '';

    // NFD normalization
    let normalized = text.normalize('NFD');

    // Remove Devanagari combining marks (candrabindu, anusvara, visarga)
    normalized = normalized.replace(/[\u0900-\u0903]/g, '');

    // Remove nukta
    normalized = normalized.replace(/[\u093C]/g, '');

    // Remove Vedic accents (udatta, anudatta)
    normalized = normalized.replace(/[\u0951-\u0952]/g, '');

    // Remove dandas (sentence markers)
    normalized = normalized.replace(/[\u0964-\u0965]/g, '');

    // Remove final visarga
    normalized = normalized.replace(/ः$/g, '');

    // Remove final anusvara
    normalized = normalized.replace(/ं$/g, '');

    return normalized;
}

// Cache for normalization patterns loaded from database
let normalizationPatterns = {};

// Load normalization patterns from database for all languages
function loadNormalizationPatterns() {
    db.all(`SELECT language, pattern, replacement, priority FROM normalization_patterns ORDER BY priority`, [], (err, rows) => {
        if (err) {
            console.error('Failed to load normalization patterns:', err);
            return;
        }

        normalizationPatterns = {};
        rows.forEach(row => {
            if (!normalizationPatterns[row.language]) {
                normalizationPatterns[row.language] = [];
            }
            normalizationPatterns[row.language].push({
                pattern: new RegExp(row.pattern, 'g'),
                replacement: row.replacement
            });
        });

        console.log(`Loaded normalization patterns for languages: ${Object.keys(normalizationPatterns).join(', ')}`);
    });
}

// Generic normalization function using database patterns
function normalizeText(text, language) {
    if (!text) return '';

    // Use hardcoded functions for Greek and Latin (they have complex normalization)
    if (language === 'greek') {
        return normalizeGreekUltra(text);
    } else if (language === 'latin') {
        return normalizeLatin(text);
    }

    // For other languages, apply NFD normalization first
    let normalized = text.normalize('NFD');

    // Apply language-specific patterns from database if available
    if (normalizationPatterns[language]) {
        normalizationPatterns[language].forEach(({ pattern, replacement }) => {
            normalized = normalized.replace(pattern, replacement);
        });
    }

    return normalized;
}

// Initialize database connection
function initDatabase() {
    if (!fs.existsSync(dbPath)) {
        console.error(`Database not found at ${dbPath}`);
        process.exit(1);
    }
    
    db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
        if (err) {
            console.error('Error opening database:', err);
            process.exit(1);
        }
        console.log('Connected to Perseus database');

        // Load normalization patterns for all languages
        loadNormalizationPatterns();
    });
}

// Routes
app.get('/', (req, res) => {
    const selectedLanguage = req.cookies.language || 'greek';

    // Get available languages from database
    db.all(`
        SELECT DISTINCT a.language
        FROM authors a
        ORDER BY a.language
    `, [], (err, rows) => {
        if (err) {
            console.error('Error fetching languages:', err);
            // Fallback to default languages
            res.render('index', {
                language: selectedLanguage,
                languages: ['greek', 'latin']
            });
        } else {
            const languages = rows.map(row => row.language);
            res.render('index', {
                language: selectedLanguage,
                languages: languages
            });
        }
    });
});

// Set language preference
app.post('/api/language', (req, res) => {
    const { language } = req.body;
    // Validate that language exists in database
    db.get('SELECT COUNT(*) as count FROM authors WHERE language = ?', [language], (err, row) => {
        if (err || !row || row.count === 0) {
            res.status(400).json({ error: 'Invalid language' });
        } else {
            res.cookie('language', language, { maxAge: 365 * 24 * 60 * 60 * 1000 }); // 1 year
            res.json({ success: true });
        }
    });
});

// License page
app.get('/license', (req, res) => {
    res.render('license');
});

// API Routes
app.get('/api/authors/:language', (req, res) => {
    const language = req.params.language;
    const query = `SELECT id, name, name_alt, has_translations as has_translated_works FROM authors WHERE language = ? ORDER BY name`;

    db.all(query, [language], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

app.get('/api/works/:authorId', (req, res) => {
    const authorId = req.params.authorId;
    const query = `
        SELECT
            w.id,
            w.title,
            w.title_english,
            CASE WHEN EXISTS(
                SELECT 1 FROM translation_segments ts
                JOIN books b ON ts.book_id = b.id
                WHERE b.work_id = w.id
            ) THEN 1 ELSE 0 END as has_translation
        FROM works w
        WHERE w.author_id = ?
        ORDER BY w.title`;
    
    db.all(query, [authorId], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

app.get('/api/books/:workId', (req, res) => {
    const workId = req.params.workId;
    const query = `SELECT id, label, start_line, end_line FROM books WHERE work_id = ? ORDER BY book_number`;
    
    db.all(query, [workId], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

app.get('/api/text/:bookId/:startLine/:endLine', (req, res) => {
    const { bookId, startLine, endLine } = req.params;
    const query = `
        SELECT line_number, line_text, sequence_number, speaker 
        FROM text_lines 
        WHERE book_id = ? AND line_number BETWEEN ? AND ?
        ORDER BY sequence_number
    `;
    
    db.all(query, [bookId, startLine, endLine], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

app.get('/api/translation/:bookId/:startLine/:endLine', (req, res) => {
    const { bookId, startLine, endLine } = req.params;
    const { translator } = req.query; // Optional translator filter

    let query = `
        SELECT DISTINCT ts.*
        FROM translation_segments ts
        WHERE ts.book_id = ?
    `;

    const params = [bookId];

    // Add translator filter if specified
    if (translator) {
        query += ` AND ts.translator = ? `;
        params.push(translator);
    } else {
        // Exclude interlinear translations by default
        query += ` AND ts.translator NOT LIKE 'Interlinear%' `;
    }

    query += `
        AND (
            (ts.start_line <= ? AND (ts.end_line IS NULL OR ts.end_line >= ?))
            OR
            EXISTS (
                SELECT 1 FROM translation_lookup tl
                WHERE tl.book_id = ?
                AND tl.segment_id = ts.id
                AND tl.line_number BETWEEN ? AND ?
            )
        )
        ORDER BY ts.start_line
    `;

    params.push(endLine, startLine, bookId, startLine, endLine);

    db.all(query, params, (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

// Get available translators for a book
app.get('/api/translators/:bookId', (req, res) => {
    const { bookId } = req.params;
    const query = `
        SELECT DISTINCT translator
        FROM translation_segments
        WHERE book_id = ?
        AND translator IS NOT NULL
        AND translator NOT LIKE 'Interlinear%'
        ORDER BY translator
    `;

    db.all(query, [bookId], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows.map(r => r.translator));
    });
});


// Enhanced dictionary lookup with lemma mapping and morphology
app.get('/api/dictionary/:word/:language', (req, res) => {
    const { word, language } = req.params;
    const normalizedWord = normalizeText(word, language);

    console.log(`Dictionary lookup: word="${word}", language="${language}", normalized="${normalizedWord}"`);

    // Get morphological info and lemmas for the word
    const morphQuery = `
        SELECT DISTINCT lemma, morph_info, confidence, source as morph_source
        FROM lemma_map
        WHERE word_form = ? OR word_form_normalized_ultra = ?
        ORDER BY confidence DESC
        LIMIT 10
    `;

    db.all(morphQuery, [word, normalizedWord], (err, morphRows) => {
        const morphInfo = morphRows || [];
        
        // First try direct lookup
        let query = `
            SELECT id, headword, entry_plain, entry_html, source
            FROM dictionary_entries
            WHERE (headword_normalized_ultra = ? OR headword = ?) AND language = ?
            LIMIT 5
        `;

        db.all(query, [normalizedWord, word, language], (err, directEntries) => {
            if (err) {
                console.error('Direct lookup error:', err);
                return res.status(500).json({ error: err.message });
            }

            console.log(`Direct lookup found ${directEntries.length} entries`);

            // Then try lemma lookup
            query = `
                SELECT DISTINCT de.id, de.headword, de.entry_plain, de.entry_html, de.source
                FROM lemma_map lm
                JOIN dictionary_entries de ON de.headword = lm.lemma AND de.language = ?
                WHERE lm.word_form_normalized_ultra = ?
                LIMIT 5
            `;

            db.all(query, [language, normalizedWord], (err, lemmaEntries) => {
                if (err) {
                    console.error('Lemma lookup error:', err);
                    return res.status(500).json({ error: err.message });
                }

                console.log(`Lemma lookup found ${lemmaEntries.length} entries`);

                // Combine results, removing duplicates
                const allEntries = [...directEntries];
                const seenIds = new Set(directEntries.map(e => e.id));

                for (const entry of lemmaEntries) {
                    if (!seenIds.has(entry.id)) {
                        allEntries.push(entry);
                        seenIds.add(entry.id);
                    }
                }

                console.log(`Total entries returned: ${allEntries.length}`);

                // Return entries with morph info separately
                res.json({
                    morph_info: morphInfo,
                    entries: allEntries
                });
            });
        });
    });
});

// Lemma information endpoint - provides detailed morphological data
app.get('/api/lemma/:word/:language', (req, res) => {
    const { word, language } = req.params;
    const normalizedWord = language === 'greek' ? normalizeGreek(word) : word.toLowerCase();
    
    // Get lemma and all inflected forms - simpler query without morphological_forms table
    const query = `
        SELECT DISTINCT 
            lm.lemma,
            lm.word_form,
            lm.morph_info
        FROM lemma_map lm
        WHERE lm.word_form_normalized_ultra = ? OR lm.lemma = ?
        ORDER BY lm.lemma, lm.word_form
    `;
    
    db.all(query, [normalizedWord, normalizedWord], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        
        // Group by lemma
        const lemmaGroups = {};
        rows.forEach(row => {
            if (!lemmaGroups[row.lemma]) {
                lemmaGroups[row.lemma] = {
                    lemma: row.lemma,
                    forms: []
                };
            }
            lemmaGroups[row.lemma].forms.push({
                word_form: row.word_form,
                morph_info: row.morph_info
            });
        });
        
        // Get all related forms for each lemma
        const lemmas = Object.keys(lemmaGroups);
        if (lemmas.length > 0) {
            const allFormsQuery = `
                SELECT DISTINCT lemma, word_form, morph_info
                FROM lemma_map
                WHERE lemma IN (${lemmas.map(() => '?').join(',')})
                ORDER BY lemma, word_form
                LIMIT 200
            `;
            
            db.all(allFormsQuery, lemmas, (err, allForms) => {
                if (err) {
                    return res.status(500).json({ error: err.message });
                }
                
                // Add all forms to each lemma group
                allForms.forEach(form => {
                    if (lemmaGroups[form.lemma]) {
                        const existing = lemmaGroups[form.lemma].forms.find(f => f.word_form === form.word_form);
                        if (!existing) {
                            lemmaGroups[form.lemma].forms.push({
                                word_form: form.word_form,
                                morph_info: form.morph_info
                            });
                        }
                    }
                });
                
                res.json({
                    word: word,
                    normalized: normalizedWord,
                    lemmas: Object.values(lemmaGroups)
                });
            });
        } else {
            res.json({
                word: word,
                normalized: normalizedWord,
                lemmas: []
            });
        }
    });
});

// Word occurrences - using same method as Android (lemma_map)
app.get('/api/occurrences/:word/:bookId?', (req, res) => {
    const { word, bookId } = req.params;
    const language = req.query.language || 'greek';
    const normalizedWord = normalizeText(word, language);
    const limit = parseInt(req.query.limit) || 500;

    console.log(`Occurrences lookup: word="${word}", language="${language}", normalized="${normalizedWord}"`);
    
    // First, find the lemma for this word
    const findLemmaQuery = `
        SELECT DISTINCT lemma 
        FROM lemma_map 
        WHERE word_form_normalized_ultra = ? OR lemma = ?
        LIMIT 1
    `;
    
    db.get(findLemmaQuery, [normalizedWord, normalizedWord], (err, lemmaRow) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }

        const lemma = lemmaRow ? lemmaRow.lemma : normalizedWord;
        console.log(`Found lemma: "${lemma}" for normalized word: "${normalizedWord}"`);
        
        // Now get all word forms for this lemma (Android approach)
        const getFormsQuery = `
            SELECT DISTINCT word_form 
            FROM lemma_map 
            WHERE lemma = ?
        `;
        
        db.all(getFormsQuery, [lemma], (err, wordForms) => {
            if (err) {
                return res.status(500).json({ error: err.message });
            }

            const forms = wordForms.map(f => f.word_form);
            if (forms.length === 0) {
                forms.push(word); // Fallback to original word
            }

            console.log(`Found ${forms.length} word forms for lemma "${lemma}":`, forms.slice(0, 5));
            
            // Build query for occurrences using lemma_map like Android
            let query = `
                SELECT DISTINCT
                    w.book_id,
                    w.line_number,
                    w.word,
                    w.word_position,
                    tl.line_text,
                    b.label as book_label,
                    wk.title as work_title,
                    a.name as author_name
                FROM words w
                INNER JOIN lemma_map lm ON w.word = lm.word_form
                JOIN text_lines tl ON w.book_id = tl.book_id AND w.line_number = tl.line_number
                JOIN books b ON w.book_id = b.id
                JOIN works wk ON b.work_id = wk.id
                JOIN authors a ON wk.author_id = a.id
                WHERE lm.lemma = ?
                AND w.word != '_'
            `;
            
            const params = [lemma];
            
            if (language) {
                query += ' AND a.language = ?';
                params.push(language);
            }
            
            if (bookId) {
                query += ' AND w.book_id = ?';
                params.push(bookId);
            }
            
            query += ' ORDER BY w.book_id, w.line_number LIMIT ?';
            params.push(limit);
            
            db.all(query, params, (err, occurrences) => {
                if (err) {
                    return res.status(500).json({ error: err.message });
                }
                
                // Group by book for easier display
                const grouped = {};
                occurrences.forEach(occ => {
                    const key = `${occ.author_name} - ${occ.work_title} - ${occ.book_label}`;
                    if (!grouped[key]) {
                        grouped[key] = {
                            book_id: occ.book_id,
                            title: key,
                            occurrences: []
                        };
                    }
                    grouped[key].occurrences.push({
                        line_number: occ.line_number,
                        line_text: occ.line_text,
                        word: occ.word,
                        word_position: occ.word_position
                    });
                });

                // Log first occurrence for debugging
                if (occurrences.length > 0) {
                    const first = occurrences[0];
                    console.log(`First occurrence: word="${first.word}", position=${first.word_position}, line="${first.line_text.substring(0, 100)}"`);
                }

                res.json({
                    word: word,
                    lemma: lemma,
                    total_found: occurrences.length,
                    word_forms: forms,
                    results: Object.values(grouped)
                });
            });
        });
    });
});

// Get interlinear translation for a book
app.get('/api/interlinear/:bookId', (req, res) => {
    const { bookId } = req.params;

    // Query translation_segments for interlinear data
    // Interlinear is stored as a translator type with pipe-delimited format in translation_text
    const query = `
        SELECT ts.start_line, ts.end_line, ts.translation_text
        FROM translation_segments ts
        WHERE ts.book_id = ?
        AND ts.translator = 'Interlinear (Beta, AI-generated from app dictionary)'
        ORDER BY ts.start_line
    `;

    db.all(query, [bookId], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }

        if (rows.length === 0) {
            return res.status(404).json({ error: 'No interlinear translation available for this work' });
        }

        // Parse the pipe-delimited format from translation_text
        // Format: | word | **gloss** | morphology |  | next_word | etc.
        const interlinearData = {};

        for (const row of rows) {
            const lineNumber = row.start_line; // Each row is one line
            const content = row.translation_text;

            // Split by pipe and process
            const parts = content.split('|').map(p => p.trim()).filter(p => p);

            const words = [];

            // Process in groups of 3: word, gloss (in **), morphology
            for (let i = 0; i < parts.length; i += 3) {
                if (i + 1 < parts.length) {
                    const word = parts[i];
                    let gloss = parts[i + 1];
                    const morph = i + 2 < parts.length ? parts[i + 2] : '';

                    // Extract gloss from **text** format
                    const glossMatch = gloss.match(/\*\*(.*?)\*\*/);
                    if (glossMatch) {
                        gloss = glossMatch[1];
                    }

                    words.push({
                        word: word,
                        gloss: gloss,
                        morph: morph
                    });
                }
            }

            if (words.length > 0) {
                interlinearData[lineNumber] = { words: words };
            }
        }

        res.json(interlinearData);
    });
});

// Get statistics for the database
app.get('/api/stats', (req, res) => {
    const queries = {
        greek_authors: 'SELECT COUNT(*) as count FROM authors WHERE language = "greek"',
        latin_authors: 'SELECT COUNT(*) as count FROM authors WHERE language = "latin"',
        total_works: 'SELECT COUNT(*) as count FROM works',
        total_books: 'SELECT COUNT(*) as count FROM books',
        total_lines: 'SELECT COUNT(*) as count FROM text_lines',
        total_words: 'SELECT COUNT(*) as count FROM words',
        dictionary_entries: 'SELECT COUNT(*) as count FROM dictionary_entries',
        lemma_mappings: 'SELECT COUNT(*) as count FROM lemma_map'
    };

    const stats = {};
    const queryPromises = Object.entries(queries).map(([key, query]) => {
        return new Promise((resolve, reject) => {
            db.get(query, (err, row) => {
                if (err) reject(err);
                else {
                    stats[key] = row.count;
                    resolve();
                }
            });
        });
    });

    Promise.all(queryPromises)
        .then(() => res.json(stats))
        .catch(err => res.status(500).json({ error: err.message }));
});

// Search for texts
app.get('/api/search/text', (req, res) => {
    const { q, language, author_id, work_id } = req.query;

    if (!q || !language) {
        return res.status(400).json({ error: 'Query and language are required' });
    }

    const normalizedQuery = language === 'greek' ? normalizeGreekUltra(q) : normalizeLatin(q);

    let query = `
        SELECT DISTINCT
            tl.book_id,
            tl.line_number,
            tl.line_text,
            b.label as book_label,
            wk.title as work_title,
            a.name as author_name
        FROM text_lines tl
        JOIN books b ON tl.book_id = b.id
        JOIN works wk ON b.work_id = wk.id
        JOIN authors a ON wk.author_id = a.id
        WHERE tl.line_text_normalized LIKE ?
        AND a.language = ?
    `;

    let params = ['%' + normalizedQuery + '%', language];

    if (author_id) {
        query += ' AND a.id = ?';
        params.push(author_id);
    }
    if (work_id) {
        query += ' AND wk.id = ?';
        params.push(work_id);
    }

    query += ' ORDER BY a.name, wk.title, b.book_number, tl.line_number LIMIT 200';

    db.all(query, params, (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

// Set language preference
app.post('/api/language', (req, res) => {
    const { language } = req.body;
    res.cookie('language', language, {
        maxAge: 365 * 24 * 60 * 60 * 1000, // 1 year
        httpOnly: true
    });
    res.json({ success: true });
});

// Error handling
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send('Something went wrong!');
});

// Start server
initDatabase();
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
