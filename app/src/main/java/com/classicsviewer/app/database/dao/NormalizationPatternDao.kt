package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.classicsviewer.app.database.entities.NormalizationPatternEntity

@Dao
interface NormalizationPatternDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(patterns: List<NormalizationPatternEntity>)

    @Query("SELECT * FROM normalization_patterns WHERE language = :language ORDER BY priority ASC")
    suspend fun getPatternsForLanguage(language: String): List<NormalizationPatternEntity>

    @Query("SELECT * FROM normalization_patterns WHERE package_id = :packageId ORDER BY language, priority ASC")
    suspend fun getPatternsForPackage(packageId: Long): List<NormalizationPatternEntity>

    @Query("DELETE FROM normalization_patterns WHERE package_id = :packageId")
    suspend fun deleteByPackageId(packageId: Long)

    @Query("SELECT COUNT(*) FROM normalization_patterns WHERE language = :language")
    suspend fun countPatternsForLanguage(language: String): Int

    @Query("DELETE FROM normalization_patterns")
    suspend fun deleteAll()
}
