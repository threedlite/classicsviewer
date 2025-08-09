package com.classicsviewer.app.viewmodels

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.asLiveData
import androidx.lifecycle.viewModelScope
import com.classicsviewer.app.database.entities.BookmarkEntity
import com.classicsviewer.app.repository.BookmarkRepository
import kotlinx.coroutines.launch

class BookmarkViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = BookmarkRepository(application)
    
    val allBookmarks: LiveData<List<BookmarkEntity>> = repository.getAllBookmarks().asLiveData()
    val recentBookmarks: LiveData<List<BookmarkEntity>> = repository.getRecentBookmarks().asLiveData()
    val bookmarksWithNotes: LiveData<List<BookmarkEntity>> = repository.getBookmarksWithNotes().asLiveData()
    
    private val _isBookmarked = MutableLiveData<Boolean>()
    val isBookmarked: LiveData<Boolean> = _isBookmarked
    
    private val _bookmarkToggled = MutableLiveData<Boolean>()
    val bookmarkToggled: LiveData<Boolean> = _bookmarkToggled
    
    fun checkBookmarkStatus(bookId: String, lineNumber: Int) {
        viewModelScope.launch {
            _isBookmarked.value = repository.isBookmarked(bookId, lineNumber)
        }
    }
    
    fun toggleBookmark(
        workId: String,
        bookId: String,
        lineNumber: Int,
        authorName: String,
        workTitle: String,
        bookLabel: String?,
        lineText: String,
        note: String? = null
    ) {
        viewModelScope.launch {
            val wasAdded = repository.toggleBookmark(
                workId, bookId, lineNumber, authorName, workTitle, bookLabel, lineText, note
            )
            _bookmarkToggled.value = wasAdded
            _isBookmarked.value = wasAdded
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
        val id = repository.addBookmark(
            workId, bookId, lineNumber, authorName, workTitle, bookLabel, lineText, note
        )
        _isBookmarked.value = true
        return id
    }
    
    fun deleteBookmark(bookmarkId: Long) {
        viewModelScope.launch {
            repository.deleteBookmark(bookmarkId)
        }
    }
    
    fun deleteBookmarkByLocation(bookId: String, lineNumber: Int) {
        viewModelScope.launch {
            repository.deleteBookmarkByLocation(bookId, lineNumber)
            _isBookmarked.value = false
        }
    }
    
    fun updateBookmarkNote(bookmarkId: Long, note: String?) {
        viewModelScope.launch {
            repository.updateBookmarkNote(bookmarkId, note)
        }
    }
    
    fun updateLastAccessed(bookmarkId: Long) {
        viewModelScope.launch {
            repository.updateLastAccessed(bookmarkId)
        }
    }
    
    fun getBookmarksByBook(bookId: String): LiveData<List<BookmarkEntity>> {
        return repository.getBookmarksByBook(bookId).asLiveData()
    }
    
    fun getBookmarksByWork(workId: String): LiveData<List<BookmarkEntity>> {
        return repository.getBookmarksByWork(workId).asLiveData()
    }
    
    fun getRecentBookmarksByWork(workId: String): LiveData<List<BookmarkEntity>> {
        return repository.getRecentBookmarksByWork(workId).asLiveData()
    }
    
    fun getBookmarksWithNotesByWork(workId: String): LiveData<List<BookmarkEntity>> {
        return repository.getBookmarksWithNotesByWork(workId).asLiveData()
    }
    
    fun deleteAllBookmarks() {
        viewModelScope.launch {
            repository.deleteAllBookmarks()
        }
    }
    
    suspend fun getBookmark(bookId: String, lineNumber: Int): BookmarkEntity? {
        return repository.getBookmark(bookId, lineNumber)
    }
    
    suspend fun getAllBookmarksForExport(): List<BookmarkEntity> {
        return repository.getAllBookmarksForExport()
    }
    
    suspend fun importBookmarks(bookmarks: List<BookmarkEntity>): Int {
        val results = repository.importBookmarks(bookmarks)
        return results.count { it != -1L }
    }
    
    suspend fun getBookLineCount(bookId: String): Int {
        return repository.getBookLineCount(bookId)
    }
}