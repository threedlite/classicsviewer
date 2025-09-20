package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.LemmaMapEntity

@Dao
interface LemmaMapDao {
    @Query("SELECT lemma FROM lemma_map WHERE word_form = :wordForm ORDER BY confidence DESC LIMIT 1")
    suspend fun getLemmaForWord(wordForm: String): String?
    
    @Query("SELECT DISTINCT lemma FROM lemma_map WHERE word_form = :wordForm ORDER BY confidence DESC")
    suspend fun getAllLemmasForWord(wordForm: String): List<String>
    
    @Query("SELECT * FROM lemma_map WHERE word_form = :wordForm ORDER BY confidence DESC")
    suspend fun getAllLemmaMappingsForWord(wordForm: String): List<LemmaMapEntity>
    
    @Query("SELECT * FROM lemma_map WHERE word_form = :wordForm ORDER BY confidence DESC LIMIT 1")
    suspend fun getLemmaMapEntry(wordForm: String): LemmaMapEntity?
    
    @Query("SELECT * FROM lemma_map WHERE word_form LIKE :prefix || '%' ORDER BY LENGTH(word_form) ASC, confidence DESC")
    suspend fun getLemmaMappingsWithPrefix(prefix: String): List<LemmaMapEntity>
    
    @Query("SELECT * FROM lemma_map WHERE word_form_normalized_ultra = :normalizedWord ORDER BY confidence DESC")
    suspend fun getAllLemmaMappingsByUltraNormalized(normalizedWord: String): List<LemmaMapEntity>
}