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
        INNER JOIN lemma_map lm ON w.word_normalized = lm.word_normalized
        WHERE lm.lemma = :lemma
        ORDER BY w.book_id, w.line_number
        LIMIT 500
    """)
    suspend fun findLinesWithLemma(lemma: String): List<LineReference>
    
    // Count occurrences of a lemma
    @Query("""
        SELECT COUNT(DISTINCT w.book_id || '-' || w.line_number)
        FROM words w
        INNER JOIN lemma_map lm ON w.word_normalized = lm.word_normalized
        WHERE lm.lemma = :lemma
    """)
    suspend fun countLinesWithLemma(lemma: String): Int
    
    // Find lines with lemma and include word positions
    @Query("""
        SELECT w.book_id, w.line_number, 
               GROUP_CONCAT(w.word || ':' || w.word_position) as word_positions
        FROM words w
        INNER JOIN lemma_map lm ON w.word_normalized = lm.word_normalized
        WHERE lm.lemma = :lemma
        GROUP BY w.book_id, w.line_number
        ORDER BY w.book_id, w.line_number
        LIMIT 500
    """)
    suspend fun findLinesWithLemmaAndPositions(lemma: String): List<LineReferenceWithWords>
}

data class LineReference(
    val book_id: String,
    val line_number: Int
)

data class LineReferenceWithWords(
    val book_id: String,
    val line_number: Int,
    val word_positions: String  // Format: "word1:pos1,word2:pos2,..."
)