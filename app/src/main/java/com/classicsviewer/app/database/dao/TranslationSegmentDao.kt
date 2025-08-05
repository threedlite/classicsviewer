package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.TranslationSegmentEntity

@Dao
interface TranslationSegmentDao {
    
    @Query("""
        SELECT * FROM translation_segments 
        WHERE book_id = :bookId 
        AND start_line <= :endLine 
        AND (end_line IS NULL OR end_line >= :startLine)
        ORDER BY start_line
    """)
    suspend fun getTranslationSegments(
        bookId: String, 
        startLine: Int, 
        endLine: Int
    ): List<TranslationSegmentEntity>
    
    @Query("SELECT * FROM translation_segments WHERE book_id = :bookId ORDER BY start_line")
    suspend fun getAllTranslationSegments(bookId: String): List<TranslationSegmentEntity>
    
    @Query("SELECT COUNT(*) FROM translation_segments WHERE book_id = :bookId")
    suspend fun getTranslationCount(bookId: String): Int
    
    @Query("SELECT DISTINCT translator FROM translation_segments WHERE book_id = :bookId AND translator IS NOT NULL ORDER BY translator")
    suspend fun getAvailableTranslators(bookId: String): List<String>
    
    @Query("""
        SELECT * FROM translation_segments 
        WHERE book_id = :bookId 
        AND translator = :translator
        AND start_line <= :endLine 
        AND (end_line IS NULL OR end_line >= :startLine)
        ORDER BY start_line
    """)
    suspend fun getTranslationSegmentsByTranslator(
        bookId: String,
        translator: String,
        startLine: Int,
        endLine: Int
    ): List<TranslationSegmentEntity>
    
    @Query("""
        SELECT EXISTS(
            SELECT 1 FROM translation_segments ts 
            JOIN books b ON ts.book_id = b.id 
            WHERE b.work_id = :workId
        )
    """)
    suspend fun hasTranslationsForWork(workId: String): Boolean
}