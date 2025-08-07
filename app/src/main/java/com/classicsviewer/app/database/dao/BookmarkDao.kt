package com.classicsviewer.app.database.dao

import androidx.room.*
import com.classicsviewer.app.database.entities.BookmarkEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface BookmarkDao {
    @Query("SELECT * FROM bookmarks ORDER BY created_at DESC")
    fun getAllBookmarks(): Flow<List<BookmarkEntity>>
    
    @Query("SELECT * FROM bookmarks ORDER BY last_accessed DESC LIMIT :limit")
    fun getRecentBookmarks(limit: Int = 10): Flow<List<BookmarkEntity>>
    
    @Query("SELECT * FROM bookmarks WHERE book_id = :bookId ORDER BY line_number")
    fun getBookmarksByBook(bookId: String): Flow<List<BookmarkEntity>>
    
    @Query("SELECT * FROM bookmarks WHERE work_id = :workId ORDER BY created_at DESC")
    fun getBookmarksByWork(workId: String): Flow<List<BookmarkEntity>>
    
    @Query("SELECT * FROM bookmarks WHERE work_id = :workId ORDER BY last_accessed DESC LIMIT :limit")
    fun getRecentBookmarksByWork(workId: String, limit: Int = 10): Flow<List<BookmarkEntity>>
    
    @Query("SELECT * FROM bookmarks WHERE work_id = :workId AND note IS NOT NULL AND note != '' ORDER BY created_at DESC")
    fun getBookmarksWithNotesByWork(workId: String): Flow<List<BookmarkEntity>>
    
    @Query("SELECT * FROM bookmarks WHERE book_id = :bookId AND line_number = :lineNumber LIMIT 1")
    suspend fun getBookmark(bookId: String, lineNumber: Int): BookmarkEntity?
    
    @Query("SELECT * FROM bookmarks WHERE id = :bookmarkId LIMIT 1")
    suspend fun getBookmarkById(bookmarkId: Long): BookmarkEntity?
    
    @Query("SELECT EXISTS(SELECT 1 FROM bookmarks WHERE book_id = :bookId AND line_number = :lineNumber)")
    suspend fun isBookmarked(bookId: String, lineNumber: Int): Boolean
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBookmark(bookmark: BookmarkEntity): Long
    
    @Update
    suspend fun updateBookmark(bookmark: BookmarkEntity)
    
    @Query("UPDATE bookmarks SET last_accessed = :timestamp WHERE id = :bookmarkId")
    suspend fun updateLastAccessed(bookmarkId: Long, timestamp: Long = System.currentTimeMillis())
    
    @Delete
    suspend fun deleteBookmark(bookmark: BookmarkEntity)
    
    @Query("DELETE FROM bookmarks WHERE id = :bookmarkId")
    suspend fun deleteBookmarkById(bookmarkId: Long)
    
    @Query("DELETE FROM bookmarks WHERE book_id = :bookId AND line_number = :lineNumber")
    suspend fun deleteBookmarkByLocation(bookId: String, lineNumber: Int)
    
    @Query("DELETE FROM bookmarks")
    suspend fun deleteAllBookmarks()
    
    @Query("SELECT COUNT(*) FROM bookmarks")
    suspend fun getBookmarkCount(): Int
    
    @Query("SELECT * FROM bookmarks WHERE note IS NOT NULL AND note != '' ORDER BY created_at DESC")
    fun getBookmarksWithNotes(): Flow<List<BookmarkEntity>>
    
    @Query("SELECT * FROM bookmarks ORDER BY created_at DESC")
    suspend fun getAllBookmarksForExport(): List<BookmarkEntity>
    
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertBookmarks(bookmarks: List<BookmarkEntity>): List<Long>
}