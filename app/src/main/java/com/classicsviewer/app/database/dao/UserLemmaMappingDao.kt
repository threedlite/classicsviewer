package com.classicsviewer.app.database.dao

import androidx.room.*
import com.classicsviewer.app.database.entities.UserLemmaMappingEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface UserLemmaMappingDao {
    @Query("""
        SELECT ulm.* FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE (ulm.word_form = :word OR ulm.word_form_normalized_ultra = :normalizedWord) 
        AND ulm.language = :language
        AND udp.is_active = 1
        ORDER BY ulm.confidence DESC
        LIMIT 1
    """)
    suspend fun getMappingForWord(
        word: String, 
        normalizedWord: String, 
        language: String
    ): UserLemmaMappingEntity?
    
    @Query("""
        SELECT ulm.* FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE (ulm.word_form = :word OR ulm.word_form_normalized_ultra = :normalizedWord) 
        AND ulm.language = :language
        AND udp.is_active = 1
        ORDER BY ulm.confidence DESC
    """)
    suspend fun getAllMappingsForWord(
        word: String, 
        normalizedWord: String, 
        language: String
    ): List<UserLemmaMappingEntity>
    
    @Query("""
        SELECT ulm.* FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE (ulm.lemma = :lemma OR ulm.lemma_normalized_ultra = :normalizedLemma) 
        AND ulm.language = :language
        AND udp.is_active = 1
        ORDER BY ulm.word_form
    """)
    suspend fun getMappingsForLemma(
        lemma: String,
        normalizedLemma: String,
        language: String
    ): List<UserLemmaMappingEntity>
    
    @Query("""
        SELECT ulm.* FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE ulm.language = :language AND udp.is_active = 1
        ORDER BY ulm.word_form
    """)
    fun getAllMappingsForLanguage(language: String): Flow<List<UserLemmaMappingEntity>>
    
    @Query("""
        SELECT ulm.* FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE udp.is_active = 1
        ORDER BY ulm.created_at DESC
    """)
    fun getAllMappings(): Flow<List<UserLemmaMappingEntity>>
    
    @Query("""
        SELECT COUNT(*) FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE ulm.language = :language AND udp.is_active = 1
    """)
    suspend fun getMappingCount(language: String): Int
    
    @Query("""
        SELECT COUNT(*) FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE udp.is_active = 1
    """)
    suspend fun getTotalMappingCount(): Int
    
    @Query("""
        SELECT COUNT(DISTINCT ulm.lemma) FROM user_lemma_mappings ulm
        JOIN user_dictionary_packages udp ON ulm.package_id = udp.id
        WHERE ulm.language = :language AND udp.is_active = 1
    """)
    suspend fun getUniqueLemmaCount(language: String): Int
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMappings(mappings: List<UserLemmaMappingEntity>)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMapping(mapping: UserLemmaMappingEntity): Long
    
    @Update
    suspend fun updateMapping(mapping: UserLemmaMappingEntity)
    
    @Delete
    suspend fun deleteMapping(mapping: UserLemmaMappingEntity)
    
    @Query("DELETE FROM user_lemma_mappings")
    suspend fun deleteAllMappings()
    
    @Query("DELETE FROM user_lemma_mappings WHERE package_id = :packageId")
    suspend fun deleteMappingsByPackageId(packageId: Long)
    
    @Transaction
    suspend fun replaceAllMappings(mappings: List<UserLemmaMappingEntity>) {
        deleteAllMappings()
        insertMappings(mappings)
    }
}