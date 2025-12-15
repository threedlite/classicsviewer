package com.classicsviewer.app.utils

import android.content.Context
import android.content.SharedPreferences
import com.classicsviewer.app.models.CustomLanguageConfig
import com.google.gson.Gson

object PreferencesManager {
    private const val PREFS_NAME = "ClassicsViewerPrefs"
    private const val KEY_FONT_SIZE = "font_size"
    private const val KEY_LAST_ACTIVITY = "last_activity"
    private const val KEY_LAST_EXTRAS = "last_extras_"
    private const val KEY_INVERT_COLORS = "invert_colors"
    private const val KEY_SHOW_WORD_UNDERLINES = "show_word_underlines"
    private const val KEY_EXTERNAL_DATABASE_URI = "external_database_uri"
    private const val KEY_EXTERNAL_DATABASE_COPIED_TIME = "external_database_copied_time"
    private const val KEY_OCCURRENCE_LIMIT = "occurrence_limit"
    private const val KEY_USE_SINAITICUS_FONT = "use_sinaiticus_font"
    private const val KEY_CUSTOM_LANGUAGES = "custom_languages"
    private const val KEY_SUPPRESSED_LANGUAGES = "suppressed_languages"
    private const val KEY_HAS_RUN_AUTO_DETECT_LANGUAGES = "has_run_auto_detect_languages"
    private const val KEY_HAS_FIXED_LANGUAGE_ORDER = "has_fixed_language_order"
    private const val KEY_WRAP_INTERLINEAR = "wrap_interlinear"
    private const val KEY_USE_FULL_DATABASE = "use_full_database"
    private const val KEY_FULL_AUDIO_INSTALLED = "full_audio_installed"

    private val gson = Gson()
    
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
    
    // Occurrence limit preference
    fun getOccurrenceLimit(context: Context): Int {
        return getPrefs(context).getInt(KEY_OCCURRENCE_LIMIT, 500)
    }
    
    fun setOccurrenceLimit(context: Context, limit: Int) {
        getPrefs(context).edit().putInt(KEY_OCCURRENCE_LIMIT, limit).apply()
    }
    
