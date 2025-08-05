package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.LemmaMapEntity

@Dao
interface LemmaMapDao {
    @Query("SELECT lemma FROM lemma_map WHERE word_normalized = :wordNormalized ORDER BY confidence DESC LIMIT 1")
    suspend fun getLemmaForWord(wordNormalized: String): String?
    
    @Query("SELECT DISTINCT lemma FROM lemma_map WHERE word_form = :wordForm OR word_normalized = :wordNormalized ORDER BY confidence DESC")
    suspend fun getAllLemmasForWord(wordForm: String, wordNormalized: String): List<String>
    
    @Query("SELECT * FROM lemma_map WHERE word_form = :wordForm OR word_normalized = :wordNormalized ORDER BY confidence DESC")
    suspend fun getAllLemmaMappingsForWord(wordForm: String, wordNormalized: String): List<LemmaMapEntity>
    
    @Query("SELECT * FROM lemma_map WHERE word_normalized = :wordNormalized ORDER BY confidence DESC LIMIT 1")
    suspend fun getLemmaMapEntry(wordNormalized: String): LemmaMapEntity?
}