package com.classicsviewer.app.vocabulary

import android.content.Context
import org.json.JSONArray

/**
 * Persists which words the learner has matched in a perfect round, per
 * language, as a JSON array of headwords in SharedPreferences. Headwords are
 * unique within a list (verified by the build script and on load); lemmas are
 * not, so they cannot serve as keys.
 *
 * Deliberately not in UserDatabase: no Room entity or version change.
 */
class VocabularyProgress(context: Context) {

    companion object {
        private const val PREFS = "vocabulary_progress"
        private const val KEY_MASTERED = "mastered_"
    }

    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun mastered(language: String): Set<String> {
        val json = prefs.getString(KEY_MASTERED + language, null) ?: return emptySet()
        return try {
            val array = JSONArray(json)
            val set = HashSet<String>(array.length())
            for (i in 0 until array.length()) set.add(array.getString(i))
            set
        } catch (e: Exception) {
            android.util.Log.e("VocabularyProgress", "Unreadable progress for $language: ${e.message}")
            emptySet()
        }
    }

    fun addMastered(language: String, headwords: Collection<String>) {
        val merged = mastered(language) + headwords
        val array = JSONArray()
        merged.forEach { array.put(it) }
        prefs.edit().putString(KEY_MASTERED + language, array.toString()).apply()
    }

    fun clear(language: String) {
        prefs.edit().remove(KEY_MASTERED + language).apply()
    }
}
