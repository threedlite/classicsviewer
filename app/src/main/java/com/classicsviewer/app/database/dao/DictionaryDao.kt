package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.DictionaryEntity

@Dao
interface DictionaryDao {
    @Query("SELECT * FROM dictionary_entries WHERE headword_normalized = :headword AND language = :language LIMIT 1")
    suspend fun getEntry(headword: String, language: String): DictionaryEntity?
    
    @Query("SELECT COUNT(*) FROM dictionary_entries WHERE language = :language")
    suspend fun getEntryCount(language: String): Int
    
    @Query("SELECT * FROM dictionary_entries WHERE headword_normalized LIKE :pattern AND language = :language LIMIT :limit")
    suspend fun searchEntries(pattern: String, language: String, limit: Int = 10): List<DictionaryEntity>
}