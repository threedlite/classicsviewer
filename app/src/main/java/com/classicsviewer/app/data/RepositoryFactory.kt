package com.classicsviewer.app.data

import android.content.Context

object RepositoryFactory {
    private var repository: DataRepository? = null
    
    fun getRepository(context: Context): DataRepository {
        if (repository == null) {
            repository = PerseusRepository(context)
        }
        return repository!!
    }
}