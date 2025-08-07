package com.classicsviewer.app.repository

import android.content.Context
import com.classicsviewer.app.database.UserDatabase
import com.classicsviewer.app.database.entities.BookmarkEntity
import kotlinx.coroutines.flow.Flow

class BookmarkRepository(context: Context) {
    private val bookmarkDao = UserDatabase.getInstance(context).bookmarkDao()
    
    fun getAllBookmarks(): Flow<List<BookmarkEntity>> = bookmarkDao.getAllBookmarks()
    
    fun getRecentBookmarks(limit: Int = 10): Flow<List<BookmarkEntity>> = 
        bookmarkDao.getRecentBookmarks(limit)
    
    fun getBookmarksByBook(bookId: String): Flow<List<BookmarkEntity>> = 
        bookmarkDao.getBookmarksByBook(bookId)
    
    fun getBookmarksByWork(workId: String): Flow<List<BookmarkEntity>> = 
        bookmarkDao.getBookmarksByWork(workId)
    
    fun getRecentBookmarksByWork(workId: String, limit: Int = 10): Flow<List<BookmarkEntity>> = 
        bookmarkDao.getRecentBookmarksByWork(workId, limit)
    
    fun getBookmarksWithNotesByWork(workId: String): Flow<List<BookmarkEntity>> = 
        bookmarkDao.getBookmarksWithNotesByWork(workId)
    
    fun getBookmarksWithNotes(): Flow<List<BookmarkEntity>> = 
        bookmarkDao.getBookmarksWithNotes()
    
    suspend fun isBookmarked(bookId: String, lineNumber: Int): Boolean = 
        bookmarkDao.isBookmarked(bookId, lineNumber)
    
    suspend fun toggleBookmark(
        workId: String,
        bookId: String,
        lineNumber: Int,
        authorName: String,
        workTitle: String,
        bookLabel: String?,
        lineText: String,
        note: String? = null
    ): Boolean {
        val existingBookmark = bookmarkDao.getBookmark(bookId, lineNumber)
        return if (existingBookmark != null) {
            bookmarkDao.deleteBookmark(existingBookmark)
            false // Bookmark removed
        } else {
            val bookmark = BookmarkEntity(
                workId = workId,
                bookId = bookId,
                lineNumber = lineNumber,
                authorName = authorName,
                workTitle = workTitle,
                bookLabel = bookLabel,
                lineText = lineText,
                note = note
            )
            bookmarkDao.insertBookmark(bookmark)
            true // Bookmark added
        }
    }
    
    suspend fun addBookmark(
        workId: String,
        bookId: String,
        lineNumber: Int,
        authorName: String,
        workTitle: String,
        bookLabel: String?,
        lineText: String,
        note: String? = null
    ): Long {
        val bookmark = BookmarkEntity(
            workId = workId,
            bookId = bookId,
            lineNumber = lineNumber,
            authorName = authorName,
            workTitle = workTitle,
            bookLabel = bookLabel,
            lineText = lineText,
            note = note
        )
        return bookmarkDao.insertBookmark(bookmark)
    }
    
    suspend fun updateBookmarkNote(bookmarkId: Long, note: String?) {
        bookmarkDao.getBookmarkById(bookmarkId)?.let { bookmark ->
            bookmarkDao.updateBookmark(bookmark.copy(note = note))
        }
    }
    
    suspend fun deleteBookmark(bookmarkId: Long) {
        bookmarkDao.deleteBookmarkById(bookmarkId)
    }
    
    suspend fun deleteBookmarkByLocation(bookId: String, lineNumber: Int) {
        bookmarkDao.deleteBookmarkByLocation(bookId, lineNumber)
    }
    
    suspend fun deleteAllBookmarks() {
        bookmarkDao.deleteAllBookmarks()
    }
    
    suspend fun updateLastAccessed(bookmarkId: Long) {
        bookmarkDao.updateLastAccessed(bookmarkId)
    }
    
    suspend fun getBookmarkCount(): Int = bookmarkDao.getBookmarkCount()
    
    suspend fun getBookmark(bookId: String, lineNumber: Int): BookmarkEntity? = 
        bookmarkDao.getBookmark(bookId, lineNumber)
    
    suspend fun getAllBookmarksForExport(): List<BookmarkEntity> = 
        bookmarkDao.getAllBookmarksForExport()
    
    suspend fun importBookmarks(bookmarks: List<BookmarkEntity>): List<Long> = 
        bookmarkDao.insertBookmarks(bookmarks)
}