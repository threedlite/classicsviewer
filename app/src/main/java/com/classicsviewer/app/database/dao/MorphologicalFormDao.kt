package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.MorphologicalFormEntity

@Dao
interface MorphologicalFormDao {
    @Query("SELECT * FROM morphological_forms WHERE word_normalized = :wordNormalized")
    suspend fun getMorphologyForWord(wordNormalized: String): List<MorphologicalFormEntity>
    
    @Query("SELECT * FROM morphological_forms WHERE word_form = :wordForm")
    suspend fun getMorphologyForExactForm(wordForm: String): List<MorphologicalFormEntity>
    
    @Query("SELECT * FROM morphological_forms WHERE lemma = :lemma")
    suspend fun getAllFormsForLemma(lemma: String): List<MorphologicalFormEntity>
    
    @Query("SELECT morphology FROM morphological_forms WHERE word_form = :wordForm AND lemma = :lemma LIMIT 1")
    suspend fun getMorphologyDescription(wordForm: String, lemma: String): String?
}