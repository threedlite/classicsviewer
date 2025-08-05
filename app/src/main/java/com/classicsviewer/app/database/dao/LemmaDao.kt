package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.LemmaMapEntity

@Dao
interface LemmaDao {
    @Query("SELECT * FROM lemma_map WHERE word_normalized = :normalizedForm")
    suspend fun getLemmasForForm(normalizedForm: String): List<LemmaMapEntity>
    
    @Query("SELECT DISTINCT lemma FROM lemma_map WHERE word_normalized = :normalizedForm")
    suspend fun getLemmaCandidates(normalizedForm: String): List<String>
    
    @Query("SELECT COUNT(DISTINCT lemma) FROM lemma_map")
    suspend fun getUniqueLemmaCount(): Int
    
    @Query("SELECT * FROM lemma_map WHERE word_normalized = :normalizedForm ORDER BY confidence DESC LIMIT 1")
    suspend fun getLemmaMapping(normalizedForm: String): LemmaMapEntity?
}