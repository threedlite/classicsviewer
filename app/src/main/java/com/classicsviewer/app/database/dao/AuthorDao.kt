package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.AuthorEntity

@Dao
interface AuthorDao {
    @Query("SELECT * FROM authors WHERE language = :language ORDER BY name")
    suspend fun getByLanguage(language: String): List<AuthorEntity>
    
    @Query("SELECT * FROM authors WHERE id = :authorId")
    suspend fun getById(authorId: String): AuthorEntity?
    
    @Query("SELECT DISTINCT language FROM authors")
    suspend fun getAllLanguages(): List<String>
}