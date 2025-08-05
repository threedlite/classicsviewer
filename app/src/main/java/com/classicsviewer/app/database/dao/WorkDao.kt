package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.WorkEntity

@Dao
interface WorkDao {
    @Query("SELECT * FROM works WHERE author_id = :authorId ORDER BY title")
    suspend fun getByAuthor(authorId: String): List<WorkEntity>
    
    @Query("SELECT * FROM works WHERE id = :workId")
    suspend fun getById(workId: String): WorkEntity?
    
    @Query("SELECT COUNT(*) FROM works WHERE author_id = :authorId")
    suspend fun getWorkCountByAuthor(authorId: String): Int
}