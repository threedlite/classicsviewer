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

// Database connection
const dbPath = process.env.DB_PATH || path.join(__dirname, '..', 'data-prep', 'perseus_texts.db');
let db = null;

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
    });
}

// Routes
app.get('/', (req, res) => {
    const selectedLanguage = req.cookies.language || 'greek';
    res.render('index', { language: selectedLanguage });
});

// License page
app.get('/license', (req, res) => {
    res.render('license');
});

// API Routes
app.get('/api/authors/:language', (req, res) => {
    const language = req.params.language;
    const query = `SELECT id, name FROM authors WHERE language = ? ORDER BY name`;
    
    db.all(query, [language], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

app.get('/api/works/:authorId', (req, res) => {
    const authorId = req.params.authorId;
    const query = `SELECT id, title, title_english FROM works WHERE author_id = ? ORDER BY title`;
    
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
        SELECT line_number, line_text 
        FROM text_lines 
        WHERE book_id = ? AND line_number BETWEEN ? AND ?
        ORDER BY line_number
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
    const query = `
        SELECT DISTINCT ts.* 
        FROM translation_segments ts
        WHERE ts.book_id = ? 
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
    
    db.all(query, [bookId, endLine, startLine, bookId, startLine, endLine], (err, rows) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        res.json(rows);
    });
});

// Function to normalize Greek text (remove diacritics)
function normalizeGreek(text) {
    // Remove all combining diacritical marks
    return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

// Dictionary lookup
app.get('/api/dictionary/:word/:language', (req, res) => {
    const { word, language } = req.params;
    const normalizedWord = language === 'greek' ? normalizeGreek(word) : word.toLowerCase();
    
    // First try direct lookup
    let query = `
        SELECT id, headword, entry_plain, entry_html 
        FROM dictionary_entries 
        WHERE headword_normalized = ? AND language = ?
        LIMIT 5
    `;
    
    db.all(query, [normalizedWord, language], (err, directEntries) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        
        // Then try lemma lookup
        query = `
            SELECT DISTINCT de.id, de.headword, de.entry_plain, de.entry_html, lm.morph_info
            FROM lemma_map lm
            JOIN dictionary_entries de ON de.headword_normalized = lm.lemma AND de.language = ?
            WHERE lm.word_normalized = ?
            LIMIT 5
        `;
        
        db.all(query, [language, normalizedWord], (err, lemmaEntries) => {
            if (err) {
                return res.status(500).json({ error: err.message });
            }
            
            // Combine results, removing duplicates
            const allEntries = [...directEntries];
            const seenIds = new Set(directEntries.map(e => e.id));
            
            for (const entry of lemmaEntries) {
                if (!seenIds.has(entry.id)) {
                    allEntries.push(entry);
                    seenIds.add(entry.id);
                }
            }
            
            res.json(allEntries);
        });
    });
});

// Word occurrences
app.get('/api/occurrences/:word/:bookId?', (req, res) => {
    const { word, bookId } = req.params;
    const language = req.query.language || 'greek'; // Get language from query param
    const normalizedWord = language === 'greek' ? normalizeGreek(word) : word.toLowerCase();
    const limit = parseInt(req.query.limit) || 50;
    
    // Get all forms of the word (including inflected forms)
    const lemmaQuery = `
        SELECT DISTINCT word_normalized 
        FROM lemma_map 
        WHERE lemma = ? OR word_normalized = ?
    `;
    
    db.all(lemmaQuery, [normalizedWord, normalizedWord], (err, wordForms) => {
        if (err) {
            return res.status(500).json({ error: err.message });
        }
        
        const forms = wordForms.map(f => f.word_normalized);
        if (!forms.includes(normalizedWord)) {
            forms.push(normalizedWord);
        }
        
        // Build query for occurrences
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
            JOIN text_lines tl ON w.book_id = tl.book_id AND w.line_number = tl.line_number
            JOIN books b ON w.book_id = b.id
            JOIN works wk ON b.work_id = wk.id
            JOIN authors a ON wk.author_id = a.id
            WHERE w.word_normalized IN (${forms.map(() => '?').join(',')})
        `;
        
        const params = [...forms];
        
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
            
            res.json({
                word: word,
                total_found: occurrences.length,
                word_forms: forms,
                results: Object.values(grouped)
            });
        });
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