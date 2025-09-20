package com.classicsviewer.app.utils

import android.app.Activity
import android.content.Intent
import com.classicsviewer.app.*

object NavigationHelper {
    const val EXTRA_NAVIGATION_PATH = "navigation_path"
    
    fun buildNavigationPath(activity: Activity): String {
        val currentPath = activity.intent.getStringExtra(EXTRA_NAVIGATION_PATH) ?: ""
        val separator = if (currentPath.isEmpty()) "" else " > "
        
        return when (activity) {
            is MainActivity -> "Home"
            is AuthorListActivity -> {
                val language = activity.intent.getStringExtra("language_name") ?: ""
                "$currentPath$separator$language"
            }
            is WorkListActivity -> {
                val author = activity.intent.getStringExtra("author_name") ?: ""
                "$currentPath$separator$author"
            }
            is BookListActivity -> {
                val work = activity.intent.getStringExtra("work_title") ?: ""
                "$currentPath$separator$work"
            }
            is TextViewerActivity -> {
                val book = activity.intent.getStringExtra("book_number") ?: ""
                "$currentPath${separator}Book $book"
            }
            else -> currentPath
        }
    }
    
    fun addNavigationPath(intent: Intent, activity: Activity) {
        intent.putExtra(EXTRA_NAVIGATION_PATH, buildNavigationPath(activity))
    }
}