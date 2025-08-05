package com.classicsviewer.app.data

import com.classicsviewer.app.models.*

interface DataRepository {
    suspend fun getAuthors(language: String): List<Author>
    suspend fun getWorks(authorId: String, language: String): List<Work>
    suspend fun getBooks(workId: String): List<Book>
    suspend fun getTextLines(workId: String, bookId: String, startLine: Int, endLine: Int): List<TextLine>
    suspend fun getDictionaryEntry(word: String, language: String): String?
    suspend fun getDictionaryEntryWithMorphology(word: String, language: String): DictionaryResult?
    suspend fun getAllDictionaryEntries(word: String, language: String): DictionaryResultMultiple
    suspend fun getLemmaOccurrences(lemma: String, language: String): List<Occurrence>
    suspend fun countLemmaOccurrences(lemma: String, language: String): Int
    suspend fun getTranslationSegments(bookId: String, startLine: Int, endLine: Int): List<TranslationSegment>
    suspend fun getAvailableTranslators(bookId: String): List<String>
    suspend fun getTranslationSegmentsByTranslator(bookId: String, translator: String, startLine: Int, endLine: Int): List<TranslationSegment>
    suspend fun getLemmaForWord(word: String, language: String): String?
}