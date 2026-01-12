package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.BookEntity

@Dao
interface BookDao {
    @Query("SELECT * FROM books WHERE work_id = :workId ORDER BY book_number")
    suspend fun getByWork(workId: String): List<BookEntity>

    @Query("SELECT * FROM books WHERE id = :bookId")
    suspend fun getById(bookId: String): BookEntity?

    @Query("SELECT COUNT(*) FROM books WHERE work_id = :workId")
    suspend fun getBookCountByWork(workId: String): Int

    @Query("""
        SELECT * FROM books
        WHERE work_id = :workId
        AND book_number > (SELECT book_number FROM books WHERE id = :currentBookId)
        ORDER BY book_number ASC
        LIMIT 1
    """)
    suspend fun getNextBook(workId: String, currentBookId: String): BookEntity?

    @Query("""
        SELECT * FROM books
        WHERE work_id = :workId
        AND book_number < (SELECT book_number FROM books WHERE id = :currentBookId)
        ORDER BY book_number DESC
        LIMIT 1
    """)
    suspend fun getPreviousBook(workId: String, currentBookId: String): BookEntity?
}