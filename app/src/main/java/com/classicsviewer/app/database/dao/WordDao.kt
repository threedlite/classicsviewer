package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.WordEntity

@Dao
interface WordDao {
    // Find lines containing words that match the lemma
    @Query("""
        SELECT DISTINCT w.book_id, w.line_number
        FROM words w
        INNER JOIN lemma_map lm ON w.word = lm.word_form
        WHERE lm.lemma = :lemma
        ORDER BY w.book_id, w.line_number
        LIMIT :limit
    """)
    suspend fun findLinesWithLemma(lemma: String, limit: Int): List<LineReference>
    
    // Find lines containing words that match the lemma, filtered by language
    @Query("""
        SELECT DISTINCT w.book_id, w.line_number
        FROM words w
        INNER JOIN lemma_map lm ON w.word = lm.word_form
        INNER JOIN books b ON w.book_id = b.id
        INNER JOIN works wk ON b.work_id = wk.id
        INNER JOIN authors a ON wk.author_id = a.id
        WHERE lm.lemma = :lemma AND a.language = :language
        ORDER BY w.book_id, w.line_number
        LIMIT :limit
    """)
    suspend fun findLinesWithLemmaByLanguage(lemma: String, language: String, limit: Int): List<LineReference>
    
    // Count occurrences of a lemma
    @Query("""
        SELECT COUNT(DISTINCT w.book_id || '-' || w.line_number)
        FROM words w
        INNER JOIN lemma_map lm ON w.word = lm.word_form
        WHERE lm.lemma = :lemma
    """)
    suspend fun countLinesWithLemma(lemma: String): Int
    
    // Count occurrences of a lemma, filtered by language
    @Query("""
        SELECT COUNT(DISTINCT w.book_id || '-' || w.line_number)
        FROM words w
        INNER JOIN lemma_map lm ON w.word = lm.word_form
        INNER JOIN books b ON w.book_id = b.id
        INNER JOIN works wk ON b.work_id = wk.id
        INNER JOIN authors a ON wk.author_id = a.id
        WHERE lm.lemma = :lemma AND a.language = :language
    """)
    suspend fun countLinesWithLemmaByLanguage(lemma: String, language: String): Int
    
    // Find lines with lemma and include word positions
    @Query("""
        SELECT DISTINCT line_info.book_id, line_info.line_number, line_info.sequence_number,
               GROUP_CONCAT(line_info.word || ':' || line_info.word_position) as word_positions
        FROM (
            SELECT w.book_id, w.line_number, w.sequence_number, w.word, w.word_position
            FROM words w
            INNER JOIN lemma_map lm ON w.word = lm.word_form
            WHERE lm.lemma = :lemma
        ) AS line_info
        GROUP BY line_info.book_id, line_info.line_number, line_info.sequence_number
        ORDER BY line_info.book_id, line_info.line_number, line_info.sequence_number
        LIMIT :limit
    """)
    suspend fun findLinesWithLemmaAndPositions(lemma: String, limit: Int): List<LineReferenceWithWords>
    
    // Find lines with lemma and include word positions, filtered by language
    @Query("""
        SELECT DISTINCT line_info.book_id, line_info.line_number, line_info.sequence_number,
               GROUP_CONCAT(line_info.word || ':' || line_info.word_position) as word_positions
        FROM (
            SELECT w.book_id, w.line_number, w.sequence_number, w.word, w.word_position
            FROM words w
            INNER JOIN lemma_map lm ON w.word = lm.word_form
            INNER JOIN books b ON w.book_id = b.id
            INNER JOIN works wk ON b.work_id = wk.id
            INNER JOIN authors a ON wk.author_id = a.id
            WHERE lm.lemma = :lemma AND a.language = :language
        ) AS line_info
        GROUP BY line_info.book_id, line_info.line_number, line_info.sequence_number
        ORDER BY line_info.book_id, line_info.line_number, line_info.sequence_number
        LIMIT :limit
    """)
    suspend fun findLinesWithLemmaAndPositionsByLanguage(lemma: String, language: String, limit: Int): List<LineReferenceWithWords>
}

data class LineReference(
    val book_id: String,
    val line_number: Int
)

data class LineReferenceWithWords(
    val book_id: String,
    val line_number: Int,
    val sequence_number: Int,
    val word_positions: String  // Format: "word1:pos1,word2:pos2,..."
)