package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.TranslationSegmentEntity

@Dao
interface TranslationSegmentDao {
    
    @Query("""
        SELECT DISTINCT ts.* FROM translation_segments ts
        WHERE ts.book_id = :bookId 
        AND (
            -- Original range-based lookup
            (ts.start_line <= :endLine AND (ts.end_line IS NULL OR ts.end_line >= :startLine))
            OR
            -- Lookup table based mapping
            EXISTS (
                SELECT 1 FROM translation_lookup tl 
                WHERE tl.book_id = :bookId 
                AND tl.segment_id = ts.id
                AND tl.line_number BETWEEN :startLine AND :endLine
            )
        )
        ORDER BY ts.start_line
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
        SELECT DISTINCT ts.* FROM translation_segments ts
        WHERE ts.book_id = :bookId 
        AND ts.translator = :translator
        AND (
            -- Original range-based lookup
            (ts.start_line <= :endLine AND (ts.end_line IS NULL OR ts.end_line >= :startLine))
            OR
            -- Lookup table based mapping
            EXISTS (
                SELECT 1 FROM translation_lookup tl 
                WHERE tl.book_id = :bookId 
                AND tl.segment_id = ts.id
                AND tl.line_number BETWEEN :startLine AND :endLine
            )
        )
        ORDER BY ts.start_line
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