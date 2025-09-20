# Debugging Missing Translations in App

## The translations ARE in the database

Homer, Hesiod, and Pindar all have translations in the database:
- Homer: 3,171 translation segments
- Hesiod: 484 translation segments  
- Pindar: 1,074 translation segments

## Likely issues in your app:

### 1. **Check your Room query**

Make sure your query handles the line number ranges correctly:

```kotlin
// CORRECT - matches lines within range
@Query("""
    SELECT * FROM translation_segments 
    WHERE book_id = :bookId 
    AND :lineNumber >= start_line 
    AND :lineNumber <= end_line
""")
fun getTranslationForLine(bookId: String, lineNumber: Int): List<TranslationSegment>

// WRONG - might miss translations
@Query("""
    SELECT * FROM translation_segments 
    WHERE book_id = :bookId 
    AND start_line = :lineNumber
""")
```

### 2. **Check for case sensitivity**

The book IDs are lowercase. Make sure you're not comparing with uppercase:

```kotlin
// Book IDs in database:
// tlg0012.tlg001.001 (NOT TLG0012.TLG001.001)
```

### 3. **Handle multiple translators**

Homer has 2 translators per book. Your app needs to handle multiple results:

```kotlin
val translations = dao.getTranslationForLine(bookId, lineNumber)
if (translations.isNotEmpty()) {
    // Pick first translator or let user choose
    val translation = translations[0]
}
```

### 4. **Check bold display logic**

To check if a work has translations:

```kotlin
@Query("""
    SELECT COUNT(DISTINCT ts.id) > 0
    FROM works w
    INNER JOIN books b ON w.id = b.work_id
    INNER JOIN translation_segments ts ON b.id = ts.book_id
    WHERE w.id = :workId
""")
fun hasTranslations(workId: String): Boolean
```

### 5. **Debug with raw SQL**

Add logging to see what your app is actually querying:

```kotlin
// In your DAO or repository
Log.d("DB", "Querying translations for book: $bookId, line: $lineNumber")

// Run raw query to debug
val cursor = db.query("""
    SELECT * FROM translation_segments 
    WHERE book_id = ? 
    AND start_line <= ? 
    AND end_line >= ?
""", arrayOf(bookId, lineNumber.toString(), lineNumber.toString()))
```

### 6. **Common mistakes to check**

1. **Wrong table name**: Ensure it's `translation_segments` not `translations`
2. **Wrong column names**: It's `start_line` and `end_line`, not `from_line` and `to_line`
3. **Foreign key issues**: Make sure book IDs match exactly
4. **Database not updated**: Clear app data and re-deploy the database

## Test queries to run in SQLite browser:

```sql
-- Check if Homer has translations
SELECT COUNT(*) FROM translation_segments 
WHERE book_id LIKE 'tlg0012%';
-- Expected: 3171

-- Get translation for Iliad Book 1 Line 1
SELECT * FROM translation_segments 
WHERE book_id = 'tlg0012.tlg001.001' 
AND start_line <= 1 
AND end_line >= 1;
-- Expected: 2 results (Butler and Murray)

-- Check work-level translation status
SELECT w.id, w.title_english, 
       COUNT(DISTINCT ts.id) as trans_count
FROM works w
LEFT JOIN books b ON w.id = b.work_id
LEFT JOIN translation_segments ts ON b.id = ts.book_id
WHERE w.author_id IN ('tlg0012', 'tlg0020', 'tlg0033')
GROUP BY w.id, w.title_english;
```

## If still not working:

1. Share your Room entity for `TranslationSegment`
2. Share your DAO query methods
3. Share any error logs from the app
4. Try the raw SQL queries in your app to bypass Room