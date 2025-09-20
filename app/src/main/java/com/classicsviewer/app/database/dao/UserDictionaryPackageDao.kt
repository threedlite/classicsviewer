package com.classicsviewer.app.database.dao

import androidx.room.*
import com.classicsviewer.app.database.entities.UserDictionaryPackageEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface UserDictionaryPackageDao {
    @Query("SELECT * FROM user_dictionary_packages ORDER BY import_date DESC")
    fun getAllPackages(): Flow<List<UserDictionaryPackageEntity>>
    
    @Query("SELECT * FROM user_dictionary_packages WHERE is_active = 1 LIMIT 1")
    suspend fun getActivePackage(): UserDictionaryPackageEntity?
    
    @Query("SELECT id FROM user_dictionary_packages WHERE is_active = 1 LIMIT 1")
    suspend fun getActivePackageId(): Long?
    
    @Query("SELECT * FROM user_dictionary_packages WHERE id = :packageId")
    suspend fun getPackageById(packageId: Long): UserDictionaryPackageEntity?
    
    @Insert
    suspend fun insertPackage(packageEntity: UserDictionaryPackageEntity): Long
    
    @Update
    suspend fun updatePackage(packageEntity: UserDictionaryPackageEntity)
    
    @Delete
    suspend fun deletePackage(packageEntity: UserDictionaryPackageEntity)
    
    @Query("DELETE FROM user_dictionary_packages WHERE id = :packageId")
    suspend fun deletePackageById(packageId: Long)
    
    @Transaction
    suspend fun setActivePackage(packageId: Long) {
        // Deactivate all packages
        deactivateAllPackages()
        // Activate the selected package
        activatePackage(packageId)
    }
    
    @Query("UPDATE user_dictionary_packages SET is_active = 0")
    suspend fun deactivateAllPackages()
    
    @Query("UPDATE user_dictionary_packages SET is_active = 1 WHERE id = :packageId")
    suspend fun activatePackage(packageId: Long)
    
    @Query("SELECT COUNT(*) FROM user_dictionary_packages")
    suspend fun getPackageCount(): Int
    
    @Query("""
        UPDATE user_dictionary_packages 
        SET total_lemmas = :totalLemmas, 
            total_mappings = :totalMappings,
            greek_lemmas = :greekLemmas,
            latin_lemmas = :latinLemmas
        WHERE id = :packageId
    """)
    suspend fun updatePackageStats(
        packageId: Long,
        totalLemmas: Int,
        totalMappings: Int,
        greekLemmas: Int,
        latinLemmas: Int
    )
}