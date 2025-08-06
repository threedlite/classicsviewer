package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.TextLineEntity

@Dao
interface TextLineDao {
    @Query("SELECT * FROM text_lines WHERE book_id = :bookId ORDER BY line_number")
    suspend fun getByBook(bookId: String): List<TextLineEntity>
    
    @Query("SELECT * FROM text_lines WHERE book_id = :bookId AND line_number >= :startLine AND line_number <= :endLine ORDER BY line_number")
    suspend fun getByBookAndRange(bookId: String, startLine: Int, endLine: Int): List<TextLineEntity>
    
    @Query("SELECT COUNT(*) FROM text_lines WHERE book_id = :bookId")
    suspend fun getLineCountByBook(bookId: String): Int
    
    @Query("SELECT MIN(line_number) FROM text_lines WHERE book_id = :bookId")
    suspend fun getFirstLineNumber(bookId: String): Int?
    
    @Query("SELECT MAX(line_number) FROM text_lines WHERE book_id = :bookId")
    suspend fun getLastLineNumber(bookId: String): Int?
}

data class OccurrenceResult(
    val bookId: String,
    val lineNumber: Int,
    val lineText: String
)

data class OccurrenceResultWithWords(
    val bookId: String,
    val lineNumber: Int,
    val lineText: String,
    val matchingWords: List<com.classicsviewer.app.models.WordMatch>
)