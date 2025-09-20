package com.classicsviewer.app.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.classicsviewer.app.database.dao.BookmarkDao
import com.classicsviewer.app.database.dao.UserDictionaryDao
import com.classicsviewer.app.database.dao.UserLemmaMappingDao
import com.classicsviewer.app.database.dao.UserDictionaryPackageDao
import com.classicsviewer.app.database.entities.BookmarkEntity
import com.classicsviewer.app.database.entities.UserDictionaryLemmaEntity
import com.classicsviewer.app.database.entities.UserLemmaMappingEntity
import com.classicsviewer.app.database.entities.UserDictionaryPackageEntity

@Database(
    entities = [
        BookmarkEntity::class,
        UserDictionaryLemmaEntity::class,
        UserLemmaMappingEntity::class,
        UserDictionaryPackageEntity::class
    ],
    version = 7,
    exportSchema = true
)
abstract class UserDatabase : RoomDatabase() {
    abstract fun bookmarkDao(): BookmarkDao
    abstract fun userDictionaryDao(): UserDictionaryDao
    abstract fun userLemmaMappingDao(): UserLemmaMappingDao
    abstract fun userDictionaryPackageDao(): UserDictionaryPackageDao
    
    companion object {
        @Volatile
        private var INSTANCE: UserDatabase? = null
        
        fun getInstance(context: Context): UserDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    UserDatabase::class.java,
                    "user_data.db"
                )
                .fallbackToDestructiveMigration() // Just recreate on schema change
                .build()
                INSTANCE = instance
                instance
            }
        }
        
        fun destroyInstance() {
            INSTANCE?.close()
            INSTANCE = null
        }
    }
}