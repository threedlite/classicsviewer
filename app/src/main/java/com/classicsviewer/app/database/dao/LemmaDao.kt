package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.LemmaMapEntity

@Dao
interface LemmaDao {
    @Query("SELECT * FROM lemma_map WHERE word_form = :wordForm")
    suspend fun getLemmasForForm(wordForm: String): List<LemmaMapEntity>
    
    @Query("SELECT DISTINCT lemma FROM lemma_map WHERE word_form = :wordForm")
    suspend fun getLemmaCandidates(wordForm: String): List<String>
    
    @Query("SELECT COUNT(DISTINCT lemma) FROM lemma_map")
    suspend fun getUniqueLemmaCount(): Int
    
    @Query("SELECT * FROM lemma_map WHERE word_form = :wordForm ORDER BY confidence DESC LIMIT 1")
    suspend fun getLemmaMapping(wordForm: String): LemmaMapEntity?
}