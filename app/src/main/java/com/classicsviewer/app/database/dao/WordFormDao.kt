package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.WordFormEntity
import com.classicsviewer.app.models.Occurrence

@Dao
interface WordFormDao {
    @Query("SELECT * FROM word_forms WHERE book_id = :bookId AND line_number = :lineNumber ORDER BY word_position")
    suspend fun getByBookAndLine(bookId: String, lineNumber: Int): List<WordFormEntity>
    
    @Query("""
        SELECT 
            wf.book_id as bookId,
            wf.line_number as lineNumber,
            tl.line_text as lineText,
            wf.word_position as position
        FROM word_forms wf
        JOIN text_lines tl ON wf.book_id = tl.book_id AND wf.line_number = tl.line_number
        WHERE wf.word_normalized = :normalizedForm
        ORDER BY wf.book_id, wf.line_number, wf.word_position
        LIMIT 500
    """)
    suspend fun findOccurrences(normalizedForm: String): List<OccurrenceResult>
    
    @Query("SELECT COUNT(DISTINCT word_normalized) FROM word_forms")
    suspend fun getUniqueWordCount(): Int
    
    @Query("SELECT COUNT(*) FROM word_forms WHERE word_normalized = :normalizedForm")
    suspend fun countOccurrences(normalizedForm: String): Int
}

data class OccurrenceResult(
    val bookId: String,
    val lineNumber: Int,
    val lineText: String,
    val position: Int
)