package com.classicsviewer.app.data

import android.content.Context
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.database.UserDatabase
import com.classicsviewer.app.database.dao.OccurrenceResult
import com.classicsviewer.app.database.dao.OccurrenceResultWithWords
import com.classicsviewer.app.lemmatization.GreekLemmatizer
import com.classicsviewer.app.models.*
import com.classicsviewer.app.database.dao.LineReferenceWithWords
import com.classicsviewer.app.utils.GreekNormalizer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class PerseusRepository(private val context: Context) : DataRepository {
    private val database = PerseusDatabase.getInstance(context)
    private val userDatabase = UserDatabase.getInstance(context)
    private val authorDao = database.authorDao()
    private val workDao = database.workDao()
    private val bookDao = database.bookDao()
    private val textLineDao = database.textLineDao()
    private val wordDao = database.wordDao()
    private val lemmaDao = database.lemmaDao()
    private val lemmaMapDao = database.lemmaMapDao()
    private val dictionaryDao = database.dictionaryDao()
    private val translationSegmentDao = database.translationSegmentDao()
    private val userDictionaryDao = userDatabase.userDictionaryDao()
    private val userLemmaMappingDao = userDatabase.userLemmaMappingDao()
    
    private val greekLemmatizer = GreekLemmatizer()
    
    // Cache Latin dictionary availability - check once on first access
    private var cachedHasLatinDictionary: Boolean? = null
    
    // Method to invalidate cache when database changes
    fun invalidateLatinDictionaryCache() {
        cachedHasLatinDictionary = null
        android.util.Log.d("PerseusRepository", "Latin dictionary cache invalidated")
    }
    
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
                sequenceNumber = entity.sequenceNumber,
                text = entity.lineText,
                words = words,
                speaker = entity.speaker
            )
        }
    }
    
    override suspend fun getAllDictionaryEntries(word: String, language: String): DictionaryResultMultiple = withContext(Dispatchers.IO) {
        try {
            // Clean punctuation first, but preserve apostrophes for elided forms
            var cleanedWord = word.replace(Regex("[.,;:!?·]"), "")
            
            // Normalize apostrophes for Greek words
            if (language.equals("greek", ignoreCase = true)) {
                val beforeNormalization = cleanedWord
                cleanedWord = normalizeApostrophes(cleanedWord)
                android.util.Log.d("PerseusRepository", "Apostrophe normalization: '$beforeNormalization' -> '$cleanedWord'")
            }
            
            // For Greek words, also create acute accent variant if word has grave accents
            val acuteVariant = if (language.equals("greek", ignoreCase = true) && hasGraveAccent(cleanedWord)) {
                convertGraveToAcute(cleanedWord)
            } else {
                null
            }
            
            // Normalize language parameter to match database (database uses lowercase)
            val normalizedLanguage = language.lowercase().trim()
            
            android.util.Log.d("PerseusRepository", "getAllDictionaryEntries: word='$word', cleaned='$cleanedWord', language='$normalizedLanguage' (original: '$language')")
        
            val entries = mutableListOf<DictionaryEntry>()
            val addedLemmas = mutableSetOf<String>()
            val userAddedLemmas = mutableSetOf<String>() // Track user entries separately
            
            // FIRST: Check user dictionary for direct match
            val normalizedWord = if (normalizedLanguage == "greek") {
                GreekNormalizer.normalize(cleanedWord)
            } else {
                cleanedWord.lowercase()
            }
            
            android.util.Log.d("PerseusRepository", "Checking user dictionary for direct match: word='$cleanedWord', normalized='$normalizedWord', language='$normalizedLanguage'")
            val userEntries = userDictionaryDao.getEntriesForLemma(cleanedWord, normalizedWord, normalizedLanguage)
            android.util.Log.d("PerseusRepository", "User dictionary returned ${userEntries.size} entries for '$cleanedWord'")
            for (userEntry in userEntries) {
                android.util.Log.d("PerseusRepository", "User entry found: lemma=${userEntry.lemma}, definitionPlain='${userEntry.definitionPlain}', definitionHtml='${userEntry.definitionHtml}'")
                
                // Check if definition is empty and provide fallback
                val definition = if (!userEntry.definitionHtml.isNullOrEmpty()) userEntry.definitionHtml else userEntry.definitionPlain
                val finalDefinition = if (definition.isNullOrEmpty()) {
                    "Dictionary entry for: $cleanedWord (no definition available)"
                } else {
                    definition
                }
                
                entries.add(DictionaryEntry(
                    lemma = cleanedWord,
                    definition = finalDefinition,
                    morphInfo = null,
                    isDirectMatch = true,
                    confidence = 1.0,
                    source = "User: ${userEntry.sourceName}",
                    hasNonTreebankPath = true // User sources are always non-treebank
                ))
                userAddedLemmas.add(cleanedWord) // Track user entries separately
            }
            
            // Also check user lemma mappings for this word
            val userMapping = userLemmaMappingDao.getMappingForWord(cleanedWord, normalizedWord, normalizedLanguage)
            if (userMapping != null && userMapping.lemma !in userAddedLemmas) {
                // Get dictionary entry for the mapped lemma
                val normalizedLemma = if (normalizedLanguage == "greek") {
                    GreekNormalizer.normalize(userMapping.lemma)
                } else {
                    userMapping.lemma.lowercase()
                }
                
                // First try user dictionary
                val userLemmaEntries = userDictionaryDao.getEntriesForLemma(userMapping.lemma, normalizedLemma, normalizedLanguage)
                if (userLemmaEntries.isNotEmpty()) {
                    for (userLemmaEntry in userLemmaEntries) {
                        // Check if definition is empty and provide fallback with morphology
                        val definition = if (!userLemmaEntry.definitionHtml.isNullOrEmpty()) userLemmaEntry.definitionHtml else userLemmaEntry.definitionPlain
                        val finalDefinition = if (definition.isNullOrEmpty() && !userMapping.morphInfo.isNullOrEmpty()) {
                            // Handle pipe-delimited morphology info
                            val morphForms = userMapping.morphInfo.split("|").map { it.trim() }
                            if (morphForms.size > 1) {
                                "Forms: ${morphForms.joinToString(", ")}"
                            } else {
                                "Form: ${userMapping.morphInfo}"
                            }
                        } else if (definition.isNullOrEmpty()) {
                            "Dictionary entry for: ${userMapping.lemma} (no definition available)"
                        } else {
                            definition
                        }
                        
                        entries.add(DictionaryEntry(
                            lemma = userMapping.lemma,
                            definition = finalDefinition,
                            morphInfo = userMapping.morphInfo,
                            isDirectMatch = false,
                            confidence = userMapping.confidence,
                            source = "User: ${userLemmaEntry.sourceName}",
                            hasNonTreebankPath = true // User sources are always non-treebank
                        ))
                    }
                    userAddedLemmas.add(userMapping.lemma) // Track user entries separately
                } else {
                    // No user dictionary entry for this lemma, try built-in dictionaries
                    val builtinEntries = dictionaryDao.getAllEntriesForHeadword(userMapping.lemma, normalizedLanguage)
                    for (builtinEntry in builtinEntries) {
                        entries.add(DictionaryEntry(
                            lemma = userMapping.lemma,
                            definition = builtinEntry.entryHtml ?: builtinEntry.entryPlain ?: "",
                            morphInfo = userMapping.morphInfo,  // Use the user's morphology info
                            isDirectMatch = false,
                            confidence = userMapping.confidence,
                            source = builtinEntry.source + " (via User morphology)",
                            hasNonTreebankPath = true // User sources are always non-treebank
                        ))
                    }
                    if (builtinEntries.isNotEmpty()) {
                        addedLemmas.add(userMapping.lemma) // Track that we found this lemma
                    }
                }
            }
        
            // Then try built-in dictionary lookup with cleaned word - get ALL entries from ALL sources
            val directEntries = dictionaryDao.getAllEntriesForHeadword(cleanedWord, normalizedLanguage)
            for (directEntry in directEntries) {
                entries.add(DictionaryEntry(
                    lemma = cleanedWord,
                    definition = directEntry.entryHtml ?: directEntry.entryPlain ?: "",
                    morphInfo = null,
                    isDirectMatch = true,
                    source = directEntry.source,
                    hasNonTreebankPath = true // Direct dictionary matches are always valid
                ))
            }
            if (directEntries.isNotEmpty()) {
                addedLemmas.add(cleanedWord)
            }
            
            // If no direct match and we have an acute variant, try that too
            if (directEntries.isEmpty() && acuteVariant != null && acuteVariant != cleanedWord) {
                val acuteEntries = dictionaryDao.getAllEntriesForHeadword(acuteVariant, normalizedLanguage)
                for (acuteEntry in acuteEntries) {
                    entries.add(DictionaryEntry(
                        lemma = acuteVariant,
                        definition = acuteEntry.entryHtml ?: acuteEntry.entryPlain ?: "",
                        morphInfo = null,
                        isDirectMatch = true,
                        source = acuteEntry.source,
                        confidence = 1.0,  // High confidence for direct dictionary match via acute conversion
                        hasNonTreebankPath = true // Direct dictionary matches are always valid
                    ))
                }
                if (acuteEntries.isNotEmpty()) {
                    addedLemmas.add(acuteVariant)
                }
            }
        
            // Get all possible lemmas from lemma map for both Greek and Latin
            if (normalizedLanguage == "greek" || normalizedLanguage == "latin") {
                android.util.Log.d("PerseusRepository", "Getting all lemmas for $normalizedLanguage word - comprehensive approach")
                
                // Get all lemma mappings with confidence scores from BOTH built-in and user sources
                // For Latin, normalize to lowercase for database lookups
                // For Greek, use the word with normalized apostrophes (cleanedWord already has normalized apostrophes)
                val normalizedForLookup = if (normalizedLanguage == "latin") cleanedWord.lowercase() else cleanedWord
                android.util.Log.d("PerseusRepository", "Looking up lemma mappings for: '$normalizedForLookup' (original cleaned: '$cleanedWord')")
                var lemmaMappings = database.lemmaMapDao().getAllLemmaMappingsForWord(normalizedForLookup)
                android.util.Log.d("PerseusRepository", "Found ${lemmaMappings.size} built-in lemma mappings for word: $cleanedWord (normalized: $normalizedForLookup)")
                
                // Log the lemmas found
                for (mapping in lemmaMappings) {
                    android.util.Log.d("PerseusRepository", "  Lemma mapping: ${mapping.wordForm} -> ${mapping.lemma} (confidence: ${mapping.confidence})")
                }
                
                // For Latin, generate variants and check for TACKON/orthographic variations
                if (normalizedLanguage == "latin" && lemmaMappings.isEmpty()) {
                    val latinVariants = generateLatinVariants(cleanedWord)
                    android.util.Log.d("PerseusRepository", "Trying Latin variants for '$cleanedWord': $latinVariants")
                    
                    for (variant in latinVariants) {
                        if (variant != normalizedForLookup) {
                            val variantMappings = database.lemmaMapDao().getAllLemmaMappingsForWord(variant)
                            if (variantMappings.isNotEmpty()) {
                                android.util.Log.d("PerseusRepository", "Found ${variantMappings.size} mappings for Latin variant: $variant")
                                lemmaMappings = lemmaMappings + variantMappings
                                
                                // Also check if there's a direct dictionary entry for the variant
                                val variantEntries = dictionaryDao.getAllEntriesForHeadword(variant, normalizedLanguage)
                                for (variantEntry in variantEntries) {
                                    entries.add(DictionaryEntry(
                                        lemma = variant,
                                        definition = variantEntry.entryHtml ?: variantEntry.entryPlain ?: "",
                                        morphInfo = null,
                                        isDirectMatch = true,
                                        source = variantEntry.source + " (via ${if (variant.contains('j') || variant.contains('v')) "orthographic variant" else "TACKON split"})",
                                        confidence = 0.9,  // Slightly lower confidence for variant matches
                                        hasNonTreebankPath = true // Direct dictionary matches are always valid
                                    ))
                                }
                            }
                        }
                    }
                }
                
                // For Latin, also check user lemma mappings since built-in Latin support is limited
                if (normalizedLanguage == "latin") {
                    // For Latin, we need to use lowercase for lookups
                    val latinNormalizedWord = cleanedWord.lowercase()
                    android.util.Log.d("PerseusRepository", "Checking user mappings for Latin word: '$cleanedWord' (normalized: '$latinNormalizedWord')")
                    var userMappings = userLemmaMappingDao.getAllMappingsForWord(latinNormalizedWord, latinNormalizedWord, normalizedLanguage)
                    
                    // If no user mappings found, try Latin variants
                    if (userMappings.isEmpty()) {
                        val latinVariants = generateLatinVariants(cleanedWord)
                        for (variant in latinVariants) {
                            if (variant != latinNormalizedWord) {
                                val variantUserMappings = userLemmaMappingDao.getAllMappingsForWord(variant, variant, normalizedLanguage)
                                if (variantUserMappings.isNotEmpty()) {
                                    android.util.Log.d("PerseusRepository", "Found ${variantUserMappings.size} user mappings for Latin variant: $variant")
                                    userMappings = userMappings + variantUserMappings
                                }
                            }
                        }
                    }
                    
                    android.util.Log.d("PerseusRepository", "Found ${userMappings.size} user lemma mappings for cleaned word: $cleanedWord")
                    
                    // Log first few mappings for debugging
                    userMappings.take(3).forEach { mapping ->
                        android.util.Log.d("PerseusRepository", "  User mapping: ${mapping.wordForm} -> ${mapping.lemma} (${mapping.morphInfo})")
                    }
                    
                    // Convert user mappings to the same format as built-in mappings
                    val convertedUserMappings = userMappings.map { userMapping ->
                        com.classicsviewer.app.database.entities.LemmaMapEntity(
                            wordForm = userMapping.wordForm,
                            wordFormNormalizedUltra = userMapping.wordFormNormalizedUltra,
                            lemma = userMapping.lemma,
                            morphInfo = userMapping.morphInfo,
                            confidence = userMapping.confidence,
                            source = "user_import"
                        )
                    }
                    
                    // Combine both sources
                    lemmaMappings = lemmaMappings + convertedUserMappings
                    android.util.Log.d("PerseusRepository", "Total lemma mappings after combining: ${lemmaMappings.size}")
                }
                
                // If we have an acute variant and found no mappings, try that too
                if (lemmaMappings.isEmpty() && acuteVariant != null && acuteVariant != cleanedWord) {
                    lemmaMappings = database.lemmaMapDao().getAllLemmaMappingsForWord(acuteVariant)
                    android.util.Log.d("PerseusRepository", "Found ${lemmaMappings.size} lemma mappings for acute variant: $acuteVariant")
                }
                
                // For Greek: If no exact match and word ends with apostrophe, try prefix search
                // Check for various apostrophe types: ' (U+0027), ' (U+2019), ʼ (U+02BC)
                // Note: This is Greek-specific logic for elided forms
                if (normalizedLanguage == "greek" && lemmaMappings.isEmpty() && (cleanedWord.endsWith("'") || cleanedWord.endsWith("'") || cleanedWord.endsWith("ʼ"))) {
                    val prefix = cleanedWord.removeSuffix("'").removeSuffix("'").removeSuffix("ʼ")
                    android.util.Log.d("PerseusRepository", "No exact match for apostrophe word '$cleanedWord', trying prefix: '$prefix'")
                    val allPrefixMappings = database.lemmaMapDao().getLemmaMappingsWithPrefix(prefix)
                    
                    // Filter to prefer shorter words and limit results
                    // For single letter prefix (like δ'), only take words up to 3 characters
                    // For longer prefixes, allow slightly longer words
                    val maxLength = if (prefix.length == 1) prefix.length + 2 else prefix.length + 4
                    lemmaMappings = allPrefixMappings
                        .filter { it.wordForm.length <= maxLength }
                        .take(10) // Limit to top 10 matches
                    
                    android.util.Log.d("PerseusRepository", "Found ${allPrefixMappings.size} total matches, filtered to ${lemmaMappings.size}")
                    // Log first few results for debugging
                    lemmaMappings.take(5).forEach { mapping ->
                        android.util.Log.d("PerseusRepository", "  - ${mapping.wordForm} -> ${mapping.lemma}")
                    }
                }
                
                // Group by lemma and keep highest confidence mapping for each lemma (like iOS bestByLemma)
                // ALSO track whether each lemma has any non-treebank source
                val bestByLemma = lemmaMappings.groupBy { it.lemma }
                    .mapValues { (_, mappings) ->
                        mappings.maxByOrNull { it.confidence ?: 0.0 }!!
                    }

                // Track which lemmas have at least one non-treebank source
                // IMPORTANT: Normalize lemmas to NFC form to match later lookups
                val lemmasWithNonTreebankSource = mutableSetOf<String>()
                lemmaMappings.forEach { mapping ->
                    if (mapping.source != "perseus_treebank") {
                        // Normalize to NFC form just like we do when processing lemmas
                        val normalizedLemma = java.text.Normalizer.normalize(mapping.lemma, java.text.Normalizer.Form.NFC)
                        lemmasWithNonTreebankSource.add(normalizedLemma)
                    }
                }

                android.util.Log.d("PerseusRepository", "Found ${bestByLemma.size} unique lemmas after grouping")
                android.util.Log.d("PerseusRepository", "Lemmas with non-treebank sources: ${lemmasWithNonTreebankSource.size}")

                // Get dictionary entries for each unique lemma (sorted by confidence for now)
                val sortedLemmas = bestByLemma.values.sortedByDescending { it.confidence ?: 0.0 }
                
                for (lemmaMapping in sortedLemmas) {
                    // CRITICAL: Normalize lemma to NFC form to match dictionary entries
                    // The lemma_map table may contain decomposed forms (e.g., ε + combining accent)
                    // but dictionary_entries uses precomposed forms (e.g., έ)
                    val lemma = java.text.Normalizer.normalize(lemmaMapping.lemma, java.text.Normalizer.Form.NFC)
                    
                    // Skip if we already added this lemma
                    if (addedLemmas.contains(lemma)) {
                        android.util.Log.d("PerseusRepository", "Skipping already added lemma: $lemma")
                        continue
                    }
                    
                    // Follow lemma chain to find the canonical form with a dictionary entry
                    val resolvedLemma = resolveLemmaChain(lemma, normalizedLanguage)
                    val chainFollowed = resolvedLemma != lemma
                    
                    // FIRST: Check user dictionary for this lemma (if not already added)
                    if (resolvedLemma !in userAddedLemmas) {
                        val normalizedResolvedLemma = if (normalizedLanguage == "greek") {
                            GreekNormalizer.normalize(resolvedLemma)
                        } else {
                            resolvedLemma.lowercase()
                        }
                        val userLemmaEntries = userDictionaryDao.getEntriesForLemma(resolvedLemma, normalizedResolvedLemma, normalizedLanguage)
                        for (userEntry in userLemmaEntries) {
                            // Check if definition is actually empty
                            val definition = if (!userEntry.definitionHtml.isNullOrEmpty()) userEntry.definitionHtml else userEntry.definitionPlain
                            val finalDefinition = if (definition.isNullOrEmpty() && !lemmaMapping.morphInfo.isNullOrEmpty()) {
                                // If no definition but we have morphology, show that
                                // Handle pipe-delimited morphology info
                                val morphForms = lemmaMapping.morphInfo.split("|").map { it.trim() }
                                if (morphForms.size > 1) {
                                    "Forms: ${morphForms.joinToString(", ")}"
                                } else {
                                    "Form: ${lemmaMapping.morphInfo}"
                                }
                            } else {
                                definition ?: ""
                            }
                            
                            entries.add(DictionaryEntry(
                                lemma = resolvedLemma,
                                definition = finalDefinition,
                                morphInfo = lemmaMapping.morphInfo,
                                isDirectMatch = false,
                                confidence = lemmaMapping.confidence ?: 0.0,
                                source = "User: ${userEntry.sourceName}",
                                hasNonTreebankPath = true // User sources are always non-treebank
                            ))
                        }
                        if (userLemmaEntries.isNotEmpty()) {
                            userAddedLemmas.add(resolvedLemma)
                        } else if (!lemmaMapping.morphInfo.isNullOrEmpty()) {
                            // No user dictionary entry, but we have morphology from user mappings
                            entries.add(DictionaryEntry(
                                lemma = resolvedLemma,
                                definition = if (lemmaMapping.morphInfo.contains("|")) {
                                    val morphForms = lemmaMapping.morphInfo.split("|").map { it.trim() }
                                    "Forms: ${morphForms.joinToString(", ")}"
                                } else {
                                    "Form: ${lemmaMapping.morphInfo}"
                                },
                                morphInfo = lemmaMapping.morphInfo,
                                isDirectMatch = false,
                                confidence = lemmaMapping.confidence ?: 0.0,
                                source = "User morphology",
                                hasNonTreebankPath = true // User sources are always non-treebank
                            ))
                            userAddedLemmas.add(resolvedLemma)
                        }
                    }
                    
                    // Then get ALL dictionary entries for the resolved lemma from ALL built-in sources
                    val lemmaEntries = dictionaryDao.getAllEntriesForHeadword(resolvedLemma, normalizedLanguage)
                    
                    
                    for (entry in lemmaEntries) {
                        val hasNonTreebank = lemmasWithNonTreebankSource.contains(lemma)
                        // Debug log to verify treebank-only detection
                        if (!hasNonTreebank) {
                            android.util.Log.d("PerseusRepository", "Marking as treebank-only: $lemma -> ${entry.source} (via Treebank)")
                        }
                        entries.add(DictionaryEntry(
                            lemma = resolvedLemma,
                            definition = entry.entryHtml ?: entry.entryPlain ?: "",
                            morphInfo = lemmaMapping.morphInfo,
                            isDirectMatch = false,
                            confidence = lemmaMapping.confidence,
                            source = if (!hasNonTreebank) "${entry.source} (via Treebank)" else entry.source,
                            hasNonTreebankPath = hasNonTreebank // Check if this lemma has any non-treebank source
                        ))
                    }
                    if (lemmaEntries.isNotEmpty()) {
                        addedLemmas.add(lemma)
                    } else if (lemmaMapping.source == "wiktionary") {
                        // If still no definition found, create an entry that at least shows the morphological info
                        android.util.Log.d("PerseusRepository", "No definition found for $resolvedLemma, creating morphology-only entry")
                        entries.add(DictionaryEntry(
                            lemma = resolvedLemma,
                            definition = "Form of $resolvedLemma (no definition available)",
                            morphInfo = lemmaMapping.morphInfo,
                            isDirectMatch = false,
                            confidence = lemmaMapping.confidence,
                            source = "wiktionary",
                            hasNonTreebankPath = true // Wiktionary is non-treebank
                        ))
                        addedLemmas.add(lemma)
                    }
                }
                
                // Always check for morphologically related forms to get comprehensive results
                android.util.Log.d("PerseusRepository", "Checking for morphologically related forms to find additional lemmas")
                
                val relatedForms = findMorphologicallyRelatedForms(cleanedWord, normalizedLanguage)
                
                for (relatedForm in relatedForms) {
                    val relatedMappings = database.lemmaMapDao().getAllLemmaMappingsForWord(relatedForm)
                    for (relatedMapping in relatedMappings) {
                        val relatedLemma = relatedMapping.lemma
                        
                        // Skip if already processed or is self-referential
                        if (addedLemmas.contains(relatedLemma) || relatedLemma == relatedForm) {
                            continue
                        }
                        
                        val relatedEntries = dictionaryDao.getAllEntriesForHeadword(relatedLemma, normalizedLanguage)
                        for (relatedEntry in relatedEntries) {
                            android.util.Log.d("PerseusRepository", "Found related lemma $relatedLemma via form $relatedForm (source: ${relatedEntry.source})")
                            val hasNonTreebank = relatedMapping.source != "perseus_treebank"
                            entries.add(DictionaryEntry(
                                lemma = relatedLemma,
                                definition = relatedEntry.entryHtml ?: relatedEntry.entryPlain ?: "",
                                morphInfo = "inferred from related form: $relatedForm (${relatedMapping.morphInfo ?: ""})",
                                isDirectMatch = false,
                                confidence = (relatedMapping.confidence ?: 0.0) * 0.8, // Lower confidence for inferred
                                source = if (!hasNonTreebank) "${relatedEntry.source} (via Treebank)" else relatedEntry.source,
                                hasNonTreebankPath = hasNonTreebank // Check if the related form has non-treebank source
                            ))
                        }
                        if (relatedEntries.isNotEmpty()) {
                            addedLemmas.add(relatedLemma)
                        }
                    }
                }
            }
        
            // Deduplicate entries before sorting - keep only one entry per lemma+source combination
            // This prevents showing the same LSJ entry multiple times
            val deduplicatedEntries = entries.distinctBy { entry ->
                // Create a unique key from lemma + source + definition (first 100 chars to handle minor variations)
                val definitionKey = (entry.definition ?: "").take(100)
                "${entry.lemma}_${entry.source}_$definitionKey"
            }
            
            // Sort entries - prioritize entries with non-treebank sources first, then by source quality
            val sortedEntries = deduplicatedEntries.sortedWith(compareBy(
                { entry ->
                    // FIRST priority: entries with non-treebank paths come before treebank-only entries
                    if (entry.hasNonTreebankPath) 0 else 1000  // Large gap to ensure separation
                },
                { entry ->
                    // Second priority: source ranking (User entries come FIRST)
                    when {
                        entry.source?.startsWith("User:") == true -> -1  // User entries highest priority
                        entry.source?.lowercase() == "lsj" -> 0
                        entry.source?.lowercase() == "cunliffe" -> 1
                        entry.source?.lowercase() == "wiktionary" -> 2
                        else -> 3
                    }
                },
                { entry ->
                    // Third priority: ascending length of the dictionary form (lemma)
                    entry.lemma.length
                },
                { entry ->
                    // Fourth priority: alphabetical order as tiebreaker for same length
                    entry.lemma
                }
            ))
            
            // Debug logging to verify sorting
            android.util.Log.d("PerseusRepository", "Before sorting: ${entries.map { "${it.lemma}(${it.source})" }.joinToString(", ")}")
            android.util.Log.d("PerseusRepository", "After sorting: ${sortedEntries.map { "${it.lemma}(${it.source})" }.joinToString(", ")}")
            android.util.Log.d("PerseusRepository", "Returning ${sortedEntries.size} dictionary entries (${sortedEntries.count { it.source?.contains("LSJ", true) == true }} LSJ entries)")
        
            // If no entries found and word starts with uppercase, try lowercase version (only for non-Greek)
            if (sortedEntries.isEmpty() && word.isNotEmpty() && word[0].isUpperCase() && normalizedLanguage != "greek") {
                android.util.Log.d("PerseusRepository", "No entries found for uppercase word '$word', trying lowercase")
                val lowercaseWord = word[0].lowercase() + word.substring(1)
                return@withContext getAllDictionaryEntries(lowercaseWord, language)
            }
            
            // If no entries found and it's Greek, try ultra-normalized search (handles uppercase too)
            if (sortedEntries.isEmpty() && normalizedLanguage == "greek") {
                android.util.Log.d("PerseusRepository", "No entries found, trying ultra-normalized search for '$cleanedWord'")
                val ultraNormalized = normalizeGreekUltra(cleanedWord)
                android.util.Log.d("PerseusRepository", "Ultra-normalized form: '$ultraNormalized'")
                
                // Try direct dictionary lookup with ultra-normalized form
                val ultraDirectEntry = dictionaryDao.getEntryByUltraNormalized(ultraNormalized, normalizedLanguage)
                if (ultraDirectEntry != null) {
                    android.util.Log.d("PerseusRepository", "Found entry via ultra-normalization: ${ultraDirectEntry.headword}")
                    entries.add(DictionaryEntry(
                        lemma = ultraDirectEntry.headword,
                        definition = ultraDirectEntry.entryHtml ?: ultraDirectEntry.entryPlain ?: "",
                        morphInfo = "found via simplified form",
                        isDirectMatch = true,
                        source = ultraDirectEntry.source,
                        confidence = 0.7,  // Lower confidence for ultra-normalized matches
                        hasNonTreebankPath = true // Direct dictionary matches are always valid
                    ))
                }
                
                // Also try lemma mappings with ultra-normalized form
                val ultraLemmaMappings = database.lemmaMapDao().getAllLemmaMappingsByUltraNormalized(ultraNormalized)
                android.util.Log.d("PerseusRepository", "Found ${ultraLemmaMappings.size} ultra-normalized lemma mappings")
                
                for (lemmaMapping in ultraLemmaMappings.take(5)) { // Limit to top 5
                    val lemma = lemmaMapping.lemma
                    
                    // Skip if we already added this lemma
                    if (addedLemmas.contains(lemma)) continue
                    
                    val ultraEntries = dictionaryDao.getAllEntriesForHeadword(lemma, normalizedLanguage)
                    for (entry in ultraEntries) {
                        android.util.Log.d("PerseusRepository", "Adding ultra-normalized lemma: $lemma (source: ${entry.source})")
                        val hasNonTreebank = lemmaMapping.source != "perseus_treebank"
                        entries.add(DictionaryEntry(
                            lemma = lemma,
                            definition = entry.entryHtml ?: entry.entryPlain ?: "",
                            morphInfo = "found via simplified form: ${lemmaMapping.morphInfo ?: ""}",
                            isDirectMatch = false,
                            confidence = (lemmaMapping.confidence ?: 0.0) * 0.6, // Lower confidence
                            source = if (!hasNonTreebank) "${entry.source} (via Treebank)" else entry.source,
                            hasNonTreebankPath = hasNonTreebank // Check source of the mapping
                        ))
                    }
                    if (ultraEntries.isNotEmpty()) {
                        addedLemmas.add(lemma)
                    }
                }
                
                // Re-sort if we found any ultra-normalized entries
                if (entries.isNotEmpty()) {
                    // Deduplicate before returning
                    val dedupedEntries = entries.distinctBy { entry ->
                        val definitionKey = (entry.definition ?: "").take(100)
                        "${entry.lemma}_${entry.source}_$definitionKey"
                    }
                    return@withContext DictionaryResultMultiple(entries = dedupedEntries.sortedWith(compareBy(
                        { entry ->
                            // FIRST priority: entries with non-treebank paths come before treebank-only entries
                            if (entry.hasNonTreebankPath) 0 else 1000  // Large gap to ensure separation
                        },
                        { entry ->
                            // Second priority: source ranking
                            when (entry.source?.lowercase()) {
                                "lsj" -> 0
                                "cunliffe" -> 1
                                "wiktionary" -> 2
                                else -> 3
                            }
                        },
                        { entry ->
                            // Third priority: ascending length of the dictionary form (lemma)
                            entry.lemma.length
                        },
                        { entry ->
                            // Fourth priority: alphabetical order as tiebreaker for same length
                            entry.lemma
                        }
                    )))
                }
            }
        
            DictionaryResultMultiple(entries = sortedEntries)
            
        } catch (e: Exception) {
            android.util.Log.e("PerseusRepository", "Error in getAllDictionaryEntries", e)
            // Return empty result on error rather than crashing
            DictionaryResultMultiple(entries = emptyList())
        }
    }

    override suspend fun getDictionaryEntryWithMorphology(word: String, language: String): DictionaryResult? = withContext(Dispatchers.IO) {
        // Normalize apostrophes first for Greek
        val wordWithNormalizedApostrophes = if (language.equals("greek", ignoreCase = true)) {
            normalizeApostrophes(word)
        } else {
            word
        }
        
        // Normalize the word for searching
        val normalized = if (language.equals("greek", ignoreCase = true)) {
            normalizeGreek(wordWithNormalizedApostrophes)
        } else {
            wordWithNormalizedApostrophes.lowercase().replace(Regex("[.,;:!?]"), "")
        }
        
        // Normalize language parameter to match database (database uses lowercase)
        val normalizedLanguage = language.lowercase()
        
        android.util.Log.d("PerseusRepository", "getDictionaryEntryWithMorphology: word='$word', normalized='$normalized', language='$language'")
        
        // First try direct dictionary lookup
        var entry = dictionaryDao.getEntry(normalized, normalizedLanguage)
        var morphInfo: String? = null
        var lemma: String? = null
        
        // If not found and it's Greek, try lemma map
        if (entry == null && normalizedLanguage == "greek") {
            // Look up in lemma_map table using lemmaMapDao
            val lemmaMapEntry = database.lemmaMapDao().getLemmaMapEntry(normalized)
            if (lemmaMapEntry != null) {
                lemma = lemmaMapEntry.lemma
                morphInfo = lemmaMapEntry.morphInfo
                // Now look up the lemma in dictionary
                entry = dictionaryDao.getEntry(lemma, normalizedLanguage)
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
        // Normalize apostrophes first for Greek
        val wordWithNormalizedApostrophes = if (language.equals("greek", ignoreCase = true)) {
            normalizeApostrophes(word)
        } else {
            word
        }
        
        // Normalize the word for searching
        val normalized = if (language.equals("greek", ignoreCase = true)) {
            normalizeGreek(wordWithNormalizedApostrophes)
        } else {
            wordWithNormalizedApostrophes.lowercase().replace(Regex("[.,;:!?]"), "")
        }
        
        // Normalize language parameter to match database (database uses lowercase)
        val normalizedLanguage = language.lowercase()
        
        // First try direct dictionary lookup
        var entry = dictionaryDao.getEntry(normalized, normalizedLanguage)
        
        // If not found and it's Greek, try lemma map
        if (entry == null && normalizedLanguage == "greek") {
            // Look up in lemma_map table using lemmaMapDao
            val lemma = database.lemmaMapDao().getLemmaForWord(normalized)
            if (lemma != null) {
                // Normalize the lemma before dictionary lookup
                val normalizedLemma = if (normalizedLanguage == "greek") {
                    normalizeGreek(lemma)
                } else {
                    lemma.lowercase()
                }
                // Now look up the normalized lemma in dictionary
                entry = dictionaryDao.getEntry(normalizedLemma, normalizedLanguage)
            }
        }
        
        // Return HTML content for display, fallback to plain text
        entry?.entryHtml ?: entry?.entryPlain
    }
    
    override suspend fun getLemmaOccurrences(lemma: String, language: String, limit: Int): List<Occurrence> = withContext(Dispatchers.IO) {
        android.util.Log.d("PerseusRepository", "getLemmaOccurrences: lemma='$lemma', language='$language', limit=$limit")
        
        // Get line references with word positions - filter by language to avoid cross-language results
        val lineRefsWithWords = wordDao.findLinesWithLemmaAndPositionsByLanguage(lemma, language, limit)
        android.util.Log.d("PerseusRepository", "Found ${lineRefsWithWords.size} lines with lemma in $language texts (limit: $limit)")
        
        // Now fetch the actual text lines
        val allOccurrences = lineRefsWithWords.mapNotNull { ref ->
            // Use the specific sequence_number to fetch the exact line
            val line = textLineDao.getByBookLineAndSequence(ref.book_id, ref.line_number, ref.sequence_number)
            line?.let {
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
                    sequenceNumber = ref.sequence_number,
                    lineText = it.lineText,
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
                sequenceNumber = result.sequenceNumber,
                lineText = result.lineText,
                wordForm = lemma,
                language = language,
                matchingWords = result.matchingWords
            )
        }
    }
    
    override suspend fun countLemmaOccurrences(lemma: String, language: String): Int = withContext(Dispatchers.IO) {
        // Count using the fast words table - filter by language to avoid cross-language results
        wordDao.countLinesWithLemmaByLanguage(lemma, language)
    }
    
    
    override suspend fun getTranslationSegments(bookId: String, startLine: Int, endLine: Int): List<TranslationSegment> = withContext(Dispatchers.IO) {
        // Expand the range to ensure we get segments that start before or end after our range
        // This prevents gaps in translation display
        val expandedStartLine = maxOf(1, startLine - 50)
        val expandedEndLine = endLine + 50
        
        android.util.Log.d("PerseusRepository", "getTranslationSegments: Requested range $startLine-$endLine, expanded to $expandedStartLine-$expandedEndLine")
        
        val segments = translationSegmentDao.getTranslationSegments(bookId, expandedStartLine, expandedEndLine).map { entity ->
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
        
        android.util.Log.d("PerseusRepository", "Found ${segments.size} translation segments. First segment starts at line ${segments.firstOrNull()?.startLine}")
        
        return@withContext segments
    }
    
    override suspend fun getAvailableTranslators(bookId: String): List<String> = withContext(Dispatchers.IO) {
        translationSegmentDao.getAvailableTranslators(bookId)
    }
    
    override suspend fun getTranslationSegmentsByTranslator(bookId: String, translator: String, startLine: Int, endLine: Int): List<TranslationSegment> = withContext(Dispatchers.IO) {
        // Expand the range to ensure we get segments that start before or end after our range
        // This prevents gaps in translation display
        val expandedStartLine = maxOf(1, startLine - 50)
        val expandedEndLine = endLine + 50
        
        android.util.Log.d("PerseusRepository", "getTranslationSegmentsByTranslator: Requested range $startLine-$endLine, expanded to $expandedStartLine-$expandedEndLine for translator: $translator")
        
        val segments = translationSegmentDao.getTranslationSegmentsByTranslator(bookId, translator, expandedStartLine, expandedEndLine).map { entity ->
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
        
        android.util.Log.d("PerseusRepository", "Found ${segments.size} translation segments by $translator. First segment starts at line ${segments.firstOrNull()?.startLine}, last at ${segments.lastOrNull()?.startLine}")
        
        return@withContext segments
    }
    
    override suspend fun hasUserDictionary(): Boolean = withContext(Dispatchers.IO) {
        try {
            android.util.Log.d("PerseusRepository", "Checking user dictionary...")
            android.util.Log.d("PerseusRepository", "Using existing UserDictionaryDao: $userDictionaryDao")
            val count = userDictionaryDao.getTotalLemmaCount()
            android.util.Log.d("PerseusRepository", "Total lemma count: $count")
            val result = count > 0
            android.util.Log.d("PerseusRepository", "hasUserDictionary returning: $result (count was $count)")
            result
        } catch (e: Exception) {
            android.util.Log.e("PerseusRepository", "Error checking user dictionary", e)
            false
        }
    }
    
    override suspend fun hasLatinDictionary(): Boolean = withContext(Dispatchers.IO) {
        // Return cached value if available
        cachedHasLatinDictionary?.let { 
            android.util.Log.d("PerseusRepository", "Returning cached Latin dictionary availability: $it")
            return@withContext it 
        }
        
        // Otherwise check and cache the result
        try {
            // Check if we have any Latin dictionary entries in the bundled database
            val bundledLatinCount = dictionaryDao.getEntryCount("latin")
            
            // Check if we have any Latin entries in user dictionary
            val userLatinCount = userDictionaryDao.getLemmaCount("latin")
            
            val hasBundledLatin = bundledLatinCount > 0
            val hasUserLatin = userLatinCount > 0
            
            android.util.Log.d("PerseusRepository", "Latin dictionary check - Bundled: $bundledLatinCount, User: $userLatinCount")
            
            // Cache the result
            val result = hasBundledLatin || hasUserLatin
            cachedHasLatinDictionary = result
            
            android.util.Log.d("PerseusRepository", "Cached Latin dictionary availability: $result")
            result
        } catch (e: Exception) {
            android.util.Log.e("PerseusRepository", "Error checking Latin dictionary", e)
            false
        }
    }
    
    override suspend fun getLemmaForWord(word: String, language: String): String? = withContext(Dispatchers.IO) {
        try {
            // Clean punctuation first, then normalize for lookup
            var cleanedWord = word.replace(Regex("[.,;:!?·]"), "")
            
            // Normalize apostrophes for Greek words
            if (language.equals("greek", ignoreCase = true)) {
                cleanedWord = normalizeApostrophes(cleanedWord)
            }
            
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
    
    private fun normalizeApostrophes(word: String): String {
        // CRITICAL: First normalize Unicode to NFC (precomposed) form
        // This converts combining accents (e.g., ε + ́ ) to precomposed characters (έ)
        // Fixes issue where οὐδέ with combining accent doesn't match database entries
        val nfcNormalized = java.text.Normalizer.normalize(word, java.text.Normalizer.Form.NFC)
        
        // Then normalize all apostrophe variants to the standard form used in the database (U+02BC)
        // This handles different apostrophe types that might come from the UI
        return nfcNormalized
            .replace("'", "ʼ")  // U+0027 APOSTROPHE → U+02BC
            .replace("'", "ʼ")  // U+2019 RIGHT SINGLE QUOTATION MARK → U+02BC  
            .replace("᾿", "ʼ")  // U+1FBF GREEK PSILI → U+02BC
            .replace("′", "ʼ")  // U+2032 PRIME → U+02BC
            .replace("´", "ʼ")  // U+00B4 ACUTE ACCENT → U+02BC
    }
    
    private fun normalizeGreek(word: String): String {
        // Only remove punctuation (period, comma, semi-colon, raised dot)
        // Keep all diacritics and apostrophes
        // This is used for direct dictionary lookups where the database stores words WITH diacritics
        return word.replace(Regex("[.,;·]"), "")
    }
    
    private fun hasGraveAccent(word: String): Boolean {
        // Check if word contains any Greek grave accent characters
        val graveChars = setOf(
            'ὰ', 'ὲ', 'ὴ', 'ὶ', 'ὸ', 'ὺ', 'ὼ',  // Simple grave
            'ἂ', 'ἒ', 'ἢ', 'ἲ', 'ὂ', 'ὒ', 'ὢ',  // With smooth breathing
            'ἃ', 'ἓ', 'ἣ', 'ἳ', 'ὃ', 'ὓ', 'ὣ'   // With rough breathing
        )
        return word.any { it in graveChars }
    }
    
    private fun convertGraveToAcute(word: String): String {
        // Convert grave accents to acute accents
        val graveToAcuteMap = mapOf(
            // Simple vowels
            'ὰ' to 'ά', 'ὲ' to 'έ', 'ὴ' to 'ή', 'ὶ' to 'ί', 
            'ὸ' to 'ό', 'ὺ' to 'ύ', 'ὼ' to 'ώ',
            // With smooth breathing
            'ἂ' to 'ἄ', 'ἒ' to 'ἔ', 'ἢ' to 'ἤ', 'ἲ' to 'ἴ',
            'ὂ' to 'ὄ', 'ὒ' to 'ὔ', 'ὢ' to 'ὤ',
            // With rough breathing
            'ἃ' to 'ἅ', 'ἓ' to 'ἕ', 'ἣ' to 'ἥ', 'ἳ' to 'ἵ',
            'ὃ' to 'ὅ', 'ὓ' to 'ὕ', 'ὣ' to 'ὥ'
        )
        
        return word.map { char ->
            graveToAcuteMap[char] ?: char
        }.joinToString("")
    }
    
    private fun normalizeGreekUltra(word: String): String {
        // Ultra-aggressive Greek normalization - removes ALL diacritics
        // First normalize to NFD (decomposed form)
        val decomposed = java.text.Normalizer.normalize(word, java.text.Normalizer.Form.NFD)
        
        // Remove all combining characters (diacritics, breathings, etc.)
        val withoutCombining = decomposed.replace(Regex("\\p{InCombiningDiacriticalMarks}"), "")
        
        // Convert to lowercase
        val lowercased = withoutCombining.lowercase()
        
        // Replace final sigma with regular sigma
        val withRegularSigma = lowercased.replace('ς', 'σ')
        
        // Map any remaining pre-composed characters to base forms
        val diacriticMap = mapOf(
            // Vowels with diacritics to plain vowels
            'ά' to 'α', 'ὰ' to 'α', 'ᾶ' to 'α', 'ἀ' to 'α', 'ἁ' to 'α', 'ἄ' to 'α', 'ἅ' to 'α', 'ἂ' to 'α', 'ἃ' to 'α', 'ἆ' to 'α', 'ἇ' to 'α',
            'ᾳ' to 'α', 'ᾷ' to 'α', 'ᾴ' to 'α', 'ᾲ' to 'α', 'ᾀ' to 'α', 'ᾁ' to 'α', 'ᾄ' to 'α', 'ᾅ' to 'α', 'ᾂ' to 'α', 'ᾃ' to 'α', 'ᾆ' to 'α', 'ᾇ' to 'α',
            'έ' to 'ε', 'ὲ' to 'ε', 'ἐ' to 'ε', 'ἑ' to 'ε', 'ἔ' to 'ε', 'ἕ' to 'ε', 'ἒ' to 'ε', 'ἓ' to 'ε',
            'ή' to 'η', 'ὴ' to 'η', 'ῆ' to 'η', 'ἠ' to 'η', 'ἡ' to 'η', 'ἤ' to 'η', 'ἥ' to 'η', 'ἢ' to 'η', 'ἣ' to 'η', 'ἦ' to 'η', 'ἧ' to 'η',
            'ῃ' to 'η', 'ῇ' to 'η', 'ῄ' to 'η', 'ῂ' to 'η', 'ᾐ' to 'η', 'ᾑ' to 'η', 'ᾔ' to 'η', 'ᾕ' to 'η', 'ᾒ' to 'η', 'ᾓ' to 'η', 'ᾖ' to 'η', 'ᾗ' to 'η',
            'ί' to 'ι', 'ὶ' to 'ι', 'ῖ' to 'ι', 'ἰ' to 'ι', 'ἱ' to 'ι', 'ἴ' to 'ι', 'ἵ' to 'ι', 'ἲ' to 'ι', 'ἳ' to 'ι', 'ἶ' to 'ι', 'ἷ' to 'ι',
            'ΐ' to 'ι', 'ῒ' to 'ι', 'ῗ' to 'ι',
            'ό' to 'ο', 'ὸ' to 'ο', 'ὀ' to 'ο', 'ὁ' to 'ο', 'ὄ' to 'ο', 'ὅ' to 'ο', 'ὂ' to 'ο', 'ὃ' to 'ο',
            'ύ' to 'υ', 'ὺ' to 'υ', 'ῦ' to 'υ', 'ὐ' to 'υ', 'ὑ' to 'υ', 'ὔ' to 'υ', 'ὕ' to 'υ', 'ὒ' to 'υ', 'ὓ' to 'υ', 'ὖ' to 'υ', 'ὗ' to 'υ',
            'ΰ' to 'υ', 'ῢ' to 'υ', 'ῧ' to 'υ',
            'ώ' to 'ω', 'ὼ' to 'ω', 'ῶ' to 'ω', 'ὠ' to 'ω', 'ὡ' to 'ω', 'ὤ' to 'ω', 'ὥ' to 'ω', 'ὢ' to 'ω', 'ὣ' to 'ω', 'ὦ' to 'ω', 'ὧ' to 'ω',
            'ῳ' to 'ω', 'ῷ' to 'ω', 'ῴ' to 'ω', 'ῲ' to 'ω', 'ᾠ' to 'ω', 'ᾡ' to 'ω', 'ᾤ' to 'ω', 'ᾥ' to 'ω', 'ᾢ' to 'ω', 'ᾣ' to 'ω', 'ᾦ' to 'ω', 'ᾧ' to 'ω',
            // Rho with breathing
            'ῤ' to 'ρ', 'ῥ' to 'ρ'
        )
        
        return withRegularSigma.map { char ->
            diacriticMap[char] ?: char
        }.joinToString("")
    }
    
    private suspend fun findMorphologicallyRelatedForms(word: String, language: String): List<String> = withContext(Dispatchers.IO) {
        android.util.Log.d("PerseusRepository", "Finding morphologically related forms for $language word: $word")
        
        val relatedForms = mutableListOf<String>()
        
        if (language == "greek") {
            // Extract the stem by removing common endings and try multiple related forms
            when {
            // λαων (gen pl) -> try λαοι (nom pl), λαος (nom sg), λαου (gen sg), etc.
            word.endsWith("ων") -> {
                val stem = word.dropLast(2) // λα
                if (stem.length >= 2) {
                    val candidates = listOf(
                        stem + "οι",  // λαοι (nom pl)
                        stem + "ος",  // λαος (nom sg)
                        stem + "ου",  // λαου (gen sg)
                        stem + "ον",  // λαον (acc sg)
                        stem + "οις", // λαοις (dat pl)
                        stem + "ους"  // λαους (acc pl)
                    )
                    
                    for (candidate in candidates) {
                        val exists = database.lemmaMapDao().getLemmaForWord(candidate) != null
                        if (exists) {
                            android.util.Log.d("PerseusRepository", "Found related form: $candidate")
                            relatedForms.add(candidate)
                        }
                    }
                }
            }
            // Add other morphological patterns as needed
            word.endsWith("οι") -> {
                val stem = word.dropLast(2)
                if (stem.length >= 2) {
                    val candidates = listOf(stem + "ος", stem + "ων", stem + "ου")
                    for (candidate in candidates) {
                        val exists = database.lemmaMapDao().getLemmaForWord(candidate) != null
                        if (exists) {
                            android.util.Log.d("PerseusRepository", "Found related form: $candidate")
                            relatedForms.add(candidate)
                        }
                    }
                }
            }
            word.endsWith("ος") -> {
                val stem = word.dropLast(2)
                if (stem.length >= 2) {
                    val candidates = listOf(stem + "οι", stem + "ων", stem + "ου")
                    for (candidate in candidates) {
                        val exists = database.lemmaMapDao().getLemmaForWord(candidate) != null
                        if (exists) {
                            android.util.Log.d("PerseusRepository", "Found related form: $candidate")
                            relatedForms.add(candidate)
                        }
                    }
                }
            }
            }
        } else if (language == "latin") {
            // Latin morphological patterns
            val lowercaseWord = word.lowercase()
            when {
                // First declension: -a, -ae, -am, -arum, -is, -as
                lowercaseWord.endsWith("ae") -> {
                    val stem = lowercaseWord.dropLast(2)
                    if (stem.length >= 2) {
                        val candidates = listOf(
                            stem + "a",    // nom sg
                            stem + "am",   // acc sg
                            stem + "arum", // gen pl
                            stem + "as",   // acc pl
                            stem + "is"    // dat/abl pl
                        )
                        for (candidate in candidates) {
                            val exists = database.lemmaMapDao().getLemmaForWord(candidate) != null
                            if (exists) {
                                android.util.Log.d("PerseusRepository", "Found related Latin form: $candidate")
                                relatedForms.add(candidate)
                            }
                        }
                    }
                }
                // Second declension: -us, -i, -o, -um, -orum, -os, -is
                lowercaseWord.endsWith("i") -> {
                    val stem = lowercaseWord.dropLast(1)
                    if (stem.length >= 2) {
                        val candidates = listOf(
                            stem + "us",   // nom sg
                            stem + "um",   // nom/acc sg neut
                            stem + "o",    // dat/abl sg
                            stem + "orum", // gen pl
                            stem + "os",   // acc pl
                            stem + "is"    // dat/abl pl
                        )
                        for (candidate in candidates) {
                            val exists = database.lemmaMapDao().getLemmaForWord(candidate) != null
                            if (exists) {
                                android.util.Log.d("PerseusRepository", "Found related Latin form: $candidate")
                                relatedForms.add(candidate)
                            }
                        }
                    }
                }
                lowercaseWord.endsWith("orum") -> {
                    val stem = lowercaseWord.dropLast(4)
                    if (stem.length >= 2) {
                        val candidates = listOf(
                            stem + "us",   // nom sg
                            stem + "um",   // nom/acc sg neut
                            stem + "i",    // gen sg / nom pl
                            stem + "o",    // dat/abl sg
                            stem + "a"     // nom/acc pl neut
                        )
                        for (candidate in candidates) {
                            val exists = database.lemmaMapDao().getLemmaForWord(candidate) != null
                            if (exists) {
                                android.util.Log.d("PerseusRepository", "Found related Latin form: $candidate")
                                relatedForms.add(candidate)
                            }
                        }
                    }
                }
                // Handle neuter plurals like "arma"
                lowercaseWord.endsWith("a") && !lowercaseWord.endsWith("ia") -> {
                    // Could be neuter plural or first declension singular
                    val stem = lowercaseWord.dropLast(1)
                    if (stem.length >= 2) {
                        val candidates = listOf(
                            stem + "um",   // neuter sg (if this is neuter pl)
                            stem + "ae",   // gen/dat sg, nom pl (if first decl)
                            stem + "am",   // acc sg (if first decl)
                            stem + "is"    // dat/abl pl
                        )
                        for (candidate in candidates) {
                            val exists = database.lemmaMapDao().getLemmaForWord(candidate) != null
                            if (exists) {
                                android.util.Log.d("PerseusRepository", "Found related Latin form: $candidate")
                                relatedForms.add(candidate)
                            }
                        }
                    }
                }
            }
        }
        
        android.util.Log.d("PerseusRepository", "Found ${relatedForms.size} related forms: $relatedForms")
        relatedForms
    }
    
    private suspend fun resolveLemmaChain(
        lemma: String, 
        language: String,
        visitedLemmas: MutableSet<String> = mutableSetOf(),
        maxDepth: Int = 3
    ): String {
        // Prevent infinite loops
        if (visitedLemmas.contains(lemma) || visitedLemmas.size >= maxDepth) {
            return lemma
        }
        visitedLemmas.add(lemma)
        
        // Check if this lemma has a MEANINGFUL dictionary entry (not just "Morphological entry")
        val entries = dictionaryDao.getAllEntriesForHeadword(lemma, language)
        val hasMeaningfulEntry = entries.any { entry ->
            val plainText = entry.entryPlain ?: ""
            val htmlText = entry.entryHtml ?: ""
            // Check if it's more than just "Morphological entry"
            plainText.isNotBlank() && plainText != "Morphological entry" ||
            htmlText.isNotBlank() && !htmlText.contains("Morphological entry")
        }
        
        if (hasMeaningfulEntry) {
            return lemma  // Found a real definition, stop here
        }
        
        // Check if this lemma appears as a word_form that maps to another lemma
        val nextLemmaMapping = database.lemmaMapDao().getAllLemmaMappingsForWord(lemma)
            .filter { it.lemma != lemma }  // Avoid self-references
            .maxByOrNull { it.confidence ?: 0.0 }  // Get highest confidence mapping
        
        if (nextLemmaMapping != null) {
            return resolveLemmaChain(nextLemmaMapping.lemma, language, visitedLemmas, maxDepth)
        }
        
        return lemma  // No further mapping found
    }
    
    /**
     * Latin-specific normalization for handling orthographic variations
     */
    private fun normalizeLatinWord(word: String): List<String> {
        val variants = mutableListOf<String>()
        val lowered = word.lowercase()
        variants.add(lowered)
        
        // Handle i/j variations
        if (lowered.contains('i')) {
            variants.add(lowered.replace('i', 'j'))
        }
        if (lowered.contains('j')) {
            variants.add(lowered.replace('j', 'i'))
        }
        
        // Handle u/v variations (less common but sometimes needed)
        if (lowered.contains('u')) {
            variants.add(lowered.replace('u', 'v'))
        }
        if (lowered.contains('v')) {
            variants.add(lowered.replace('v', 'u'))
        }
        
        return variants.distinct()
    }
    
    /**
     * Check if a Latin word ends with a TACKON (enclitic particle)
     * Returns pair of (base word, tackon) or null if no tackon found
     */
    private fun splitLatinTackon(word: String): Pair<String, String>? {
        val tackons = listOf("que", "ve", "ne", "cum", "met", "vis", "pte", "nam", "dem", "dum")
        val lowered = word.lowercase()
        
        for (tackon in tackons) {
            if (lowered.endsWith(tackon) && lowered.length > tackon.length + 2) {
                // Make sure we have at least 3 characters left after removing tackon
                val baseWord = word.substring(0, word.length - tackon.length)
                return Pair(baseWord, tackon)
            }
        }
        
        return null
    }
    
    /**
     * Generate all possible Latin word variants for lookup
     */
    private fun generateLatinVariants(word: String): List<String> {
        val variants = mutableListOf<String>()
        
        // Add the original word and its normalizations
        variants.addAll(normalizeLatinWord(word))
        
        // Check for TACKON and add base word variants
        val tackonSplit = splitLatinTackon(word)
        if (tackonSplit != null) {
            val (baseWord, _) = tackonSplit
            variants.addAll(normalizeLatinWord(baseWord))
        }
        
        return variants.distinct()
    }
}