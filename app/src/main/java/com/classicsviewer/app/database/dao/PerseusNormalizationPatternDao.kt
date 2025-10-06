package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Query
import com.classicsviewer.app.database.entities.PerseusNormalizationPatternEntity

@Dao
interface PerseusNormalizationPatternDao {
    @Query("SELECT * FROM normalization_patterns WHERE language = :language ORDER BY priority ASC")
    suspend fun getPatternsForLanguage(language: String): List<PerseusNormalizationPatternEntity>

    @Query("SELECT COUNT(*) FROM normalization_patterns WHERE language = :language")
    suspend fun countPatternsForLanguage(language: String): Int
}
