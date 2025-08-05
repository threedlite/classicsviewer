package com.classicsviewer.app.data

import com.classicsviewer.app.models.*
import kotlinx.coroutines.delay

class MockDataRepository : DataRepository {
    
    override suspend fun getAuthors(language: String): List<Author> {
        // Simulate network/database delay
        delay(300)
        return MockDataProvider.getMockAuthors(language)
    }
    
    override suspend fun getWorks(authorId: String, language: String): List<Work> {
        delay(200)
        return MockDataProvider.getMockWorks(authorId)
    }
    
    override suspend fun getBooks(workId: String): List<Book> {
        delay(200)
        return MockDataProvider.getMockBooks(workId)
    }
    
    override suspend fun getTextLines(
        workId: String, 
        bookId: String, 
        startLine: Int, 
        endLine: Int
    ): List<TextLine> {
        delay(400)
        val isGreek = workId.startsWith("tlg")
        return MockDataProvider.getMockTextLines(startLine, endLine, isGreek)
    }
    
    override suspend fun getDictionaryEntry(word: String, language: String): String? {
        delay(300)
        return MockDataProvider.getMockDictionaryEntry(word, language)
    }
    
    override suspend fun getDictionaryEntryWithMorphology(word: String, language: String): DictionaryResult? {
        delay(300)
        val definition = MockDataProvider.getMockDictionaryEntry(word, language)
        return definition?.let {
            DictionaryResult(
                definition = it,
                morphInfo = null,
                lemma = null
            )
        }
    }
    
    override suspend fun getAllDictionaryEntries(word: String, language: String): DictionaryResultMultiple {
        delay(300)
        // Mock implementation - return a single entry
        val definition = MockDataProvider.getMockDictionaryEntry(word, language)
        val entries = if (definition != null) {
            listOf(DictionaryEntry(
                lemma = word,
                definition = definition,
                morphInfo = null,
                isDirectMatch = true
            ))
        } else {
            emptyList()
        }
        return DictionaryResultMultiple(entries = entries)
    }
    
    override suspend fun getLemmaOccurrences(lemma: String, language: String): List<Occurrence> {
        delay(500)
        return MockDataProvider.getMockOccurrences(lemma, language).take(500)
    }
    
    override suspend fun countLemmaOccurrences(lemma: String, language: String): Int {
        delay(200)
        // Mock count - return a larger number for common words
        return when (lemma.lowercase()) {
            "και", "καί", "the", "et", "de", "in" -> 1234
            "μεν", "δε", "a", "an", "ad" -> 876
            else -> MockDataProvider.getMockOccurrences(lemma, language).size
        }
    }
    
    override suspend fun getTranslationSegments(bookId: String, startLine: Int, endLine: Int): List<TranslationSegment> {
        delay(300)
        return MockDataProvider.getMockTranslationSegments(bookId, startLine, endLine)
    }
    
    override suspend fun getAvailableTranslators(bookId: String): List<String> {
        delay(100)
        return listOf("Mock Translator 1", "Mock Translator 2")
    }
    
    override suspend fun getTranslationSegmentsByTranslator(bookId: String, translator: String, startLine: Int, endLine: Int): List<TranslationSegment> {
        delay(300)
        return MockDataProvider.getMockTranslationSegments(bookId, startLine, endLine).map {
            it.copy(translator = translator)
        }
    }
    
    override suspend fun getLemmaForWord(word: String, language: String): String? {
        delay(100)
        // Simple mock implementation - just return the normalized word as lemma
        return word.lowercase().replace(Regex("[.,;:!?]"), "")
    }
}