package com.classicsviewer.app.utils

import android.content.Context
import android.content.SharedPreferences

object PreferencesManager {
    private const val PREFS_NAME = "ClassicsViewerPrefs"
    private const val KEY_FONT_SIZE = "font_size"
    private const val KEY_LAST_ACTIVITY = "last_activity"
    private const val KEY_LAST_EXTRAS = "last_extras_"
    private const val KEY_INVERT_COLORS = "invert_colors"
    private const val KEY_SHOW_WORD_UNDERLINES = "show_word_underlines"
    
    private fun getPrefs(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }
    
    // Font size preferences
    fun getFontSize(context: Context): Float {
        return getPrefs(context).getFloat(KEY_FONT_SIZE, 22f)
    }
    
    fun setFontSize(context: Context, size: Float) {
        getPrefs(context).edit().putFloat(KEY_FONT_SIZE, size).apply()
    }
    
    // Color inversion preference
    fun getInvertColors(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_INVERT_COLORS, true)
    }
    
    fun setInvertColors(context: Context, invert: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_INVERT_COLORS, invert).apply()
    }
    
    // Word underline preference
    fun getShowWordUnderlines(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_SHOW_WORD_UNDERLINES, false)
    }
    
    fun setShowWordUnderlines(context: Context, show: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_SHOW_WORD_UNDERLINES, show).apply()
    }
    
    // Navigation state persistence
    fun saveNavigationState(context: Context, activityName: String, extras: Map<String, String>) {
        val prefs = getPrefs(context).edit()
        prefs.putString(KEY_LAST_ACTIVITY, activityName)
        
        // Clear previous extras
        getPrefs(context).all.keys
            .filter { it.startsWith(KEY_LAST_EXTRAS) }
            .forEach { prefs.remove(it) }
        
        // Save new extras
        extras.forEach { (key, value) ->
            prefs.putString("$KEY_LAST_EXTRAS$key", value)
        }
        
        prefs.apply()
    }
    
    fun getLastActivity(context: Context): String? {
        return getPrefs(context).getString(KEY_LAST_ACTIVITY, null)
    }
    
    fun getLastExtras(context: Context): Map<String, String> {
        val extras = mutableMapOf<String, String>()
        val prefs = getPrefs(context)
        
        prefs.all.entries
            .filter { it.key.startsWith(KEY_LAST_EXTRAS) }
            .forEach { entry ->
                val key = entry.key.removePrefix(KEY_LAST_EXTRAS)
                val value = entry.value as? String
                if (value != null) {
                    extras[key] = value
                }
            }
        
        return extras
    }
    
    fun clearNavigationState(context: Context) {
        val prefs = getPrefs(context).edit()
        prefs.remove(KEY_LAST_ACTIVITY)
        
        // Clear all extras
        getPrefs(context).all.keys
            .filter { it.startsWith(KEY_LAST_EXTRAS) }
            .forEach { prefs.remove(it) }
        
        prefs.apply()
    }
}