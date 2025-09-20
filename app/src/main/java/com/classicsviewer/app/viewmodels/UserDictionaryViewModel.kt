package com.classicsviewer.app.viewmodels

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.classicsviewer.app.repository.UserDictionaryRepository
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.first

class UserDictionaryViewModel(application: Application) : AndroidViewModel(application) {
    
    private val repository = UserDictionaryRepository(application)
    
    private val _dictionaryInfo = MutableLiveData<UserDictionaryRepository.DictionaryInfo?>()
    val dictionaryInfo: LiveData<UserDictionaryRepository.DictionaryInfo?> = _dictionaryInfo
    
    private val _importState = MutableLiveData<ImportState>()
    val importState: LiveData<ImportState> = _importState
    
    private val _isLoading = MutableLiveData(false)
    val isLoading: LiveData<Boolean> = _isLoading
    
    sealed class ImportState {
        object Idle : ImportState()
        data class Importing(
            val progress: Int = 0,
            val message: String = "Importing dictionary..."
        ) : ImportState()
        data class Success(
            val lemmaCount: Int,
            val mappingCount: Int,
            val warnings: List<String> = emptyList()
        ) : ImportState()
        data class Error(val message: String) : ImportState()
    }
    
    init {
        loadDictionaryInfo()
    }
    
    fun loadDictionaryInfo() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                _dictionaryInfo.value = repository.getCurrentDictionaryInfo()
            } catch (e: Exception) {
                _dictionaryInfo.value = null
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun importDictionary(uri: Uri) {
        viewModelScope.launch {
            _importState.value = ImportState.Importing()
            _isLoading.value = true
            
            try {
                val result = repository.importDictionary(uri) { progress, message ->
                    // Progress callback - post to main thread
                    viewModelScope.launch {
                        _importState.value = ImportState.Importing(progress, message)
                    }
                }
                
                if (result.success) {
                    _importState.value = ImportState.Success(
                        lemmaCount = result.lemmaCount,
                        mappingCount = result.mappingCount,
                        warnings = result.warnings
                    )
                    // Reload dictionary info after successful import
                    loadDictionaryInfo()
                } else {
                    _importState.value = ImportState.Error(
                        result.errors.firstOrNull() ?: "Import failed"
                    )
                }
            } catch (e: Exception) {
                _importState.value = ImportState.Error(
                    e.message ?: "Unknown error during import"
                )
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun clearDictionary() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                repository.clearAllData()
                _dictionaryInfo.value = null
                _importState.value = ImportState.Idle
            } catch (e: Exception) {
                _importState.value = ImportState.Error(
                    "Failed to clear dictionary: ${e.message}"
                )
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun resetImportState() {
        _importState.value = ImportState.Idle
    }
    
    suspend fun getAllPackages(): List<com.classicsviewer.app.database.entities.UserDictionaryPackageEntity> {
        return repository.getAllPackages().first()
    }
    
    suspend fun getActivePackage() = repository.getActivePackage()
    
    suspend fun setActivePackage(packageId: Long) {
        repository.setActivePackage(packageId)
    }
}