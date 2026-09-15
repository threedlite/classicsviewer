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

    /**
     * Same as [getAllLemmaMappingsForWord] but restricted to a set of sources.
     *
     * lemma_map has no language column, and every language's mappings live in
     * one table, so a Latin word can match another language's entry. 2,182
     * Latin surface forms collide this way. "terra" maps to terr (Whitaker),
     * terra (IcePaHC, Old Norse) and tāru (RINAP, Akkadian).
     *
     * source does identify the owning module: no source string is shared
     * between language modules. Filtering on it needs no schema change.
     *
     * Only Latin uses this. Every other language keeps the unfiltered query
     * above, so their behaviour is unchanged.
     */
    @Query("SELECT * FROM lemma_map WHERE word_form = :wordForm AND source IN (:sources) ORDER BY confidence DESC")
    suspend fun getAllLemmaMappingsForWordFiltered(wordForm: String, sources: List<String>): List<LemmaMapEntity>
    
    @Query("SELECT * FROM lemma_map WHERE word_form = :wordForm ORDER BY confidence DESC LIMIT 1")
    suspend fun getLemmaMapEntry(wordForm: String): LemmaMapEntity?
    
    @Query("SELECT * FROM lemma_map WHERE word_form LIKE :prefix || '%' ORDER BY LENGTH(word_form) ASC, confidence DESC")
    suspend fun getLemmaMappingsWithPrefix(prefix: String): List<LemmaMapEntity>
    
    @Query("SELECT * FROM lemma_map WHERE word_form_normalized_ultra = :normalizedWord ORDER BY confidence DESC")
    suspend fun getAllLemmaMappingsByUltraNormalized(normalizedWord: String): List<LemmaMapEntity>
}