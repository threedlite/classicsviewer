package com.classicsviewer.app.database.dao

import androidx.room.*
import com.classicsviewer.app.database.entities.UserDictionaryLemmaEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface UserDictionaryDao {
    @Query("""
        SELECT udl.* FROM user_dictionary_lemmas udl
        JOIN user_dictionary_packages udp ON udl.package_id = udp.id
        WHERE (udl.lemma = :lemma OR udl.lemma_normalized_ultra = :normalizedLemma) 
        AND udl.language = :language
        AND udp.is_active = 1
        ORDER BY udl.created_at DESC
    """)
    suspend fun getEntriesForLemma(
        lemma: String, 
        normalizedLemma: String, 
        language: String
    ): List<UserDictionaryLemmaEntity>
    
    @Query("""
        SELECT udl.* FROM user_dictionary_lemmas udl
        JOIN user_dictionary_packages udp ON udl.package_id = udp.id
        WHERE udl.language = :language
        AND udp.is_active = 1
        ORDER BY udl.lemma
    """)
    fun getAllEntriesForLanguage(language: String): Flow<List<UserDictionaryLemmaEntity>>
    
    @Query("""
        SELECT udl.* FROM user_dictionary_lemmas udl
        JOIN user_dictionary_packages udp ON udl.package_id = udp.id
        WHERE udp.is_active = 1
        ORDER BY udl.created_at DESC
    """)
    fun getAllEntries(): Flow<List<UserDictionaryLemmaEntity>>
    
    @Query("""
        SELECT COUNT(*) FROM user_dictionary_lemmas udl
        JOIN user_dictionary_packages udp ON udl.package_id = udp.id
        WHERE udl.language = :language AND udp.is_active = 1
    """)
    suspend fun getLemmaCount(language: String): Int

    @Query("SELECT COUNT(*) FROM user_dictionary_lemmas")
    suspend fun getTotalLemmaCountAnyPackage(): Int
    
    @Query("""
        SELECT COUNT(*) FROM user_dictionary_lemmas udl
        JOIN user_dictionary_packages udp ON udl.package_id = udp.id
        WHERE udp.is_active = 1
    """)
    suspend fun getTotalLemmaCount(): Int
    
    @Query("""
        SELECT DISTINCT udl.import_file_name FROM user_dictionary_lemmas udl
        JOIN user_dictionary_packages udp ON udl.package_id = udp.id
        WHERE udp.is_active = 1
        LIMIT 1
    """)
    suspend fun getCurrentDictionaryFileName(): String?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLemmas(entries: List<UserDictionaryLemmaEntity>)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLemma(entry: UserDictionaryLemmaEntity): Long
    
    @Update
    suspend fun updateLemma(entry: UserDictionaryLemmaEntity)
    
    @Delete
    suspend fun deleteLemma(entry: UserDictionaryLemmaEntity)
    
    @Query("DELETE FROM user_dictionary_lemmas")
    suspend fun deleteAllLemmas()
    
    @Query("DELETE FROM user_dictionary_lemmas WHERE package_id = :packageId")
    suspend fun deleteLemmasByPackageId(packageId: Long)
    
    @Transaction
    suspend fun replaceAllLemmas(entries: List<UserDictionaryLemmaEntity>) {
        deleteAllLemmas()
        insertLemmas(entries)
    }
}