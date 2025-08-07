package com.classicsviewer.app.data

import android.content.Context
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.database.dao.OccurrenceResult
import com.classicsviewer.app.database.dao.OccurrenceResultWithWords
import com.classicsviewer.app.lemmatization.GreekLemmatizer
import com.classicsviewer.app.models.*
import com.classicsviewer.app.database.dao.LineReferenceWithWords
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class PerseusRepository(context: Context) : DataRepository {
    private val database = PerseusDatabase.getInstance(context)
    private val authorDao = database.authorDao()
    private val workDao = database.workDao()
    private val bookDao = database.bookDao()
    private val textLineDao = database.textLineDao()
    private val wordDao = database.wordDao()
    private val lemmaDao = database.lemmaDao()
    private val lemmaMapDao = database.lemmaMapDao()
    private val dictionaryDao = database.dictionaryDao()
    private val translationSegmentDao = database.translationSegmentDao()
    
    private val greekLemmatizer = GreekLemmatizer()
    
    override suspend fun getAuthors(language: String): List<Author> = withContext(Dispatchers.IO) {
        authorDao.getByLanguage(language).map { entity ->
            Author(
                id = entity.id,
                name = entity.name,
                language = entity.language,
                hasTranslatedWorks = entity.hasTranslations ?: false
            )
        }
    }
    
    override suspend fun getWorks(authorId: String, language: String): List<Work> = withContext(Dispatchers.IO) {
        val workEntities = workDao.getByAuthor(authorId)
        workEntities.map { entity ->
            // Check if this work has any translations
            val hasTranslation = translationSegmentDao.hasTranslationsForWork(entity.id)
            
            // Debug logging for Homer, Hesiod, Pindar, and Latin authors
            if (authorId in listOf("tlg0012", "tlg0020", "tlg0033", "phi0690", "phi0893")) {
                android.util.Log.d("PerseusRepository", "Work ${entity.id}: titleEnglish='${entity.titleEnglish}', title='${entity.title}', hasTranslation=$hasTranslation")
            }
            
            Work(
                id = entity.id,
                title = when {
                    // If titleEnglish exists and doesn't look like an ID, use it
                    !entity.titleEnglish.isNullOrBlank() && 
                    !entity.titleEnglish.startsWith("tlg") && 
                    !entity.titleEnglish.startsWith("phi") -> entity.titleEnglish
                    // Otherwise use the main title
                    else -> entity.title
                },
                authorId = entity.authorId,
                language = language,
                hasTranslation = hasTranslation
            )
        }
    }
    
    override suspend fun getBooks(workId: String): List<Book> = withContext(Dispatchers.IO) {
        bookDao.getByWork(workId).map { entity ->
            Book(
                id = entity.id,
                number = entity.bookNumber.toString(),
                workId = entity.workId,
                lineCount = entity.lineCount ?: 0
            )
        }
    }
    
    override suspend fun getTextLines(
        workId: String,
        bookId: String,
        startLine: Int,
        endLine: Int
    ): List<TextLine> = withContext(Dispatchers.IO) {
        textLineDao.getByBookAndRange(bookId, startLine, endLine).map { entity ->
            // Parse words from line text
            val words = emptyList<Word>()
            
            TextLine(
                lineNumber = entity.lineNumber,
                text = entity.lineText,
                words = words,
                speaker = entity.speaker
            )
        }
    }
    
    override suspend fun getAllDictionaryEntries(word: String, language: String): DictionaryResultMultiple = withContext(Dispatchers.IO) {
        try {
            // Clean punctuation first, then normalize for searching
            val cleanedWord = word.replace(Regex("[.,;:!?·]"), "")
            val normalized = if (language.equals("greek", ignoreCase = true)) {
                normalizeGreek(cleanedWord)
            } else {
                cleanedWord.lowercase()
            }
            
            // Normalize language parameter to match database (database uses lowercase)
            val normalizedLanguage = language.lowercase().trim()
            
            android.util.Log.d("PerseusRepository", "getAllDictionaryEntries: word='$word', cleaned='$cleanedWord', normalized='$normalized', language='$normalizedLanguage' (original: '$language')")
        
        val entries = mutableListOf<DictionaryEntry>()
        
        // First try direct dictionary lookup
        val directEntry = database.dictionaryDao().getEntry(normalized, normalizedLanguage)
        if (directEntry != null) {
            entries.add(DictionaryEntry(
                lemma = normalized,
                definition = directEntry.entryHtml ?: directEntry.entryPlain ?: "",
                morphInfo = null,
                isDirectMatch = true
            ))
        }
        
        // If it's Greek, get all possible lemmas from lemma map
        if (normalizedLanguage == "greek") {
            android.util.Log.d("PerseusRepository", "Getting all lemmas for Greek word")
            
            // Get all lemma mappings with confidence scores
            // Note: In the current database, both word_form and word_normalized columns
            // contain the same normalized values (no diacritics), so we need to normalize
            // the input word before querying
            val lemmaMappings = database.lemmaMapDao().getAllLemmaMappingsForWord(normalized)
            android.util.Log.d("PerseusRepository", "Found ${lemmaMappings.size} lemma mappings for normalized word: $normalized")
            
            // Group by lemma to get the highest confidence mapping for each lemma
            val lemmaToMapping = lemmaMappings.groupBy { it.lemma }
                .mapValues { it.value.maxByOrNull { mapping -> mapping.confidence ?: 0.0 } }
            
            // For each unique lemma, get its dictionary entry
            for ((lemma, mapping) in lemmaToMapping) {
                // Skip if we already added this as a direct match
                if (lemma == normalized && directEntry != null) continue
                
                val entry = database.dictionaryDao().getEntry(lemma, normalizedLanguage)
                if (entry != null && mapping != null) {
                    entries.add(DictionaryEntry(
                        lemma = lemma,
                        definition = entry.entryHtml ?: entry.entryPlain ?: "",
                        morphInfo = mapping.morphInfo,
                        isDirectMatch = false,
                        confidence = mapping.confidence
                    ))
                }
            }
            
        }
        
        // Sort all entries by confidence (highest first), with direct matches always first
        val sortedEntries = entries.sortedWith(compareBy(
            { !it.isDirectMatch }, // Direct matches first
            { -(it.confidence ?: 0.0) } // Then by confidence descending
        ))
        
        DictionaryResultMultiple(entries = sortedEntries)
        } catch (e: Exception) {
            android.util.Log.e("PerseusRepository", "Error in getAllDictionaryEntries", e)
            // Return empty result on error rather than crashing
            DictionaryResultMultiple(entries = emptyList())
        }
    }

    override suspend fun getDictionaryEntryWithMorphology(word: String, language: String): DictionaryResult? = withContext(Dispatchers.IO) {
        // Normalize the word for searching
        val normalized = if (language.equals("greek", ignoreCase = true)) {
            normalizeGreek(word)
        } else {
            word.lowercase().replace(Regex("[.,;:!?]"), "")
        }
        
        // Normalize language parameter to match database (database uses lowercase)
        val normalizedLanguage = language.lowercase()
        
        android.util.Log.d("PerseusRepository", "getDictionaryEntryWithMorphology: word='$word', normalized='$normalized', language='$language'")
        
        // First try direct dictionary lookup
        var entry = database.dictionaryDao().getEntry(normalized, normalizedLanguage)
        var morphInfo: String? = null
        var lemma: String? = null
        
        // If not found and it's Greek, try lemma map
        if (entry == null && normalizedLanguage == "greek") {
            android.util.Log.d("PerseusRepository", "No direct match, trying lemma map")
            
            // Look up in lemma_map table using lemmaMapDao
            val lemmaMapEntry = database.lemmaMapDao().getLemmaMapEntry(normalized)
            if (lemmaMapEntry != null) {
                lemma = lemmaMapEntry.lemma
                morphInfo = lemmaMapEntry.morphInfo
                android.util.Log.d("PerseusRepository", "Found lemma mapping: $lemma, morph: $morphInfo")
                // Now look up the lemma in dictionary
                entry = database.dictionaryDao().getEntry(lemma, normalizedLanguage)
            }
        }
        
        entry?.let { 
            DictionaryResult(
                definition = it.entryHtml ?: it.entryPlain ?: "",
                morphInfo = morphInfo,
                lemma = lemma
            )
        }
    }

    override suspend fun getDictionaryEntry(word: String, language: String): String? = withContext(Dispatchers.IO) {
        // Normalize the word for searching
        val normalized = if (language.equals("greek", ignoreCase = true)) {
            normalizeGreek(word)
        } else {
            word.lowercase().replace(Regex("[.,;:!?]"), "")
        }
        
        // Normalize language parameter to match database (database uses lowercase)
        val normalizedLanguage = language.lowercase()
        
        android.util.Log.d("PerseusRepository", "getDictionaryEntry: word='$word', normalized='$normalized', language='$language', normalizedLanguage='$normalizedLanguage'")
        
        // First try direct dictionary lookup
        var entry = database.dictionaryDao().getEntry(normalized, normalizedLanguage)
        
        // If not found and it's Greek, try lemma map
        if (entry == null && normalizedLanguage == "greek") {
            android.util.Log.d("PerseusRepository", "No direct match, trying lemma map")
            
            // Look up in lemma_map table using lemmaMapDao
            val lemma = database.lemmaMapDao().getLemmaForWord(normalized)
            if (lemma != null) {
                android.util.Log.d("PerseusRepository", "Found lemma mapping: $lemma")
                // Now look up the lemma in dictionary
                entry = database.dictionaryDao().getEntry(lemma, normalizedLanguage)
            }
        }
        
        android.util.Log.d("PerseusRepository", "Dictionary result: ${if (entry != null) "Found" else "Not found"}")
        
        // Return HTML content for display, fallback to plain text
        entry?.entryHtml ?: entry?.entryPlain
    }
    
    override suspend fun getLemmaOccurrences(lemma: String, language: String): List<Occurrence> = withContext(Dispatchers.IO) {
        android.util.Log.d("PerseusRepository", "getLemmaOccurrences: lemma='$lemma', language='$language'")
        
        // Get line references with word positions - this is fast!
        val lineRefsWithWords = wordDao.findLinesWithLemmaAndPositions(lemma)
        android.util.Log.d("PerseusRepository", "Found ${lineRefsWithWords.size} lines with lemma")
        
        // Now fetch the actual text lines
        val allOccurrences = lineRefsWithWords.mapNotNull { ref ->
            val lines = textLineDao.getByBookAndRange(ref.book_id, ref.line_number, ref.line_number)
            lines.firstOrNull()?.let { line ->
                // Parse word positions
                val matchingWords = ref.word_positions.split(",").mapNotNull { wordPos ->
                    val parts = wordPos.split(":")
                    if (parts.size == 2) {
                        WordMatch(word = parts[0], position = parts[1].toIntOrNull() ?: 0)
                    } else null
                }
                
                OccurrenceResultWithWords(
                    bookId = ref.book_id,
                    lineNumber = ref.line_number,
                    lineText = line.lineText,
                    matchingWords = matchingWords
                )
            }
        }
        
        android.util.Log.d("PerseusRepository", "Fetched ${allOccurrences.size} text lines")
        
        // Group by book and convert to Occurrence model
        allOccurrences.map { result ->
            val book = bookDao.getById(result.bookId)
            val work = book?.let { workDao.getById(it.workId) }
            val author = work?.let { authorDao.getById(it.authorId) }
            
            Occurrence(
                author = author?.name ?: "Unknown Author",
                authorId = author?.id ?: "",
                work = work?.titleEnglish ?: work?.title ?: "Unknown Work",
                workId = work?.id ?: "",
                book = "Book ${book?.bookNumber ?: 1}",
                bookId = result.bookId,
                lineNumber = result.lineNumber,
                lineText = result.lineText,
                wordForm = lemma,
                language = language,
                matchingWords = result.matchingWords
            )
        }
    }
    
    override suspend fun countLemmaOccurrences(lemma: String, language: String): Int = withContext(Dispatchers.IO) {
        // Count using the fast words table
        wordDao.countLinesWithLemma(lemma)
    }
    
    
    override suspend fun getTranslationSegments(bookId: String, startLine: Int, endLine: Int): List<TranslationSegment> = withContext(Dispatchers.IO) {
        translationSegmentDao.getTranslationSegments(bookId, startLine, endLine).map { entity ->
            TranslationSegment(
                id = entity.id,
                bookId = entity.bookId,
                startLine = entity.startLine,
                endLine = entity.endLine,
                translationText = entity.translationText,
                translator = entity.translator,
                speaker = entity.speaker
            )
        }
    }
    
    override suspend fun getAvailableTranslators(bookId: String): List<String> = withContext(Dispatchers.IO) {
        translationSegmentDao.getAvailableTranslators(bookId)
    }
    
    override suspend fun getTranslationSegmentsByTranslator(bookId: String, translator: String, startLine: Int, endLine: Int): List<TranslationSegment> = withContext(Dispatchers.IO) {
        translationSegmentDao.getTranslationSegmentsByTranslator(bookId, translator, startLine, endLine).map { entity ->
            TranslationSegment(
                id = entity.id,
                bookId = entity.bookId,
                startLine = entity.startLine,
                endLine = entity.endLine,
                translationText = entity.translationText,
                translator = entity.translator,
                speaker = entity.speaker
            )
        }
    }
    
    override suspend fun getLemmaForWord(word: String, language: String): String? = withContext(Dispatchers.IO) {
        try {
            // Clean punctuation first, then normalize for lookup
            val cleanedWord = word.replace(Regex("[.,;:!?·]"), "")
            val normalized = if (language.equals("greek", ignoreCase = true)) {
                normalizeGreek(cleanedWord)
            } else {
                cleanedWord.lowercase()
            }
            
            android.util.Log.d("PerseusRepository", "getLemmaForWord: word='$word', cleaned='$cleanedWord', normalized='$normalized', language='$language'")
            
            // Try to find lemma in lemma_map table
            val lemma = lemmaMapDao.getLemmaForWord(normalized)
            android.util.Log.d("PerseusRepository", "Lemma lookup result: '$lemma' for normalized word: '$normalized'")
            lemma
        } catch (e: Exception) {
            android.util.Log.e("PerseusRepository", "Error in getLemmaForWord", e)
            null
        }
    }
    
    private fun normalizeGreek(word: String): String {
        // Match the Python normalize_greek function exactly
        // First normalize to NFD (decomposed form)
        val nfd = java.text.Normalizer.normalize(word, java.text.Normalizer.Form.NFD)
        
        // Remove all combining diacritical marks (this matches Python's unicodedata.combining())
        val noCombining = nfd.toCharArray().filter { char ->
            val type = Character.getType(char)
            type != Character.NON_SPACING_MARK.toInt() &&
            type != Character.ENCLOSING_MARK.toInt() &&
            type != Character.COMBINING_SPACING_MARK.toInt()
        }.joinToString("")
        
        // Convert to lowercase
        val lowercased = noCombining.lowercase()
        
        // Replace final sigma
        val normalizedSigma = lowercased.replace("ς", "σ")
        
        // Keep only Greek letters (matching Python's isalpha() and Greek Unicode ranges)
        // This removes ALL punctuation including apostrophes, which is correct because
        // elided forms (δ', τ', ἀλλ') are mapped to their full forms in lemma_map
        return normalizedSigma.filter { char ->
            char.isLetter() && (char in '\u0370'..'\u03ff' || char in '\u1f00'..'\u1fff')
        }
    }
}