    // Sinaiticus font preference
    fun getUseSinaiticusFont(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_USE_SINAITICUS_FONT, false)
    }

    fun setUseSinaiticusFont(context: Context, use: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_USE_SINAITICUS_FONT, use).apply()
    }

    // Wrap interlinear text preference
    fun getWrapInterlinear(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_WRAP_INTERLINEAR, true)
    }

    fun setWrapInterlinear(context: Context, wrap: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_WRAP_INTERLINEAR, wrap).apply()
    }

    // Full database preference (on-demand downloaded via Play Asset Delivery)
    fun getUseFullDatabase(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_USE_FULL_DATABASE, false)
    }

    fun setUseFullDatabase(context: Context, useFullDb: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_USE_FULL_DATABASE, useFullDb).apply()
    }

    // Full audio preference (on-demand downloaded via Play Asset Delivery)
    fun getFullAudioInstalled(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_FULL_AUDIO_INSTALLED, false)
    }

    fun setFullAudioInstalled(context: Context, installed: Boolean) {
        getPrefs(context).edit().putBoolean(KEY_FULL_AUDIO_INSTALLED, installed).apply()
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
    
    // External database URI preferences
    fun getExternalDatabaseUri(context: Context): String? {
        return getPrefs(context).getString(KEY_EXTERNAL_DATABASE_URI, null)
    }
    
    fun setExternalDatabaseUri(context: Context, uri: String) {
        getPrefs(context).edit().putString(KEY_EXTERNAL_DATABASE_URI, uri).apply()
    }
    
    fun clearExternalDatabaseUri(context: Context) {
        getPrefs(context).edit().remove(KEY_EXTERNAL_DATABASE_URI).apply()
    }
    
    fun setExternalDatabaseCopiedTime(context: Context, time: Long) {
        getPrefs(context).edit().putLong(KEY_EXTERNAL_DATABASE_COPIED_TIME, time).apply()
    }
    
    fun getExternalDatabaseCopiedTime(context: Context): Long {
        return getPrefs(context).getLong(KEY_EXTERNAL_DATABASE_COPIED_TIME, 0L)
    }

    // Custom language preferences - using JSONArray to avoid TypeToken issues
    fun getCustomLanguages(context: Context): List<CustomLanguageConfig> {
        val json = getPrefs(context).getString(KEY_CUSTOM_LANGUAGES, null)
        android.util.Log.d("PreferencesManager", "Loading custom languages, JSON: $json")
        if (json.isNullOrEmpty()) {
            android.util.Log.d("PreferencesManager", "No custom languages found in preferences")
            return emptyList()
        }

        return try {
            // Parse JSON manually to avoid TypeToken issues with ProGuard
            val jsonArray = org.json.JSONArray(json)
            val languages = mutableListOf<CustomLanguageConfig>()

            for (i in 0 until jsonArray.length()) {
                val jsonObject = jsonArray.getJSONObject(i)
                val language = CustomLanguageConfig(
                    id = jsonObject.getString("id"),
                    displayName = jsonObject.getString("displayName"),
                    color = jsonObject.getInt("color")
                )
                languages.add(language)
                android.util.Log.d("PreferencesManager", "Loaded language: id=${language.id}, name=${language.displayName}, color=${language.color}")
            }

            android.util.Log.d("PreferencesManager", "Successfully loaded ${languages.size} custom languages")
            languages
        } catch (e: Exception) {
            android.util.Log.e("PreferencesManager", "Failed to deserialize custom languages: ${e.message}", e)
            android.util.Log.e("PreferencesManager", "JSON that failed: $json")
            emptyList()
        }
    }

    fun addCustomLanguage(context: Context, language: CustomLanguageConfig) {
        android.util.Log.d("PreferencesManager", "Adding custom language: ${language.id} - ${language.displayName}")
        val languages = getCustomLanguages(context).toMutableList()

        // Find the position of existing language with same ID (if any)
        val existingIndex = languages.indexOfFirst { it.id == language.id }

        if (existingIndex >= 0) {
            // Update in place to preserve order
            languages[existingIndex] = language
            android.util.Log.d("PreferencesManager", "Updated existing language at position $existingIndex")
        } else {
            // New language - add to end
            languages.add(language)
            android.util.Log.d("PreferencesManager", "Added new language at end")
        }

        android.util.Log.d("PreferencesManager", "Updated languages list size: ${languages.size}")
        saveCustomLanguages(context, languages)

        // Remove from suppressed list (user is manually adding it back)
        removeSuppressedLanguage(context, language.id)
    }

    fun removeCustomLanguage(context: Context, languageId: String) {
        val languages = getCustomLanguages(context).toMutableList()
        languages.removeAll { it.id == languageId }
        saveCustomLanguages(context, languages)

        // Add to suppressed list so it won't be auto-detected again
        addSuppressedLanguage(context, languageId)
    }

    fun setCustomLanguagesOrder(context: Context, languages: List<CustomLanguageConfig>) {
        saveCustomLanguages(context, languages)
    }

    fun reorderLanguagesByPreferredOrder(context: Context, preferredOrder: List<String>) {
        val languages = getCustomLanguages(context).toMutableList()

        // Sort by preferred order, with unknown languages at the end
        languages.sortWith(compareBy { language ->
            val index = preferredOrder.indexOf(language.id)
            if (index >= 0) index else Int.MAX_VALUE
        })

        saveCustomLanguages(context, languages)
        android.util.Log.d("PreferencesManager", "Reordered languages by preferred order")
    }

    private fun saveCustomLanguages(context: Context, languages: List<CustomLanguageConfig>) {
        android.util.Log.d("PreferencesManager", "Saving ${languages.size} custom languages")

        // Use JSONArray to avoid Gson/ProGuard issues
        val jsonArray = org.json.JSONArray()
        for (language in languages) {
            val jsonObject = org.json.JSONObject()
            jsonObject.put("id", language.id)
            jsonObject.put("displayName", language.displayName)
            jsonObject.put("color", language.color)
            jsonArray.put(jsonObject)
        }

        val json = jsonArray.toString()
        android.util.Log.d("PreferencesManager", "JSON to save: $json")

        val editor = getPrefs(context).edit()
        editor.putString(KEY_CUSTOM_LANGUAGES, json)

        // Use apply() for better reliability
        editor.apply()

        // Verify the save by immediately reading back with commit to force sync
        getPrefs(context).edit().commit() // Force sync

        val savedJson = getPrefs(context).getString(KEY_CUSTOM_LANGUAGES, null)
        android.util.Log.d("PreferencesManager", "Verification read - saved JSON: $savedJson")

        if (savedJson != json) {
            android.util.Log.e("PreferencesManager", "WARNING: Saved JSON doesn't match! Expected: $json, Got: $savedJson")
        }

        // Double-check by calling getCustomLanguages
        val loadedLanguages = getCustomLanguages(context)
        android.util.Log.d("PreferencesManager", "Verification: loaded ${loadedLanguages.size} languages after save")
    }

    // Auto-detect languages flag
    fun hasRunAutoDetectLanguages(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_HAS_RUN_AUTO_DETECT_LANGUAGES, false)
    }

    fun setHasRunAutoDetectLanguages(context: Context) {
        getPrefs(context).edit().putBoolean(KEY_HAS_RUN_AUTO_DETECT_LANGUAGES, true).apply()
    }

    // Language order migration flag
    fun hasFixedLanguageOrder(context: Context): Boolean {
        return getPrefs(context).getBoolean(KEY_HAS_FIXED_LANGUAGE_ORDER, false)
    }

    fun setHasFixedLanguageOrder(context: Context) {
        getPrefs(context).edit().putBoolean(KEY_HAS_FIXED_LANGUAGE_ORDER, true).apply()
    }

    // Suppressed languages (explicitly deleted, won't be auto-added)
    fun getSuppressedLanguages(context: Context): Set<String> {
        val json = getPrefs(context).getString(KEY_SUPPRESSED_LANGUAGES, null)
        if (json.isNullOrEmpty()) {
            return emptySet()
        }

        return try {
            val jsonArray = org.json.JSONArray(json)
            val suppressed = mutableSetOf<String>()
            for (i in 0 until jsonArray.length()) {
                suppressed.add(jsonArray.getString(i))
            }
            suppressed
        } catch (e: Exception) {
            android.util.Log.e("PreferencesManager", "Failed to load suppressed languages: ${e.message}", e)
            emptySet()
        }
    }

    fun addSuppressedLanguage(context: Context, languageId: String) {
        val suppressed = getSuppressedLanguages(context).toMutableSet()
        suppressed.add(languageId)
        saveSuppressedLanguages(context, suppressed)
        android.util.Log.d("PreferencesManager", "Added $languageId to suppressed languages")
    }

    fun removeSuppressedLanguage(context: Context, languageId: String) {
        val suppressed = getSuppressedLanguages(context).toMutableSet()
        suppressed.remove(languageId)
        saveSuppressedLanguages(context, suppressed)
        android.util.Log.d("PreferencesManager", "Removed $languageId from suppressed languages")
    }

    private fun saveSuppressedLanguages(context: Context, suppressed: Set<String>) {
        val jsonArray = org.json.JSONArray()
        for (languageId in suppressed) {
            jsonArray.put(languageId)
        }
        getPrefs(context).edit().putString(KEY_SUPPRESSED_LANGUAGES, jsonArray.toString()).apply()
    }
}