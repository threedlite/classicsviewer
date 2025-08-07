package com.classicsviewer.app.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.classicsviewer.app.database.dao.BookmarkDao
import com.classicsviewer.app.database.entities.BookmarkEntity

@Database(
    entities = [
        BookmarkEntity::class
    ],
    version = 4,
    exportSchema = true
)
abstract class UserDatabase : RoomDatabase() {
    abstract fun bookmarkDao(): BookmarkDao
    
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
                .fallbackToDestructiveMigration() // For now, just recreate on schema change
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