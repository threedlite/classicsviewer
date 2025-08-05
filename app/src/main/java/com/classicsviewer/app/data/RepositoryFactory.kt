package com.classicsviewer.app.data

import android.content.Context
import com.classicsviewer.app.BuildConfig

object RepositoryFactory {
    private var repository: DataRepository? = null
    
    fun getRepository(context: Context): DataRepository {
        if (repository == null) {
            repository = if (BuildConfig.USE_MOCK_DATA) {
                MockDataRepository()
            } else {
                PerseusRepository(context)
            }
        }
        return repository!!
    }
}